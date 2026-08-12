"""Give every HSK entry a Vietnamese meaning.

The bundled HSK dataset was assembled from CC-CEDICT, and the import left three
kinds of damage behind:

* about 6.000 of the 10.969 words kept their English gloss and were flagged
  ``meaning_is_vietnamese: false``;
* about 1.000 more were flagged as Vietnamese while still holding the English
  text verbatim, or nothing but the headword repeated back;
* a few dozen were mojibake -- UTF-8 bytes written out through a Latin-1 or
  CP1252 encoder, so ``old variant of 和`` reached the app as ``old variant of
  å'Œ``.

Together that is why the app showed Vietnamese and English cards side by side.
This script repairs all three from CVDICT, a Vietnamese translation of
CC-CEDICT published by Phong Phan under CC BY-SA 4.0.  Because CVDICT keeps the
CC-CEDICT keying (simplified form plus numbered pinyin), each definition is
matched to the right *reading* rather than merely the right character, which
matters for the many HSK homographs (看 kàn vs kān, 说 shuō vs shuì).

Hand-written Vietnamese already in the dataset is never overwritten: an entry is
only retranslated when it fails the checks in `needs_translation`.

Run this only when the dataset needs refreshing -- the translated JSON is
committed, so a normal checkout never needs the source dictionary:

    python scripts/translate_meanings.py --download
    python scripts/translate_meanings.py --dictionary path/to/CVDICT.u8
    python scripts/translate_meanings.py --download --check   # verify only

``--check`` exits non-zero when a file would change, which makes the script
usable as a data-drift guard in CI.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import NamedTuple

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.pinyin_utils import normalize_pinyin
from scripts.meaning_quality import is_english_gloss, repair_mojibake

DATA_DIR = Path(__file__).resolve().parent / "data"
LEVEL_FILES = (
    "hsk_1.json",
    "hsk_2.json",
    "hsk_3.json",
    "hsk_4.json",
    "hsk_5.json",
    "hsk_6.json",
    "hsk_7_9.json",
)

CVDICT_URL = "https://raw.githubusercontent.com/ph0ngp/CVDICT/master/CVDICT.u8"

# trad simp [numbered pinyin] /sense/sense/
_ENTRY_PATTERN = re.compile(r"^(\S+)\s+(\S+)\s+\[([^\]]*)\]\s+/(.*)/\s*$")

# Morpheme tags from the Peking University tagset that the original importer had
# no Vietnamese mapping for, so they reached the UI as raw codes.
POS_VI_FIXUPS = {
    "g": "ngữ tố",
    "cc": "liên từ đẳng lập",
    "Mg": "ngữ tố số",
    "Rg": "ngữ tố đại từ",
}

# Words whose stored reading is a real but rare one, so the card taught the
# wrong pronunciation: 说 as shuì rather than shuō, 离 as chī rather than lí.
# The upstream import took whichever CC-CEDICT line came first, which for a
# polyphone is a coin toss.
#
# Curated by hand rather than derived: picking "the reading with the most
# senses" gets 说 right but 女 wrong (it would prefer the archaic rǔ), so only
# entries where the HSK sense makes the reading unambiguous are listed. Setting
# a reading here also re-derives the meaning, because a definition looked up
# against the old reading no longer describes the word.
PREFERRED_READINGS = {
    # HSK 1
    "个": "gè", "说": "shuō", "要": "yào", "都": "dōu", "上": "shàng",
    "还": "hái", "着": "zhe", "那": "nà", "看": "kàn", "过": "guò",
    "吗": "ma", "打": "dǎ", "几": "jǐ", "听": "tīng", "东西": "dōng xi",
    "地方": "dì fang", "行": "xíng", "号": "hào", "正": "zhèng",
    "跑": "pǎo", "读": "dú", "页": "yè",
    # HSK 2
    "场": "chǎng", "结果": "jié guǒ", "万": "wàn", "片": "piàn", "句": "jù",
    "故事": "gù shi", "离": "lí", "提": "tí", "弄": "nòng", "查": "chá",
    "假": "jiǎ", "节": "jié", "重点": "zhòng diǎn", "鸟": "niǎo",
    "骑": "qí", "角": "jiǎo", "好处": "hǎo chu", "便宜": "pián yi",
    "教学": "jiào xué",
    # HSK 3
    "转": "zhuǎn", "区": "qū", "约": "yuē", "追": "zhuī", "合": "hé",
    "任": "rèn", "化": "huà", "生意": "shēng yi", "结实": "jiē shi",
    "工夫": "gōng fu", "所长": "suǒ zhǎng",
    # HSK 4-9: single characters left holding only a surname reading, so the
    # card said nothing but "họ Shàn" where the word means "single".
    "单": "dān", "盖": "gài", "番": "fān", "祭": "jì",
}

# Colloquial compounds the HSK list carries but CC-CEDICT does not, so there is
# no CVDICT entry to borrow.  Translated by hand.
MANUAL_MEANINGS = {
    "车上": "trên xe",
    "这时候": "lúc này, khi đó",
    "送到": "đưa đến, giao đến",
    "不一会儿": "chỉ một lát, chẳng mấy chốc",
    "不太": "không lắm, không mấy",
    "见过": "đã từng gặp, đã thấy qua",
    "放到": "đặt vào, để vào",
    "能不能": "có thể ... không?",
    "眼里": "trong mắt, trong cách nhìn",
    "有劲儿": "có sức, khoẻ; thú vị",
    "城里": "trong thành phố, trong nội thành",
    "很难说": "khó nói, khó mà nói được",
    "指着": "chỉ vào, trỏ vào",
    "致力于": "dốc sức vào, cống hiến cho",
    "怀着": "mang trong lòng, ôm ấp (tình cảm, ý định)",
    "飞往": "bay đến, bay đi (nơi nào)",
    "不肯": "không chịu, không chấp nhận",
    "定为": "định là, quy định thành",
    "不难": "không khó",
    "不利于": "bất lợi cho, không có lợi cho",
    "难以想象": "khó mà tưởng tượng nổi",
    "说起来": "nói ra thì, nhắc đến thì",
    "着眼于": "chú trọng vào, nhắm vào",
}


# --------------------------------------------------------------------------
# Pinyin: numbered (CC-CEDICT) -> tone marked (what a learner reads)
# --------------------------------------------------------------------------

_TONE_VOWELS = {
    "a": "aāáǎà",
    "e": "eēéěè",
    "i": "iīíǐì",
    "o": "oōóǒò",
    "u": "uūúǔù",
    "v": "üǖǘǚǜ",
}

_SYLLABLE_PATTERN = re.compile(r"([a-zA-ZüÜ:]+[1-5]?)")


def _mark_syllable(syllable: str) -> str:
    match = re.fullmatch(r"([a-zA-ZüÜ:]+)([1-5])", syllable)
    if not match:
        return syllable.replace("u:", "ü").replace("U:", "Ü")
    body, tone_text = match.groups()
    body = body.replace("u:", "ü").replace("U:", "Ü")
    tone = int(tone_text)
    if tone == 5:  # neutral tone carries no diacritic
        return body

    lowered = body.lower()
    # Standard placement: a and e always take the mark, "ou" marks the o,
    # otherwise it lands on the last vowel of the syllable.
    if "a" in lowered:
        position = lowered.index("a")
    elif "e" in lowered:
        position = lowered.index("e")
    elif "ou" in lowered:
        position = lowered.index("ou")
    else:
        vowels = [index for index, char in enumerate(lowered) if char in "aeiouü"]
        if not vowels:
            return body
        position = vowels[-1]

    target = lowered[position]
    marked = _TONE_VOWELS["v" if target == "ü" else target][tone]
    if body[position].isupper():
        marked = marked.upper()
    return body[:position] + marked + body[position + 1 :]


def numbered_to_marked(pinyin: str) -> str:
    """Convert CC-CEDICT numbered pinyin (``hao3``) to tone marks (``hǎo``)."""
    return _SYLLABLE_PATTERN.sub(lambda m: _mark_syllable(m.group(1)), pinyin)


# --------------------------------------------------------------------------
# CC-CEDICT markup -> plain Vietnamese prose
# --------------------------------------------------------------------------

_HANZI = r"[一-鿿㐀-䶿·]"
# "LT:" is CVDICT's rendering of CC-CEDICT's "CL:" classifier note.
_CLASSIFIER_PATTERN = re.compile(
    rf"\bLT:\s*((?:{_HANZI}+(?:\|{_HANZI}+)?(?:\[[^\]]*\])?\s*[,、]?\s*)+)"
)
_REFERENCE_PATTERN = re.compile(rf"({_HANZI}+(?:\|{_HANZI}+)?)\[([^\]]*)\]")
_TRAD_SIMP_PATTERN = re.compile(rf"({_HANZI}+)\|({_HANZI}+)")
_BARE_PINYIN_PATTERN = re.compile(r"\[([^\]]*)\]")


def _clean_classifiers(text: str) -> str:
    """Rewrite ``LT:個|个[ge4],位[wei4]`` as ``lượng từ: 个, 位``."""

    def replace(match: re.Match[str]) -> str:
        parts = []
        for chunk in re.split(r"[,、]", match.group(1)):
            chunk = _BARE_PINYIN_PATTERN.sub("", chunk).strip()
            if "|" in chunk:
                chunk = chunk.split("|")[-1]
            if chunk:
                parts.append(chunk)
        return "lượng từ: " + ", ".join(parts) if parts else ""

    return _CLASSIFIER_PATTERN.sub(replace, text)


def _simplify_reference(match: re.Match[str]) -> str:
    """Render a cross-reference as ``简体 (pīnyīn)``."""
    hanzi, pinyin = match.group(1), match.group(2)
    if "|" in hanzi:  # traditional|simplified -- keep what the learner sees
        hanzi = hanzi.split("|")[-1]
    marked = numbered_to_marked(pinyin).strip()
    return f"{hanzi} ({marked})" if marked else hanzi


def clean_definition(text: str) -> str:
    """Strip dictionary-file markup that means nothing inside a flashcard."""
    text = _clean_classifiers(text)
    text = _REFERENCE_PATTERN.sub(_simplify_reference, text)
    text = _TRAD_SIMP_PATTERN.sub(r"\2", text)
    # Any bracket left holds a bare romanisation, as in "họ [Ye3]".
    text = _BARE_PINYIN_PATTERN.sub(lambda m: numbered_to_marked(m.group(1)).strip(), text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s+([;,.)])", r"\1", text)
    return text.strip(" ;,")


# --------------------------------------------------------------------------
# Deciding which entries are actually broken
# --------------------------------------------------------------------------

def needs_translation(record: dict, meaning: str) -> bool:
    """True when the record's stored meaning is not usable Vietnamese."""
    if not record.get("meaning_is_vietnamese"):
        return True
    return is_english_gloss(meaning, record.get("meaning_en"), record.get("hanzi", ""))


