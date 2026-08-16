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
    response = client.post("/api/sentences/session", json={"count": 201})
    assert response.status_code == 422


def test_long_sentence_session_is_allowed(client):
    """A 100-sentence run is a supported study style, not a rejected request."""
    response = client.post("/api/sentences/session", json={"count": 100})
    assert response.status_code == 201
    # The corpus is smaller than the request, so the session holds what exists.
    assert 0 < len(response.json()["items"]) <= 100



def test_duplicate_clauses_are_graded_on_the_sentence_not_the_tiles(client):
    """这个饭馆又便宜又好吃。 has 又 twice, and both tiles look identical.

    Tapping the second 又 first builds exactly the right sentence out of a
    different set of positions. Grading on positions called that wrong and then
    showed the learner their own answer back as the correction.
    """
    import json

    from backend.database import get_connection

    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, tokens_json FROM sentences WHERE hanzi = ?",
            ("这个饭馆又便宜又好吃。",),
        ).fetchone()
    assert row, "câu mẫu phải có trong kho"
    tokens = json.loads(row["tokens_json"])

    # Swap the two identical 又 tiles: same sentence, different positions.
    duplicated = [i for i, token in enumerate(tokens) if tokens.count(token) > 1]
    assert len(duplicated) >= 2
    order = list(range(len(tokens)))
    order[duplicated[0]], order[duplicated[1]] = order[duplicated[1]], order[duplicated[0]]
    assert order != list(range(len(tokens)))
    assert [tokens[i] for i in order] == tokens

    session = client.post("/api/sentences/session", json={"count": 5}).json()
    response = client.post(
        "/api/sentences/attempt",
        json={
            "session_id": session["session_id"],
            "sentence_id": row["id"],
            "ordered_positions": order,
        },
    )
    assert response.status_code == 201
    assert response.json()["is_correct"] is True


def test_a_genuinely_wrong_order_is_still_wrong(client):
    import json

    from backend.database import get_connection

    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, tokens_json FROM sentences WHERE hanzi = ?",
            ("这个饭馆又便宜又好吃。",),
        ).fetchone()
    tokens = json.loads(row["tokens_json"])
    order = list(reversed(range(len(tokens))))

    session = client.post("/api/sentences/session", json={"count": 5}).json()
    response = client.post(
        "/api/sentences/attempt",
        json={
            "session_id": session["session_id"],
            "sentence_id": row["id"],
            "ordered_positions": order,
        },
    )
    assert response.json()["is_correct"] is False
