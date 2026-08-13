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


def test_permissions_policy_allows_the_microphone_for_hskk(client):
    """The HSKK mock exam records the learner; blocking the mic here made the
    browser refuse getUserMedia without even prompting. Camera and location
    must stay blocked — nothing in the app uses them."""
    policy = client.get("/api/health").headers["Permissions-Policy"]
    assert "microphone=(self)" in policy
    assert "camera=()" in policy
    assert "geolocation=()" in policy


def test_frontend_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "HSK Master" in response.text

