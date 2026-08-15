"""Grammar lessons: listing, the answer key staying server-side, and progress."""

from __future__ import annotations

import json

from backend.database import get_connection, utc_now


def _add_point(code: str = "test-point", hsk_level: str = "1") -> None:
    now = utc_now()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO grammar_points (
                code, hsk_level, title_vi, pattern_zh, summary_vi, explanation_vi,
                pitfall_vi, examples_json, exercises_json, sort_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            ON CONFLICT(code) DO NOTHING
            """,
            (
                code,
                hsk_level,
                "Câu với 是",
                "A + 是 + B",
                "Dùng 是 để nối hai danh từ.",
                "Giải thích dài hơn.",
                "Không dùng 是 trước tính từ.",
                json.dumps(
                    [{"hanzi": "我是学生。", "pinyin": "Wǒ shì xuésheng.", "vi": "Tôi là học sinh."}],
                    ensure_ascii=False,
                ),
                json.dumps(
                    [
                        {
                            "question_zh": "我(  )学生。",
                            "options": ["是", "很", "在"],
                            "answer": "是",
                            "explanation_vi": "学生 là danh từ.",
                        }
                    ],
                    ensure_ascii=False,
                ),
                now,
                now,
            ),
        )


def test_listing_reports_totals_per_level(client):
    _add_point()
    response = client.get("/api/grammar/points")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert any(entry["total"] >= 1 for entry in payload["levels"])


def test_level_filter_only_returns_that_level(client):
    _add_point(code="test-l1", hsk_level="1")
    _add_point(code="test-l4", hsk_level="4")
    items = client.get("/api/grammar/points", params={"hsk_level": "4"}).json()["items"]
    assert items
    assert {item["hsk_level"] for item in items} == {"4"}


def test_detail_never_ships_the_answer_key(client):
    _add_point()
    detail = client.get("/api/grammar/points/test-point").json()
    assert detail["explanation_vi"]
    assert detail["examples"][0]["pinyin"]
    exercise = detail["exercises"][0]
    assert exercise["options"] == ["是", "很", "在"]
    # The whole point of grading server-side: nothing in the payload says which
    # option is right.
    assert "answer" not in exercise
    assert "explanation_vi" not in exercise


def test_checking_a_right_answer_advances_progress(client):
    _add_point()
    outcome = client.post(
        "/api/grammar/points/test-point/check", json={"index": 0, "answer": "是"}
    ).json()
    assert outcome["is_correct"] is True
    assert outcome["correct_answer"] == "是"
    assert outcome["explanation_vi"]

    listed = client.get("/api/grammar/points").json()["items"]
    point = next(item for item in listed if item["code"] == "test-point")
    assert point["status"] == "learning"
    assert point["correct_count"] == 1


def test_checking_a_wrong_answer_still_reveals_the_reason(client):
    _add_point()
    outcome = client.post(
        "/api/grammar/points/test-point/check", json={"index": 0, "answer": "很"}
    ).json()
    assert outcome["is_correct"] is False
    assert outcome["correct_answer"] == "是"
    assert outcome["explanation_vi"]


def test_three_correct_answers_master_the_point(client):
    _add_point()
    for _ in range(3):
        client.post("/api/grammar/points/test-point/check", json={"index": 0, "answer": "是"})
    stats = client.get("/api/grammar/stats").json()
    assert stats["mastered"] >= 1


def test_unknown_point_and_exercise_are_rejected(client):
    _add_point()
    assert client.get("/api/grammar/points/khong-ton-tai").status_code == 404
    # In range for the schema, but this point only has one exercise. The app
    # maps InvalidOperationError to 409 throughout.
    assert (
        client.post(
            "/api/grammar/points/test-point/check", json={"index": 5, "answer": "是"}
        ).status_code
        == 409
    )
    # Out of range for the schema, rejected before the service is reached.
    assert (
        client.post(
            "/api/grammar/points/test-point/check", json={"index": 999, "answer": "是"}
        ).status_code
        == 422
    )
