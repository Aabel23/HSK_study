def test_list_vocabulary(client):
    response = client.get("/api/vocabulary", params={"limit": 20})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 10000
    assert len(data["items"]) == 20
    assert data["limit"] == 20


def test_search_hanzi(client):
    data = client.get("/api/vocabulary", params={"search": "中国"}).json()
    assert data["total"] >= 1
    assert any(item["hanzi"] == "中国" for item in data["items"])


def test_search_pinyin(client):
    data = client.get("/api/vocabulary", params={"search": "píng"}).json()
    assert any(item["hanzi"] == "苹果" for item in data["items"])


def test_search_vietnamese_meaning(client):
    data = client.get("/api/vocabulary", params={"search": "cảm ơn"}).json()
    assert data["total"] >= 1
    assert any(item["hanzi"] == "谢谢" for item in data["items"])


def test_filter_topic(client):
    data = client.get("/api/vocabulary", params={"topic": "Chào hỏi", "limit": 100}).json()
    assert data["total"] > 0
    assert all(item["topic"] == "Chào hỏi" for item in data["items"])


def test_filter_status(client):
    item_id = client.get("/api/vocabulary", params={"limit": 1}).json()["items"][0]["id"]
    client.post("/api/progress/status", json={"vocabulary_id": item_id, "status": "review"})
    data = client.get("/api/vocabulary", params={"status": "review"}).json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == item_id


def test_missing_vocabulary_returns_404(client):
    response = client.get("/api/vocabulary/999999")
    assert response.status_code == 404


def test_random_vocabulary_has_no_duplicates(client):
    response = client.get("/api/vocabulary/random", params={"count": 30})
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert len(ids) == len(set(ids)) == 30