# --------------------------------------------------------------------------
# Dictionary lookup
# --------------------------------------------------------------------------

class Reading(NamedTuple):
    """One CC-CEDICT line: how the word is read, what it means, and its casing.

    `capitalised` records whether CC-CEDICT wrote the reading as a proper noun
    (``Ye3`` rather than ``ye3``); it is what lets the pinyin repair below tell
    "the surname Yě" apart from "也, also".
    """

    sound: tuple[str, list[int]]
    meaning: str
    capitalised: bool


def load_dictionary(path: Path) -> dict[str, list[Reading]]:
    """Index CVDICT by simplified form, keeping every reading of each word."""
    index: dict[str, list[Reading]] = collections.defaultdict(list)
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("#") or line.startswith("%"):
                continue
            match = _ENTRY_PATTERN.match(line.rstrip("\n"))
            if not match:
                continue
            _traditional, simplified, pinyin, definitions = match.groups()
            senses = [clean_definition(part) for part in definitions.split("/")]
            meaning = "; ".join(sense for sense in senses if sense)
            if meaning:
                index[simplified].append(
                    Reading(normalize_pinyin(pinyin), meaning, pinyin[:1].isupper())
                )
    return index


_SURNAME_ONLY = re.compile(r"^họ\s+\S+$")


def _best(meanings: list[str]) -> str:
    """Prefer a substantive definition over a bare surname stub.

    CC-CEDICT splits 也 into "surname Ye" and "also; too", both read ye3.  Taking
    whichever line came first would leave a flashcard for 也 that says only "họ
    Yě" -- true, but useless to a learner -- so the richest sense wins, with the
    surname kept as a trailing note.
    """
    substantive = [m for m in meanings if not _SURNAME_ONLY.match(m)]
    if not substantive:
        return meanings[0]
    best = max(substantive, key=len)
    surnames = [m for m in meanings if _SURNAME_ONLY.match(m)]
    return "; ".join([best, *surnames]) if surnames else best


