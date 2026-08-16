"""Pinyin normalisation and answer grading.

Typing pinyin is the point of the exercise, so the grader has to accept every
way a learner can reasonably enter the same syllable:

    nǐ hǎo   (tone marks, what a Chinese IME produces)
    ni3 hao3 (tone numbers, what most people type on a plain keyboard)
    ni hao   (no tones at all -- accepted, but flagged as incomplete)

Tones are graded separately from spelling so the UI can tell a learner "đúng
nhưng thiếu thanh điệu" instead of simply marking them wrong, which is what
makes the drill teach tones rather than punish them.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Tone-marked vowel -> (base letter, tone number).
TONE_MARKS: dict[str, tuple[str, int]] = {
    "ā": ("a", 1), "á": ("a", 2), "ǎ": ("a", 3), "à": ("a", 4),
    "ē": ("e", 1), "é": ("e", 2), "ě": ("e", 3), "è": ("e", 4),
    "ī": ("i", 1), "í": ("i", 2), "ǐ": ("i", 3), "ì": ("i", 4),
    "ō": ("o", 1), "ó": ("o", 2), "ǒ": ("o", 3), "ò": ("o", 4),
    "ū": ("u", 1), "ú": ("u", 2), "ǔ": ("u", 3), "ù": ("u", 4),
    "ǖ": ("v", 1), "ǘ": ("v", 2), "ǚ": ("v", 3), "ǜ": ("v", 4),
    "ü": ("v", 0),
    "ń": ("n", 2), "ň": ("n", 3), "ǹ": ("n", 4),
    "ḿ": ("m", 2),
}

# Punctuation and separators that carry no grading signal.
_STRIP_PATTERN = re.compile(r"[\s'’\-·,，.。!！?？:：;；\"“”()（）]+")
_TONE_DIGIT_PATTERN = re.compile(r"([a-z]+)([1-5])")


@dataclass(frozen=True)
class PinyinComparison:
    """Outcome of grading one typed pinyin answer."""

    is_correct: bool
    """True when the syllables match, whether or not tones were supplied."""

    tones_correct: bool
    """True only when every tone was typed and matched."""

    tones_provided: bool
    """Whether the learner attempted tones at all."""

    normalized_expected: str
    normalized_answer: str


def _fold_tone_marks(text: str) -> tuple[str, list[int]]:
    """Return (toneless text, tones) for a tone-marked pinyin string."""
    letters: list[str] = []
    tones: list[int] = []
    for char in unicodedata.normalize("NFC", text):
        mapped = TONE_MARKS.get(char)
        if mapped is None:
            letters.append(char)
            continue
        base, tone = mapped
        letters.append(base)
        if tone:
            tones.append(tone)
    return "".join(letters), tones


def _extract_tone_digits(text: str) -> tuple[str, list[int]]:
    """Pull trailing tone numbers out of `ni3hao3`-style input.

    A trailing 5 marks the neutral tone, which carries no diacritic and so
    contributes nothing on the tone-mark path either. Dropping it here is what
    makes "hao3 chu5" and "hǎo chu" grade as the same tones -- otherwise
    spelling the neutral tone out counted against the learner.
    """
    tones = [
        int(match.group(2))
        for match in _TONE_DIGIT_PATTERN.finditer(text)
        if match.group(2) != "5"
    ]
    return _TONE_DIGIT_PATTERN.sub(r"\1", text), tones


def normalize_pinyin(text: str) -> tuple[str, list[int]]:
    """Reduce any pinyin spelling to a comparable (letters, tones) pair."""
    # "lu:" and "lv" are the standard keyboard spellings of "lü"; fold them to
    # the same form before the tone marks are stripped.
    lowered = (text or "").strip().lower().replace("u:", "v")
    folded, mark_tones = _fold_tone_marks(lowered)
    folded, digit_tones = _extract_tone_digits(folded)
    folded = _STRIP_PATTERN.sub("", folded)
    return folded, mark_tones or digit_tones


def compare_pinyin(expected: str, answer: str) -> PinyinComparison:
    """Grade a typed pinyin answer against the expected reading."""
    expected_letters, expected_tones = normalize_pinyin(expected)
    answer_letters, answer_tones = normalize_pinyin(answer)
    spelled_right = bool(expected_letters) and expected_letters == answer_letters
    tones_provided = bool(answer_tones)
    tones_right = spelled_right and tones_provided and answer_tones == expected_tones
    return PinyinComparison(
        is_correct=spelled_right,
        tones_correct=tones_right,
        tones_provided=tones_provided,
        normalized_expected=expected_letters,
        normalized_answer=answer_letters,
    )


def normalize_hanzi(text: str) -> str:
    """Strip whitespace and punctuation so typed Chinese compares cleanly."""
    cleaned = unicodedata.normalize("NFC", (text or "").strip())
    return _STRIP_PATTERN.sub("", cleaned)


def compare_hanzi(expected: str, answer: str) -> bool:
    normalized_expected = normalize_hanzi(expected)
    return bool(normalized_expected) and normalized_expected == normalize_hanzi(answer)


def character_diff(expected: str, answer: str) -> list[dict[str, object]]:
    """Per-character feedback for the answer review UI."""
    expected_clean = normalize_hanzi(expected)
    answer_clean = normalize_hanzi(answer)
    result: list[dict[str, object]] = []
    for index, char in enumerate(expected_clean):
        typed = answer_clean[index] if index < len(answer_clean) else None
        result.append({"expected": char, "typed": typed, "correct": typed == char})
    return result


def plain_letters(text: str | None) -> str:
    """Lowercase letters only, with every accent removed.

    Used to make search match what a learner types. Both readings this app
    shows carry diacritics — pinyin as tone marks (xué) and âm Hán-Việt as
    Vietnamese accents (học) — and nobody types either on a first attempt.
    NFD splits a letter from its marks, and dropping the combining marks leaves
    the bare letters; đ has no decomposition so it is mapped by hand.
    """
    lowered = unicodedata.normalize("NFD", (text or "").strip().lower())
    stripped = "".join(char for char in lowered if not unicodedata.combining(char))
    return stripped.replace("đ", "d")
