"""Tests for SQLite database path normalization (Task 1)."""
import datetime
import pytest
from unittest.mock import patch

from app import database
from app.models import CheckInLog


@pytest.fixture()
def in_memory_db():
    """Set up an in-memory SQLite database for testing SQLite database paths."""
    # Save original settings
    orig_engine = database._sqlite_engine
    orig_session_local = database._SessionLocal

    # Force reset
    database._sqlite_engine = None
    database._SessionLocal = None

    # Patch config and availability
    with patch("app.database.supabase_available", return_value=False), \
         patch("app.database.DATABASE_URL", "sqlite:///:memory:"):
        
        database._init_sqlite()
        yield

    # Clean up and restore original settings
    if database._sqlite_engine:
        database._sqlite_engine.dispose()
    database._sqlite_engine = orig_engine
    database._SessionLocal = orig_session_local


def test_get_latest_check_in_log_sqlite_timestamp_isoformat(in_memory_db):
    """Test that SQLite path in get_latest_check_in_log returns timestamp as ISO 8601 string."""
    session = next(database._get_sqlite_session())
    test_time = datetime.datetime(2026, 7, 2, 12, 34, 56)
    
    log = CheckInLog(
        student_id="S999",
        similarity_score=0.92,
        device_id="ESP-TEST-01",
        timestamp=test_time
    )
    session.add(log)
    session.commit()
    session.close()

    res = database.get_latest_check_in_log("S999")
    
    assert res is not None
    assert res["student_id"] == "S999"
    assert res["similarity_score"] == 0.92
    assert res["device_id"] == "ESP-TEST-01"
    # Ensure it's normalized to ISO 8601 string, not a datetime object!
    assert res["timestamp"] == "2026-07-02T12:34:56"
    assert isinstance(res["timestamp"], str)


def test_get_latest_check_in_log_nonexistent(in_memory_db):
    """Test that get_latest_check_in_log returns None if no logs exist for student."""
    res = database.get_latest_check_in_log("S_NONEXISTENT")
    assert res is None
