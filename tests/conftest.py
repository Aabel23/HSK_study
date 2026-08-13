from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.database import initialize_database
from backend.main import create_app
from backend.settings import reset_settings_cache
from scripts.seed_data import seed_database


@pytest.fixture(scope="session")
def seeded_template(tmp_path_factory) -> Path:
    """Seed the full HSK dataset once per session.

    Seeding ~11k words produces a ~10 MB file; doing it per test made the suite
    slow and filled the temp volume, so tests copy this template instead.
    """
    template_path = tmp_path_factory.mktemp("template") / "seeded.db"
    previous = os.environ.get("CHINESE_STUDY_DB")
    os.environ["CHINESE_STUDY_DB"] = str(template_path)
    try:
        initialize_database()
        seed_database()
    finally:
        if previous is None:
            os.environ.pop("CHINESE_STUDY_DB", None)
        else:
            os.environ["CHINESE_STUDY_DB"] = previous
    return template_path


@pytest.fixture(autouse=True)
def _no_live_payment_credentials(monkeypatch):
    """Keep the test suite away from the real PayOS account.

    A developer's `.env` holds working keys, and `backend.settings` loads it on
    import. Without this the donation tests would create real payment links
    against a real bank account. Tests that need the feature switched on set
    their own fake keys on top of this.
    """
    for name in ("PAYOS_CLIENT_ID", "PAYOS_API_KEY", "PAYOS_CHECKSUM_KEY"):
        monkeypatch.delenv(name, raising=False)
    reset_settings_cache()


@pytest.fixture(autouse=True)
def _no_live_ai_credentials(monkeypatch):
    """Keep the test suite away from the real Gemini account.

    Same reasoning as the PayOS fixture above: a developer's `.env` holds a
    working key, and grading a spoken answer costs a real API call. Tests that
    exercise grading stub `gemini_service.generate_json` instead.
    """
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    reset_settings_cache()


@pytest.fixture()
def client(tmp_path, monkeypatch, seeded_template):
    database_path = tmp_path / "chinese_study_test.db"
    shutil.copyfile(seeded_template, database_path)
    monkeypatch.setenv("CHINESE_STUDY_DB", str(database_path))
    # The copy is already seeded, so skip the startup reseed.
    monkeypatch.setenv("CHINESE_STUDY_SEED", "0")
    reset_settings_cache()
    try:
        with TestClient(create_app()) as test_client:
            yield test_client
    finally:
        reset_settings_cache()
        # Reclaim the copy immediately; the temp volume is the constraint here.
        database_path.unlink(missing_ok=True)
