"""HSK mock exam: paper layout, written + spoken scoring, and AI grading."""

from __future__ import annotations

import base64
import json

import pytest

from backend.services import gemini_service, hskk_service
from backend.settings import reset_settings_cache


EXPECTED_LAYOUT = {
    # Sơ cấp keeps all three official speaking parts.
    "beginner": {"counts": [15, 10, 2], "points": [2, 3, 20], "reading": 15},
    # Trung cấp drops part 2 (nhìn tranh kể chuyện) — no picture bank — and its
    # points move to part 3 so the speaking half still totals 100.
    "intermediate": {"counts": [10, 2], "points": [3, 35], "reading": 12},
}

FAKE_GEMINI_REPLY = {
    "transcript": "我很高兴认识你",
    "score_percent": 82,
    "verdict": "Nhắc lại đúng nguyên văn, phát âm khá tốt.",
    "strengths": ["Đủ chữ, không thiếu từ nào"],
    "fixes": ["Chữ 兴 đọc thành thanh 4, đúng phải là thanh 1"],
    "pronunciation_percent": 78,
    "content_percent": 95,
    "fluency_percent": 80,
}


@pytest.fixture()
def fake_gemini(monkeypatch):
    """Stand in for Gemini. Tests must never reach the live API."""
    calls: list[dict] = []

    def _generate_json(**kwargs):
        calls.append(kwargs)
        return dict(FAKE_GEMINI_REPLY)

    monkeypatch.setattr(gemini_service, "generate_json", _generate_json)
    monkeypatch.setattr(gemini_service, "is_configured", lambda: True)
    monkeypatch.setattr(hskk_service.gemini_service, "generate_json", _generate_json)
    monkeypatch.setattr(hskk_service.gemini_service, "is_configured", lambda: True)
    return calls


def test_levels_match_the_official_format(client):
    items = {item["code"]: item for item in client.get("/api/hskk/levels").json()["items"]}
    assert set(items) == set(EXPECTED_LAYOUT)

    for code, expected in EXPECTED_LAYOUT.items():
        level = items[code]
        assert [part["count"] for part in level["parts"]] == expected["counts"]
        assert [part["points_per_item"] for part in level["parts"]] == expected["points"]
        # The speaking half keeps the exam's real 100-point scale.
        assert level["speaking_points"] == 100
        assert level["reading"]["total_questions"] == expected["reading"]
        assert level["reading"]["total_points"] == 100
        assert level["total_items"] == expected["reading"] + sum(expected["counts"])


def test_intermediate_explains_the_dropped_picture_part(client):
    items = {item["code"]: item for item in client.get("/api/hskk/levels").json()["items"]}
    skipped = items["intermediate"]["skipped_parts"]
    assert [entry["part"] for entry in skipped] == [2]
    assert skipped[0]["reason"]
    assert items["beginner"]["skipped_parts"] == []


def test_session_bundles_a_reading_section_and_the_speaking_parts(client):
    paper = client.post("/api/hskk/session", json={"exam_level": "beginner"}).json()
    reading = paper["reading"]

    assert reading["max_score"] == 100
    assert reading["total_questions"] == 15
    assert paper["quiz_session_id"] > 0
    assert [part["question_type"] for part in reading["parts"]] == [
        "judge_true_false",
        "fill_in_blank_sentence",
        "multiple_choice_dialogue",
    ]

    ids = []
    for part in paper["parts"]:
        for item in part["items"]:
            ids.append(item["question_id"])
            if part["kind"] in {"repeat", "answer"}:
                assert item["audio_text"] == item["hanzi"]
            else:
                assert item["audio_text"] is None
    assert len(ids) == len(set(ids))
    assert paper["total_items"] == 15 + 27


def _reading_questions(paper):
    for part in paper["reading"]["parts"]:
        for question in part["questions"]:
            yield part, question


def test_the_paper_never_carries_the_reading_answer_key(client):
    """A learner with devtools open must not be able to read the answers."""
    paper = client.post("/api/hskk/session", json={"exam_level": "beginner"}).json()
    serialised = json.dumps(paper["reading"], ensure_ascii=False)
    assert '"answer"' not in serialised
    assert "explanation_vi" not in serialised

    for part, question in _reading_questions(paper):
        assert "answer" not in question
        if part["question_type"] == "multiple_choice_dialogue":
            assert [option["key"] for option in question["options"]] == ["A", "B", "C"]


def test_fill_in_the_blank_offers_one_spare_word(client):
    paper = client.post("/api/hskk/session", json={"exam_level": "intermediate"}).json()
    part = next(
        entry
        for entry in paper["reading"]["parts"]
        if entry["question_type"] == "fill_in_blank_sentence"
    )
    assert len(part["word_bank"]) == part["question_count"] + 1
    assert [word["key"] for word in part["word_bank"]] == ["A", "B", "C", "D", "E", "F"]


