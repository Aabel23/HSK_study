"""Grammar lessons: the rule, why Vietnamese learners get it wrong, and drills.

Every other drill in the app trains vocabulary — recognising a word, hearing it,
typing it. None of them teach why 我学习在学校 is wrong, which is the mistake a
Vietnamese learner actually makes, because Vietnamese puts the place after the
verb and Chinese does not.

So each lesson carries four things: the pattern, an explanation written against
Vietnamese habits, a `pitfall` naming the specific error, and exercises. The
lesson text ships as ``scripts/data/grammar.json`` and is seeded into the
database; the learner's own progress lives in a separate table so importing new
lessons never disturbs it.
"""

from __future__ import annotations

import json
from typing import Any

from backend.database import get_connection, utc_now
from backend.services import streak_service
from backend.services.errors import InvalidOperationError, ResourceNotFoundError


XP_CORRECT = 8

#: What a learner has to get right before a point counts as mastered. Three is
#: the same threshold the flashcard flow uses, so "đã thuộc" means one thing
#: across the whole app.
MASTERY_THRESHOLD = 3

_SUMMARY_FIELDS = """
    g.id, g.code, g.hsk_level, g.title_vi, g.pattern_zh, g.summary_vi,
    COALESCE(p.status, 'new') AS status,
    COALESCE(p.practice_count, 0) AS practice_count,
    COALESCE(p.correct_count, 0) AS correct_count,
    COALESCE(p.incorrect_count, 0) AS incorrect_count,
    p.last_practiced_at
"""


def _decode(row: Any, *, full: bool) -> dict[str, Any]:
    point = dict(row)
    if full:
        point["examples"] = json.loads(row["examples_json"] or "[]")
        # The answer key is stripped before the exercise reaches the browser;
        # `check_exercise` is what decides right or wrong.
        point["exercises"] = [
            {
                "index": index,
                "question_zh": exercise.get("question_zh", ""),
                "options": exercise.get("options", []),
            }
            for index, exercise in enumerate(json.loads(row["exercises_json"] or "[]"))
        ]
        point.pop("examples_json", None)
        point.pop("exercises_json", None)
    return point


def list_points(hsk_level: str | None = None, status: str | None = None) -> dict[str, Any]:
    conditions: list[str] = []
    parameters: list[Any] = []
    if hsk_level:
        conditions.append("g.hsk_level = ?")
        parameters.append(hsk_level)
    if status:
        conditions.append("COALESCE(p.status, 'new') = ?")
        parameters.append(status)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT {_SUMMARY_FIELDS}
            FROM grammar_points g
            LEFT JOIN grammar_progress p ON p.grammar_id = g.id
            {where_clause}
            ORDER BY g.hsk_level, g.sort_order, g.id
            """,
            parameters,
        ).fetchall()
        levels = connection.execute(
            """
            SELECT g.hsk_level AS level,
                   COUNT(*) AS total,
                   SUM(CASE WHEN p.status = 'mastered' THEN 1 ELSE 0 END) AS mastered
            FROM grammar_points g
            LEFT JOIN grammar_progress p ON p.grammar_id = g.id
            GROUP BY g.hsk_level
            ORDER BY g.hsk_level
            """
        ).fetchall()

    return {
        "items": [_decode(row, full=False) for row in rows],
        "total": len(rows),
        "levels": [
            {
                "level": row["level"],
                "total": row["total"],
                "mastered": row["mastered"] or 0,
            }
            for row in levels
        ],
    }


def get_point(code: str) -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            f"""
            SELECT {_SUMMARY_FIELDS}, g.explanation_vi, g.pitfall_vi,
                   g.examples_json, g.exercises_json
            FROM grammar_points g
            LEFT JOIN grammar_progress p ON p.grammar_id = g.id
            WHERE g.code = ?
            """,
            (code,),
        ).fetchone()
    if not row:
        raise ResourceNotFoundError("Không tìm thấy điểm ngữ pháp này.")
    return _decode(row, full=True)


def _exercise(connection: Any, code: str, index: int) -> tuple[int, dict[str, Any]]:
    row = connection.execute(
        "SELECT id, exercises_json FROM grammar_points WHERE code = ?", (code,)
    ).fetchone()
    if not row:
        raise ResourceNotFoundError("Không tìm thấy điểm ngữ pháp này.")
    exercises = json.loads(row["exercises_json"] or "[]")
    if not 0 <= index < len(exercises):
        raise InvalidOperationError("Bài tập này không tồn tại.")
    return row["id"], exercises[index]


def check_exercise(code: str, index: int, answer: str) -> dict[str, Any]:
    """Grade one exercise and fold the result into the point's progress."""
    with get_connection() as connection:
        grammar_id, exercise = _exercise(connection, code, index)
        expected = str(exercise.get("answer", ""))
        is_correct = str(answer).strip() == expected.strip()

        # One more correct answer than the threshold cannot demote a point, so
        # the status only ever moves forward.
        correct_so_far = connection.execute(
            "SELECT correct_count FROM grammar_progress WHERE grammar_id = ?",
            (grammar_id,),
        ).fetchone()
        total_correct = (correct_so_far["correct_count"] if correct_so_far else 0) + (
            1 if is_correct else 0
        )
        status = "mastered" if total_correct >= MASTERY_THRESHOLD else "learning"

        now = utc_now()
        connection.execute(
            """
            INSERT INTO grammar_progress (
                grammar_id, status, practice_count, correct_count, incorrect_count,
                last_practiced_at, created_at, updated_at
            ) VALUES (?, ?, 1, ?, ?, ?, ?, ?)
            ON CONFLICT(grammar_id) DO UPDATE SET
                status = excluded.status,
                practice_count = grammar_progress.practice_count + 1,
                correct_count = grammar_progress.correct_count + excluded.correct_count,
                incorrect_count = grammar_progress.incorrect_count + excluded.incorrect_count,
                last_practiced_at = excluded.last_practiced_at,
                updated_at = excluded.updated_at
            """,
            (
                grammar_id, status, 1 if is_correct else 0, 0 if is_correct else 1,
                now, now, now,
            ),
        )

    streak_service.record_activity(correct=is_correct, xp=XP_CORRECT if is_correct else 0)
    return {
        "code": code,
        "index": index,
        "is_correct": is_correct,
        "correct_answer": expected,
        "explanation_vi": exercise.get("explanation_vi", ""),
        "status": status,
    }


def get_stats() -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM grammar_points) AS total,
                (SELECT COUNT(*) FROM grammar_progress WHERE status = 'mastered') AS mastered,
                (SELECT COUNT(*) FROM grammar_progress WHERE status = 'learning') AS learning,
                (SELECT COALESCE(SUM(correct_count), 0) FROM grammar_progress) AS correct,
                (SELECT COALESCE(SUM(incorrect_count), 0) FROM grammar_progress) AS incorrect
            """
        ).fetchone()
    total = row["total"] or 0
    correct = row["correct"] or 0
    incorrect = row["incorrect"] or 0
    attempts = correct + incorrect
    mastered = row["mastered"] or 0
    return {
        "total": total,
        "mastered": mastered,
        "learning": row["learning"] or 0,
        "correct": correct,
        "incorrect": incorrect,
        "accuracy": round(correct / attempts * 100, 1) if attempts else 0.0,
        "completion": round(mastered / total * 100, 1) if total else 0.0,
    }
