"""The character layer: lookup, word families, and the decoding drill.

Every other practice screen in this app asks the learner to recall a word they
have been taught. This one asks them to work out a word they have *not* been
taught, and that difference is the whole point.

A Vietnamese learner can do that, and learners of other native languages
largely cannot. Over half of formal Vietnamese vocabulary is Sino-Vietnamese,
and each Chinese character has a fixed âm Hán-Việt, so the characters of an
unseen word spell out a Vietnamese word the learner has known since school:

    图书馆  →  đồ · thư · quán  →  "đồ thư quán"  →  thư viện
    发展    →  phát · triển     →  "phát triển"   →  phát triển

Nothing here has to be memorised for that to work — it has to be *decoded*.
So the drill trains the decoding step: it deliberately draws words the learner
has never opened, shows the reading of each character, and asks for the
meaning. Getting good at it is what lets someone read past the end of the HSK
syllabus, which is where every word-list app leaves them.

The queries lean on `word_characters`, the word ↔ character index the seeder
builds, so a word family is one indexed lookup rather than a LIKE scan.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.database import get_connection, utc_now
from backend.services import session_store, srs_service
from backend.services.errors import InvalidOperationError, ResourceNotFoundError
from backend.services.gloss import short_gloss
from backend.services.pinyin_utils import plain_letters
from backend.services.session_store import SessionKind


SESSION = SessionKind(
    table="decode_sessions",
    not_found="Không tìm thấy phiên giải mã.",
    already_ended="Phiên giải mã này đã kết thúc.",
    completed="Đã hoàn tất phiên giải mã.",
)

#: Drill modes.
#:
#: ``han_viet_to_meaning`` is the headline one — the learner sees an unfamiliar
#: word plus the Hán-Việt reading of its characters and picks the meaning.
#: ``meaning_to_han_viet`` runs it backwards, and ``character_reading`` drills
#: the readings themselves, which is the prerequisite for either.
MODES: dict[str, str] = {
    "han_viet_to_meaning": "Đoán nghĩa từ âm Hán-Việt",
    "meaning_to_han_viet": "Chọn âm Hán-Việt đúng của từ",
    "character_reading": "Âm Hán-Việt của từng chữ",
}

OPTION_COUNT = 4

#: How many words to draw before keeping the three that match the target.
#:
#: Sized by the syllable-matching in :func:`next_question` rather than by the
#: option count. The bank mixes two-syllable words with four-syllable thành
#: ngữ, so a pool of sixteen regularly failed to hold three words the same
#: shape as the target and the question gave itself away on rhythm alone.
CANDIDATE_POOL = 60

CHARACTER_FIELDS = """
    c.hanzi, c.pinyin, c.han_viet, c.han_viet_source, c.meaning_vi,
    c.meaning_en, c.traditional, c.stroke_count, c.radical_number,
    c.radicals_json, c.radical_source, c.mnemonic_vi, c.stroke_hint_vi, c.hsk_level,
    c.word_count,
    COALESCE(p.status, 'new') AS status,
    COALESCE(p.seen_count, 0) AS seen_count,
    COALESCE(p.correct_count, 0) AS correct_count,
    COALESCE(p.incorrect_count, 0) AS incorrect_count,
    COALESCE(p.is_favorite, 0) AS is_favorite,
    COALESCE(p.repetitions, 0) AS repetitions,
    COALESCE(p.lapses, 0) AS lapses,
    p.due_at,
    p.last_seen_at
