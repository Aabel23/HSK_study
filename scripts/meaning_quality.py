"""Tell a real Vietnamese gloss apart from leftover English.

The HSK dataset was imported from CC-CEDICT, and for a long stretch of the
project's history the importer wrote the English definition into the Vietnamese
``meaning`` column -- sometimes verbatim, sometimes a truncated slice of it,
sometimes as mojibake, and sometimes just the headword echoed back. That is why
the app showed Vietnamese and English cards side by side.

Both the dataset builder (`translate_meanings.py`) and the seeder
(`seed_data.py`) need the same answer to "is this text usable Vietnamese?" --
the builder to decide what to translate, the seeder to decide what to repair in
a database that already exists. Keeping the rule in one place is what stops the
two from drifting apart and re-introducing mixed-language cards.
"""

from __future__ import annotations

import re

# Openings that only ever start an English CC-CEDICT gloss. Deliberately
# missing the tempting "to ", "a " and "an ": those are ordinary Vietnamese
# words ("to lớn", "an toàn", "a lô"), and the English glosses beginning with
# them are already caught by the substring check against the English column.
_ENGLISH_LEAD = re.compile(
    r"^\(?(the\s|old\s+variant|variant\s+of|erhua\s+variant|abbr\.|"
    r"used\s+in|surname\s|see\s+also|see\s|CL:|classifier\s|onomatopoeia|"
    r"interjection|particle|prefix|suffix|pronoun|adverb|adjective)",
    re.I,
)

# Words that appear in English glosses and never inside a Vietnamese one.
_ENGLISH_MARKERS = re.compile(
    r"\b(sb|sth|one's|etc\.|the|of|and|with|from|that|this|which|used|something|"
    r"someone|surname|variant|abbr)\b",
    re.I,
)


def repair_mojibake(text: str) -> str:
    """Undo a UTF-8 string that was written out through a Latin-1/CP1252 encoder.

    Round-tripping is only accepted when it yields CJK characters, so ordinary
    Vietnamese text -- which is full of the same accented letters mojibake is
    made of -- is never mangled by the repair itself.
    """
    if not text or text.isascii():
        return text
    for encoding in ("latin-1", "cp1252"):
        try:
            candidate = text.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if candidate != text and any("一" <= char <= "鿿" for char in candidate):
            return candidate
    return text


# International loanwords Vietnamese spells the same way English does. No
# heuristic can tell "video" as a Vietnamese gloss from "video" left over from
# the English column, so they are named here rather than flagged forever.
_SHARED_LOANWORDS = frozenset(
    {
        "hecta",
        "hormone",
        "internet",
        "kilogram",
        "laser",
        "peugeot",
        "protein",
        "sushi",
        "video",
        "vitamin",
        "world cup",
    }
)


#: A Vietnamese gloss shorter than this, for a word whose English gloss is long,
#: has almost certainly lost most of the meaning. Tuned against the real data:
#: "vui" for "happy; joyous" is thin but defensible, while "nhìn" for "rare;
#: seldom seen; it's a rare pleasure to see you" is not a translation at all.
_THIN_GLOSS_RATIO = 0.35

#: Below this many characters a gloss is too short to carry a compound word's
#: meaning regardless of what the English column says.
_MINIMUM_GLOSS_LENGTH = 4


def _senses(gloss: str) -> list[str]:
    """Split a gloss into its semicolon-separated senses."""
    return [part.strip() for part in (gloss or "").split(";") if part.strip()]


def is_thin_gloss(meaning: str, meaning_en: str | None, hanzi: str) -> bool:
    """True when the Vietnamese gloss is present but too poor to ship.

    Separate from :func:`is_english_gloss`, which asks whether the text is
    Vietnamese at all. This asks whether it is a *translation* — the failure mode
    left behind when the import fell back to glossing a single character of a
    compound word, turning 少见 ("rare, seldom seen") into "nhìn", the gloss of
    its second character alone.

    Deliberately only applied to multi-character words: a one-character word
    genuinely can mean just "nhẹ".
    """
    meaning = (meaning or "").strip()
    english = repair_mojibake(meaning_en or "").strip()
    if not meaning or len(hanzi) < 2:
        return False
    if len(meaning) < _MINIMUM_GLOSS_LENGTH:
        return True
    if not english:
        return False

    # A word whose English side lists several senses but whose Vietnamese side is
    # a fraction of its length has dropped most of them.
    if len(meaning) < len(english) * _THIN_GLOSS_RATIO:
        return True

    # Repeated senses ("hoàng thượng; Bệ hạ hoàng đế; Hoàng đế bệ hạ") come from
    # translating each English sense in isolation and are noise, not detail.
    senses = _senses(meaning)
    if len(senses) > 2:
        words = [frozenset(sense.lower().split()) for sense in senses]
        overlapping = sum(
            1
            for index, first in enumerate(words)
            for second in words[index + 1 :]
            if first and second and len(first & second) >= min(len(first), len(second))
        )
        if overlapping:
            return True
    return False


def is_english_gloss(meaning: str, meaning_en: str | None, hanzi: str) -> bool:
    """True when `meaning` is not usable Vietnamese.

    `meaning` is expected to be mojibake-repaired already. The checks stay
    deliberately conservative: a short hand-written Vietnamese gloss ("tham
    gia", "của; trợ từ") has to survive, while anything copied out of the
    English column must not.
    """
    meaning = (meaning or "").strip()
    if not meaning:
        return True
    if meaning == hanzi:  # headword echoed back, never translated
        return True
    if meaning.lower() in _SHARED_LOANWORDS:
        return False
    english = repair_mojibake(meaning_en or "")
    if english and meaning.lower() in english.lower():  # verbatim slice
        return True
    if _ENGLISH_LEAD.match(meaning):
        return True
    return bool(_ENGLISH_MARKERS.search(meaning))
