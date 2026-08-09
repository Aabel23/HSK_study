def create_matching(client, mode="meaning"):
    response = client.post("/api/matching/session", json={"mode": mode, "count": 6})
    assert response.status_code == 201
    return response.json()


def test_create_meaning_session_with_shuffled_lists(client):
    data = create_matching(client, "meaning")
    left_ids = [item["vocabulary_id"] for item in data["left_items"]]
    right_ids = [item["vocabulary_id"] for item in data["right_items"]]
    assert len(left_ids) == len(right_ids) == 6
    assert set(left_ids) == set(right_ids)
    assert left_ids != right_ids


def test_create_pinyin_session(client):
    data = create_matching(client, "pinyin")
    assert data["mode"] == "pinyin"
    assert len(data["left_items"]) == len(data["right_items"]) == 6


def test_record_correct_and_incorrect_attempts(client):
    data = create_matching(client)
    item_id = data["left_items"][0]["vocabulary_id"]
    base = {"session_id": data["session_id"], "vocabulary_id": item_id, "mode": "meaning"}
    correct = client.post("/api/matching/attempt", json={**base, "is_correct": True})
    incorrect = client.post("/api/matching/attempt", json={**base, "is_correct": False})
    assert correct.status_code == 201
    assert correct.json()["is_correct"] is True
    assert incorrect.status_code == 201
    assert incorrect.json()["is_correct"] is False


def test_invalid_matching_mode(client):
    response = client.post("/api/matching/session", json={"mode": "example", "count": 6})
    assert response.status_code == 422


def test_complete_matching_session(client):
    data = create_matching(client)
    response = client.post(
        f"/api/matching/session/{data['session_id']}/complete",
        json={"total_items": 6, "correct_items": 6, "incorrect_items": 2},
    )
    assert response.status_code == 200