"""


def _row_to_character(row: Any) -> dict[str, Any]:
    entry = dict(row)
    entry["radicals"] = json.loads(entry.pop("radicals_json") or "[]")
    return entry


# --------------------------------------------------------------------------
# Lookup
# --------------------------------------------------------------------------


def get_character(hanzi: str) -> dict[str, Any]:
    """One character, with its radicals resolved and its word family attached."""
    with get_connection() as connection:
        row = connection.execute(
            f"""
            SELECT {CHARACTER_FIELDS}
            FROM characters c
            LEFT JOIN character_progress p ON p.hanzi = c.hanzi
            WHERE c.hanzi = ?
            """,
            (hanzi,),
        ).fetchone()
        if not row:
            raise ResourceNotFoundError("Không tìm thấy chữ Hán này.")
        character = _row_to_character(row)

        # Radical glosses turn "⺍ 冖 子" into something a learner can hold on
        # to; a bare list of components teaches nothing.
        if character["radicals"]:
            placeholders = ",".join("?" * len(character["radicals"]))
            character["radical_details"] = [
                dict(item)
                for item in connection.execute(
                    f"SELECT hanzi, name_vi, meaning_vi, mnemonic_vi FROM radicals"
                    f" WHERE hanzi IN ({placeholders})",
                    character["radicals"],
                )
            ]
        else:
            character["radical_details"] = []

        character["words"] = [
            dict(item)
            for item in connection.execute(
                """
                SELECT v.id, v.hanzi, v.pinyin, v.han_viet, v.meaning, v.hsk_level,
                       COALESCE(lp.status, 'new') AS status
                FROM word_characters wc
                JOIN vocabulary v ON v.id = wc.vocabulary_id
                LEFT JOIN learning_progress lp ON lp.vocabulary_id = v.id
                WHERE wc.hanzi = ?
                ORDER BY CASE v.hsk_level
                    WHEN '1' THEN 1 WHEN '2' THEN 2 WHEN '3' THEN 3
                    WHEN '4' THEN 4 WHEN '5' THEN 5 WHEN '6' THEN 6 ELSE 7 END,
                    LENGTH(v.hanzi), v.hanzi
                LIMIT 60
                """,
                (hanzi,),
            )
        ]
    return character


def list_characters(
    search: str | None = None,
    hsk_level: str | None = None,
    limit: int = 40,
    offset: int = 0,
    sort: str = "reach",
    in_bank_only: bool = True,
) -> dict[str, Any]:
    """Browse the character table.

    Defaults to ``sort="reach"`` — most word-unlocking first — because that is
    the order worth learning them in. A learner who takes the top 100 by reach
    covers a large share of the whole bank, which no HSK word list can promise.
    """
    conditions: list[str] = []
    parameters: list[Any] = []
    if in_bank_only:
        conditions.append("c.word_count > 0")
    if hsk_level:
        conditions.append("c.hsk_level = ?")
        parameters.append(hsk_level)
    if search and search.strip():
        term = f"%{search.strip()}%"
        # Searched twice over: once as typed, and once accent-free, because
        # "xue" and "hoc" are what a learner reaches for before "xué" and "học".
        plain = f"%{plain_letters(search)}%"
        conditions.append(
            "(c.hanzi LIKE ? OR c.han_viet LIKE ? OR c.pinyin LIKE ? OR c.meaning_vi LIKE ?"
            " OR c.pinyin_plain LIKE ? OR c.han_viet_plain LIKE ?)"
        )
        parameters.extend([term, term, term, term, plain, plain])

    # Whitelisted: the value is interpolated into SQL.
    orders = {
        "reach": "c.word_count DESC, c.hanzi",
        "strokes": "c.stroke_count IS NULL, c.stroke_count ASC, c.hanzi",
        "level": "c.hsk_level, c.word_count DESC",
        "han_viet": "c.han_viet COLLATE NOCASE, c.hanzi",
    }
    order_clause = orders.get(sort, orders["reach"])
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with get_connection() as connection:
        total = connection.execute(
            f"SELECT COUNT(*) FROM characters c {where_clause}", parameters
        ).fetchone()[0]
        rows = connection.execute(
            f"""
            SELECT {CHARACTER_FIELDS}
            FROM characters c
            LEFT JOIN character_progress p ON p.hanzi = c.hanzi
            {where_clause}
            ORDER BY {order_clause}
            LIMIT ? OFFSET ?
            """,
            [*parameters, limit, offset],
        ).fetchall()
    return {
        "items": [_row_to_character(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def stats() -> dict[str, Any]:
    """Headline numbers for the decode screen."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM characters WHERE word_count > 0) AS total,
                (SELECT COUNT(*) FROM characters
                    WHERE word_count > 0 AND han_viet <> '') AS with_reading,
                (SELECT COUNT(*) FROM character_progress WHERE status = 'mastered')
                    AS mastered,
                (SELECT COUNT(*) FROM character_progress WHERE status = 'learning')
                    AS learning,
                (SELECT COUNT(*) FROM vocabulary WHERE han_viet IS NOT NULL)
                    AS words_decodable,
                (SELECT COUNT(*) FROM vocabulary) AS words_total,
                (SELECT COUNT(*) FROM character_progress
                    WHERE due_at IS NOT NULL AND due_at <= :now) AS due_now
            """,
            {"now": utc_now()},
        ).fetchone()
        result = dict(row)
        # How much vocabulary the characters already marked mastered reach. This
        # is the number that makes the case for the whole feature, so it is
        # computed rather than estimated.
        result["words_unlocked"] = connection.execute(
            """
            SELECT COUNT(DISTINCT wc.vocabulary_id)
            FROM word_characters wc
            JOIN character_progress p ON p.hanzi = wc.hanzi
            WHERE p.status = 'mastered'
            """
        ).fetchone()[0]
    return result


# --------------------------------------------------------------------------
# Progress
# --------------------------------------------------------------------------


def set_status(hanzi: str, status: str) -> dict[str, Any]:
    if status not in {"new", "learning", "mastered"}:
        raise InvalidOperationError("Trạng thái không hợp lệ.")
    now = utc_now()
    with get_connection() as connection:
        exists = connection.execute(
            "SELECT 1 FROM characters WHERE hanzi = ?", (hanzi,)
        ).fetchone()
        if not exists:
            raise ResourceNotFoundError("Không tìm thấy chữ Hán này.")
        connection.execute(
            """
            INSERT INTO character_progress (hanzi, status, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(hanzi) DO UPDATE SET
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            (hanzi, status, now, now),
        )
    return {"hanzi": hanzi, "status": status}


