"""Drawing one multiple-choice question out of the vocabulary bank.

Kiểm tra and Luyện nghe ask different things — one shows the word, the other
plays it — but the machinery underneath is identical: pick a target word, pull
three more from the same HSK level to act as distractors, label all four with
whichever field the mode is testing, and shuffle. Both services used to carry
their own copy of that; it lives here now.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from backend.services.errors import InvalidOperationError
from backend.services.vocabulary_service import get_random_vocabulary


OPTION_COUNT = 4


@dataclass(frozen=True)
class Question:
    target: dict[str, Any]
    options: list[dict[str, Any]]


def draw(
    hsk_level: str | None,
    label_field: str,
    *,
    empty_message: str,
    option_count: int = OPTION_COUNT,
) -> Question:
    """Pick a target word and ``option_count - 1`` distractors to hide it among.

    Distractors come from the same HSK level so the choice is a real one — at
    HSK 6 a beginner word stands out and gives the answer away. A narrow level
    can run out of candidates, so the search widens to the whole bank rather
    than failing the session.
    """
    targets = get_random_vocabulary(1, hsk_level=hsk_level)
    if not targets:
        raise InvalidOperationError(empty_message)
    target = targets[0]

    wanted = option_count - 1
    distractors = get_random_vocabulary(wanted, hsk_level=hsk_level, exclude_ids=[target["id"]])
    if len(distractors) < wanted:
        distractors = get_random_vocabulary(wanted, exclude_ids=[target["id"]])
    if len(distractors) < wanted:
        raise InvalidOperationError("Không đủ từ vựng để tạo các lựa chọn.")

    options = [
        {"vocabulary_id": word["id"], "label": word[label_field]}
        for word in (target, *distractors)
    ]
    random.shuffle(options)
    return Question(target=target, options=options)
