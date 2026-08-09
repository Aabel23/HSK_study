def test_health_returns_expected_response(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "chinese-study-api"}


def test_frontend_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Chinese Study" in response.text

