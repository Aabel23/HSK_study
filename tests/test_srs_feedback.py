"""Getting a word wrong anywhere pulls it back into the review queue.

Until now the SM-2 schedule only moved on the Ôn tập screen. A learner could
miss 我 in a listening drill, miss it again while typing, and the queue that
decides what to show tomorrow never heard about either mistake.

The feedback is deliberately one-way — wrong answers only. A four-option
question is right by luck a quarter of the time, so a correct answer must not
lengthen an interval or a guess would look like mastery.
"""

import pytest

from backend.database import get_connection


def any_word(client):
    return client.get("/api/vocabulary?limit=1").json()["items"][0]


def schedule(vocabulary_id):
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT due_at, interval_days, repetitions, lapses, status
            FROM learning_progress WHERE vocabulary_id = ?
            """,
            (vocabulary_id,),
        ).fetchone()


def review_sources(vocabulary_id):
    with get_connection() as connection:
        return [
            row[0]
            for row in connection.execute(
                "SELECT source FROM review_log WHERE vocabulary_id = ? ORDER BY id",
                (vocabulary_id,),
            )
        ]


def settle(client, vocabulary_id):
    """Put a word on a long interval, the way a good review would."""
    for _ in range(3):
        client.post("/api/review/submit", json={"vocabulary_id": vocabulary_id, "rating": "easy"})
    return schedule(vocabulary_id)


# --------------------------------------------------------------------------
# One drill per test, because each wires the hook up separately
# --------------------------------------------------------------------------


def quiz_wrong(client, word):
    session = client.post("/api/quiz/session", json={"count": 1}).json()
    client.post(
        "/api/quiz/attempt",
        json={
            "session_id": session["session_id"],
            "vocabulary_id": word["id"],
            "question_type": "mcq_meaning",
            "is_correct": False,
        },
    )


def listening_wrong(client, word):
    session = client.post(
        "/api/listening/session", json={"mode": "audio_to_meaning", "count": 1}
    ).json()
    client.post(
        "/api/listening/attempt",
        json={
            "session_id": session["session_id"],
            "vocabulary_id": word["id"],
            "mode": "audio_to_meaning",
            "is_correct": False,
        },
    )


def matching_wrong(client, word):
    session = client.post("/api/matching/session", json={"mode": "meaning", "count": 6}).json()
    client.post(
        "/api/matching/attempt",
        json={
            "session_id": session["session_id"],
            "vocabulary_id": word["id"],
            "mode": "meaning",
            "is_correct": False,
        },
    )


DRILLS = [
    ("quiz", quiz_wrong),
    ("listening", listening_wrong),
    ("matching", matching_wrong),
]


@pytest.mark.parametrize(("source", "answer_wrong"), DRILLS, ids=[d[0] for d in DRILLS])
def test_a_wrong_answer_brings_the_word_forward(client, source, answer_wrong):
    word = any_word(client)
    before = settle(client, word["id"])
    assert before["interval_days"] > 1, "phải đang ở khoảng ôn dài thì mới thấy được tác dụng"

    answer_wrong(client, word)

    after = schedule(word["id"])
    assert after["interval_days"] < before["interval_days"]
    assert after["due_at"] < before["due_at"]
    assert after["lapses"] == before["lapses"] + 1
    # And the log says which screen it came from, not just "review".
    assert review_sources(word["id"])[-1] == source


@pytest.mark.parametrize(("source", "answer_wrong"), DRILLS, ids=[d[0] for d in DRILLS])
def test_the_word_comes_due_again_within_minutes(client, source, answer_wrong):
    """SM-2 relearns a lapse after ten minutes, not instantly.

    So the check is that a word a month out is now minutes out, rather than
    that it is already sitting in the queue — it is not, and should not be.
    """
    from datetime import datetime, timedelta, timezone

    word = any_word(client)
    settle(client, word["id"])

    answer_wrong(client, word)

    due = datetime.fromisoformat(schedule(word["id"])["due_at"])
    assert due < datetime.now(timezone.utc) + timedelta(hours=1)


def test_a_correct_answer_leaves_the_schedule_alone(client):
    """A lucky guess must not look like mastery."""
    word = any_word(client)
    before = settle(client, word["id"])
    session = client.post("/api/quiz/session", json={"count": 1}).json()

    for _ in range(3):
        client.post(
            "/api/quiz/attempt",
            json={
                "session_id": session["session_id"],
                "vocabulary_id": word["id"],
                "question_type": "mcq_meaning",
                "is_correct": True,
            },
        )

    after = schedule(word["id"])
    assert after["due_at"] == before["due_at"]
    assert after["interval_days"] == before["interval_days"]
    assert after["repetitions"] == before["repetitions"]
    assert review_sources(word["id"]).count("quiz") == 0


def test_a_drill_does_not_pay_xp_twice(client):
    """The drills already credit their own answers; the SRS hook must not add more.

    `submit_review` normally awards XP, which is right on the review screen and
    wrong here — the quiz already counts the session when it completes.
    """
    word = any_word(client)
    settle(client, word["id"])
    before = client.get("/api/streak").json()["today_xp"]

    quiz_wrong(client, word)

    assert client.get("/api/streak").json()["today_xp"] == before


def test_typing_a_wrong_answer_also_counts(client):
    session = client.post(
        "/api/typing/session", json={"mode": "hanzi_to_pinyin", "count": 1}
    ).json()
    vocabulary_id = session["items"][0]["vocabulary_id"]
    before = settle(client, vocabulary_id)

    checked = client.post(
        "/api/typing/check",
        json={
            "session_id": session["session_id"],
            "vocabulary_id": vocabulary_id,
            "mode": "hanzi_to_pinyin",
            "answer": "zzzz",
        },
    )
    assert checked.status_code == 200
    assert checked.json()["is_correct"] is False

    after = schedule(vocabulary_id)
    assert after["interval_days"] < before["interval_days"]
    assert review_sources(vocabulary_id)[-1] == "typing"


def test_an_unknown_word_does_not_break_the_attempt(client):
    """The schedule is a side effect; it must never fail the answer being saved."""
    from backend.services import srs_service

    assert srs_service.record_lapse(None, source="dictation") is None
    assert srs_service.record_lapse(10**9, source="quiz") is None