#: Ten minutes, matching `srs_service.RELEARN_INTERVAL_DAYS`. A missed reading
#: should come back inside the same sitting.
RELEARN_INTERVAL_DAYS = 10 / (24 * 60)
DEFAULT_EASE = 2.5


def _next_character_interval(interval: float, repetitions: int, ease: float) -> float:
    """SM-2's growth curve, with the ratings collapsed to right or wrong.

    The word queue asks the learner how hard a card felt and has four ratings to
    work with. A character question is multiple choice, so there is no such
    signal to ask for — only whether they got it. Same shape of schedule, one
    bit of input.
    """
    if repetitions <= 1:
        return 1.0
    if repetitions == 2:
        return 4.0
    return round(min(max(interval, 1.0) * ease, 365.0), 4)


def _record_seen(connection: Any, hanzi: str, is_correct: bool) -> None:
    """Count the answer and move the character's schedule.

    Characters are the unit most worth scheduling in this app: unlike a word, a
    character carries over to vocabulary the learner has never studied, so a
    reading recalled today is worth something on a page they read next month.
    Before this, `character_progress` counted right and wrong answers and
    nothing else, and the drill drew at random — a reading missed thirty
    seconds ago was no likelier to come back than any other.
    """
    now = utc_now()
    current = connection.execute(
        """
        SELECT COALESCE(ease_factor, ?) AS ease_factor,
               COALESCE(interval_days, 0) AS interval_days,
               COALESCE(repetitions, 0) AS repetitions,
               COALESCE(lapses, 0) AS lapses
        FROM character_progress WHERE hanzi = ?
        """,
        (DEFAULT_EASE, hanzi),
    ).fetchone()

    ease = float(current["ease_factor"]) if current else DEFAULT_EASE
    interval = float(current["interval_days"]) if current else 0.0
    repetitions = int(current["repetitions"]) if current else 0
    lapses = int(current["lapses"]) if current else 0

    if is_correct:
        repetitions += 1
        interval = _next_character_interval(interval, repetitions, ease)
        ease = min(2.8, ease + 0.05)
    else:
        repetitions = 0
        lapses += 1
        interval = RELEARN_INTERVAL_DAYS
        ease = max(1.3, ease - 0.2)

    due_at = (
        datetime.now(timezone.utc) + timedelta(days=interval)
    ).isoformat(timespec="seconds")
    # Six correct answers in a row is roughly a month of intervals; below that
    # the learner is still meeting it. Marking a character mastered by hand on
    # the lookup screen stays available and is not undone here.
    status = "mastered" if repetitions >= 6 else "learning"

    connection.execute(
        """
        INSERT INTO character_progress (
            hanzi, status, seen_count, correct_count, incorrect_count,
            last_seen_at, created_at, updated_at,
            ease_factor, interval_days, repetitions, lapses, due_at
        ) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(hanzi) DO UPDATE SET
            seen_count = seen_count + 1,
            correct_count = correct_count + excluded.correct_count,
            incorrect_count = incorrect_count + excluded.incorrect_count,
            last_seen_at = excluded.last_seen_at,
            -- A character never drops back out of 'mastered' on one slip; the
            -- shortened interval is what a lapse costs it.
            status = CASE
                WHEN character_progress.status = 'mastered' THEN 'mastered'
                ELSE excluded.status
            END,
            updated_at = excluded.updated_at,
            ease_factor = excluded.ease_factor,
            interval_days = excluded.interval_days,
            repetitions = excluded.repetitions,
            lapses = excluded.lapses,
            due_at = excluded.due_at
        """,
        (
            hanzi,
            status,
            1 if is_correct else 0,
            0 if is_correct else 1,
            now,
            now,
            now,
            ease,
            interval,
            repetitions,
            lapses,
            due_at,
        ),
    )


