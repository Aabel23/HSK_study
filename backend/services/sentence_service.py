"""Sentence-order exercises and persisted results."""

from __future__ import annotations

import json
import random
from typing import Any

from backend.database import get_connection, utc_now
from backend.services import session_store
from backend.services.errors import InvalidOperationError, ResourceNotFoundError
from backend.services.session_store import SessionKind


SESSION = SessionKind(
    table="sentence_sessions",
    not_found="Không tìm thấy phiên luyện câu.",
    already_ended="Phiên luyện câu này đã kết thúc.",
    completed="Đã hoàn tất phiên luyện câu.",
)


def list_topics() -> list[str]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT DISTINCT topic FROM sentences WHERE topic IS NOT NULL ORDER BY topic"
        ).fetchall()
    return [row[0] for row in rows]


def list_levels() -> list[dict[str, Any]]:
    """Sentence counts per HSK level, for the level picker."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT hsk_level AS level, COUNT(*) AS total,
                   MIN(difficulty) AS min_tokens, MAX(difficulty) AS max_tokens
            FROM sentences
            GROUP BY hsk_level
            ORDER BY hsk_level
            """
        ).fetchall()
    return [dict(row) for row in rows]


def create_session(
    count: int,
    topic: str | None = None,
    hsk_level: str | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    conditions: list[str] = []
    parameters: list[Any] = []
    if topic:
        conditions.append("topic = ?")
        parameters.append(topic)
    if hsk_level:
        conditions.append("hsk_level = ?")
        parameters.append(hsk_level)
    if max_tokens:
        conditions.append("difficulty <= ?")
        parameters.append(max_tokens)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT id, hanzi, pinyin, meaning, topic, tokens_json, pinyin_tokens_json,
                   hsk_level, difficulty
            FROM sentences
            {where_clause}
            ORDER BY RANDOM()
            LIMIT ?
            """,
            [*parameters, count],
        ).fetchall()
        if not rows:
            raise InvalidOperationError("Không có câu phù hợp để tạo phiên luyện tập.")

    session_id = session_store.start(SESSION, total_items=len(rows))
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
                "hsk_level": row["hsk_level"],
                "difficulty": row["difficulty"],
                "tokens": pieces,
            }
        )
    return {"session_id": session_id, "items": items}


def record_attempt(
    session_id: int,
    sentence_id: int,
    ordered_positions: list[int],
) -> dict[str, Any]:
    with get_connection() as connection:
        session_store.require_open(connection, SESSION, session_id)
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
    return session_store.complete(
        SESSION, session_id, total_items, correct_items, incorrect_items
    )


def get_stats() -> dict[str, Any]:
    return session_store.attempt_stats(SESSION, "sentence_attempts")

