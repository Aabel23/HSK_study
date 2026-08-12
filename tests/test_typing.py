import pytest

from backend.services import pinyin_utils


@pytest.mark.parametrize(
    "expected,answer,correct,tones",
    [
        ("nǐ hǎo", "nǐ hǎo", True, True),      # exact, tone marks
        ("nǐ hǎo", "ni3hao3", True, True),      # tone numbers
        ("nǐ hǎo", "ni3 hao3", True, True),     # tone numbers with a space
        ("nǐ hǎo", "ni hao", True, False),      # toneless: accepted, tones missing
        ("nǐ hǎo", "NI HAO", True, False),      # case insensitive
        ("nǐ hǎo", "ni2hao2", True, False),     # right syllables, wrong tones
        ("nǐ hǎo", "ni hai", False, False),     # wrong syllable
        ("lǜ", "lv4", True, True),              # ü typed as v
        ("lǜ", "lu:4", True, True),             # ü typed as u:
        ("xiè xie", "xiexie", True, False),     # spacing ignored
    ],
)
def test_pinyin_grading(expected, answer, correct, tones):
    result = pinyin_utils.compare_pinyin(expected, answer)
    assert result.is_correct is correct
    assert result.tones_correct is tones


def test_empty_answer_is_never_correct():
    assert pinyin_utils.compare_pinyin("nǐ hǎo", "").is_correct is False
    assert pinyin_utils.compare_hanzi("你好", "") is False


def test_hanzi_comparison_ignores_punctuation():
    assert pinyin_utils.compare_hanzi("你好。", "你好") is True
    assert pinyin_utils.compare_hanzi("你好", "你 好") is True
    assert pinyin_utils.compare_hanzi("你好", "你們") is False


def test_character_diff_marks_each_position():
    diff = pinyin_utils.character_diff("学校", "学生")
    assert [entry["correct"] for entry in diff] == [True, False]
    assert diff[1]["expected"] == "校"
    assert diff[1]["typed"] == "生"


def test_character_diff_handles_short_answer():
    diff = pinyin_utils.character_diff("学校", "学")
    assert diff[1]["typed"] is None
    assert diff[1]["correct"] is False


def start_session(client, mode="hanzi_to_pinyin", level=None, count=5):
    payload = {"mode": mode, "count": count}
    if level:
        payload["hsk_level"] = level
    response = client.post("/api/typing/session", json=payload)
    assert response.status_code == 201
    return response.json()


def test_typing_session_hides_the_answer(client):
    session = start_session(client, "audio_to_pinyin")
    assert session["mode"] == "audio_to_pinyin"
    for item in session["items"]:
        # Audio modes must not leak the pinyin or the meaning into the prompt.
        assert set(item["prompt"]) == {"audio_text"}


def test_hanzi_prompt_shows_characters_not_pinyin(client):
    session = start_session(client, "hanzi_to_pinyin")
    prompt = session["items"][0]["prompt"]
    assert "hanzi" in prompt
    assert "pinyin" not in prompt


def test_typing_check_grades_and_reveals(client):
    session = start_session(client)
    item = session["items"][0]
    word = client.get(f"/api/vocabulary/{item['vocabulary_id']}").json()

    response = client.post(
        "/api/typing/check",
        json={
            "session_id": session["session_id"],
            "vocabulary_id": item["vocabulary_id"],
            "mode": "hanzi_to_pinyin",
            "answer": word["pinyin"],
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["is_correct"] is True
    assert result["reveal"]["hanzi"] == word["hanzi"]


def test_typing_wrong_answer_is_recorded(client):
    session = start_session(client)
    item = session["items"][0]
    result = client.post(
        "/api/typing/check",
        json={
            "session_id": session["session_id"],
            "vocabulary_id": item["vocabulary_id"],
            "mode": "hanzi_to_pinyin",
            "answer": "zzzz",
        },
    ).json()
    assert result["is_correct"] is False

    stats = client.get("/api/typing/stats").json()
    assert stats["attempts"] == 1
    assert stats["correct"] == 0
    assert stats["accuracy"] == 0.0


def test_typing_session_respects_hsk_level(client):
    session = start_session(client, level="3", count=8)
    assert session["hsk_level"] == "3"
    assert all(item["hsk_level"] == "3" for item in session["items"])


def test_typing_rejects_unknown_mode(client):
    assert client.post("/api/typing/session", json={"mode": "telepathy"}).status_code == 422


def test_typing_complete_session(client):
    session = start_session(client, count=2)
    response = client.post(
        f"/api/typing/session/{session['session_id']}/complete",
        json={"total_items": 2, "correct_items": 2, "incorrect_items": 0},
    )
    assert response.status_code == 200
    assert client.get("/api/typing/stats").json()["sessions"] == 1