# --------------------------------------------------------------------------
# The decoding drill
# --------------------------------------------------------------------------


def create_session(mode: str, count: int, hsk_level: str | None = None) -> dict[str, Any]:
    if mode not in MODES:
        raise InvalidOperationError("Chế độ giải mã không hợp lệ.")
    session_id = session_store.start(
        SESSION, hsk_level=hsk_level or "all", mode=mode, total_items=count
    )
    return {
        "session_id": session_id,
        "mode": mode,
        "mode_label": MODES[mode],
        "total": count,
        "hsk_level": hsk_level or "all",
    }


def _draw_words(count: int, hsk_level: str | None, *, unseen_first: bool) -> list[dict[str, Any]]:
    """Candidate words for a drill question.

    ``unseen_first`` is what separates this from every other drill in the app.
    The others hand back words the learner has been studying; decoding is only
    being practised if the word on screen is one they have *not* studied, so
    untouched words are drawn first and studied ones are the fallback for a
    learner who has already opened everything at their level.
    """
    conditions = ["v.han_viet IS NOT NULL", "LENGTH(v.hanzi) >= 2"]
    parameters: list[Any] = []
    if hsk_level:
        conditions.append("v.hsk_level = ?")
        parameters.append(hsk_level)
    where_clause = " AND ".join(conditions)

    with get_connection() as connection:
        rows = []
        if unseen_first:
            rows = connection.execute(
                f"""
                SELECT v.id, v.hanzi, v.pinyin, v.han_viet, v.meaning, v.hsk_level
                FROM vocabulary v
                LEFT JOIN learning_progress p ON p.vocabulary_id = v.id
                WHERE {where_clause} AND COALESCE(p.status, 'new') = 'new'
                ORDER BY RANDOM() LIMIT ?
                """,
                [*parameters, count],
            ).fetchall()
        if len(rows) < count:
            rows = connection.execute(
                f"""
                SELECT v.id, v.hanzi, v.pinyin, v.han_viet, v.meaning, v.hsk_level
                FROM vocabulary v
                WHERE {where_clause}
                ORDER BY RANDOM() LIMIT ?
                """,
                [*parameters, count],
            ).fetchall()
    return [dict(row) for row in rows]


