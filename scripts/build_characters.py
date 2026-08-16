"""Build ``scripts/data/characters.json`` — the character layer under the words.

Why the app needs a character table at all
------------------------------------------
Every HSK app on the market teaches words. A Vietnamese learner does not need
to be taught only words, because Vietnamese already contains the answer: well
over half of its formal vocabulary is Sino-Vietnamese, and every Chinese
character has a fixed âm Hán-Việt. Once a learner knows 学 = *học* and 生 =
*sinh*, 学生 is not a word to memorise — it is *học sinh*, a Vietnamese word
they have known since childhood. The same two characters then unlock 学期 (học
kỳ), 生活 (sinh hoạt), 学校 (học hiệu), 医生 (y sinh) and several hundred more.

That is the leverage this file exists to create: a table keyed by character
rather than by word, carrying the Hán-Việt reading, the radical it is built
from and a mnemonic, so the app can teach *decoding* instead of only recall.
Words outside the HSK syllabus stop being unknown and become derivable, which
is the "học rộng hơn ngoài HSK" the project owner asked for.

Sources, and why each one
-------------------------
``hanzi-sino-vietnamese`` (CC BY 4.0)
    659 core HSK characters with hand-checked Hán-Việt readings, Vietnamese
    meanings, radical lists, and Vietnamese mnemonics. The highest-quality
    material here, so it wins every conflict. The mnemonics in particular
    cannot be derived from anywhere else.

English Wiktionary via kaikki.org (CC BY-SA 4.0)
    Readings for the remaining ~6,000 characters. Wiktionary tags some readings
    explicitly as Hán-Việt and lists others in a mixed "Hán-Nôm" forms field
    that also contains Nôm readings — 们 is listed as *món* there, which is Nôm,
    where the Hán-Việt reading is *môn*. So explicitly tagged readings are
    taken first and the mixed list only fills gaps. This is the same licence
    family as CVDICT, which the project already credits.

Unicode Unihan (Unicode licence)
    Total stroke counts, radical numbers and the simplified/traditional
    variant map. Facts rather than prose, and the variant map is what lets a
    simplified character borrow the reading of its traditional form.

Run with ``--refresh`` to re-download the three sources into
``scripts/_character_cache/``; without it the cache is reused.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CACHE_DIR = Path(__file__).resolve().parent / "_character_cache"
DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT = DATA_DIR / "characters.json"

SOURCES = {
    "hanzi_sv": (
        "https://raw.githubusercontent.com/binhbuithithanh/"
        "hanzi-sino-vietnamese/HEAD/data/characters.json"
    ),
    "radicals": (
        "https://raw.githubusercontent.com/binhbuithithanh/"
        "hanzi-sino-vietnamese/HEAD/data/radicals.json"
    ),
    "wiktionary": (
        "https://kaikki.org/dictionary/Vietnamese/kaikki.org-dictionary-Vietnamese.jsonl"
    ),
    "unihan": "https://www.unicode.org/Public/UCD/latest/ucd/Unihan.zip",
}

CJK = re.compile(r"[一-鿿]")
GLOSS_FORM = re.compile(r"chữ Hán form of ([^\s(,;]+)")
#: A Hán-Việt syllable is one Vietnamese word: letters and diacritics, nothing
#: else. Anything with a space or a digit came from a malformed template.
READING = re.compile(r"^[a-zàáâãèéêìíòóôõùúýăđĩũơưạ-ỹ]+$")

#: Source ranking. Lower wins. Kept as named constants because the whole point
#: of the pipeline is that a worse source never overwrites a better one.
TIER_VERIFIED = 0  # hand-checked dataset
TIER_TAGGED = 1  # Wiktionary, explicitly labelled Hán-Việt
TIER_FORMS = 2  # Wiktionary, mixed Hán-Nôm forms list
TIER_VARIANT = 3  # borrowed from the traditional form
TIER_UNIHAN = 4  # Unihan kVietnamese, often a Nôm reading

TIER_NAMES = {
    TIER_VERIFIED: "hanzi-sino-vietnamese",
    TIER_TAGGED: "wiktionary",
    TIER_FORMS: "wiktionary-forms",
    TIER_VARIANT: "variant",
    TIER_UNIHAN: "unihan",
}


def _download(name: str, url: str, *, refresh: bool) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    suffix = ".zip" if url.endswith(".zip") else (".jsonl" if url.endswith(".jsonl") else ".json")
    path = CACHE_DIR / f"{name}{suffix}"
    if path.exists() and not refresh:
        return path
    print(f"  downloading {name} …", flush=True)
    request = Request(url, headers={"User-Agent": "HSK-study/1.0 (character table build)"})
    with urlopen(request, timeout=600) as response, path.open("wb") as handle:
        while chunk := response.read(1 << 20):
            handle.write(chunk)
    return path


class Readings:
    """A best-source-wins map from character to Hán-Việt reading."""

    def __init__(self) -> None:
        self._best: dict[str, tuple[int, str]] = {}

    def offer(self, char: str, reading: str | None, tier: int) -> None:
        if not char or not reading:
            return
        # Wiktionary occasionally hands back a decomposed form; the database
        # and every comparison in the app use NFC.
        value = unicodedata.normalize("NFC", reading.strip().lower())
        if not READING.match(value):
            return
        current = self._best.get(char)
        if current is None or tier < current[0]:
            self._best[char] = (tier, value)

    def reading(self, char: str) -> str | None:
        found = self._best.get(char)
        return found[1] if found else None

    def tier(self, char: str) -> int | None:
        found = self._best.get(char)
        return found[0] if found else None

    def __contains__(self, char: str) -> bool:
        return char in self._best

    def __len__(self) -> int:
        return len(self._best)


def load_verified(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_unihan(path: Path) -> dict[str, dict[str, Any]]:
    """Stroke counts, radical numbers, variants and the kVietnamese fallback."""
    facts: dict[str, dict[str, Any]] = defaultdict(dict)
    with zipfile.ZipFile(path) as archive:
        wanted = {
            "Unihan_IRGSources.txt": {"kTotalStrokes", "kRSUnicode"},
            "Unihan_Readings.txt": {"kVietnamese", "kMandarin", "kDefinition"},
            "Unihan_Variants.txt": {"kTraditionalVariant", "kSimplifiedVariant"},
        }
        for filename, fields in wanted.items():
            for line in archive.read(filename).decode("utf-8").splitlines():
                if line.startswith("#") or not line.strip():
                    continue
                code, field, value = line.split("\t", 2)
                if field not in fields:
                    continue
                facts[chr(int(code[2:], 16))][field] = value
    return facts


def _first_codepoint(value: str) -> str | None:
    """The first ``U+XXXX`` in a Unihan variant field, as a character."""
    match = re.search(r"U\+([0-9A-F]{4,5})", value)
    return chr(int(match.group(1), 16)) if match else None


#: Kangxi radical *number* to the ordinary character for that radical.
#:
#: Unicode's Kangxi Radicals block runs U+2F00..U+2FD5 as radicals 1 to 214 in
#: order, and each of those compatibility characters normalises under NFKC to
#: the unified ideograph a reader would recognise — ⼝ becomes 口. So the map is
#: derived rather than typed out, which is both shorter and impossible to get
#: subtly wrong halfway down a list of 214 entries.
KANGXI_RADICALS: dict[int, str] = {
    number: unicodedata.normalize("NFKC", chr(0x2F00 + number - 1))
    for number in range(1, 215)
}


def build(refresh: bool) -> dict[str, Any]:
    print("Fetching sources")
    paths = {name: _download(name, url, refresh=refresh) for name, url in SOURCES.items()}

    verified = load_verified(paths["hanzi_sv"])
    radicals = json.loads(paths["radicals"].read_text(encoding="utf-8"))
    unihan = load_unihan(paths["unihan"])
    print(f"  verified characters: {len(verified)}   radicals: {len(radicals)}   unihan: {len(unihan)}")

    readings = Readings()
    verified_by_char = {entry["hanzi"]: entry for entry in verified}
    for entry in verified:
        readings.offer(entry["hanzi"], entry.get("sinoViet"), TIER_VERIFIED)

    print("Reading Wiktionary")
    alt_of: dict[str, str] = {}
    with paths["wiktionary"].open(encoding="utf-8") as handle:
        for line in handle:
            entry = json.loads(line)
            word = entry.get("word", "")
            if len(word) != 1 or not CJK.match(word):
                continue
            for sense in entry.get("senses", []):
                for related in sense.get("related") or []:
                    if "han-viet-reading" in (related.get("tags") or []):
                        readings.offer(word, related.get("word"), TIER_TAGGED)
                for gloss in sense.get("glosses") or []:
                    match = GLOSS_FORM.search(gloss)
                    if match:
                        readings.offer(word, match.group(1), TIER_TAGGED)
                for alt in sense.get("alt_of") or []:
                    target = alt.get("word", "")
                    if len(target) == 1 and CJK.match(target):
                        alt_of.setdefault(word, target)
                    match = GLOSS_FORM.search(alt.get("extra") or "")
                    if match:
                        readings.offer(word, match.group(1), TIER_TAGGED)
            for form in entry.get("forms") or []:
                if "Hán-Nôm" in (form.get("tags") or []):
                    # Only the first: the rest of the list is usually Nôm.
                    readings.offer(word, form.get("form"), TIER_FORMS)
                    break
    print(f"  readings after Wiktionary: {len(readings)}")

    # Simplified characters borrow from their traditional form, which is where
    # the Hán-Việt reading was recorded in the first place.
    #
    # Unihan states the relation from both ends and neither end alone is
    # complete: 学 carries kTraditionalVariant → 學, but 丝 carries nothing and
    # is only reachable because 絲 carries kSimplifiedVariant → 丝. Reading both
    # directions is what takes the bank from 93% to full coverage.
    for char, facts in unihan.items():
        traditional = _first_codepoint(facts.get("kTraditionalVariant", ""))
        if traditional and traditional != char:
            alt_of.setdefault(char, traditional)
        for match in re.finditer(r"U\+([0-9A-F]{4,5})", facts.get("kSimplifiedVariant", "")):
            simplified = chr(int(match.group(1), 16))
            if simplified != char:
                alt_of.setdefault(simplified, char)
    for simplified, traditional in alt_of.items():
        if simplified not in readings:
            borrowed = readings.reading(traditional)
            if borrowed:
                readings.offer(simplified, borrowed, TIER_VARIANT)
    print(f"  readings after the variant bridge: {len(readings)}")

    # Unihan's kVietnamese is deliberately *not* used as a reading source.
    #
    # It mixes Hán-Việt with chữ Nôm and does not say which is which: it gives
    # 库 as "kho", 貝 as "buổi", 礎 as "sờ" and 紐 as "néo" — all real Vietnamese
    # readings of those characters, and all the Nôm one, where the Hán-Việt
    # readings are khố, bối, sở and nữu. Feeding those to a screen whose entire
    # premise is "the Hán-Việt reading tells you the word" would teach the
    # wrong thing with full confidence. A character with no reading is shown as
    # having none, which is honest and costs only coverage.

    # --- assemble ---------------------------------------------------------
    entries: list[dict[str, Any]] = []
    for char in sorted(set(readings._best) | set(verified_by_char)):
        facts = unihan.get(char, {})
        source = verified_by_char.get(char, {})
        strokes = facts.get("kTotalStrokes", "").split()
        radical_number = None
        if facts.get("kRSUnicode"):
            head = facts["kRSUnicode"].split()[0]
            radical_number = head.split(".")[0].rstrip("'")
        number = int(radical_number) if radical_number and radical_number.isdigit() else None

        # The hand-written dataset decomposes 659 characters fully — 学 into
        # ⺍ 冖 子 — and that is the material the 'Chiết tự' panel was built for.
        # For the other two thousand in the bank there is no decomposition
        # anywhere with a licence, but Unihan does give the radical every
        # character is *filed* under, and the radical table has a Vietnamese
        # name and mnemonic for it. One component with a gloss is a long way
        # short of a full breakdown and a long way better than an empty panel,
        # so it is offered and labelled as what it is.
        # Named `components` rather than `radicals`: the latter is the whole
        # radical table this function also builds, and shadowing it here left
        # that list holding one character's parts.
        components = source.get("radicals") or []
        radical_source = "dataset" if components else ""
        if not components and number and KANGXI_RADICALS.get(number):
            components = [KANGXI_RADICALS[number]]
            radical_source = "kangxi"

        entries.append(
            {
                "hanzi": char,
                "han_viet": readings.reading(char) or "",
                "han_viet_source": TIER_NAMES.get(readings.tier(char), ""),
                "pinyin": source.get("pinyin") or _unihan_pinyin(facts),
                "meaning_vi": source.get("meaningVi") or "",
                "meaning_en": (facts.get("kDefinition") or "").strip(),
                "traditional": source.get("traditional") or _first_codepoint(facts.get("kTraditionalVariant", "")),
                "stroke_count": int(strokes[0]) if strokes and strokes[0].isdigit() else None,
                "radical_number": number,
                "radicals": components,
                "radical_source": radical_source,
                "mnemonic_vi": source.get("mnemonic") or "",
                "stroke_hint_vi": source.get("strokeHint") or "",
            }
        )

    radical_entries = [
        {
            "hanzi": item["char"],
            "name_vi": item.get("nameVi", ""),
            "meaning_vi": item.get("meaning", ""),
            "mnemonic_vi": item.get("mnemonic", ""),
        }
        for item in radicals
    ]

    return {
        "version": 1,
        "credits": [
            {
                "name": "hanzi-sino-vietnamese",
                "url": "https://github.com/binhbuithithanh/hanzi-sino-vietnamese",
                "license": "CC BY 4.0",
                "used_for": "âm Hán-Việt, nghĩa, bộ thủ và mẹo nhớ của 659 chữ HSK cốt lõi",
            },
            {
                "name": "English Wiktionary (via kaikki.org)",
                "url": "https://kaikki.org/dictionary/Vietnamese/",
                "license": "CC BY-SA 4.0",
                "used_for": "âm Hán-Việt cho các chữ còn lại",
            },
            {
                "name": "Unicode Unihan Database",
                "url": "https://www.unicode.org/charts/unihan.html",
                "license": "Unicode License",
                "used_for": "số nét, bộ thủ và ánh xạ giản thể ↔ phồn thể",
            },
        ],
        "radicals": radical_entries,
        "characters": entries,
    }


def _unihan_pinyin(facts: dict[str, Any]) -> str:
    value = facts.get("kMandarin", "")
    return value.split()[0] if value else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="re-download the sources")
    arguments = parser.parse_args()

    payload = build(arguments.refresh)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    characters = payload["characters"]
    by_source = Counter(entry["han_viet_source"] for entry in characters if entry["han_viet"])
    print(f"\nWrote {OUTPUT} — {len(characters)} characters, {len(payload['radicals'])} radicals")
    for name, count in by_source.most_common():
        print(f"  {name:24s} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
