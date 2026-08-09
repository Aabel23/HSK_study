"""Sentence-order exercises and persisted results."""

from __future__ import annotations

import json
import random
from typing import Any

from backend.database import get_connection, utc_now
from backend.services.errors import InvalidOperationError, ResourceNotFoundError


def list_topics() -> list[str]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT DISTINCT topic FROM sentences WHERE topic IS NOT NULL ORDER BY topic"
        ).fetchall()
    return [row[0] for row in rows]


def create_session(count: int, topic: str | None = None) -> dict[str, Any]:
    conditions = "WHERE topic = ?" if topic else ""
    parameters: list[Any] = [topic] if topic else []
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT id, hanzi, pinyin, meaning, topic, tokens_json, pinyin_tokens_json
            FROM sentences
            {conditions}
            ORDER BY RANDOM()
            LIMIT ?
            """,
            [*parameters, count],
        ).fetchall()
        if not rows:
            raise InvalidOperationError("Không có câu phù hợp để tạo phiên luyện tập.")
        cursor = connection.execute(
            "INSERT INTO sentence_sessions (started_at, total_items) VALUES (?, ?)",
            (utc_now(), len(rows)),
        )
        session_id = cursor.lastrowid

    items = []
    for row in rows:
        tokens = json.loads(row["tokens_json"])
        pinyin_tokens = json.loads(row["pinyin_tokens_json"])
        if len(tokens) != len(pinyin_tokens):
            raise InvalidOperationError("Dữ liệu câu không đồng nhất.")
        pieces = [
            {
                "token_id": f"{row['id']}-{position}",
                "position": position,
                "text": token,
                "pinyin": pinyin_tokens[position],
            }
            for position, token in enumerate(tokens)
        ]
        random.shuffle(pieces)
        if len(pieces) > 1 and [item["position"] for item in pieces] == list(range(len(pieces))):
            pieces.append(pieces.pop(0))
        items.append(
            {
                "id": row["id"],
                "hanzi": row["hanzi"],
                "pinyin": row["pinyin"],
                "meaning": row["meaning"],
                "topic": row["topic"],
                "tokens": pieces,
            }
        )
    return {"session_id": session_id, "items": items}


def _get_open_session(connection: Any, session_id: int) -> Any:
    session = connection.execute(
        "SELECT * FROM sentence_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not session:
        raise ResourceNotFoundError("Không tìm thấy phiên luyện câu.")
    if session["ended_at"]:
        raise InvalidOperationError("Phiên luyện câu này đã kết thúc.")
    return session


def record_attempt(
    session_id: int,
    sentence_id: int,
    ordered_positions: list[int],
) -> dict[str, Any]:
    with get_connection() as connection:
        _get_open_session(connection, session_id)
        sentence = connection.execute(
            """
            SELECT id, hanzi, pinyin, meaning, tokens_json
            FROM sentences WHERE id = ?
            """,
            (sentence_id,),
        ).fetchone()
        if not sentence:
            raise ResourceNotFoundError("Không tìm thấy câu luyện tập.")
        token_count = len(json.loads(sentence["tokens_json"]))
        expected_positions = list(range(token_count))
        if len(ordered_positions) != token_count or sorted(ordered_positions) != expected_positions:
            raise InvalidOperationError("Thứ tự gửi lên phải chứa đủ mỗi cụm từ đúng một lần.")
        is_correct = ordered_positions == expected_positions
        connection.execute(
            """
            INSERT INTO sentence_attempts (
                session_id, sentence_id, ordered_positions_json, is_correct, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                sentence_id,
                json.dumps(ordered_positions),
                int(is_correct),
                utc_now(),
            ),
        )
    return {
        "session_id": session_id,
        "sentence_id": sentence_id,
        "is_correct": is_correct,
        "answer": {
            "hanzi": sentence["hanzi"],
            "pinyin": sentence["pinyin"],
            "meaning": sentence["meaning"],
        },
    }


def complete_session(
    session_id: int,
    total_items: int,
    correct_items: int,
    incorrect_items: int,
) -> dict[str, Any]:
    with get_connection() as connection:
        _get_open_session(connection, session_id)
        connection.execute(
            """
            UPDATE sentence_sessions
            SET ended_at = ?, total_items = ?, correct_items = ?, incorrect_items = ?
            WHERE id = ?
            """,
            (utc_now(), total_items, correct_items, incorrect_items, session_id),
        )
    return {"message": "Đã hoàn tất phiên luyện câu.", "session_id": session_id}


def get_stats() -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(DISTINCT s.id) AS sessions,
                   COALESCE(SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END), 0) AS correct,
                   COALESCE(SUM(CASE WHEN a.is_correct = 0 THEN 1 ELSE 0 END), 0) AS incorrect
            FROM sentence_sessions s
            LEFT JOIN sentence_attempts a ON a.session_id = s.id
            """
        ).fetchone()
    correct = row["correct"] or 0
    incorrect = row["incorrect"] or 0
    total_attempts = correct + incorrect
    return {
        "sessions": row["sessions"] or 0,
        "correct": correct,
        "incorrect": incorrect,
        "accuracy": round(correct / total_attempts * 100, 1) if total_attempts else 0,
    }