def lookup(index: dict[str, list[Reading]], hanzi: str, pinyin: str) -> str | None:
    """Pick the definition whose reading matches, falling back progressively.

    Casing is part of the match, not decoration. 牡丹 is both "Mǔ dan", a
    district of Heze, and "mǔ dan", the peony; an HSK card wants the flower, and
    the only thing separating the two entries is the capital letter.
    """
    candidates = index.get(hanzi)
    if not candidates:
        return None
    proper_noun = pinyin[:1].isupper()

    def pick(matches: list[Reading]) -> str:
        same_case = [entry for entry in matches if entry.capitalised == proper_noun]
        return _best([entry.meaning for entry in (same_case or matches)])

    letters, tones = normalize_pinyin(pinyin)
    exact = [entry for entry in candidates if entry.sound == (letters, tones)]
    if exact:
        return pick(exact)
    toneless = [entry for entry in candidates if entry.sound[0] == letters]
    if toneless:
        return pick(toneless)
    return pick(candidates)


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------

def lowercase_common_reading(
    index: dict[str, list[Reading]], hanzi: str, pinyin: str
) -> str | None:
    """Down-case a reading CC-CEDICT capitalises only for the proper noun.

    The upstream import took its pinyin from whichever CC-CEDICT line came
    first, so ordinary words arrived wearing the surname entry's capital: a
    flashcard for 也 read "Yě", 能 read "Néng". Capitalisation is only dropped
    when CC-CEDICT also lists the *same sound* under a lower-case entry, which
    is what distinguishes 也 from a genuine proper noun such as 北京.
    """
    if not pinyin[:1].isupper():
        return None
    candidates = index.get(hanzi)
    if not candidates:
        return None
    sound = normalize_pinyin(pinyin)
    if any(entry.sound == sound and not entry.capitalised for entry in candidates):
        return pinyin.lower()
    return None


