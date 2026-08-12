def start_session(client, mode="word_pinyin", level=None, count=5):
    payload = {"mode": mode, "count": count}
    if level:
        payload["hsk_level"] = level
    response = client.post("/api/dictation/session", json=payload)
    assert response.status_code == 201
    return response.json()


def test_word_dictation_only_exposes_audio(client):
    session = start_session(client)
    for item in session["items"]:
        assert item["audio_text"]
        assert item["is_sentence"] is False
        # A word dictation must not hand over the meaning as a hint.
        assert item["hint"]["meaning"] is None
        assert item["hint"]["length"] > 0


def test_sentence_dictation_gives_meaning_as_context(client):
    session = start_session(client, "sentence_hanzi", count=3)
    assert session["items"]
    for item in session["items"]:
        assert item["is_sentence"] is True
        assert item["hint"]["meaning"]


def test_dictation_grades_correct_pinyin(client):
    session = start_session(client)
    item = session["items"][0]
    word = client.get(f"/api/vocabulary/{item['target_id']}").json()

    result = client.post(
        "/api/dictation/check",
        json={
            "session_id": session["session_id"],
            "target_id": item["target_id"],
            "mode": "word_pinyin",
            "answer": word["pinyin"],
            "replays": 1,
        },
    ).json()
    assert result["is_correct"] is True
    assert result["reveal"]["meaning"] == word["meaning"]


def test_dictation_tracks_replays_and_first_listen_rate(client):
    session = start_session(client, count=2)
    first, second = session["items"][0], session["items"][1]
    first_word = client.get(f"/api/vocabulary/{first['target_id']}").json()
    second_word = client.get(f"/api/vocabulary/{second['target_id']}").json()

    client.post("/api/dictation/check", json={
        "session_id": session["session_id"], "target_id": first["target_id"],
        "mode": "word_pinyin", "answer": first_word["pinyin"], "replays": 1,
    })
    client.post("/api/dictation/check", json={
        "session_id": session["session_id"], "target_id": second["target_id"],
        "mode": "word_pinyin", "answer": second_word["pinyin"], "replays": 5,
    })

    stats = client.get("/api/dictation/stats").json()
    assert stats["attempts"] == 2
    assert stats["correct"] == 2
    assert stats["average_replays"] == 3.0
    # Only the one answered within a single replay counts as a first listen.
    assert stats["first_listen_correct"] == 1
    assert stats["first_listen_rate"] == 50.0


def test_sentence_dictation_accepts_answer_without_punctuation(client):
    session = start_session(client, "sentence_hanzi", count=1)
    item = session["items"][0]
    result = client.post("/api/dictation/check", json={
        "session_id": session["session_id"],
        "target_id": item["target_id"],
        "mode": "sentence_hanzi",
        "answer": item["audio_text"].replace("。", "").replace("，", ""),
        "replays": 1,
    }).json()
    assert result["is_correct"] is True


def test_dictation_wrong_answer_returns_character_diff(client):
    session = start_session(client, "word_hanzi", count=1)
    item = session["items"][0]
    result = client.post("/api/dictation/check", json={
        "session_id": session["session_id"],
        "target_id": item["target_id"],
        "mode": "word_hanzi",
        "answer": "错",
        "replays": 2,
    }).json()
    assert result["is_correct"] is False
    assert result["character_diff"]
    assert result["character_diff"][0]["expected"] == item["audio_text"][0]


def test_dictation_rejects_unknown_mode(client):
    assert client.post("/api/dictation/session", json={"mode": "guess"}).status_code == 422


def test_dictation_missing_target_returns_404(client):
    response = client.post("/api/dictation/check", json={
        "target_id": 999999, "mode": "word_pinyin", "answer": "x", "replays": 0,
    })
    assert response.status_code == 404
