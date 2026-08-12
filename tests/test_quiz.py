def test_create_quiz_session_and_answer(client):
    response = client.post("/api/quiz/session", json={"hsk_level": "1", "count": 5})
    assert response.status_code == 201
    data = response.json()
    assert data["hsk_level"] == "1"
    assert len(data["questions"]) == 5
    session_id = data["session_id"]

    question = data["questions"][0]
    assert len(question["options"]) == 4
    assert any(opt["vocabulary_id"] == question["target_vocabulary_id"] for opt in question["options"])

    attempt = client.post(
        "/api/quiz/attempt",
        json={
            "session_id": session_id,
            "vocabulary_id": question["target_vocabulary_id"],
            "question_type": question["question_type"],
            "is_correct": True,
        },
    )
    assert attempt.status_code == 201

    complete = client.post(
        f"/api/quiz/session/{session_id}/complete",
        json={"total_items": 5, "correct_items": 1, "incorrect_items": 0},
    )
    assert complete.status_code == 200


def test_quiz_stats_endpoint(client):
    response = client.get("/api/quiz/stats")
    assert response.status_code == 200
    assert "accuracy" in response.json()
