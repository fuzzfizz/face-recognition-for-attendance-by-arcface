"""Tests for database operations (Task 3)."""
import datetime
import pytest
from unittest.mock import patch

from app import database
from app.models import CheckInLog


@pytest.fixture()
def in_memory_db():
    """Set up an in-memory SQLite database for testing database paths."""
    # Save original settings
    orig_engine = database._engine
    orig_session_local = database._SessionLocal

    # Force reset
    database._engine = None
    database._SessionLocal = None

    with patch("app.database.MYSQL_URL", "sqlite:///:memory:"):
        database.init_db()
        yield

    # Clean up and restore original settings
    if database._engine:
        database._engine.dispose()
    database._engine = orig_engine
    database._SessionLocal = orig_session_local


def test_get_latest_check_in_log_timestamp_isoformat(in_memory_db):
    """Test that get_latest_check_in_log returns timestamp as ISO 8601 string."""
    session = next(database.get_db())
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


def test_delete_student_db(in_memory_db):
    """Test delete_student_from_db cascade deletion of user and queue items."""
    from app.database import (
        delete_student_from_db,
        upload_image,
        upsert_user,
        get_db
    )
    from app.models import User, RegistrationQueue

    # 1. Setup: insert user and queue items
    upsert_user("S999", "Test Delete User")
    
    session = next(get_db())
    user = session.query(User).filter(User.student_id == "S999").first()
    assert user is not None

    upload_image(b"dummy queue data", "S999")
    session.close()

    # 2. Perform deletion
    success = delete_student_from_db("S999")
    assert success is True

    # 3. Verify database clean up
    session = next(get_db())
    user_after = session.query(User).filter(User.student_id == "S999").first()
    assert user_after is None

    queue_after = session.query(RegistrationQueue).filter(RegistrationQueue.student_id == "S999").all()
    assert len(queue_after) == 0
    session.close()


def test_delete_student_transaction_safety(in_memory_db):
    """Test that if DB commit fails, the database rollback works and records are kept."""
    from unittest.mock import patch
    from app.database import (
        delete_student_from_db,
        upload_image,
        upsert_user,
        get_db
    )
    from app.models import User, RegistrationQueue
    from sqlalchemy.orm import Session

    # Setup: insert user and queue item
    upsert_user("S999_FAIL", "Test Delete User Fail")
    upload_image(b"dummy queue data", "S999_FAIL")

    # Patch Session.commit to raise an exception
    with patch.object(Session, 'commit', side_effect=Exception("Simulated commit failure")):
        success = delete_student_from_db("S999_FAIL")
        assert success is False

    # Verify database record is still present (rollback succeeded)
    session = next(get_db())
    user_after = session.query(User).filter(User.student_id == "S999_FAIL").first()
    assert user_after is not None
    
    queue_after = session.query(RegistrationQueue).filter(RegistrationQueue.student_id == "S999_FAIL").all()
    assert len(queue_after) == 1
    session.close()


def test_insert_log_with_error_message(in_memory_db):
    """Test that we can insert a log with an error message."""
    from app.database import insert_log, get_logs
    success = insert_log(
        student_id=None,
        similarity_score=0.0,
        device_id="TEST-DEV",
        error_message="Blur Check Failed"
    )
    assert success is True
    
    logs = get_logs(limit=1)
    assert len(logs) == 1
    assert logs[0].get("error_message") == "Blur Check Failed"


def test_mysql_mode_upload_image(in_memory_db):
    """Test upload_image directly inserts pending queue item in MySQL mode."""
    from app.database import upload_image, _get_sqlite_session
    from app.models import RegistrationQueue

    image_bytes = b"mysql_dummy_image_bytes"
    queue_id = upload_image(image_bytes, "S100")
    assert queue_id is not None
    
    # Verify row exists in DB and is pending
    session = next(_get_sqlite_session())
    item = session.query(RegistrationQueue).filter(RegistrationQueue.id == queue_id).first()
    assert item is not None
    assert item.student_id == "S100"
    assert item.image_blob == image_bytes
    assert item.status == "pending"
    session.close()



