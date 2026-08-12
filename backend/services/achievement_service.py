"""Achievements derived from stored progress.

Nothing is duplicated into the achievements table except the unlock timestamp:
progress is always recomputed from the source data, so the list stays correct
even if a database is restored from a backup taken at a different point in time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from backend.database import get_connection, utc_now
from backend.services import streak_service


@dataclass(frozen=True)
class Achievement:
    code: str
    title: str
    description: str
    icon: str
    tier: str
    target: int
    measure: Callable[[dict[str, Any]], int]


CATALOG: tuple[Achievement, ...] = (
    Achievement("first_steps", "Bước đầu tiên", "Ôn tập từ đầu tiên của bạn.", "spark", "bronze", 1, lambda s: s["total_reviews"]),
    Achievement("century", "Trăm lượt ôn", "Hoàn thành 100 lượt ôn tập.", "layers", "bronze", 100, lambda s: s["total_reviews"]),
    Achievement("thousand", "Nghìn lượt ôn", "Hoàn thành 1.000 lượt ôn tập.", "layers", "gold", 1000, lambda s: s["total_reviews"]),
    Achievement("streak_3", "Ba ngày liền", "Học 3 ngày liên tiếp.", "flame", "bronze", 3, lambda s: s["longest_streak"]),
    Achievement("streak_7", "Tuần chuyên cần", "Học 7 ngày liên tiếp.", "flame", "silver", 7, lambda s: s["longest_streak"]),
    Achievement("streak_30", "Tháng bền bỉ", "Học 30 ngày liên tiếp.", "flame", "gold", 30, lambda s: s["longest_streak"]),
    Achievement("streak_100", "Trăm ngày không nghỉ", "Học 100 ngày liên tiếp.", "flame", "diamond", 100, lambda s: s["longest_streak"]),
    Achievement("mastered_50", "Vốn từ vững", "Thuộc 50 từ vựng.", "check", "bronze", 50, lambda s: s["mastered"]),
    Achievement("mastered_150", "Nền tảng HSK 1", "Thuộc 150 từ vựng.", "check", "silver", 150, lambda s: s["mastered"]),
    Achievement("mastered_600", "Trình độ HSK 3", "Thuộc 600 từ vựng.", "check", "gold", 600, lambda s: s["mastered"]),
    Achievement("mastered_2500", "Trình độ HSK 5", "Thuộc 2.500 từ vựng.", "check", "diamond", 2500, lambda s: s["mastered"]),
    Achievement("writer_25", "Nét bút đầu tiên", "Luyện viết 25 chữ Hán.", "pencil", "bronze", 25, lambda s: s["writing_practiced"]),
    Achievement("writer_200", "Thư pháp gia", "Luyện viết 200 chữ Hán.", "pencil", "gold", 200, lambda s: s["writing_practiced"]),
    Achievement("listener_100", "Đôi tai nhạy", "Trả lời đúng 100 câu luyện nghe.", "headphones", "silver", 100, lambda s: s["listening_correct"]),
    Achievement("quiz_100", "Bậc thầy kiểm tra", "Trả lời đúng 100 câu kiểm tra.", "target", "silver", 100, lambda s: s["quiz_correct"]),
    Achievement("level_5", "Cấp độ 5", "Đạt cấp độ 5 kinh nghiệm.", "star", "silver", 5, lambda s: s["level"]),
    Achievement("level_10", "Cấp độ 10", "Đạt cấp độ 10 kinh nghiệm.", "star", "gold", 10, lambda s: s["level"]),
    Achievement("collector", "Nhà sưu tầm", "Đánh dấu 25 từ yêu thích.", "bookmark", "bronze", 25, lambda s: s["favorites"]),
)


def _gather_stats() -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM review_log) AS total_reviews,
                (SELECT COUNT(*) FROM learning_progress WHERE status = 'mastered') AS mastered,
                (SELECT COUNT(*) FROM learning_progress WHERE is_favorite = 1) AS favorites,
                (SELECT COUNT(*) FROM writing_progress) AS writing_practiced,
                (SELECT COALESCE(SUM(correct_items), 0) FROM listening_sessions) AS listening_correct,
                (SELECT COALESCE(SUM(correct_items), 0) FROM quiz_sessions) AS quiz_correct
            """
        ).fetchone()
    streak = streak_service.get_summary(heatmap_days=1)
    return {
        "total_reviews": row["total_reviews"] or 0,
        "mastered": row["mastered"] or 0,
        "favorites": row["favorites"] or 0,
        "writing_practiced": row["writing_practiced"] or 0,
        "listening_correct": row["listening_correct"] or 0,
        "quiz_correct": row["quiz_correct"] or 0,
        "longest_streak": streak["longest_streak"],
        "level": streak["level"],
    }


def evaluate() -> dict[str, Any]:
    """Recompute every achievement, persisting first-time unlocks."""
    stats = _gather_stats()
    now = utc_now()

    with get_connection() as connection:
        unlocked_rows = connection.execute(
            "SELECT code, unlocked_at FROM achievements"
        ).fetchall()
        unlocked = {row["code"]: row["unlocked_at"] for row in unlocked_rows}

        newly_unlocked: list[str] = []
        for achievement in CATALOG:
            if achievement.code in unlocked:
                continue
            if achievement.measure(stats) >= achievement.target:
                connection.execute(
                    "INSERT OR IGNORE INTO achievements (code, unlocked_at) VALUES (?, ?)",
                    (achievement.code, now),
                )
                unlocked[achievement.code] = now
                newly_unlocked.append(achievement.code)

    items = []
    for achievement in CATALOG:
        value = achievement.measure(stats)
        items.append(
            {
                "code": achievement.code,
                "title": achievement.title,
                "description": achievement.description,
                "icon": achievement.icon,
                "tier": achievement.tier,
                "target": achievement.target,
                "progress": min(value, achievement.target),
                "percentage": round(min(100.0, value / achievement.target * 100), 1),
                "unlocked": achievement.code in unlocked,
                "unlocked_at": unlocked.get(achievement.code),
            }
        )

    return {
        "items": items,
        "unlocked_count": sum(1 for item in items if item["unlocked"]),
        "total_count": len(items),
        "newly_unlocked": newly_unlocked,
    }
