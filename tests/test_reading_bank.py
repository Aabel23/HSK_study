"""The reading bank has to be deep enough that a resit is a new paper.

The intermediate pools once held 10, 6 and 6 items against draws of 5, 3 and 4.
Sitting the exam twice therefore returned most of the same questions, which
turns a mock exam into a memory test of that one paper.
"""

import json
from pathlib import Path

import pytest

from backend.services import reading_service


DATA = Path(__file__).resolve().parent.parent / "scripts" / "data"
BANK = json.loads((DATA / "hsk_reading_bank.json").read_text(encoding="utf-8"))
HSKK = json.loads((DATA / "hskk_bank.json").read_text(encoding="utf-8"))

PARTS = [
    (level_name, part)
    for level_name, level in BANK["levels"].items()
    for part in level["parts"]
]
PART_IDS = [f"{level}-{part['part_id']}" for level, part in PARTS]


@pytest.mark.parametrize(("level_name", "part"), PARTS, ids=PART_IDS)
def test_every_pool_holds_several_papers_worth(level_name, part):
    """Four sittings without repeating is the bar."""
    assert len(part["pool"]) >= part["count"] * 4, part["part_id"]


@pytest.mark.parametrize(("level_name", "part"), PARTS, ids=PART_IDS)
def test_pool_items_are_well_formed(level_name, part):
    ids = [item["id"] for item in part["pool"]]
    assert len(set(ids)) == len(ids), "trùng id trong pool"

    for item in part["pool"]:
        assert item.get("explanation_vi"), f"{item['id']} thiếu giải thích tiếng Việt"
        if part["question_type"] == "sentence_reordering":
            # The stored answer must be exactly the clauses, reordered — a typo
            # in either field would make the question unanswerable.
            assert sorted(item["answer"].split("|")) == sorted(item["words_zh"]), item["id"]
        if "options" in item:
            assert item["answer"] in item["options"], item["id"]
            assert len(set(item["options"])) == len(item["options"]), item["id"]


def test_four_sittings_of_the_intermediate_paper_barely_overlap(client):
    papers = []
    for _ in range(4):
        section = reading_service.build_section("intermediate")
        papers.append({q["id"] for part in section["parts"] for q in part["questions"]})

    # `item_pool` hands out unseen items first, so the first sittings should be
    # disjoint outright; the assertion is loosened by one to leave room for a
    # pool that has just run dry.
    assert len(papers[0] & papers[1]) <= 1
    assert len(set().union(*papers)) >= 40


def test_fill_in_blank_word_bank_has_exactly_one_spare(client):
    section = reading_service.build_section("intermediate")
    part = next(p for p in section["parts"] if p["question_type"] == "fill_in_blank_sentence")
    # 选词填空 offers one word more than there are blanks, so the last blank is
    # still a choice rather than whatever is left over.
    assert len(part["word_bank"]) == part["question_count"] + 1
    assert len({word["word_zh"] for word in part["word_bank"]}) == len(part["word_bank"])


# --------------------------------------------------------------------------
# The spoken half
# --------------------------------------------------------------------------

HSKK_PARTS = [
    (level_name, part, level["pools"].get(str(part["part"]), []))
    for level_name, level in HSKK["levels"].items()
    for part in level["parts"]
]
HSKK_IDS = [f"{level}-part{part['part']}" for level, part, _ in HSKK_PARTS]


@pytest.mark.parametrize(("level_name", "part", "pool"), HSKK_PARTS, ids=HSKK_IDS)
def test_every_speaking_pool_holds_several_papers_worth(level_name, part, pool):
    """Part 1 once drew 15 of 24, so most of a resit was the same prompts."""
    assert len(pool) >= part["count"] * 4, f"{level_name} phần {part['part']}"


@pytest.mark.parametrize(("level_name", "part", "pool"), HSKK_PARTS, ids=HSKK_IDS)
def test_speaking_items_carry_hanzi_pinyin_and_vietnamese(level_name, part, pool):
    ids = [item["id"] for item in pool]
    assert len(set(ids)) == len(ids)
    for item in pool:
        # The prompt is spoken aloud by TTS and shown with a gloss, so a missing
        # pinyin or Vietnamese line breaks the question rather than the styling.
        assert item.get("hanzi"), item["id"]
        assert item.get("pinyin"), item["id"]
        assert item.get("vi"), item["id"]
