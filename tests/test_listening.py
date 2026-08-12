def test_create_listening_session_and_answer(client):
    response = client.post(
        "/api/listening/session",
        json={"hsk_level": "2", "mode": "audio_to_meaning", "count": 4},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["mode"] == "audio_to_meaning"
    assert len(data["items"]) == 4
    session_id = data["session_id"]

    item = data["items"][0]
    assert item["audio_text"]
    assert len(item["options"]) == 4

    attempt = client.post(
        "/api/listening/attempt",
        json={
            "session_id": session_id,
            "vocabulary_id": item["target_vocabulary_id"],
            "mode": "audio_to_meaning",
            "is_correct": True,
        },
    )
    assert attempt.status_code == 201

    complete = client.post(
        f"/api/listening/session/{session_id}/complete",
        json={"total_items": 4, "correct_items": 1, "incorrect_items": 0},
    )
    assert complete.status_code == 200


def test_listening_stats_endpoint(client):
    response = client.get("/api/listening/stats")
    assert response.status_code == 200
    assert "accuracy" in response.json()
