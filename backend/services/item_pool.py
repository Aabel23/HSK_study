"""Drawing exam questions so the same one does not come back too soon.

A bigger question bank on its own does not stop repeats: `random.sample` over a
pool of 40 will still hand a learner the same passage twice in three sittings,
which is exactly what makes a mock exam feel fake. So the sampler remembers what
it has already handed out.

The rule is simple and has one job: **never show a question a second time while
an unseen one is left.** Items are sorted into tiers by how often they have been
shown, the tiers are consumed in order, and each tier is shuffled so two papers
drawn from the same tier are still different. Once the whole pool has been seen
the cycle starts again from the least-recently-seen items, so the bank degrades
gracefully instead of failing.

Exposure is recorded when the paper is built rather than when it is submitted:
a question the learner read and walked away from has still been spent.
"""

from __future__ import annotations

import random
from typing import Any, Iterable

from backend.database import get_connection, utc_now


def _exposure(connection: Any, keys: Iterable[str]) -> dict[str, tuple[int, str]]:
    """Seen-count and last-seen time for the keys that have any history."""
    keys = list(keys)
    if not keys:
        return {}
    placeholders = ",".join("?" * len(keys))
    rows = connection.execute(
        f"""
        SELECT item_key, seen_count, last_seen_at
        FROM item_exposure
        WHERE item_key IN ({placeholders})
        """,
        keys,
    ).fetchall()
    return {row["item_key"]: (row["seen_count"], row["last_seen_at"]) for row in rows}


def _record(connection: Any, keys: Iterable[str]) -> None:
    now = utc_now()
    connection.executemany(
        """
        INSERT INTO item_exposure (item_key, seen_count, last_seen_at)
        VALUES (?, 1, ?)
        ON CONFLICT(item_key) DO UPDATE SET
            seen_count = item_exposure.seen_count + 1,
            last_seen_at = excluded.last_seen_at
        """,
        [(key, now) for key in keys],
    )


def take(
    pool: list[dict[str, Any]],
    count: int,
    *,
    key_field: str = "id",
    record: bool = True,
) -> list[dict[str, Any]]:
    """Pick ``count`` items from ``pool``, freshest-to-the-learner first.

    Falls back to plain random sampling if the exposure table cannot be read,
    because a bookkeeping problem must never stop an exam from starting.
    """
    count = min(count, len(pool))
    if count <= 0:
        return []

    try:
        with get_connection() as connection:
            history = _exposure(connection, (item[key_field] for item in pool))

            # Sort key: fewest views first, then oldest view first. Items never
            # seen have no row at all and sort ahead of everything.
            def rank(item: dict[str, Any]) -> tuple[int, str]:
                seen_count, last_seen_at = history.get(item[key_field], (0, ""))
                return seen_count, last_seen_at

            shuffled = list(pool)
            random.shuffle(shuffled)  # breaks ties inside a tier
            chosen = sorted(shuffled, key=rank)[:count]

            if record:
                _record(connection, [item[key_field] for item in chosen])
    except Exception:  # noqa: BLE001 - the exam matters more than the history
        return random.sample(pool, count)

    # The paper should not present questions in "least used" order, which would
    # leak how fresh each one is; shuffle again before handing it over.
    random.shuffle(chosen)
    return chosen


def coverage(keys: Iterable[str]) -> dict[str, Any]:
    """How much of a pool the learner has already worked through."""
    keys = list(keys)
    if not keys:
        return {"total": 0, "seen": 0, "unseen": 0, "percentage": 0.0}
    with get_connection() as connection:
        history = _exposure(connection, keys)
    seen = sum(1 for key in keys if key in history)
    return {
        "total": len(keys),
        "seen": seen,
        "unseen": len(keys) - seen,
        "percentage": round(seen / len(keys) * 100, 1),
    }
