from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.database import initialize_database
from backend.main import create_app
from scripts.seed_data import seed_database


@pytest.fixture()
def client(tmp_path, monkeypatch):
    database_path = tmp_path / "chinese_study_test.db"
    monkeypatch.setenv("CHINESE_STUDY_DB", str(database_path))
    initialize_database()
    seed_database()
    with TestClient(create_app()) as test_client:
        yield test_client