def test_delete_student_cascade_sql(in_memory_db):
    """Test cascade deletion of user records, queue items, and logs cleanly in SQL mode."""
    from app.database import delete_student_from_db, get_db
    from app.models import User, RegistrationQueue, CheckInLog

    session = next(get_db())
    
    # Setup
    user = User(student_id="S102", name="Cascade User")
    session.add(user)
    session.commit()
    u_id = user.id

    q_item = RegistrationQueue(student_id="S102", image_blob=b"dummy_blob", status="pending")
    session.add(q_item)
    
    log1 = CheckInLog(student_id="S102", similarity_score=0.9, device_id="D1")
    session.add(log1)
    
    log2 = CheckInLog(user_id=u_id, student_id="S102", similarity_score=0.95, device_id="D2")
    session.add(log2)

    session.commit()
    session.close()

    # Verify everything exists before deletion
    session = next(get_db())
    assert session.query(User).filter(User.student_id == "S102").count() == 1
    assert session.query(RegistrationQueue).filter(RegistrationQueue.student_id == "S102").count() == 1
    assert session.query(CheckInLog).filter(CheckInLog.student_id == "S102").count() == 2
    session.close()

    # Delete student
    success = delete_student_from_db("S102")
    assert success is True

    # Verify cascade deletion
    session = next(get_db())
    assert session.query(User).filter(User.student_id == "S102").count() == 0
    assert session.query(RegistrationQueue).filter(RegistrationQueue.student_id == "S102").count() == 0
    assert session.query(CheckInLog).filter(CheckInLog.student_id == "S102").count() == 0
    session.close()


def test_mysql_mode_process_training_queue_blob_migration(in_memory_db):
    """Test training pipeline processing in MySQL DB_MODE."""
    from app.database import upload_image, get_db, upsert_user
    from app.services.training_service import process_pending_queue
    from app.models import RegistrationQueue, User
    from unittest.mock import patch, MagicMock

    # 1. Simulate MySQL mode
    with patch("app.database.MYSQL_URL", "mysql+pymysql://dummy"), \
         patch("app.services.training_service.get_face_processor") as mock_get_processor, \
         patch("app.services.training_service.get_all_embeddings") as mock_get_all, \
         patch("app.services.training_service.save_all_embeddings") as mock_save, \
         patch("app.services.training_service.invalidate_cache") as mock_invalidate:
         
        # Create user
        upsert_user("S106", "MySQL Test User")
        
        # Upload image to registration queue
        image_bytes = b"mysql_integration_test_image_bytes"
        row_id = upload_image(image_bytes, "S106")
        assert row_id is not None
        assert isinstance(row_id, int)
        
        # Setup mock processor
        mock_processor = MagicMock()
        # Mock decode_image to return a valid numpy array for training
        mock_processor.decode_image.return_value = MagicMock()
        mock_processor.validate_image_quality.return_value = {
            "passed": True,
            "results": {"face_detected": True, "single_face": True},
            "face": MagicMock()
        }
        mock_processor.extract_face_embedding.return_value = {"embedding": [0.1] * 512}
        mock_get_processor.return_value = mock_processor
        
        mock_get_all.return_value = []
        
        # 2. Process the training queue
        result = process_pending_queue()
        
        # Verify training succeeded
        assert result["message"] == "Training completed for batch"
        assert "S106" in result["processed_students"]
        
        # 3. Verify status of the queue item is updated to completed
        session = next(get_db())
        item = session.query(RegistrationQueue).filter(RegistrationQueue.id == row_id).first()
        assert item is not None
        assert item.status == "completed"
        session.close()


def test_database_rollback_on_write_error(in_memory_db):
    """Test that database write operations call session.rollback() on failure."""
    from unittest.mock import patch, MagicMock
    from app.database import upsert_user

    # Create a mock session that raises an exception on commit
    mock_session = MagicMock()
    mock_session.commit.side_effect = Exception("Database write failed")

    with patch("app.database._get_db_session", return_value=mock_session):
        with pytest.raises(Exception, match="Database write failed"):
            upsert_user("S_ERROR", "Error User")

        # Verify rollback was called
        mock_session.rollback.assert_called_once()
        # Verify close was called
        mock_session.close.assert_called_once()


def test_config_production_error():
    """Test that importing config.py throws RuntimeError in production if MYSQL_URL is missing."""
    import sys
    import importlib
    from unittest.mock import patch

    # Remove app.config from sys.modules if it exists
    sys.modules.pop("app.config", None)

    # Set env vars to simulate production environment without MYSQL_URL
    with patch.dict("os.environ", {"MYSQL_URL": "", "ENV": "production", "APP_ENV": "", "TESTING": "", "FORCE_PROD_CHECK": "true"}):
        with pytest.raises(RuntimeError) as exc_info:
            importlib.import_module("app.config")
        assert "MYSQL_URL environment variable is not set" in str(exc_info.value)

    # Cleanup and reload config in clean test environment
    sys.modules.pop("app.config", None)
    importlib.import_module("app.config")
