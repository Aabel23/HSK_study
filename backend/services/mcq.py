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
from backend.services.gloss import gloss_length
from backend.services.vocabulary_service import get_random_vocabulary


OPTION_COUNT = 4

#: How many candidates to draw before picking the distractors that match the
#: target's answer length. Big enough that there is a real choice at every
#: level, small enough that HSK 1 (506 words) is not effectively unshuffled.
_CANDIDATE_POOL = 40


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

    Level alone is not enough when the answers are Vietnamese glosses. The
    entries behind them run from "ăn" to a four-hundred-character list of
    senses, so a question drawn purely at random hands the learner a giveaway:
    one button is visibly the essay and the other three are single words. So
    the draw is oversampled and the distractors closest to the target's answer
    length win. See :mod:`backend.services.gloss`.
    """
    targets = get_random_vocabulary(1, hsk_level=hsk_level)
    if not targets:
        raise InvalidOperationError(empty_message)
    target = targets[0]

    wanted = option_count - 1
    candidates = get_random_vocabulary(
        max(_CANDIDATE_POOL, wanted), hsk_level=hsk_level, exclude_ids=[target["id"]]
    )
    if len(candidates) < wanted:
        candidates = get_random_vocabulary(
            max(_CANDIDATE_POOL, wanted), exclude_ids=[target["id"]]
        )
    if len(candidates) < wanted:
        raise InvalidOperationError("Không đủ từ vựng để tạo các lựa chọn.")

    distractors = _match_answer_length(target, candidates, label_field, wanted)

    options = [
        {"vocabulary_id": word["id"], "label": word[label_field]}
        for word in (target, *distractors)
    ]
    random.shuffle(options)
    return Question(target=target, options=options)


def _match_answer_length(
    target: dict[str, Any],
    candidates: list[dict[str, Any]],
    label_field: str,
    wanted: int,
) -> list[dict[str, Any]]:
    """The candidates whose answer looks most like the target's.

    Only meanings need this. Hanzi and pinyin answers are naturally within a
    syllable or two of each other, and sorting those by length would quietly
    turn every question into "the four shortest words at this level" — losing
    the randomness that keeps a session from repeating itself.
    """
    if label_field != "meaning":
        return candidates[:wanted]

    target_length = gloss_length(target.get("meaning"))
    ranked = sorted(
        candidates,
        key=lambda word: abs(gloss_length(word.get("meaning")) - target_length),
    )
    # Take a band rather than the exact top so two sessions on a small level do
    # not produce the same four options every time.
    band = ranked[: max(wanted * 3, wanted)]
    return random.sample(band, wanted)
