"""Example sentences on a dictionary entry.

Only 150 of 10.969 words shipped with an example, which is the widest gap
between this and a real dictionary. The fix imports nothing: it indexes the
sentences the project already wrote and already checked — the rearrange bank,
the grammar lessons and the HSKK speaking prompts.
"""

from backend.database import get_connection


def entry(client, word):
    items = client.get(f"/api/vocabulary?search={word}").json()["items"]
    match = next(item for item in items if item["hanzi"] == word)
    return client.get(f"/api/vocabulary/{match['id']}").json()


def test_a_common_word_gets_examples(client):
    data = entry(client, "图书馆")
    assert data["examples"], "图书馆 xuất hiện trong kho câu, phải có ví dụ"
    for example in data["examples"]:
        assert "图书馆" in example["hanzi"]
        assert example["meaning_vi"]
        assert example["source"] in {"sentences", "grammar", "hskk"}


def test_examples_are_absent_from_the_list_endpoint(client):
    """The list renders two dozen cards a page and has no room for them."""
    items = client.get("/api/vocabulary?limit=5").json()["items"]
    assert items
    assert all("examples" not in item for item in items)


def test_coverage_is_far_above_the_shipped_examples(client):
    with get_connection() as connection:
        covered = connection.execute(
            "SELECT COUNT(DISTINCT vocabulary_id) FROM word_examples"
        ).fetchone()[0]
        total = connection.execute("SELECT COUNT(*) FROM vocabulary").fetchone()[0]
    # 150 words came with an example; the index reaches well over a thousand.
    assert covered > 1000
    assert covered < total  # and it is honest about not covering everything


def test_every_example_actually_contains_its_word(client):
    with get_connection() as connection:
        mismatched = connection.execute(
            """
            SELECT COUNT(*)
            FROM word_examples we
            JOIN vocabulary v ON v.id = we.vocabulary_id
            WHERE INSTR(we.hanzi, v.hanzi) = 0
            """
        ).fetchone()[0]
    assert mismatched == 0


def test_no_word_is_buried_in_examples(client):
    with get_connection() as connection:
        worst = connection.execute(
            """
            SELECT MAX(n) FROM (
                SELECT COUNT(*) AS n FROM word_examples GROUP BY vocabulary_id
            )
            """
        ).fetchone()[0]
    assert worst <= 4


def test_single_characters_are_kept_to_short_sentences(client):
    """的 matches nearly every sentence, so it must not collect four at random."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT we.hanzi, LENGTH(we.hanzi) AS n
            FROM word_examples we
            JOIN vocabulary v ON v.id = we.vocabulary_id
            WHERE LENGTH(v.hanzi) = 1
            """
        ).fetchall()
    assert rows
    assert all(row["n"] <= 18 for row in rows)


def test_open_ended_speaking_prompts_are_not_used_as_examples(client):
    """Their Vietnamese is a suggested outline, not a translation.

    The HSKK picture-description items gloss 两个同学在图书馆一起复习 with a whole
    story about how the exam went. Right for a speaking task, wrong beside a
    dictionary headword, so items carrying `hints` are excluded.
    """
    import json
    from pathlib import Path

    bank = json.loads(
        (Path(__file__).resolve().parent.parent / "scripts" / "data" / "hskk_bank.json")
        .read_text(encoding="utf-8")
    )
    hinted = {
        item["id"]
        for level in bank["levels"].values()
        for pool in level["pools"].values()
        for item in pool
        if item.get("hints")
    }
    assert hinted, "bộ đề phải còn dạng đề nói mở, nếu không test này vô nghĩa"

    with get_connection() as connection:
        used = {
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT source_ref FROM word_examples WHERE source = 'hskk'"
            )
        }
    assert not (used & hinted)


def test_reseeding_does_not_duplicate_examples(client):
    """The table is derived, so a second seed must rebuild rather than append."""
    from scripts.seed_data import seed_word_examples

    before = seed_word_examples()
    after = seed_word_examples()
    assert before == after

    with get_connection() as connection:
        duplicates = connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT vocabulary_id, hanzi, COUNT(*) AS n
                FROM word_examples GROUP BY 1, 2 HAVING n > 1
            )
            """
        ).fetchone()[0]
    assert duplicates == 0
