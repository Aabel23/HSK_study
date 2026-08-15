"""Cutting a dictionary entry down to the size of an answer button.

The vocabulary table holds whole CVDICT entries, which is what a dictionary
screen wants: 就 really does have fourteen senses. A multiple-choice question
wants the opposite. Left alone, one question ends up offering

    A. ăn
    B. (sau một mệnh đề giả định) trong trường hợp đó; thì; (sau một mệnh đề
       hành động) ngay khi; ngay sau khi; (giống như 就是 (jiù shì)) chỉ; …
    C. và
    D. đi

and the learner picks B without reading a word of Chinese, because the long
option is obviously the one the question is about. That is not a vocabulary
test.

`frontend-web/src/lib/format.ts` already trims each label at display time, and
that stays — it is what keeps a button one line tall. But trimming cannot undo
the giveaway, because the trim happens *after* the four words were chosen. The
fix has to happen at selection: pick distractors whose gloss is roughly as long
as the target's, so all four buttons come out the same size and the only way
through is to know the word.

This module is the Python half of that shortening, used for measuring rather
than for display.
"""

from __future__ import annotations

import re


#: Sense fragments that are dictionary apparatus rather than a meaning. Mirrors
#: ``NOT_A_MEANING`` in ``frontend-web/src/lib/format.ts`` — keep the two in
#: step, or the backend will balance on a length the learner never sees.
_NOT_A_MEANING = re.compile(r"^(lượng từ|CL)\s*[:：]", re.IGNORECASE)


def senses(meaning: str | None) -> list[str]:
    """The gloss split into senses, with apparatus dropped."""
    parts = [part.strip() for part in (meaning or "").split(";")]
    return [part for part in parts if part and not _NOT_A_MEANING.match(part)]


def short_gloss(meaning: str | None, *, max_senses: int = 1, max_chars: int = 38) -> str:
    """The leading senses of a gloss, for somewhere with one line to spare.

    Senses arrive semicolon-separated and roughly in order of usefulness, so
    the first one is the sense a learner most likely wants. The first sense is
    kept even when it alone is over budget: a blank button is worse than a long
    one.
    """
    parts = senses(meaning)
    if not parts:
        return (meaning or "").strip()

    kept: list[str] = []
    for part in parts[:max_senses]:
        if kept and len("; ".join(kept)) + len(part) + 2 > max_chars:
            break
        kept.append(part)
    return "; ".join(kept)


def gloss_length(meaning: str | None) -> int:
    """How long this gloss will look once it reaches a button."""
    return len(short_gloss(meaning))
