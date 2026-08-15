"""Give a meaning to entries whose "meaning" only points at another word.

CVDICT defines some headwords by cross-reference rather than by explanation.
女孩儿 is glossed "biến thể er hoá của 女孩" — true, and useless on a flashcard:
the learner is told which word this is a variant of, and never told what it
means. 87 entries are in that state.

The fix is a lookup, not a translation:

    女孩儿  "biến thể er hoá của 女孩 (nǚ hái)"
         -> "bé gái; con gái (biến thể er hoá của 女孩)"

Meaning first, because that is what the learner needs; the note kept after it,
because "this is the er-suffixed form" is genuinely worth knowing.

Most of the targets are **not in the HSK dataset** — the syllabus lists 女孩儿
but never 女孩 — so the resolver falls back to CVDICT, which has both and is
already this project's source of record for Vietnamese meanings. Without that
fallback only three of the forty-three entries could be resolved.

The rule is deliberately narrow: it fires only when the *whole* gloss is one
pointer. See :func:`_resolve` for the two ways a cleverer version broke the
data.
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

from scripts.seed_data import FULL_DATA_DIR, FULL_LEVEL_FILES
from scripts.translate_meanings import load_dictionary, lookup


CVDICT_PATH = Path(__file__).resolve().parent / "_cvdict_cache" / "CVDICT.u8"


#: A sense that is only a pointer at another headword. The Chinese run is the
#: target; the pinyin CVDICT puts in brackets after it is ignored.
REFERENCE = re.compile(
    r"^\s*(?P<note>(?:biến thể(?:\s+\w+)*|dạng biến thể|cách viết\s+\w+|viết tắt(?:\s+\w+)*|xem)"
    r"(?:\s+(?:của|cho|lại))?)\s+(?P<target>[一-鿿]+)\s*(?:\((?P<pinyin>[^)]*)\))?\s*$",
    re.I,
)

#: How many of the target's senses to borrow. All of them would make a long
#: entry longer for no gain — the first two carry the meaning.
BORROWED_SENSES = 2


def _senses(gloss: str) -> list[str]:
    return [part.strip() for part in (gloss or "").split(";") if part.strip()]


def _load_records() -> list[tuple[Path, list[dict[str, Any]]]]:
    loaded = []
    for filename in FULL_LEVEL_FILES:
        path = FULL_DATA_DIR / filename
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        loaded.append((path, payload["words"] if isinstance(payload, dict) else payload))
    return loaded


def _resolve(
    hanzi: str,
    gloss: str,
    index: dict[str, str],
    cvdict: dict[str, Any] | None,
    counts: Counter,
) -> str | None:
    """Return a replacement gloss, or ``None`` to leave the entry alone.

    Deliberately narrow: it acts only when the *entire* gloss is one pointer at
    another word. A first attempt was cleverer — it dropped self-references and
    spliced borrowed senses into multi-sense entries — and it made the data
    worse. Splicing put an archaic borrowed sense at the front, so 合 ("đóng,
    hợp") came out defined as "hộp", the meaning of 盒 it is only an old variant
    of. Dropping self-references left entries reading just "biến thể".

    Both failures share a cause: an entry with other senses already has a
    meaning, so there is nothing to fix and every edit is a chance to break it.
    """
    senses = _senses(gloss)
    if len(senses) != 1:
        counts["has_other_senses"] += 1
        return None

    match = REFERENCE.match(senses[0])
    if not match:
        return None

    target = match.group("target")
    if target == hanzi:
        # "变体 of itself" says nothing, but nothing here can supply what it
        # should have said either. Reported, not guessed at.
        counts["self_reference"] += 1
        return None

    borrowed = _senses(index.get(target, ""))
    if not borrowed and cvdict is not None:
        # The base forms are usually *not* in the HSK list — the syllabus lists
        # 女孩儿 but not 女孩 — so the dataset alone can resolve almost none of
        # these. CVDICT has both, and it is already this project's source of
        # record for Vietnamese meanings.
        borrowed = _senses(lookup(cvdict, target, match.group("pinyin") or "") or "")
        if borrowed:
            counts["from_cvdict"] += 1

    # Guard against a chain: if the target is itself only a pointer, borrowing
    # its gloss would move the problem one word along rather than solve it.
    if not borrowed or REFERENCE.match(borrowed[0]):
        counts["target_has_no_meaning"] += 1
        return None

    counts["resolved"] += 1
    # Meaning first — that is what the learner needs — with the relationship
    # kept after it, because "this is the er-suffixed form" is worth knowing.
    return f"{'; '.join(borrowed[:BORROWED_SENSES])} ({match.group('note')} {target})"


def run(*, dry_run: bool) -> Counter:
    files = _load_records()
    index = {
        record["hanzi"]: record.get("meaning", "")
        for _, records in files
        for record in records
    }

    cvdict = load_dictionary(CVDICT_PATH) if CVDICT_PATH.is_file() else None
    if cvdict is None:
        print(f"! Không có {CVDICT_PATH.name}; chỉ giải được tham chiếu trong bộ HSK.")

    counts: Counter = Counter()
    samples: list[tuple[str, str, str]] = []

    for path, records in files:
        changed = 0
        for record in records:
            hanzi = record.get("hanzi", "")
            current = (record.get("meaning") or "").strip()
            replacement = _resolve(hanzi, current, index, cvdict, counts)
            if not replacement or replacement == current:
                continue
            if len(samples) < 20:
                samples.append((hanzi, current, replacement))
            record["meaning"] = replacement
            changed += 1

        if changed and not dry_run:
            with path.open("w", encoding="utf-8") as handle:
                json.dump(records, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
        if changed:
            print(f"{path.name:16} {changed:4} mục")

    print("\nMẫu:")
    for hanzi, before, after in samples:
        print(f"  {hanzi:8} {before[:44]!r}\n           -> {after[:70]!r}")
    print(
        f"\nGiải được: {counts['resolved']}   Bỏ tự trỏ: {counts['self_reference_dropped']}   "
        f"Từ đích không có nghĩa: {counts['target_has_no_meaning']}"
    )
    print(
        "\n(dry-run) Chưa ghi file."
        if dry_run
        else "\n✓ Đã ghi scripts/data/. Chạy scripts/seed_data.py để nạp vào database."
    )
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="chỉ xem, không ghi file")
    run(dry_run=parser.parse_args().dry_run)


if __name__ == "__main__":
    main()