def translate_records(records: list[dict], index: dict[str, list[Reading]]) -> collections.Counter:
    counts: collections.Counter = collections.Counter()
    for record in records:
        # A corrected reading invalidates the meaning that was looked up against
        # the old one, so the two always move together.
        reading_changed = False
        preferred = PREFERRED_READINGS.get(record["hanzi"])
        if preferred and preferred != record.get("pinyin"):
            record["pinyin"] = preferred
            counts["pinyin_corrected"] += 1
            reading_changed = True
        elif lowered := lowercase_common_reading(index, record["hanzi"], record.get("pinyin", "")):
            record["pinyin"] = lowered
            counts["pinyin_lowercased"] += 1
            reading_changed = True

        pos_vi = record.get("pos_vi") or []
        fixed_pos = [POS_VI_FIXUPS.get(tag, tag) for tag in pos_vi]
        if fixed_pos != pos_vi:
            record["pos_vi"] = fixed_pos
            counts["pos_fixed"] += 1

        english = repair_mojibake(record.get("meaning_en") or "")
        if english != (record.get("meaning_en") or ""):
            record["meaning_en"] = english
            counts["mojibake_en"] += 1

        meaning = repair_mojibake((record.get("meaning") or "").strip())
        if not reading_changed and not needs_translation(record, meaning):
            if meaning != record.get("meaning"):
                record["meaning"] = meaning
                counts["mojibake_vi"] += 1
            else:
                counts["kept"] += 1
            continue

        replacement = MANUAL_MEANINGS.get(record["hanzi"])
        if replacement:
            counts["manual"] += 1
        else:
            replacement = lookup(index, record["hanzi"], record.get("pinyin", ""))
            if replacement:
                counts["translated"] += 1
        if not replacement:
            counts["unresolved"] += 1
            continue
        record["meaning"] = replacement
        record["meaning_is_vietnamese"] = True
    return counts


def download_dictionary(destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f"Đang tải CVDICT từ {CVDICT_URL} ...")
    with urllib.request.urlopen(CVDICT_URL, timeout=180) as response:
        destination.write_bytes(response.read())
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Dịch nghĩa từ vựng HSK sang tiếng Việt.")
    parser.add_argument("--dictionary", type=Path, help="Đường dẫn tới CVDICT.u8")
    parser.add_argument("--download", action="store_true", help="Tải CVDICT.u8 từ GitHub")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Chỉ kiểm tra, không ghi file; thoát với mã 1 nếu dữ liệu cần cập nhật",
    )
    args = parser.parse_args()

    dictionary_path = args.dictionary
    if args.download or dictionary_path is None:
        dictionary_path = download_dictionary(
            args.dictionary or Path(__file__).resolve().parent / "_cvdict_cache" / "CVDICT.u8"
        )
    if not dictionary_path.exists():
        parser.error(f"Không tìm thấy từ điển: {dictionary_path}")

    index = load_dictionary(dictionary_path)
    print(f"Đã nạp {len(index)} mục từ CVDICT.")

    stale = False
    totals: collections.Counter = collections.Counter()
    for filename in LEVEL_FILES:
        path = DATA_DIR / filename
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        records = json.loads(original)
        counts = translate_records(records, index)
        totals.update(counts)
        # Keep the upstream layout (one compact line) so the diff carries only
        # the values that actually changed.
        updated = json.dumps(records, ensure_ascii=False)
        changed = updated != original
        stale = stale or changed
        print(
            f"  {filename}: giữ {counts['kept']}, dịch {counts['translated']}, "
            f"thủ công {counts['manual']}, sửa mojibake {counts['mojibake_vi'] + counts['mojibake_en']}, "
            f"từ loại {counts['pos_fixed']}, "
            f"pinyin {counts['pinyin_corrected']}+{counts['pinyin_lowercased']}, "
            f"chưa xử lý {counts['unresolved']}"
            f" -- {'cần cập nhật' if changed else 'đã đồng bộ'}"
        )
        if changed and not args.check:
            path.write_text(updated, encoding="utf-8")

    print(
        f"Tổng cộng: giữ {totals['kept']}, dịch {totals['translated']} từ CVDICT, "
        f"{totals['manual']} thủ công, {totals['unresolved']} chưa có nghĩa tiếng Việt."
    )
    if args.check and stale:
        print("Dữ liệu chưa đồng bộ. Chạy lại script này mà không có --check.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