def _character_readings(connection: Any, word: str) -> list[dict[str, Any]]:
    """The per-character breakdown shown as the clue."""
    chars = [char for char in word if "一" <= char <= "鿿"]
    if not chars:
        return []
    placeholders = ",".join("?" * len(chars))
    found = {
        row["hanzi"]: dict(row)
        for row in connection.execute(
            f"""
            SELECT hanzi, pinyin, han_viet, meaning_vi, mnemonic_vi, word_count
            FROM characters WHERE hanzi IN ({placeholders})
            """,
            chars,
        )
    }
    # Rebuilt in word order, and repeated characters keep both slots.
    return [
        found.get(char, {"hanzi": char, "pinyin": "", "han_viet": "", "meaning_vi": ""})
        for char in chars
    ]


def next_question(session_id: int) -> dict[str, Any]:
    """Draw one question for an open session."""
    with get_connection() as connection:
        session = session_store.require_open(connection, SESSION, session_id)
        mode = session["mode"]
        level = None if session["hsk_level"] == "all" else session["hsk_level"]

    if mode == "character_reading":
        return _character_reading_question(session_id, level)

    words = _draw_words(CANDIDATE_POOL, level, unseen_first=True)
    if len(words) < OPTION_COUNT:
        raise InvalidOperationError("Không đủ từ có âm Hán-Việt để tạo câu hỏi.")

    target, *rest = words
    with get_connection() as connection:
        breakdown = _character_readings(connection, target["hanzi"])

    if mode == "meaning_to_han_viet":
        # Distractors are other words' readings, so a wrong answer is a real
        # near-miss rather than obvious noise — and they are matched on
        # syllable count, because "tưởng phương thiết pháp" beside "chủ biện"
        # is answered by counting words rather than by knowing any of them.
        syllables = len(target["han_viet"].split())
        pool = [word for word in rest if word["han_viet"] != target["han_viet"]]
        pool.sort(key=lambda word: abs(len(word["han_viet"].split()) - syllables))
        options = _shuffled_options(
            target["han_viet"], [word["han_viet"] for word in pool]
        )
        prompt = {"meaning": short_gloss(target["meaning"], max_senses=2, max_chars=64)}
    else:
        answer = short_gloss(target["meaning"], max_senses=1, max_chars=42)
        pool = [word for word in rest if word["meaning"] != target["meaning"]]
        pool.sort(
            key=lambda word: abs(
                len(short_gloss(word["meaning"], max_senses=1, max_chars=42)) - len(answer)
            )
        )
        options = _shuffled_options(
            answer,
            [short_gloss(word["meaning"], max_senses=1, max_chars=42) for word in pool],
        )
        prompt = {}

    return {
        "session_id": session_id,
        "mode": mode,
        "mode_label": MODES[mode],
        "vocabulary_id": target["id"],
        "word": target["hanzi"],
        "pinyin": target["pinyin"],
        "han_viet": target["han_viet"],
        "hsk_level": target["hsk_level"],
        "meaning": target["meaning"],
        "breakdown": breakdown,
        "options": options,
        "prompt": prompt,
    }


