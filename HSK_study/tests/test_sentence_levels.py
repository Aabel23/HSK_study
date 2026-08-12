import pytest

LEVELS_WITH_SENTENCES = ["1", "2", "3", "4", "5"]


def test_sentence_levels_cover_hsk_1_to_5(client):
    items = client.get("/api/sentences/levels").json()["items"]
    by_level = {entry["level"]: entry for entry in items}
    for level in LEVELS_WITH_SENTENCES:
        assert level in by_level, f"HSK {level} has no sentences"
        assert by_level[level]["total"] > 0


@pytest.mark.parametrize("level", LEVELS_WITH_SENTENCES)
def test_session_returns_only_the_requested_level(client, level):
    session = client.post(
        "/api/sentences/session", json={"count": 5, "hsk_level": level}
    ).json()
    assert session["items"]
    assert all(item["hsk_level"] == level for item in session["items"])


def test_max_tokens_caps_sentence_difficulty(client):
    session = client.post(
        "/api/sentences/session", json={"count": 10, "max_tokens": 6}
    ).json()
    assert session["items"]
    assert all(len(item["tokens"]) <= 6 for item in session["items"])


def test_tokens_are_shuffled_but_reconstruct_the_sentence(client):
    # The original HSK1 rows store tokens without the closing punctuation while
    # `hanzi` keeps it, so the invariant is compared on content only.
    def content(text: str) -> str:
        return "".join(char for char in text if char not in "，。？！、；：")

    session = client.post("/api/sentences/session", json={"count": 8}).json()
    for item in session["items"]:
        ordered = sorted(item["tokens"], key=lambda token: token["position"])
        assert content("".join(token["text"] for token in ordered)) == content(item["hanzi"])


def test_correct_order_is_accepted_for_a_higher_level_sentence(client):
    session = client.post(
        "/api/sentences/session", json={"count": 1, "hsk_level": "4"}
    ).json()
    item = session["items"][0]
    positions = list(range(len(item["tokens"])))
    result = client.post(
        "/api/sentences/attempt",
        json={
            "session_id": session["session_id"],
            "sentence_id": item["id"],
            "ordered_positions": positions,
        },
    ).json()
    assert result["is_correct"] is True
    assert result["answer"]["hanzi"] == item["hanzi"]


def test_unknown_level_has_no_sentences(client):
    response = client.post("/api/sentences/session", json={"count": 5, "hsk_level": "6"})
    assert response.status_code == 409
