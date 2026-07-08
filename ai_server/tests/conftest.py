"""Pytest configuration and shared fixtures for ai_server tests (Task 12)."""
import os
import sys
from unittest.mock import MagicMock

# Mock heavy/missing dependencies globally for all tests
sys.modules["insightface"] = MagicMock()
sys.modules["insightface.app"] = MagicMock()

import pytest
from fastapi.testclient import TestClient

@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Ensure tests run in pure SQLite offline mode."""
    monkeypatch.setenv("MYSQL_URL", "sqlite:///./face_recognition.db")
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    # Patch module-level constants imported before fixture runs
    import app.config as _cfg
    import app.database as _db
    monkeypatch.setattr(_cfg, "MYSQL_URL", "sqlite:///./face_recognition.db")
    monkeypatch.setattr(_db, "MYSQL_URL", "sqlite:///./face_recognition.db")

@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    """Provide a temporary data directory and override paths in matcher/config."""
    monkeypatch.setattr("app.config.DATA_DIR", tmp_path)
    monkeypatch.setattr("app.config.EMBEDDINGS_PATH", tmp_path / "face_embeddings.pkl")
    return tmp_path

@pytest.fixture()
def client():
    """Return a TestClient for the FastAPI app."""
    from app.main import app
    return TestClient(app)
