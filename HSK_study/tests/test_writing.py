def test_create_writing_session_and_attempt(client):
    response = client.post("/api/writing/session", json={"hsk_level": "1", "count": 5})
    assert response.status_code == 201
    data = response.json()
    assert len(data["characters"]) <= 5
    assert len(data["characters"]) > 0
    session_id = data["session_id"]
    character = data["characters"][0]["character"]

    attempt = client.post(
        "/api/writing/attempt",
        json={"session_id": session_id, "character": character, "mistakes": 1, "is_correct": True},
    )
    assert attempt.status_code == 201

    complete = client.post(
        f"/api/writing/session/{session_id}/complete",
        json={"total_items": len(data["characters"]), "correct_items": 1, "incorrect_items": 0},
    )
    assert complete.status_code == 200

    progress = client.get("/api/writing/progress")
    assert progress.status_code == 200
    assert progress.json()["practiced_count"] >= 1


def test_writing_session_requires_valid_level(client):
    response = client.post("/api/writing/session", json={"hsk_level": "9", "count": 5})
    assert response.status_code == 422
