"""Dashboard statistics built from persisted data."""

from __future__ import annotations

from typing import Any

from backend.database import get_connection
from backend.services.sentence_service import get_stats as get_sentence_stats
from backend.services.quiz_service import get_stats as get_quiz_stats
from backend.services.listening_service import get_stats as get_listening_stats
from backend.services.vocabulary_service import list_hsk_levels
from backend.services.writing_service import get_progress_summary as get_writing_progress


def get_dashboard() -> dict[str, Any]:
    with get_connection() as connection:
        vocabulary_counts = connection.execute(
            """
            SELECT COUNT(v.id) AS total_vocabulary,
                   SUM(CASE WHEN COALESCE(p.status, 'new') != 'new' THEN 1 ELSE 0 END) AS viewed_vocabulary,
                   SUM(CASE WHEN p.status = 'learning' THEN 1 ELSE 0 END) AS learning_vocabulary,
                   SUM(CASE WHEN p.status = 'review' THEN 1 ELSE 0 END) AS review_vocabulary,
                   SUM(CASE WHEN p.status = 'mastered' THEN 1 ELSE 0 END) AS mastered_vocabulary
            FROM vocabulary v
            LEFT JOIN learning_progress p ON p.vocabulary_id = v.id
            """
        ).fetchone()
        matching_stats = connection.execute(
            """
            SELECT COUNT(DISTINCT s.id) AS matching_sessions,
                   COALESCE(SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END), 0) AS matching_correct,
                   COALESCE(SUM(CASE WHEN a.is_correct = 0 THEN 1 ELSE 0 END), 0) AS matching_incorrect
            FROM study_sessions s
            LEFT JOIN matching_attempts a ON a.session_id = s.id
            WHERE s.session_type = 'matching'
            """
        ).fetchone()
        recent_vocabulary = connection.execute(
            """
            SELECT v.id, v.hanzi, v.pinyin, v.meaning, p.status, p.last_reviewed_at
            FROM learning_progress p
            JOIN vocabulary v ON v.id = p.vocabulary_id
            WHERE p.last_reviewed_at IS NOT NULL
            ORDER BY p.last_reviewed_at DESC, p.updated_at DESC
            LIMIT 6
            """
        ).fetchall()
        recent_sessions = connection.execute(
            """
            SELECT * FROM (
                SELECT id, session_type, started_at, ended_at, total_items,
                       correct_items, incorrect_items
                FROM study_sessions
                UNION ALL
                SELECT id, 'sentence' AS session_type, started_at, ended_at,
                       total_items, correct_items, incorrect_items
                FROM sentence_sessions
                UNION ALL
                SELECT id, 'quiz' AS session_type, started_at, ended_at,
                       total_items, correct_items, incorrect_items
                FROM quiz_sessions
                UNION ALL
                SELECT id, 'listening' AS session_type, started_at, ended_at,
                       total_items, correct_items, incorrect_items
                FROM listening_sessions
                UNION ALL
                SELECT id, 'writing' AS session_type, started_at, ended_at,
                       total_items, correct_items, incorrect_items
                FROM writing_sessions
            )
            ORDER BY started_at DESC
            LIMIT 6
            """
        ).fetchall()

    correct = matching_stats["matching_correct"] or 0
    incorrect = matching_stats["matching_incorrect"] or 0
    attempts = correct + incorrect
    sentence_stats = get_sentence_stats()
    quiz_stats = get_quiz_stats()
    listening_stats = get_listening_stats()
    writing_progress = get_writing_progress()
    return {
        "total_vocabulary": vocabulary_counts["total_vocabulary"] or 0,
        "viewed_vocabulary": vocabulary_counts["viewed_vocabulary"] or 0,
        "learning_vocabulary": vocabulary_counts["learning_vocabulary"] or 0,
        "review_vocabulary": vocabulary_counts["review_vocabulary"] or 0,
        "mastered_vocabulary": vocabulary_counts["mastered_vocabulary"] or 0,
        "matching_sessions": matching_stats["matching_sessions"] or 0,
        "matching_correct": correct,
        "matching_incorrect": incorrect,
        "matching_accuracy": round(correct / attempts * 100, 1) if attempts else 0,
        "sentence_sessions": sentence_stats["sessions"],
        "sentence_correct": sentence_stats["correct"],
        "sentence_incorrect": sentence_stats["incorrect"],
        "sentence_accuracy": sentence_stats["accuracy"],
        "quiz_sessions": quiz_stats["sessions"],
        "quiz_correct": quiz_stats["correct"],
        "quiz_incorrect": quiz_stats["incorrect"],
        "quiz_accuracy": quiz_stats["accuracy"],
        "listening_sessions": listening_stats["sessions"],
        "listening_correct": listening_stats["correct"],
        "listening_incorrect": listening_stats["incorrect"],
        "listening_accuracy": listening_stats["accuracy"],
        "writing_practiced": writing_progress["practiced_count"],
        "writing_learning": writing_progress["learning_count"],
        "writing_mastered": writing_progress["mastered_count"],
        "hsk_levels": list_hsk_levels(),
        "recent_vocabulary": [dict(row) for row in recent_vocabulary],
        "recent_sessions": [dict(row) for row in recent_sessions],
    }