def _character_reading_question(session_id: int, level: str | None) -> dict[str, Any]:
    """Which âm Hán-Việt belongs to this character?"""
    conditions = ["c.han_viet <> ''", "c.word_count > 0"]
    parameters: list[Any] = []
    if level:
        conditions.append("c.hsk_level = ?")
        parameters.append(level)
    where_clause = " AND ".join(conditions)
    select = """
            SELECT c.hanzi, c.pinyin, c.han_viet, c.meaning_vi, c.mnemonic_vi,
                   c.word_count, c.hsk_level
            FROM characters c
    """
    with get_connection() as connection:
        # A reading the learner missed earlier should come back before a
        # reading picked out of eight thousand at random. Overdue first, then
        # the widest-reaching characters they have not met — which is the order
        # the leverage list already argues for.
        due = connection.execute(
            f"""
            {select}
            JOIN character_progress p ON p.hanzi = c.hanzi
            WHERE {where_clause} AND p.due_at IS NOT NULL AND p.due_at <= ?
            ORDER BY p.due_at ASC LIMIT 1
            """,
            [*parameters, utc_now()],
        ).fetchone()

        rows = connection.execute(
            f"""
            {select}
            WHERE {where_clause}
            ORDER BY RANDOM() LIMIT ?
            """,
            [*parameters, OPTION_COUNT * 4],
        ).fetchall()
        if len(rows) < OPTION_COUNT:
            raise InvalidOperationError("Không đủ chữ Hán để tạo câu hỏi.")
        # The distractors still come from the random draw; only the character
        # being asked about is chosen by schedule.
        target = dict(due) if due else dict(rows[0])
        # Every reading here is a single syllable, so there is no length
        # giveaway to defend against — only duplicates to filter out.
        distractors = [
            dict(row)["han_viet"]
            for row in rows[1:]
            if row["han_viet"] != target["han_viet"]
        ]
        breakdown = [target]
    return {
        "session_id": session_id,
        "mode": "character_reading",
        "mode_label": MODES["character_reading"],
        "vocabulary_id": None,
        "word": target["hanzi"],
        "pinyin": target["pinyin"],
        "han_viet": target["han_viet"],
        "hsk_level": target["hsk_level"],
        "meaning": target["meaning_vi"],
        "breakdown": breakdown,
        "options": _shuffled_options(target["han_viet"], distractors),
        "prompt": {},
    }


def _shuffled_options(answer: str, distractors: list[str]) -> list[str]:
    """``answer`` plus distinct distractors, shuffled."""
    options = [answer]
    for candidate in distractors:
        if len(options) >= OPTION_COUNT:
            break
        if candidate and candidate not in options:
            options.append(candidate)
    if len(options) < OPTION_COUNT:
        raise InvalidOperationError("Không đủ lựa chọn khác nhau để tạo câu hỏi.")
    random.shuffle(options)
    return options


def record_attempt(
    session_id: int,
    word: str,
    is_correct: bool,
    vocabulary_id: int | None = None,
) -> dict[str, Any]:
    """Log an answer and credit every character the word is built from.

    Crediting each character rather than the word is the point: answering 图书馆
    correctly is evidence about 图, 书 and 馆, and it is those three that carry
    over to the next unseen word.
    """
    with get_connection() as connection:
        session = session_store.require_open(connection, SESSION, session_id)
        connection.execute(
            """
            INSERT INTO decode_attempts (
                session_id, vocabulary_id, word, mode, is_correct, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                vocabulary_id,
                word,
                session["mode"],
                1 if is_correct else 0,
                utc_now(),
            ),
        )
        for char in {c for c in word if "一" <= c <= "鿿"}:
            _record_seen(connection, char, is_correct)
    # The characters are credited above; the word itself belongs to the review
    # queue, so a word the learner could not decode comes back round sooner.
    if not is_correct:
        srs_service.record_lapse(vocabulary_id, source="decode")
    return {"message": "Đã ghi nhận câu trả lời.", "is_correct": is_correct}


def complete_session(
    session_id: int, total_items: int, correct_items: int, incorrect_items: int
) -> dict[str, Any]:
    return session_store.complete(
        SESSION, session_id, total_items, correct_items, incorrect_items
    )


def drill_stats() -> dict[str, Any]:
    return session_store.attempt_stats(SESSION, "decode_attempts")
