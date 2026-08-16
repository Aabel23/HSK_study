"""The character layer and the Hán-Việt decoding drill."""

from urllib.parse import quote


def lookup(client, hanzi):
    return client.get(f"/api/characters/{quote(hanzi)}")


def start_drill(client, mode="han_viet_to_meaning", count=5, **extra):
    response = client.post(
        "/api/characters/drill/session", json={"mode": mode, "count": count, **extra}
    )
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------------------
# Lookup
# --------------------------------------------------------------------------


def test_lookup_returns_reading_radicals_and_word_family(client):
    response = lookup(client, "学")
    assert response.status_code == 200
    data = response.json()
    assert data["hanzi"] == "学"
    assert data["han_viet"] == "học"
    assert data["pinyin"]
    # 学 is one of the hand-checked characters, so it carries a mnemonic and a
    # radical breakdown rather than only a reading.
    assert data["mnemonic_vi"]
    assert [item["hanzi"] for item in data["radical_details"]]
    family = {word["hanzi"] for word in data["words"]}
    assert {"学生", "学习"} <= family


def test_word_family_carries_the_whole_word_reading(client):
    words = {word["hanzi"]: word for word in lookup(client, "学").json()["words"]}
    assert words["学生"]["han_viet"] == "học sinh"


def test_unknown_character_is_a_404(client):
    assert lookup(client, "Z").status_code == 404


def test_listing_ranks_by_how_much_vocabulary_a_character_unlocks(client):
    response = client.get("/api/characters?limit=10")
    assert response.status_code == 200
    items = response.json()["items"]
    counts = [item["word_count"] for item in items]
    assert counts == sorted(counts, reverse=True)
    assert counts[0] > 50


def test_listing_search_matches_the_han_viet_reading(client):
    items = client.get("/api/characters?search=học&limit=20").json()["items"]
    assert any(item["hanzi"] == "学" for item in items)


def test_stats_report_decodable_coverage(client):
    data = client.get("/api/characters/stats").json()
    assert data["total"] > 2000
    assert data["with_reading"] > 0
    # The seeder only transcribes a word when every character has a reading, so
    # this can never exceed the bank.
    assert 0 < data["words_decodable"] <= data["words_total"]


# --------------------------------------------------------------------------
# Progress
# --------------------------------------------------------------------------


def test_marking_a_character_mastered_unlocks_its_words(client):
    before = client.get("/api/characters/stats").json()
    assert before["words_unlocked"] == 0

    response = client.post(f"/api/characters/{quote('学')}/status", json={"status": "mastered"})
    assert response.status_code == 200

    after = client.get("/api/characters/stats").json()
    assert after["mastered"] == 1
    # Every word built on 学 now counts as reachable — that leverage is the
    # whole argument for teaching characters rather than only words.
    assert after["words_unlocked"] >= 40
    assert lookup(client, "学").json()["status"] == "mastered"


def test_invalid_status_is_rejected(client):
    response = client.post(f"/api/characters/{quote('学')}/status", json={"status": "quen"})
    assert response.status_code == 409


# --------------------------------------------------------------------------
# The decoding drill
# --------------------------------------------------------------------------


def test_drill_question_shows_the_reading_of_every_character(client):
    session = start_drill(client)
    question = client.get(
        f"/api/characters/drill/session/{session['session_id']}/next"
    ).json()

    assert len(question["word"]) >= 2
    assert len(question["options"]) == 4
    # The clue is one entry per character of the word, in word order.
    assert [part["hanzi"] for part in question["breakdown"]] == list(question["word"])
    assert all(part["han_viet"] for part in question["breakdown"])
    # And the word's own reading is those syllables joined.
    assert question["han_viet"] == " ".join(
        part["han_viet"] for part in question["breakdown"]
    )


