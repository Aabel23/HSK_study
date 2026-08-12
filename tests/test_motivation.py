def review_one_word(client, rating="good"):
    item = client.get("/api/review/queue", params={"limit": 1}).json()["items"][0]
    client.post("/api/review/submit", json={"vocabulary_id": item["id"], "rating": rating})
    return item


def test_streak_starts_empty(client):
    payload = client.get("/api/streak").json()
    assert payload["current_streak"] == 0
    assert payload["total_xp"] == 0
    assert payload["level"] == 1
    assert payload["goal_met"] is False


def test_reviewing_today_starts_a_streak_and_awards_xp(client):
    review_one_word(client, "easy")
    payload = client.get("/api/streak").json()
    assert payload["current_streak"] == 1
    assert payload["today_reviews"] == 1
    assert payload["total_xp"] == 10
    assert payload["heatmap"][-1]["count"] == 1


def test_goal_percentage_tracks_daily_goal(client):
    client.patch("/api/settings", json={"daily_goal": 2})
    review_one_word(client)
    payload = client.get("/api/streak").json()
    assert payload["daily_goal"] == 2
    assert payload["goal_percentage"] == 50.0
    assert payload["goal_met"] is False


def test_completed_practice_session_counts_toward_streak(client):
    session = client.post(
        "/api/flashcard/session", json={"count": 2, "include_mastered": False}
    ).json()
    client.post(
        f"/api/flashcard/session/{session['session_id']}/complete",
        json={"total_items": 2, "correct_items": 2, "incorrect_items": 0},
    )
    payload = client.get("/api/streak").json()
    assert payload["today_reviews"] == 2
    assert payload["total_xp"] == 12


def test_achievements_unlock_on_first_review(client):
    before = client.get("/api/achievements").json()
    assert before["unlocked_count"] == 0
    assert before["total_count"] == len(before["items"])

    review_one_word(client)
    after = client.get("/api/achievements").json()
    unlocked = [item["code"] for item in after["items"] if item["unlocked"]]
    assert "first_steps" in unlocked
    assert after["newly_unlocked"] == ["first_steps"]

    # Unlocks are persisted, so a second call reports nothing new.
    assert client.get("/api/achievements").json()["newly_unlocked"] == []


def test_settings_round_trip_and_validation(client):
    defaults = client.get("/api/settings").json()
    assert defaults["settings"]["daily_goal"] == 20

    updated = client.patch("/api/settings", json={"daily_goal": 35, "theme": "light"}).json()
    assert updated["settings"]["daily_goal"] == 35
    assert updated["settings"]["theme"] == "light"
    assert client.get("/api/settings").json()["settings"]["daily_goal"] == 35

    assert client.patch("/api/settings", json={"daily_goal": 0}).status_code == 409
    assert client.patch("/api/settings", json={"theme": "neon"}).status_code == 409
    assert client.patch("/api/settings", json={"unknown_key": 1}).status_code == 409

    assert client.post("/api/settings/reset").json()["settings"]["daily_goal"] == 20


def test_backup_export_and_merge_import(client):
    item = review_one_word(client)
    client.post("/api/review/note", json={"vocabulary_id": item["id"], "note": "ghi chú"})

    exported = client.get("/api/backup/export")
    assert exported.status_code == 200
    assert "attachment" in exported.headers["content-disposition"]
    payload = exported.json()
    assert payload["format"] == "chinese-study-backup"
    assert len(payload["learning_progress"]) == 1

    result = client.post("/api/backup/import", json=payload).json()
    assert result["imported"]["learning_progress"] == 1
    assert result["imported"]["skipped_unknown_words"] == 0

    restored = client.get(f"/api/vocabulary/{item['id']}").json()
    assert restored["note"] == "ghi chú"


def test_import_rejects_foreign_files(client):
    response = client.post("/api/backup/import", json={"format": "anki", "backup_version": 1})
    assert response.status_code == 409
