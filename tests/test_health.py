def test_health_returns_expected_response(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "chinese-study-api"
    assert payload["version"]


def test_readiness_reports_database_counts(client):
    response = client.get("/api/health/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"]["connected"] is True
    assert payload["database"]["vocabulary"] > 0


def test_responses_carry_request_id_and_security_headers(client):
    response = client.get("/api/health")
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "Content-Security-Policy" in response.headers


def test_frontend_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "HSK Master" in response.text

