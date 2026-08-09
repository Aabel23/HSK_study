def first_vocabulary_id(client):
    return client.get("/api/vocabulary", params={"limit": 1}).json()["items"][0]["id"]


def test_default_progress_is_new(client):
    response = client.get(f"/api/progress/{first_vocabulary_id(client)}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "new"
    assert data["review_count"] == 0


def test_update_progress_status(client):
    item_id = first_vocabulary_id(client)
    response = client.post("/api/progress/status", json={"vocabulary_id": item_id, "status": "review"})
    assert response.status_code == 200
    assert response.json()["status"] == "review"


def test_progress_statistics_and_completion(client):
    item_id = first_vocabulary_id(client)
    client.post("/api/progress/status", json={"vocabulary_id": item_id, "status": "mastered"})
    response = client.get("/api/progress")
    assert response.status_code == 200
    data = response.json()
    assert data["total_vocabulary"] == 150
    assert data["new_count"] == 149
    assert data["mastered_count"] == 1
    assert data["completion_percentage"] == 0.7


def test_invalid_progress_status(client):
    response = client.post("/api/progress/status", json={
        "vocabulary_id": first_vocabulary_id(client), "status": "done",
    })
    assert response.status_code == 422


def test_dashboard_uses_persisted_data(client):
    item_id = first_vocabulary_id(client)
    client.post("/api/progress/status", json={"vocabulary_id": item_id, "status": "learning"})
    data = client.get("/api/dashboard").json()
    assert data["total_vocabulary"] == 150
    assert data["viewed_vocabulary"] == 1
    assert data["learning_vocabulary"] == 1

