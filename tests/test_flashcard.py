def create_session(client, count=10):
    response = client.post("/api/flashcard/session", json={"count": count, "include_mastered": False})
    assert response.status_code == 201
    return response.json()


def test_create_flashcard_session_with_unique_items(client):
    data = create_session(client, 10)
    assert len(data["items"]) == 10
    assert len({item["id"] for item in data["items"]}) == 10


def test_flashcard_session_honours_hsk_level(client):
    """The level picker has to reach the session, not just the page header."""
    response = client.post(
        "/api/flashcard/session",
        json={"count": 15, "include_mastered": True, "hsk_level": "3"},
    )
    assert response.status_code == 201
    items = response.json()["items"]
    assert items
    assert all(item["hsk_level"] == "3" for item in items)


def test_long_flashcard_session_is_allowed(client):
    """A 100-card run in one sitting is a supported study style."""
    response = client.post(
        "/api/flashcard/session", json={"count": 100, "include_mastered": True}
    )
    assert response.status_code == 201
    assert len(response.json()["items"]) == 100


def test_flashcard_count_above_ceiling_is_rejected(client):
    response = client.post("/api/flashcard/session", json={"count": 201})
    assert response.status_code == 422


def test_review_forgot(client):
    session = create_session(client, 1)
    item_id = session["items"][0]["id"]
    response = client.post("/api/flashcard/review", json={
        "session_id": session["session_id"], "vocabulary_id": item_id, "result": "forgot",
    })
    assert response.status_code == 200
    progress = response.json()["progress"]
    assert progress["status"] == "review"
    assert progress["review_count"] == 1
    assert progress["incorrect_count"] == 1


def test_review_hard(client):
    session = create_session(client, 1)
    item_id = session["items"][0]["id"]
    response = client.post("/api/flashcard/review", json={
        "session_id": session["session_id"], "vocabulary_id": item_id, "result": "hard",
    })
    assert response.status_code == 200
    assert response.json()["progress"]["status"] == "learning"
    assert response.json()["progress"]["review_count"] == 1


def test_review_remembered_and_mastered_after_three(client):
    session = create_session(client, 1)
    item_id = session["items"][0]["id"]
    payload = {"session_id": session["session_id"], "vocabulary_id": item_id, "result": "remembered"}
    first = client.post("/api/flashcard/review", json=payload)
    second = client.post("/api/flashcard/review", json=payload)
    third = client.post("/api/flashcard/review", json=payload)
    assert first.json()["progress"]["status"] == "learning"
    assert second.json()["progress"]["status"] == "learning"
    assert third.json()["progress"]["status"] == "mastered"
    assert third.json()["progress"]["correct_count"] == 3
    assert third.json()["progress"]["review_count"] == 3


def test_invalid_flashcard_result(client):
    session = create_session(client, 1)
    response = client.post("/api/flashcard/review", json={
        "session_id": session["session_id"],
        "vocabulary_id": session["items"][0]["id"],
        "result": "easy",
    })
    assert response.status_code == 422


def test_complete_flashcard_session(client):
    session = create_session(client, 2)
    response = client.post(
        f"/api/flashcard/session/{session['session_id']}/complete",
        json={"total_items": 2, "correct_items": 1, "incorrect_items": 1},
    )
    assert response.status_code == 200