def test_meaning_options_are_usually_of_one_size(client):
    """The long answer must not be the answer.

    A question whose options run from "ăn" to a four-hundred-character gloss is
    answered by picking the long one, without reading any Chinese at all. The
    check is on the typical question rather than every one: a target whose
    gloss has no near neighbour at its level cannot be balanced against
    anything, and pinning the worst case would only loosen the test until it
    stopped meaning anything.
    """
    session = start_drill(client, count=20)
    spreads = []
    for _ in range(20):
        question = client.get(
            f"/api/characters/drill/session/{session['session_id']}/next"
        ).json()
        lengths = [len(option) for option in question["options"]]
        spreads.append(max(lengths) - min(lengths))
    spreads.sort()
    assert spreads[len(spreads) // 2] <= 15, spreads


def test_reading_options_match_on_syllable_count(client):
    """"cáp tử" next to "tinh ích cầu tinh" is answered by counting words.

    The bank mixes two-syllable words with four-syllable thành ngữ, so options
    are chosen to be the same shape as the answer. Almost every question lands
    within one syllable; a target with no same-shape neighbour in the draw is
    allowed to be off by more, which is why this checks the spread across a run
    rather than each question alone.
    """
    session = start_drill(client, mode="meaning_to_han_viet", count=20)
    spreads = []
    for _ in range(20):
        question = client.get(
            f"/api/characters/drill/session/{session['session_id']}/next"
        ).json()
        syllables = [len(option.split()) for option in question["options"]]
        spreads.append(max(syllables) - min(syllables))
    assert sum(1 for value in spreads if value <= 1) >= 18, spreads


def test_options_are_always_distinct(client):
    session = start_drill(client, count=10)
    for _ in range(10):
        options = client.get(
            f"/api/characters/drill/session/{session['session_id']}/next"
        ).json()["options"]
        assert len(set(options)) == len(options)


def test_character_reading_mode_asks_about_a_single_character(client):
    session = start_drill(client, mode="character_reading")
    question = client.get(
        f"/api/characters/drill/session/{session['session_id']}/next"
    ).json()
    assert len(question["word"]) == 1
    assert question["han_viet"] in question["options"]
    assert question["vocabulary_id"] is None


def test_a_correct_answer_credits_every_character_of_the_word(client):
    session = start_drill(client)
    question = client.get(
        f"/api/characters/drill/session/{session['session_id']}/next"
    ).json()

    response = client.post(
        "/api/characters/drill/attempt",
        json={
            "session_id": session["session_id"],
            "word": question["word"],
            "is_correct": True,
            "vocabulary_id": question["vocabulary_id"],
        },
    )
    assert response.status_code == 201

    # Answering 图书馆 is evidence about 图, 书 and 馆 — those are what carry
    # over to the next word the learner has never seen.
    for char in set(question["word"]):
        state = lookup(client, char).json()
        assert state["seen_count"] == 1
        assert state["correct_count"] == 1
        assert state["status"] == "learning"


def test_drill_level_filter_is_respected(client):
    session = start_drill(client, count=5, hsk_level="1")
    for _ in range(5):
        question = client.get(
            f"/api/characters/drill/session/{session['session_id']}/next"
        ).json()
        assert question["hsk_level"] == "1"


def test_invalid_drill_mode_is_rejected(client):
    response = client.post(
        "/api/characters/drill/session", json={"mode": "chiet_tu", "count": 5}
    )
    assert response.status_code == 409


def test_completing_a_session_closes_it(client):
    session = start_drill(client, count=2)
    response = client.post(
        f"/api/characters/drill/session/{session['session_id']}/complete",
        json={"total_items": 2, "correct_items": 2, "incorrect_items": 0},
    )
    assert response.status_code == 200
    # A closed session hands out no more questions.
    assert (
        client.get(f"/api/characters/drill/session/{session['session_id']}/next").status_code
        == 409
    )
    assert client.get("/api/characters/drill/stats").json()["sessions"] == 1


def test_modes_are_listed_in_vietnamese(client):
    items = client.get("/api/characters/modes").json()["items"]
    assert {item["value"] for item in items} == {
        "han_viet_to_meaning",
        "meaning_to_han_viet",
        "character_reading",
    }
    assert all(item["label"] for item in items)


# --------------------------------------------------------------------------
# The character schedule
# --------------------------------------------------------------------------


def progress(hanzi):
    from backend.database import get_connection

    with get_connection() as connection:
        return connection.execute(
            """
            SELECT status, seen_count, correct_count, incorrect_count,
                   repetitions, lapses, interval_days, due_at
            FROM character_progress WHERE hanzi = ?
            """,
            (hanzi,),
        ).fetchone()


def answer(client, session_id, word, correct, vocabulary_id=None):
    return client.post(
        "/api/characters/drill/attempt",
        json={
            "session_id": session_id,
            "word": word,
            "is_correct": correct,
            "vocabulary_id": vocabulary_id,
        },
    )


def test_a_right_answer_pushes_the_character_further_out(client):
    session = start_drill(client, mode="character_reading", count=10)
    hanzi = client.get(
        f"/api/characters/drill/session/{session['session_id']}/next"
    ).json()["word"]

    intervals = []
    for _ in range(3):
        answer(client, session["session_id"], hanzi, True)
        intervals.append(progress(hanzi)["interval_days"])

    # 1 day, then 4, then ease-multiplied — the SM-2 curve with the ratings
    # collapsed to right or wrong, because a multiple-choice answer carries no
    # "how hard was that" signal to ask for.
    assert intervals == sorted(intervals)
    assert intervals[0] < intervals[-1]
    assert progress(hanzi)["repetitions"] == 3


def test_a_wrong_answer_brings_the_character_straight_back(client):
    from datetime import datetime, timedelta, timezone

    session = start_drill(client, mode="character_reading", count=10)
    hanzi = client.get(
        f"/api/characters/drill/session/{session['session_id']}/next"
    ).json()["word"]

    for _ in range(3):
        answer(client, session["session_id"], hanzi, True)
    settled = progress(hanzi)

    answer(client, session["session_id"], hanzi, False)
    lapsed = progress(hanzi)

    assert lapsed["interval_days"] < settled["interval_days"]
    assert lapsed["repetitions"] == 0
    assert lapsed["lapses"] == settled["lapses"] + 1
    due = datetime.fromisoformat(lapsed["due_at"])
    assert due < datetime.now(timezone.utc) + timedelta(hours=1)


def test_an_overdue_character_is_asked_before_a_random_one(client):
    """A reading missed thirty seconds ago must not wait its turn among 8.200."""
    session = start_drill(client, mode="character_reading", count=10)
    first = client.get(
        f"/api/characters/drill/session/{session['session_id']}/next"
    ).json()["word"]

    answer(client, session["session_id"], first, False)

    # The lapse is due in ten minutes rather than now, so nudge it into the past
    # the way waiting would.
    from backend.database import get_connection

    with get_connection() as connection:
        connection.execute(
            "UPDATE character_progress SET due_at = '2000-01-01T00:00:00+00:00' WHERE hanzi = ?",
            (first,),
        )

    served = client.get(
        f"/api/characters/drill/session/{session['session_id']}/next"
    ).json()["word"]
    assert served == first


def test_a_mastered_character_is_not_demoted_by_one_slip(client):
    from urllib.parse import quote

    client.post(f"/api/characters/{quote('学')}/status", json={"status": "mastered"})
    session = start_drill(client, mode="character_reading", count=5)
    answer(client, session["session_id"], "学", False)
    assert progress("学")["status"] == "mastered"
    # The shortened interval is what the slip costs it, not the status.
    assert progress("学")["lapses"] == 1


def test_stats_report_characters_due(client):
    session = start_drill(client, mode="character_reading", count=5)
    hanzi = client.get(
        f"/api/characters/drill/session/{session['session_id']}/next"
    ).json()["word"]
    answer(client, session["session_id"], hanzi, False)

    from backend.database import get_connection

    with get_connection() as connection:
        connection.execute(
            "UPDATE character_progress SET due_at = '2000-01-01T00:00:00+00:00' WHERE hanzi = ?",
            (hanzi,),
        )
    assert client.get("/api/characters/stats").json()["due_now"] >= 1
