"""Matching game session and attempt handling."""

from __future__ import annotations

import random
from typing import Any

from backend.database import get_connection, utc_now
from backend.services import session_store
from backend.services.errors import InvalidOperationError, ResourceNotFoundError
from backend.services.gloss import gloss_length
from backend.services.session_store import SessionKind
from backend.services.vocabulary_service import get_random_vocabulary


SESSION = SessionKind(
    table="study_sessions",
    not_found="Không tìm thấy phiên học.",
    already_ended="Phiên học này đã kết thúc.",
    completed="Đã hoàn tất vòng nối từ.",
    type_column="session_type",
    type_value="matching",
)


def _shuffle_different(items: list[dict[str, Any]], original_ids: list[int]) -> None:
    """Shuffle, then guarantee the two columns are not already lined up."""
    random.shuffle(items)
    if len(items) > 1 and [item["vocabulary_id"] for item in items] == original_ids:
        items.append(items.pop(0))


#: Oversampling factor for the length-matching draw below.
_CANDIDATE_POOL = 40


def _pick_words(
    count: int, hsk_level: str | None, *, balance_by_meaning: bool
) -> list[dict[str, Any]]:
    candidates = get_random_vocabulary(max(_CANDIDATE_POOL, count), hsk_level=hsk_level)
    if len(candidates) < count and hsk_level:
        candidates = get_random_vocabulary(max(_CANDIDATE_POOL, count))
    if not balance_by_meaning or len(candidates) <= count:
        return candidates[:count]

    # Anchor on one word, then keep its nearest neighbours by gloss length, so
    # the round is a set of comparable tiles rather than one essay and five
    # single words.
    anchor = random.choice(candidates)
    anchor_length = gloss_length(anchor.get("meaning"))
    ranked = sorted(
        candidates, key=lambda word: abs(gloss_length(word.get("meaning")) - anchor_length)
    )
    return ranked[:count]


def create_session(mode: str, count: int, hsk_level: str | None = None) -> dict[str, Any]:
    """Deal a round of tiles.

    Two things make a round playable that a plain random draw does not give:

    * **One level.** Mixing an HSK 1 word with an HSK 7-9 word lets the learner
      match by "which of these have I ever seen", not by meaning.
    * **Tiles of a similar size.** The meaning column is drawn from full CVDICT
      entries, and a tile reading "ăn" beside one running four hundred
      characters is solved on sight. Oversampling and keeping the words whose
      glosses are closest in length puts that guess back out of reach; the
      frontend still trims each tile for display.
    """
    vocabulary = _pick_words(count, hsk_level, balance_by_meaning=mode == "meaning")
    if len(vocabulary) < 2:
        raise InvalidOperationError("Không đủ từ để tạo vòng nối từ.")
    session_id = session_store.start(SESSION, total_items=len(vocabulary))

    left_items = [
        {"vocabulary_id": item["id"], "text": item["hanzi"]} for item in vocabulary
    ]
    right_field = "meaning" if mode == "meaning" else "pinyin"
    right_items = [
        {"vocabulary_id": item["id"], "text": item[right_field]} for item in vocabulary
    ]
    random.shuffle(left_items)
    _shuffle_different(right_items, [item["vocabulary_id"] for item in left_items])
    return {
        "session_id": session_id,
        "mode": mode,
        "left_items": left_items,
        "right_items": right_items,
    }


def record_attempt(
    session_id: int,
    vocabulary_id: int,
    mode: str,
    is_correct: bool,
) -> dict[str, Any]:
    with get_connection() as connection:
        session_store.require_open(connection, SESSION, session_id)
        exists = connection.execute(
            "SELECT 1 FROM vocabulary WHERE id = ?", (vocabulary_id,)
        ).fetchone()
        if not exists:
            raise ResourceNotFoundError("Không tìm thấy từ vựng.")
        connection.execute(
            """
            INSERT INTO matching_attempts (
                session_id, vocabulary_id, matching_mode, is_correct, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, vocabulary_id, mode, int(is_correct), utc_now()),
        )
    return {
        "message": "Đã ghi nhận lần nối.",
        "session_id": session_id,
        "vocabulary_id": vocabulary_id,
        "is_correct": is_correct,
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
