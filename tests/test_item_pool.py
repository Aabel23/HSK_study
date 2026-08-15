"""The sampler's one promise: no repeat while an unseen question remains."""

from __future__ import annotations

from backend.database import get_connection
from backend.services import item_pool


def _pool(size: int) -> list[dict[str, str]]:
    return [{"id": f"q-{index:03d}"} for index in range(size)]


def test_a_pool_is_exhausted_before_anything_repeats(client):
    pool = _pool(12)
    seen: list[str] = []
    # Four draws of three cover the pool exactly once.
    for _ in range(4):
        seen.extend(item["id"] for item in item_pool.take(pool, 3))
    assert len(seen) == 12
    assert len(set(seen)) == 12, "một câu đã lặp lại trước khi dùng hết ngân hàng"


def test_repeats_only_start_once_everything_has_been_seen(client):
    pool = _pool(6)
    first = {item["id"] for item in item_pool.take(pool, 6)}
    second = {item["id"] for item in item_pool.take(pool, 3)}
    assert first == set(item["id"] for item in pool)
    assert second <= first  # nothing new is left, so reuse is expected


def test_asking_for_more_than_the_pool_holds_returns_the_pool(client):
    chosen = item_pool.take(_pool(4), 10)
    assert len(chosen) == 4


def test_an_empty_pool_is_not_an_error(client):
    assert item_pool.take([], 5) == []


def test_taking_records_what_was_shown(client):
    item_pool.take(_pool(5), 2)
    with get_connection() as connection:
        rows = connection.execute("SELECT COUNT(*) FROM item_exposure").fetchone()
    assert rows[0] == 2


def test_preview_mode_does_not_spend_the_questions(client):
    pool = _pool(5)
    item_pool.take(pool, 2, record=False)
    assert item_pool.coverage([item["id"] for item in pool])["seen"] == 0


def test_coverage_counts_what_is_left(client):
    pool = _pool(10)
    item_pool.take(pool, 4)
    coverage = item_pool.coverage([item["id"] for item in pool])
    assert coverage == {"total": 10, "seen": 4, "unseen": 6, "percentage": 40.0}


def test_two_exam_papers_from_a_large_pool_do_not_overlap(client):
    pool = _pool(30)
    first = {item["id"] for item in item_pool.take(pool, 10)}
    second = {item["id"] for item in item_pool.take(pool, 10)}
    assert not (first & second)