def test_reading_answers_are_graded_on_the_server(client):
    paper = client.post("/api/hskk/session", json={"exam_level": "beginner"}).json()
    session_id = paper["session_id"]
    part, question = next(
        (part, question)
        for part, question in _reading_questions(paper)
        if part["question_type"] == "judge_true_false"
    )

    # Claiming an answer is right does not make it so: both values are tried and
    # exactly one of them is accepted.
    verdicts = []
    for answer in (True, False):
        response = client.post(
            "/api/hskk/reading",
            json={
                "session_id": session_id,
                "question_index": question["question_index"],
                "question_id": question["id"],
                "answer": answer,
            },
        )
        assert response.status_code == 201
        body = response.json()
        verdicts.append(body["is_correct"])
        assert body["explanation_vi"]
    assert sorted(verdicts) == [False, True]


def test_reordering_is_only_correct_in_the_right_order(client):
    paper = client.post("/api/hskk/session", json={"exam_level": "intermediate"}).json()
    part, question = next(
        (part, question)
        for part, question in _reading_questions(paper)
        if part["question_type"] == "sentence_reordering"
    )
    body = {
        "session_id": paper["session_id"],
        "question_index": question["question_index"],
        "question_id": question["id"],
        "answer": question["words_zh"],
    }
    first = client.post("/api/hskk/reading", json=body).json()
    body["answer"] = list(reversed(question["words_zh"]))
    second = client.post("/api/hskk/reading", json=body).json()
    # The clauses are shuffled per paper, so at most one of the two can be right.
    assert not (first["is_correct"] and second["is_correct"])
    assert " → " in first["correct_answer"]


