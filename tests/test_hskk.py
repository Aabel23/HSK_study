"""HSKK mock exam: paper layout, self-scoring and the result summary."""

from __future__ import annotations


EXPECTED_LAYOUT = {
    "beginner": {"total_items": 27, "counts": [15, 10, 2], "points": [2, 3, 20]},
    "intermediate": {"total_items": 14, "counts": [10, 2, 2], "points": [3, 17.5, 17.5]},
}


def test_levels_match_the_official_format(client):
    response = client.get("/api/hskk/levels")
    assert response.status_code == 200
    items = {item["code"]: item for item in response.json()["items"]}
    assert set(items) == set(EXPECTED_LAYOUT)

    for code, expected in EXPECTED_LAYOUT.items():
        level = items[code]
        assert level["total_items"] == expected["total_items"]
        assert [part["count"] for part in level["parts"]] == expected["counts"]
        assert [part["points_per_item"] for part in level["parts"]] == expected["points"]
        # Both levels are graded out of 100 like the real exam.
        assert level["total_points"] == 100


def test_session_builds_a_full_paper_with_hidden_audio_prompts(client):
    response = client.post("/api/hskk/session", json={"exam_level": "beginner"})
    assert response.status_code == 201
    paper = response.json()

    assert paper["total_items"] == 27
    assert paper["max_score"] == 100
    assert paper["prep_seconds"] == 420

    ids = []
    for part in paper["parts"]:
        for item in part["items"]:
            ids.append(item["question_id"])
            assert item["hanzi"] and item["pinyin"] and item["vi"]
            # Parts 1-2 are heard; part 3 is read off the paper.
            if part["kind"] in {"repeat", "answer"}:
                assert item["audio_text"] == item["hanzi"]
            else:
                assert item["audio_text"] is None
    # No question may repeat inside one paper.
    assert len(ids) == len(set(ids))


def test_intermediate_paper_has_describe_and_opinion_parts(client):
    paper = client.post("/api/hskk/session", json={"exam_level": "intermediate"}).json()
    kinds = [part["kind"] for part in paper["parts"]]
    assert kinds == ["repeat", "describe", "opinion"]
    assert all(part["items"][0]["hints"] for part in paper["parts"][1:])


def test_scoring_follows_the_self_rating_weights(client):
    paper = client.post("/api/hskk/session", json={"exam_level": "beginner"}).json()
    session_id = paper["session_id"]

    for part in paper["parts"]:
        for item in part["items"]:
            response = client.post(
                "/api/hskk/answer",
                json={
                    "session_id": session_id,
                    "part": part["part"],
                    "question_index": item["question_index"],
                    "question_id": item["question_id"],
                    "self_rating": "good",
                    "spoken_seconds": 5,
                },
            )
            assert response.status_code == 201
            assert response.json()["score"] == part["points_per_item"]

    summary = client.post(f"/api/hskk/session/{session_id}/complete").json()
    assert summary["score"] == 100
    assert summary["percent"] == 100
    assert summary["passed"] is True
    assert summary["answered_items"] == 27
    assert [part["part"] for part in summary["parts"]] == [1, 2, 3]


def test_partial_answers_and_rerating_the_same_question(client):
    paper = client.post("/api/hskk/session", json={"exam_level": "beginner"}).json()
    session_id = paper["session_id"]
    first = paper["parts"][0]

    body = {
        "session_id": session_id,
        "part": 1,
        "question_index": 0,
        "question_id": first["items"][0]["question_id"],
        "self_rating": "bad",
        "spoken_seconds": 3,
    }
    assert client.post("/api/hskk/answer", json=body).json()["score"] == 0.4
    # Re-recording the same question replaces the rating, it does not add a row.
    body["self_rating"] = "ok"
    assert client.post("/api/hskk/answer", json=body).json()["score"] == 1.2

    summary = client.post(f"/api/hskk/session/{session_id}/complete").json()
    assert summary["answered_items"] == 1
    assert summary["score"] == 1.2
    assert summary["passed"] is False


def test_a_submitted_exam_cannot_be_answered_again(client):
    paper = client.post("/api/hskk/session", json={"exam_level": "beginner"}).json()
    session_id = paper["session_id"]
    client.post(f"/api/hskk/session/{session_id}/complete")

    response = client.post(
        "/api/hskk/answer",
        json={
            "session_id": session_id,
            "part": 1,
            "question_index": 0,
            "question_id": "b1-01",
            "self_rating": "good",
        },
    )
    assert response.status_code == 409


def test_unknown_level_and_session_are_rejected(client):
    assert client.post("/api/hskk/session", json={"exam_level": "advanced"}).status_code == 422
    assert client.post("/api/hskk/session/999999/complete").status_code == 404


def test_stats_track_completed_exams(client):
    assert client.get("/api/hskk/stats").json()["sessions"] == 0

    paper = client.post("/api/hskk/session", json={"exam_level": "beginner"}).json()
    for item in paper["parts"][0]["items"]:
        client.post(
            "/api/hskk/answer",
            json={
                "session_id": paper["session_id"],
                "part": 1,
                "question_index": item["question_index"],
                "question_id": item["question_id"],
                "self_rating": "good",
            },
        )
    client.post(f"/api/hskk/session/{paper['session_id']}/complete")

    stats = client.get("/api/hskk/stats").json()
    assert stats["sessions"] == 1
    assert stats["last_percent"] == 30.0
    assert stats["best_percent"] == 30.0
    assert stats["recent"][0]["exam_level"] == "beginner"
