def create_sentence_session(client, count=6, topic=None):
    response = client.post("/api/sentences/session", json={"count": count, "topic": topic})
    assert response.status_code == 201
    return response.json()


def test_sentence_topics_and_seed_data(client):
    topics = client.get("/api/sentences/topics")
    assert topics.status_code == 200
    assert "Trường học" in topics.json()["items"]
    session = create_sentence_session(client, 20)
    assert len(session["items"]) == 20


def test_create_sentence_session_has_unique_shuffled_items(client):
    data = create_sentence_session(client, 6)
    ids = [item["id"] for item in data["items"]]
    assert len(ids) == len(set(ids)) == 6
    for item in data["items"]:
        positions = [token["position"] for token in item["tokens"]]
        assert sorted(positions) == list(range(len(positions)))
        assert positions != sorted(positions)
        assert all(token["text"] and token["pinyin"] for token in item["tokens"])


def test_sentence_session_can_filter_topic(client):
    data = create_sentence_session(client, 10, "Ăn uống")
    assert data["items"]
    assert all(item["topic"] == "Ăn uống" for item in data["items"])


def test_record_correct_sentence_attempt(client):
    data = create_sentence_session(client, 1)
    item = data["items"][0]
    ordered_positions = sorted(token["position"] for token in item["tokens"])
    response = client.post("/api/sentences/attempt", json={
        "session_id": data["session_id"],
        "sentence_id": item["id"],
        "ordered_positions": ordered_positions,
    })
    assert response.status_code == 201
    assert response.json()["is_correct"] is True
    assert response.json()["answer"]["hanzi"] == item["hanzi"]


def test_record_incorrect_sentence_attempt_without_revealing_before_submit(client):
    data = create_sentence_session(client, 1)
    item = data["items"][0]
    ordered_positions = sorted(
        (token["position"] for token in item["tokens"]), reverse=True
    )
    response = client.post("/api/sentences/attempt", json={
        "session_id": data["session_id"],
        "sentence_id": item["id"],
        "ordered_positions": ordered_positions,
    })
    assert response.status_code == 201
    assert response.json()["is_correct"] is False


def test_reject_duplicate_or_missing_sentence_positions(client):
    data = create_sentence_session(client, 1)
    item = data["items"][0]
    response = client.post("/api/sentences/attempt", json={
        "session_id": data["session_id"],
        "sentence_id": item["id"],
        "ordered_positions": [0] * len(item["tokens"]),
    })
    assert response.status_code == 409


def test_complete_sentence_session_and_stats(client):
    data = create_sentence_session(client, 1)
    item = data["items"][0]
    client.post("/api/sentences/attempt", json={
        "session_id": data["session_id"],
        "sentence_id": item["id"],
        "ordered_positions": sorted(token["position"] for token in item["tokens"]),
    })
    complete = client.post(
        f"/api/sentences/session/{data['session_id']}/complete",
        json={"total_items": 1, "correct_items": 1, "incorrect_items": 0},
    )
    assert complete.status_code == 200
    stats = client.get("/api/sentences/stats").json()
    assert stats["sessions"] == 1
    assert stats["correct"] == 1
    assert stats["accuracy"] == 100


def test_invalid_sentence_count(client):
    response = client.post("/api/sentences/session", json={"count": 21})
    assert response.status_code == 422