def test_reading_and_spoken_halves_are_scored_separately(client):
    paper = client.post("/api/hskk/session", json={"exam_level": "beginner"}).json()
    session_id = paper["session_id"]

    # Answer the reading half, alternating a real answer with a deliberate miss.
    for index, (part, question) in enumerate(_reading_questions(paper)):
        if part["question_type"] == "judge_true_false":
            answer: object = index % 2 == 0
        elif part["question_type"] == "fill_in_blank_sentence":
            answer = part["word_bank"][index % len(part["word_bank"])]["word_zh"]
        else:
            answer = question["options"][index % len(question["options"])]["text_zh"]
        client.post(
            "/api/hskk/reading",
            json={
                "session_id": session_id,
                "question_index": index,
                "question_id": question["id"],
                "answer": answer,
            },
        )
    # Every spoken answer graded "good".
    for part in paper["parts"]:
        for item in part["items"]:
            client.post(
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

    summary = client.post(f"/api/hskk/session/{session_id}/complete").json()
    assert summary["percent"] == 100  # speaking
    # The reading marks depend on which answers happened to be right, so only the
    # bookkeeping is asserted here — the grading itself is covered above.
    assert 0 <= summary["written_percent"] <= 100
    assert summary["overall_percent"] == pytest.approx(
        (summary["percent"] + summary["written_percent"]) / 2, abs=0.1
    )
    assert summary["answered_items"] == 15 + 27


def test_ai_grading_scores_and_stores_the_feedback(client, fake_gemini):
    paper = client.post("/api/hskk/session", json={"exam_level": "beginner"}).json()
    first = paper["parts"][0]
    item = first["items"][0]

    response = client.post(
        "/api/hskk/grade",
        json={
            "session_id": paper["session_id"],
            "part": first["part"],
            "question_index": item["question_index"],
            "question_id": item["question_id"],
            "transcript": "我很高兴认识你",
            "audio_base64": base64.b64encode(b"\x00" * 64).decode(),
            "audio_mime_type": "audio/wav",
            "spoken_seconds": 7,
        },
    )
    assert response.status_code == 201
    graded = response.json()
    assert graded["percent"] == 82
    assert graded["score"] == pytest.approx(first["points_per_item"] * 0.82, abs=0.01)
    assert graded["transcript"] == "我很高兴认识你"
    assert graded["expected"] == item["hanzi"]
    assert graded["fixes"]
    assert graded["graded_by"] == "ai"

    # The prompt must carry the expected sentence, otherwise the model has
    # nothing to grade the repeat against.
    prompt = fake_gemini[0]["prompt"]
    assert item["hanzi"] in prompt
    assert "NGHE VÀ NHẮC LẠI" in prompt
    assert fake_gemini[0]["audio_base64"]

    # The summary rounds to one decimal for display.
    summary = client.post(f"/api/hskk/session/{paper['session_id']}/complete").json()
    assert summary["score"] == round(first["points_per_item"] * 0.82, 1)


def test_grading_works_from_the_speech_log_alone(client, fake_gemini):
    """No audio upload: the browser's transcript is enough to be graded."""
    paper = client.post("/api/hskk/session", json={"exam_level": "beginner"}).json()
    item = paper["parts"][0]["items"][0]

    response = client.post(
        "/api/hskk/grade",
        json={
            "session_id": paper["session_id"],
            "part": 1,
            "question_index": item["question_index"],
            "question_id": item["question_id"],
            "transcript": "我很高兴认识你",
            "spoken_seconds": 6,
        },
    )
    assert response.status_code == 201

    prompt = fake_gemini[0]["prompt"]
    assert "我很高兴认识你" in prompt
    assert "Bản gỡ băng" in prompt
    # Without audio the model must be told not to invent tone mistakes.
    assert "KHÔNG có file ghi âm" in prompt
    assert fake_gemini[0]["audio_base64"] is None


def test_grading_needs_either_a_transcript_or_audio(client, fake_gemini):
    paper = client.post("/api/hskk/session", json={"exam_level": "beginner"}).json()
    item = paper["parts"][0]["items"][0]

    response = client.post(
        "/api/hskk/grade",
        json={
            "session_id": paper["session_id"],
            "part": 1,
            "question_index": item["question_index"],
            "question_id": item["question_id"],
            "transcript": "   ",
        },
    )
    assert response.status_code == 409
    assert "ghi âm lại" in response.json()["detail"]
    assert fake_gemini == []


def test_each_part_kind_gets_its_own_rubric(client, fake_gemini):
    paper = client.post("/api/hskk/session", json={"exam_level": "beginner"}).json()
    for part in paper["parts"]:
        item = part["items"][0]
        client.post(
            "/api/hskk/grade",
            json={
                "session_id": paper["session_id"],
                "part": part["part"],
                "question_index": item["question_index"],
                "question_id": item["question_id"],
                "transcript": "我说了一些话",
                "audio_base64": base64.b64encode(b"\x00" * 64).decode(),
                "spoken_seconds": 20,
            },
        )
    prompts = [call["prompt"] for call in fake_gemini]
    assert "NGHE VÀ NHẮC LẠI" in prompts[0]
    assert "NGHE VÀ TRẢ LỜI" in prompts[1]
    assert "NÓI THEO ĐỀ CHO SẴN" in prompts[2]
    # The open-ended part must tell the model the minimum sentence count.
    assert "5 câu" in prompts[2]


def test_ai_grading_is_refused_cleanly_without_a_key(client, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    reset_settings_cache()
    paper = client.post("/api/hskk/session", json={"exam_level": "beginner"}).json()
    item = paper["parts"][0]["items"][0]

    response = client.post(
        "/api/hskk/grade",
        json={
            "session_id": paper["session_id"],
            "part": 1,
            "question_index": item["question_index"],
            "question_id": item["question_id"],
            "transcript": "我很高兴认识你",
        },
    )
    assert response.status_code == 409
    assert "GEMINI_API_KEY" in response.json()["detail"]
    # Self-assessment must still work so the exam is never blocked.
    assert paper["ai_grading"] is False


def test_gemini_reply_wrapped_in_a_code_fence_is_still_read():
    fenced = "```json\n" + json.dumps(FAKE_GEMINI_REPLY, ensure_ascii=False) + "\n```"
    parsed = gemini_service._parse_json_object(fenced)
    assert parsed["score_percent"] == 82


def test_credentials_pick_the_right_auth_header(monkeypatch):
    """Only OAuth tokens use Bearer; AI Studio keys come in several shapes.

    Treating everything that was not `AIza…` as OAuth made valid `AQ.…` API keys
    fail with a 401, which is what this guards against.
    """
    from backend.settings import get_settings

    for api_key in ("AIzaSyFakeKeyForTests", "AQ.Ab8RNfakeapikeyfortests"):
        monkeypatch.setenv("GEMINI_API_KEY", api_key)
        reset_settings_cache()
        assert get_settings().gemini_uses_bearer_token is False

    monkeypatch.setenv("GEMINI_API_KEY", "ya29.fake-oauth-access-token")
    reset_settings_cache()
    assert get_settings().gemini_uses_bearer_token is True


def test_a_retired_model_reports_how_to_fix_it(monkeypatch):
    """Google withdrew gemini-2.0-flash; a 404 must name the model and the knob."""
    import urllib.error

    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyFakeKeyForTests")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.0-flash")
    reset_settings_cache()

    def _boom(*args, **kwargs):
        raise urllib.error.HTTPError("url", 404, "Not Found", {}, None)

    monkeypatch.setattr(gemini_service.urllib.request, "urlopen", _boom)
    with pytest.raises(Exception) as caught:
        gemini_service.generate_json(system_instruction="x", prompt="y")
    assert "gemini-2.0-flash" in str(caught.value)
    assert "GEMINI_MODEL" in str(caught.value)


def test_rerating_the_same_question_replaces_it(client):
    paper = client.post("/api/hskk/session", json={"exam_level": "beginner"}).json()
    session_id = paper["session_id"]
    body = {
        "session_id": session_id,
        "part": 1,
        "question_index": 0,
        "question_id": paper["parts"][0]["items"][0]["question_id"],
        "self_rating": "bad",
        "spoken_seconds": 3,
    }
    assert client.post("/api/hskk/answer", json=body).json()["score"] == 0.4
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
    # 30 of 100 on speaking, 0 on written -> 15 overall.
    assert stats["last_percent"] == 15.0
    assert stats["recent"][0]["exam_level"] == "beginner"
