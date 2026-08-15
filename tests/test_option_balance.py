"""Answer options must not give themselves away by their length.

The vocabulary table holds full CVDICT entries, so a gloss runs anywhere from
"ăn" to four hundred characters of senses. Drawing four words at random and
printing their meanings on four buttons produced questions like

    A. ăn        B. và        C. đi
    D. (sau một mệnh đề giả định) trong trường hợp đó; thì; (sau một mệnh đề
       hành động) ngay khi; ngay sau khi; (giống như 就是 (jiù shì)) chỉ; …

which are answered by picking the long one. These tests pin the fix: the words
are chosen so their answers come out roughly the same size.
"""

from backend.services.gloss import gloss_length, short_gloss


LONG_ENTRY = (
    "(sau một mệnh đề giả định) trong trường hợp đó; thì; (sau một mệnh đề hành động) "
    "ngay khi; ngay sau khi; chỉ; không gì khác ngoài; đơn giản là; chỉ là"
)


def spread(labels):
    """Length spread of what the learner actually reads.

    The API sends the whole gloss and the frontend trims each option for
    display (`shortMeaning` in ``frontend-web/src/lib/format.ts``). Measuring
    the raw strings would therefore measure something nobody sees, so these
    tests apply the same trim the screen does before comparing.
    """
    lengths = [gloss_length(label) for label in labels]
    return max(lengths) - min(lengths)


# --------------------------------------------------------------------------
# The shortening rule itself
# --------------------------------------------------------------------------


def test_short_gloss_keeps_the_leading_sense():
    assert short_gloss(LONG_ENTRY).startswith("(sau một mệnh đề giả định)")
    assert gloss_length(LONG_ENTRY) < 60


def test_classifier_notes_are_not_treated_as_meanings():
    # "lượng từ: 个" is dictionary apparatus. It is never an answer, so it must
    # not become one when it happens to sit first.
    assert short_gloss("lượng từ: 个; điểm yếu; lỗi") == "điểm yếu"


def test_a_short_gloss_is_left_alone():
    assert short_gloss("ăn") == "ăn"


def test_an_over_budget_first_sense_is_still_kept():
    """A blank button is worse than a long one."""
    single = "một câu giải thích rất dài không hề có dấu chấm phẩy nào ở bên trong cả"
    assert short_gloss(single) == single


# --------------------------------------------------------------------------
# Through the API
# --------------------------------------------------------------------------


def test_quiz_meaning_options_are_usually_of_one_size(client):
    """Asserted on the distribution, not per question, and deliberately so.

    Balancing picks the distractors nearest the target in answer length. It
    cannot rescue a target that has no near neighbours — 就 carries four
    hundred characters of senses and nothing at its level looks like it — so a
    per-question cap would either be violated by those outliers or be loose
    enough to pass unbalanced code too. What the fix does guarantee is that the
    typical question is tight: drawn at random the median spread is around 13
    characters, and balanced it is around 2.
    """
    session = client.post(
        "/api/quiz/session", json={"question_types": ["mcq_meaning"], "count": 50}
    ).json()
    spreads = sorted(
        spread([option["label"] for option in question["options"]])
        for question in session["questions"]
    )
    median = spreads[len(spreads) // 2]
    assert median <= 6, spreads


def test_matching_meaning_tiles_are_usually_of_one_size(client):
    spreads = []
    for _ in range(12):
        data = client.post(
            "/api/matching/session", json={"mode": "meaning", "count": 6}
        ).json()
        spreads.append(spread([item["text"] for item in data["right_items"]]))
    spreads.sort()
    assert spreads[len(spreads) // 2] <= 8, spreads


def test_matching_can_be_held_to_one_level(client):
    """Mixing an HSK 1 word with an HSK 7-9 word is solvable by recognition."""
    data = client.post(
        "/api/matching/session", json={"mode": "meaning", "count": 6, "hsk_level": "1"}
    ).json()
    ids = [item["vocabulary_id"] for item in data["left_items"]]
    for vocabulary_id in ids:
        assert client.get(f"/api/vocabulary/{vocabulary_id}").json()["hsk_level"] == "1"


def test_matching_without_a_level_still_works(client):
    """The field is optional, so an older client keeps working unchanged."""
    response = client.post("/api/matching/session", json={"mode": "meaning", "count": 6})
    assert response.status_code == 201
    assert len(response.json()["left_items"]) == 6
