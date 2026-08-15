"""A read-only inventory of everything the app can teach from.

The learning content now comes from four places — the vocabulary bank, the
sentence corpus, the grammar lessons and the two exam banks — and until this
existed there was no single answer to "how much is there, and how much of it
has this learner already seen?".

That question matters for a specific reason: a mock exam stops being a mock exam
once the learner recognises the questions. :mod:`backend.services.item_pool`
hands out unseen items first, and the coverage numbers here are what say when a
pool is running dry and worth regrowing with ``scripts/generate_bank.py``.

Strictly read-only. Growing the bank is a build-time job done under review, not
something the running app does to itself.
"""

from __future__ import annotations

from typing import Any

from backend.database import get_connection
from backend.services import gemini_service, hskk_service, item_pool, reading_service


#: Below this share of unseen questions a pool can no longer promise a fresh
#: paper, which is the point at which it wants regenerating.
LOW_STOCK_THRESHOLD = 25.0


def _pool_report(pool: dict[str, Any]) -> dict[str, Any]:
    """Turn one raw pool into inventory figures, dropping the answer key."""
    items = pool["items"]
    draw = pool["draw_per_exam"]
    coverage = item_pool.coverage([item["id"] for item in items])
    generated = sum(1 for item in items if item.get("source") == "gemini")
    unseen_percentage = round(100.0 - coverage["percentage"], 1)
    return {
        "label": pool["label"],
        "question_type": pool["question_type"],
        "total": len(items),
        "generated": generated,
        "handwritten": len(items) - generated,
        "draw_per_exam": draw,
        # How many different papers this pool can still supply before it has to
        # start repeating itself.
        "fresh_exams": coverage["unseen"] // draw if draw else 0,
        "seen": coverage["seen"],
        "unseen": coverage["unseen"],
        "unseen_percentage": unseen_percentage,
        "low_stock": unseen_percentage < LOW_STOCK_THRESHOLD,
    }


def _library_totals() -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM vocabulary) AS vocabulary,
                (SELECT COUNT(*) FROM sentences) AS sentences,
                (SELECT COUNT(*) FROM grammar_points) AS grammar_points,
                (SELECT COUNT(*) FROM item_exposure) AS items_seen
            """
        ).fetchone()
        by_level = connection.execute(
            """
            SELECT hsk_level AS level,
                   (SELECT COUNT(*) FROM vocabulary v WHERE v.hsk_level = x.hsk_level) AS vocabulary,
                   (SELECT COUNT(*) FROM sentences s WHERE s.hsk_level = x.hsk_level) AS sentences,
                   (SELECT COUNT(*) FROM grammar_points g WHERE g.hsk_level = x.hsk_level) AS grammar
            FROM (SELECT DISTINCT hsk_level FROM vocabulary) x
            ORDER BY hsk_level
            """
        ).fetchall()
    return {
        "vocabulary": row["vocabulary"] or 0,
        "sentences": row["sentences"] or 0,
        "grammar_points": row["grammar_points"] or 0,
        "items_seen": row["items_seen"] or 0,
        "by_level": [dict(entry) for entry in by_level],
    }


def get_overview() -> dict[str, Any]:
    """Everything the Ngân hàng đề screen shows, in one request."""
    exams = []
    for band in hskk_service.list_exam_levels():
        code = band["code"]
        pools = [
            _pool_report(pool)
            for pool in reading_service.list_pools(code) + hskk_service.list_pools(code)
        ]
        total = sum(pool["total"] for pool in pools)
        unseen = sum(pool["unseen"] for pool in pools)
        exams.append(
            {
                **band,
                "total_items": total,
                "generated_items": sum(pool["generated"] for pool in pools),
                "unseen_items": unseen,
                "unseen_percentage": round(unseen / total * 100, 1) if total else 0.0,
                # The bottleneck pool decides how many fresh papers are left,
                # because every paper needs one draw from every part.
                "fresh_exams": min((pool["fresh_exams"] for pool in pools), default=0),
                "low_stock_pools": [p["label"] for p in pools if p["low_stock"]],
                "pools": pools,
            }
        )

    return {
        "library": _library_totals(),
        "exams": exams,
        "ai_available": gemini_service.is_configured(),
        "generator_command": "python -m scripts.generate_bank --bank reading --level beginner --count 50",
    }
