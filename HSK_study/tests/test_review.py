def first_queue_item(client):
    response = client.get("/api/review/queue", params={"limit": 5})
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"], "review queue should be seeded with new words"
    return payload


def test_queue_returns_new_words_when_nothing_is_due(client):
    payload = first_queue_item(client)
    assert payload["due_count"] == 0
    assert payload["new_count"] > 0
    assert len(payload["items"]) == 5


def test_submit_review_schedules_next_due_date(client):
    item = first_queue_item(client)["items"][0]
    response = client.post(
        "/api/review/submit", json={"vocabulary_id": item["id"], "rating": "good"}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["repetitions"] == 1
    assert result["interval_days"] == 1.0
    assert result["due_at"]
    assert result["status"] == "learning"


def test_easy_grows_interval_faster_than_hard(client):
    items = first_queue_item(client)["items"]
    easy_id, hard_id = items[0]["id"], items[1]["id"]
    for _ in range(3):
        client.post("/api/review/submit", json={"vocabulary_id": easy_id, "rating": "easy"})
        client.post("/api/review/submit", json={"vocabulary_id": hard_id, "rating": "hard"})
    easy = client.get(f"/api/vocabulary/{easy_id}").json()
    hard = client.get(f"/api/vocabulary/{hard_id}").json()
    assert easy["interval_days"] > hard["interval_days"]
    assert easy["ease_factor"] > hard["ease_factor"]


def test_again_resets_repetitions_and_counts_a_lapse(client):
    item = first_queue_item(client)["items"][0]
    client.post("/api/review/submit", json={"vocabulary_id": item["id"], "rating": "good"})
    client.post("/api/review/submit", json={"vocabulary_id": item["id"], "rating": "good"})
    response = client.post(
        "/api/review/submit", json={"vocabulary_id": item["id"], "rating": "again"}
    )
    result = response.json()
    assert result["repetitions"] == 0
    assert result["lapses"] == 1
    assert result["status"] == "learning"


def test_invalid_rating_is_rejected(client):
    item = first_queue_item(client)["items"][0]
    response = client.post(
        "/api/review/submit", json={"vocabulary_id": item["id"], "rating": "perfect"}
    )
    assert response.status_code == 422


def test_review_on_missing_word_returns_404(client):
    response = client.post(
        "/api/review/submit", json={"vocabulary_id": 999999, "rating": "good"}
    )
    assert response.status_code == 404


def test_stats_and_forecast(client):
    item = first_queue_item(client)["items"][0]
    client.post("/api/review/submit", json={"vocabulary_id": item["id"], "rating": "good"})
    stats = client.get("/api/review/stats").json()
    assert stats["total_reviews"] == 1
    assert stats["in_rotation"] == 1
    assert stats["retention_percentage"] == 100.0
    assert len(stats["forecast"]) == 14

    forecast = client.get("/api/review/forecast", params={"days": 7}).json()
    assert len(forecast["items"]) == 7


def test_favorites_and_notes_round_trip(client):
    item = first_queue_item(client)["items"][0]
    assert client.post(
        "/api/review/favorite", json={"vocabulary_id": item["id"], "is_favorite": True}
    ).status_code == 200
    assert client.post(
        "/api/review/note", json={"vocabulary_id": item["id"], "note": "Nhớ thanh điệu"}
    ).status_code == 200

    favorites = client.get("/api/review/favorites").json()["items"]
    assert [entry["id"] for entry in favorites] == [item["id"]]
    assert favorites[0]["note"] == "Nhớ thanh điệu"

    filtered = client.get("/api/vocabulary", params={"favorites_only": True}).json()
    assert filtered["total"] == 1

    client.post("/api/review/favorite", json={"vocabulary_id": item["id"], "is_favorite": False})
    assert client.get("/api/review/favorites").json()["items"] == []


def test_vocabulary_sort_is_whitelisted(client):
    assert client.get("/api/vocabulary", params={"sort": "pinyin"}).status_code == 200
    assert client.get("/api/vocabulary", params={"sort": "id; DROP TABLE"}).status_code == 422
