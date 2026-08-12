"""Every vocabulary card has to read in Vietnamese.

The dataset was imported from CC-CEDICT and for a long time carried the English
gloss in the Vietnamese `meaning` column, which is what made the app show
Vietnamese and English cards side by side. These tests pin the fix in place --
both for the shipped dataset and for a database seeded by an older build.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.database import get_connection
from scripts.meaning_quality import is_english_gloss, repair_mojibake
from scripts.seed_data import FULL_DATA_DIR, FULL_LEVEL_FILES, seed_full_vocabulary


def _all_records() -> list[dict]:
    records: list[dict] = []
    for filename in FULL_LEVEL_FILES:
        path = FULL_DATA_DIR / filename
        if path.exists():
            records.extend(json.loads(Path(path).read_text(encoding="utf-8")))
    return records


def test_dataset_has_no_english_meanings_left():
    records = _all_records()
    assert len(records) > 10_000, "dataset failed to load"
    offenders = [
        record["hanzi"]
        for record in records
        if not record.get("meaning_is_vietnamese")
        or is_english_gloss(record["meaning"], record.get("meaning_en"), record["hanzi"])
    ]
    assert offenders == [], f"{len(offenders)} mục còn nghĩa tiếng Anh: {offenders[:10]}"


def test_dataset_has_no_mojibake():
    offenders = [
        record["hanzi"]
        for record in _all_records()
        if repair_mojibake(record["meaning"]) != record["meaning"]
    ]
    assert offenders == [], f"{len(offenders)} mục bị lỗi mã hoá: {offenders[:10]}"


def test_dataset_has_no_untranslated_pos_tags():
    """The Peking University morpheme codes must not reach the UI as raw codes."""
    raw_codes = {"g", "cc", "Mg", "Rg"}
    offenders = [
        record["hanzi"]
        for record in _all_records()
        if raw_codes & set(record.get("pos_vi") or [])
    ]
    assert offenders == [], f"{len(offenders)} mục còn mã từ loại thô: {offenders[:10]}"


@pytest.mark.parametrize(
    ("stored", "expected_english"),
    [
        ("you", True),  # verbatim slice of the English gloss
        ("erhua variant of 一点", True),  # English lead-in
        ("你", True),  # headword echoed back
        ("", True),
        ("bạn (ngôi thứ hai thông dụng)", False),
        ("tham gia", False),  # Vietnamese without diacritics still counts
        ("an toàn", False),  # must not be read as the English article "an"
        ("to lớn", False),  # must not be read as the English infinitive "to"
    ],
)
def test_is_english_gloss(stored: str, expected_english: bool):
    english = "you (informal, as opposed to courteous 您)"
    assert is_english_gloss(stored, english, "你") is expected_english


def test_seeding_repairs_a_legacy_english_meaning(client):
    """A database written by an older build must be healed, not left as-is."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, hanzi, meaning, meaning_en FROM vocabulary WHERE hanzi = '你'"
        ).fetchone()
        assert row is not None
        # Reproduce the damage older builds left behind: the English gloss, or a
        # slice of it, sitting in the Vietnamese column.
        connection.execute("UPDATE vocabulary SET meaning = 'you' WHERE id = ?", (row["id"],))

    seed_full_vocabulary()

    with get_connection() as connection:
        healed = connection.execute(
            "SELECT meaning, meaning_en FROM vocabulary WHERE hanzi = '你'"
        ).fetchone()
    assert healed["meaning"] != "you"
    assert not is_english_gloss(healed["meaning"], healed["meaning_en"], "你")


def test_seeding_preserves_a_hand_written_meaning(client):
    """The repair pass must never overwrite Vietnamese somebody wrote by hand."""
    with get_connection() as connection:
        connection.execute("UPDATE vocabulary SET meaning = ? WHERE hanzi = '你'", ("cậu, bồ",))

    seed_full_vocabulary()

    with get_connection() as connection:
        kept = connection.execute(
            "SELECT meaning FROM vocabulary WHERE hanzi = '你'"
        ).fetchone()["meaning"]
    assert kept == "cậu, bồ"


def test_api_serves_vietnamese_meanings(client):
    data = client.get("/api/vocabulary", params={"limit": 100, "hsk_level": "1"}).json()
    offenders = [
        item["hanzi"]
        for item in data["items"]
        if is_english_gloss(item["meaning"], item["meaning_en"], item["hanzi"])
    ]
    assert offenders == []
