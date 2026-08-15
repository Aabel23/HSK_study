"""Repair Vietnamese glosses that survived the import while being wrong.

``translate_meanings.py`` only consults CVDICT when the current gloss *looks
like* leftover English. A gloss that reads as perfectly good Vietnamese but says
the wrong thing therefore sails straight through — which is how 少见 ("rare;
seldom seen") ended up defined as "nhìn", 忽悠 ("to sway, to flicker") as "nhẹ",
and 满怀 as "đầy tâm". The words are not rare edge cases: roughly one entry in
six at HSK 7-9 is affected, which is what makes the dictionary feel unfinished.

The repair needs no translation and no model, because CVDICT already holds the
correct Vietnamese for every one of them. It only needs a rule for *when to
trust CVDICT over what is already there*, and that rule has to be careful in one
specific direction: the HSK 1 glosses were written by hand for beginners and are
deliberately better than CVDICT's. CVDICT defines 本 as "gốc; rễ" (root); the
curated gloss says "quyển (lượng từ)", which is the only sense a beginner meets.
Overwriting those would be a regression dressed up as a fix.

So two conservative rules, and nothing else:

* **Replace** when the current gloss shares no sense at all with CVDICT's. No
  overlap means one of them is about a different word, and CVDICT is the
  designated source (see ``AGENTS.md``).
* **Enrich** when the current gloss is a strict subset of CVDICT's — every sense
  it has is present there, and CVDICT knows more. This is safe by construction:
  nothing is lost, only added.

Hand-curated entries are exempt from both. Run with ``--dry-run`` first; the
changes are written back to ``scripts/data/hsk_*.json``, which is what ships.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.seed_data import FULL_DATA_DIR, FULL_LEVEL_FILES, HSK1_VOCABULARY
from scripts.resolve_references import REFERENCE as REFERENCE_ONLY
from scripts.translate_meanings import load_dictionary, lookup


CVDICT_PATH = Path(__file__).resolve().parent / "_cvdict_cache" / "CVDICT.u8"

#: Words whose Vietnamese was written by hand for this app. CVDICT may be richer
#: but it is not better here, so they are never touched.
CURATED = frozenset(record[0] for record in HSK1_VOCABULARY)


def _senses(gloss: str) -> set[str]:
    return {part.strip().lower() for part in (gloss or "").split(";") if part.strip()}


#: Letters that only appear in Vietnamese, never in an English gloss.
_VIETNAMESE_MARKS = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ")


def has_untranslated_english(gloss: str, meaning_en: str | None = None) -> bool:
    """True when a sense is a run of English that never got translated.

    The import mistranslated the English infinitive marker "to" as the
    Vietnamese word "từ" and split it off as its own sense, stranding the rest:
    "to make a copy" became "make a copy; từ".

    Detection is per sense, and only a sense with no Vietnamese diacritic
    anywhere in it is even considered — that alone clears "an toàn" and "to
    lớn", which any English-word-list check would flag.

    Then two tests, in order of how much they can be trusted:

    1. **The sense appears verbatim in the English column.** Decisive, and the
       only test that catches a one-word leak: 处 reads "reside; từ", and
       "reside" is right there in "to reside; to live; to dwell". A single word
       is far too short to judge on shape alone, so without the English column
       to compare against it would have to be let through.
    2. **Three or more Latin words.** The fallback for entries with no English
       recorded. A chemical formula or a loanword never runs that long.
    """
    english = (meaning_en or "").lower()
    for sense in (gloss or "").split(";"):
        sense = sense.strip()
        if not sense or any(char in _VIETNAMESE_MARKS for char in sense.lower()):
            continue
        if not re.search(r"[A-Za-z]", sense):
            continue  # Chinese or punctuation only; nothing to judge.
        if english and sense.lower() in english:
            return True
        if len(re.findall(r"[A-Za-z][A-Za-z'\-]*", sense)) >= 3:
            return True
    return False


def strip_english_prefix(gloss: str, meaning_en: str | None) -> str:
    """Drop a stranded English sense and the "từ" the importer left beside it.

    The signature of this bug is exact and worth keying on. The importer read an
    English gloss beginning "to …", mistranslated the infinitive marker as the
    Vietnamese word "từ", and emitted the two as separate senses — so 限制 reads
    "restrict; từ; hạn chế; giới hạn; …" with the correct Vietnamese sitting
    right there after the wreckage.

    Keying on that adjacency is what makes the repair safe. Plenty of glosses
    hold a single Latin word that is genuinely Vietnamese — email, radio, laser,
    sushi, World Cup — and no test of shape can tell those from "restrict".
    A bare "từ" standing immediately after them can: it never occurs otherwise,
    and 从 ("từ; thông qua; qua") keeps its "từ" because nothing precedes it.
    """
    senses = [part.strip() for part in (gloss or "").split(";")]
    english = (meaning_en or "").lower()

    kept: list[str] = []
    index = 0
    while index < len(senses):
        sense = senses[index]
        follows_marker = index + 1 < len(senses) and senses[index + 1].lower() == "từ"
        looks_english = (
            sense
            and not any(char in _VIETNAMESE_MARKS for char in sense.lower())
            and bool(re.search(r"[A-Za-z]", sense))
            and (not english or sense.lower() in english or len(sense.split()) >= 2)
        )
        if follows_marker and looks_english:
            index += 2  # drop the English sense and the "từ" after it
            continue
        if sense:
            kept.append(sense)
        index += 1

    # Never strip an entry down to nothing; a broken gloss beats an empty one.
    return "; ".join(kept) if kept else gloss


def close_orphan_bracket(gloss: str) -> str:
    """Put back an opening bracket the source dropped.

    CVDICT ships a few glosses that open mid-qualifier — 赐 begins "hình thức
    hạn chế) phong tặng" — which renders as a stray bracket on the card.
    """
    if gloss.count(")") == gloss.count("(") + 1 and not gloss.lstrip().startswith("("):
        return f"({gloss.lstrip()}"
    return gloss


def _merge(current: str, candidate: str) -> str:
    """Current gloss first, then the CVDICT senses it does not already cover."""
    kept = [part.strip() for part in current.split(";") if part.strip()]
    covered = " ; ".join(kept).lower()
    for sense in candidate.split(";"):
        sense = sense.strip()
        if sense and sense.lower() not in covered:
            kept.append(sense)
            covered += f" ; {sense.lower()}"
    return "; ".join(kept)


def _decide(hanzi: str, current: str, candidate: str, meaning_en: str | None) -> str | None:
    """Return the reason to take ``candidate``, or ``None`` to keep ``current``."""
    current_senses = _senses(current)
    candidate_senses = _senses(candidate)
    if not candidate_senses or current_senses == candidate_senses:
        return None

    # CVDICT defines some headwords by pointing at another one — 大伙儿 is only
    # "biến thể er hoá của 大伙". `resolve_references.py` replaces those with the
    # target's real meaning, and without this guard the two scripts fight: this
    # one would hand the useless pointer straight back. A gloss that explains
    # nothing never wins, whatever the overlap rules say.
    if REFERENCE_ONLY.match(candidate.strip()):
        return None

    if current_senses & candidate_senses:
        # Some overlap: only act when CVDICT is a strict superset, so the repair
        # can only ever add senses and never contradict what is already shown.
        if current_senses < candidate_senses:
            return "enriched"
        return None

    # A gloss can also be a substring of the other without splitting the same
    # way ("vui" inside "hạnh phúc; vui mừng"). That still counts as agreement.
    if any(sense in candidate.lower() for sense in current_senses):
        return "enriched"

    # No agreement at all. For a compound this means the current gloss is simply
    # wrong and CVDICT wins. For a single character it usually means something
    # else: the character has several readings, and the lookup matched the wrong
    # one — 更 is gèng "hơn" on an HSK card but gēng "thay đổi" in CVDICT's first
    # entry. Replacing there swaps a right answer for a wrong one, so single
    # characters are left alone and only ever enriched.
    #
    # Unless the gloss still contains raw English, which is not a disagreement
    # between two defensible readings but a broken entry. 更's "hơn, thêm" is
    # Vietnamese and stays protected; 抄's "make a copy; từ" is not, and CVDICT's
    # "sao chép; đạo văn; …" can only be an improvement.
    if len(hanzi) >= 2 or has_untranslated_english(current, meaning_en):
        return "replaced"
    return None


def repair(*, dry_run: bool, level: str | None, limit: int | None) -> Counter:
    if not CVDICT_PATH.is_file():
        raise SystemExit(
            f"Không tìm thấy {CVDICT_PATH}. Chạy scripts/translate_meanings.py "
            "một lần để tải CVDICT về trước."
        )
    index = load_dictionary(CVDICT_PATH)
    counts: Counter = Counter()
    samples: list[tuple[str, str, str, str]] = []

    for filename in FULL_LEVEL_FILES:
        # "hsk_7_9.json" -> "7-9", matching the hsk_level column.
        code = filename.removeprefix("hsk_").removesuffix(".json").replace("_", "-")
        if level and code != level:
            continue
        path = FULL_DATA_DIR / filename
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        records: list[dict[str, Any]] = payload["words"] if isinstance(payload, dict) else payload
        changed = 0
        for record in records:
            hanzi = record.get("hanzi", "")
            if hanzi in CURATED:
                counts["curated_kept"] += 1
                continue
            candidate = lookup(index, hanzi, record.get("pinyin", ""))
            if not candidate:
                counts["not_in_cvdict"] += 1
                continue

            # Two repairs that need no second opinion from CVDICT, because the
            # entry is damaged rather than merely disputed.
            original = (record.get("meaning") or "").strip()
            current = close_orphan_bracket(
                strip_english_prefix(original, record.get("meaning_en"))
            )
            if current != original:
                record["meaning"] = current
                counts["cleaned"] += 1
                changed += 1
            reason = _decide(hanzi, current, candidate, record.get("meaning_en"))
            if not reason:
                counts["kept"] += 1
                continue
            if limit and counts["replaced"] + counts["enriched"] >= limit:
                continue

            # Enriching keeps what is already there and appends only the senses
            # CVDICT adds. Overwriting would quietly drop a sense the current
            # gloss had and CVDICT splits differently — 才 is "mới; tài" here and
            # "khả năng; tài năng; …" there, and the adverb "mới" must survive.
            merged = close_orphan_bracket(
                _merge(current, candidate) if reason == "enriched" else candidate
            )
            if merged == current:
                counts["kept"] += 1
                continue

            counts[reason] += 1
            if len(samples) < 25:
                samples.append((code, hanzi, current, merged))
            record["meaning"] = merged
            record["meaning_is_vietnamese"] = True
            changed += 1

        if changed and not dry_run:
            with path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
        print(f"HSK {code:4} {changed:5} mục được sửa trong {filename}")

    print("\nMẫu thay đổi:")
    for code, hanzi, current, candidate in samples:
        print(f"  HSK{code:4} {hanzi:8} {current[:30]!r:34} -> {candidate[:52]!r}")
    print(
        f"\nThay hẳn: {counts['replaced']}   Bổ sung nét nghĩa: {counts['enriched']}   "
        f"Giữ nguyên: {counts['kept']}   Curated: {counts['curated_kept']}   "
        f"Không có trong CVDICT: {counts['not_in_cvdict']}"
    )
    if dry_run:
        print("\n(dry-run) Chưa ghi file nào.")
    else:
        print("\n✓ Đã ghi lại scripts/data/. Chạy scripts/seed_data.py để nạp vào database.")
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="chỉ xem, không ghi file")
    parser.add_argument("--level", help="chỉ sửa một cấp, ví dụ 7-9")
    parser.add_argument("--limit", type=int, help="giới hạn số mục sửa, để thử trước")
    arguments = parser.parse_args()
    repair(dry_run=arguments.dry_run, level=arguments.level, limit=arguments.limit)


if __name__ == "__main__":
    main()
