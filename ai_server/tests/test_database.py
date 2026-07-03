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


def test_delete_student_sqlite(in_memory_db, tmp_path):
    """Test that delete_student_from_db deletes student records and associated files in SQLite mode."""
    import os
    from app.database import (
        delete_student_from_db,
        insert_queue_item,
        upsert_user,
        _get_sqlite_session
    )
    from app.models import UserImage, User, RegistrationQueue

    # 1. Setup: insert user and queue items, and create physical dummy files on disk
    upsert_user("S999", "Test Delete User")
    
    # Let's get the user id
    session = next(_get_sqlite_session())
    user = session.query(User).filter(User.student_id == "S999").first()
    assert user is not None
    user_id = user.id

    # Create dummy files
    user_img_file = tmp_path / "user_img.jpg"
    user_img_file.write_bytes(b"dummy image data")
    
    queue_img_file = tmp_path / "queue_img.jpg"
    queue_img_file.write_bytes(b"dummy queue data")

    assert os.path.exists(user_img_file)
    assert os.path.exists(queue_img_file)

    # Insert user image and queue items
    user_image = UserImage(user_id=user_id, image_path=str(user_img_file))
    session.add(user_image)
    session.commit()
    session.close()

    insert_queue_item("S999", str(queue_img_file))

    # 2. Perform deletion
    success = delete_student_from_db("S999")
    assert success is True

    # 3. Verify database clean up
    session = next(_get_sqlite_session())
    user_after = session.query(User).filter(User.student_id == "S999").first()
    assert user_after is None

    images_after = session.query(UserImage).filter(UserImage.user_id == user_id).all()
    assert len(images_after) == 0

    queue_after = session.query(RegistrationQueue).filter(RegistrationQueue.student_id == "S999").all()
    assert len(queue_after) == 0
    session.close()

    # 4. Verify physical files are deleted
    assert not os.path.exists(user_img_file)
    assert not os.path.exists(queue_img_file)


def test_sqlite_foreign_keys_pragma(in_memory_db):
    """Test that SQLite foreign key constraints are enabled."""
    from sqlalchemy import text
    session = next(database._get_sqlite_session())
    try:
        # Check foreign_keys pragma status
        status = session.execute(text("PRAGMA foreign_keys")).scalar()
        assert status == 1
    finally:
        session.close()


def test_sqlite_foreign_keys_enforcement(in_memory_db):
    """Test that foreign key cascading (ondelete="CASCADE" and "SET NULL") is enforced in SQLite."""
    from sqlalchemy import text
    from app.models import User, UserImage, CheckInLog
    session = next(database._get_sqlite_session())
    
    # 1. Create a user
    user = User(student_id="S555", name="FK Test")
    session.add(user)
    session.commit()
    user_id = user.id
    
    # 2. Add an image and a check-in log
    img = UserImage(user_id=user_id, image_path="dummy.jpg")
    log = CheckInLog(user_id=user_id, student_id="S555", similarity_score=0.95)
    session.add_all([img, log])
    session.commit()
    
    # Verify they exist
    assert session.query(UserImage).filter_by(user_id=user_id).count() == 1
    assert session.query(CheckInLog).filter_by(user_id=user_id).count() == 1
    
    # 3. Perform raw SQL delete to bypass SQLAlchemy's default cascades
    session.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": user_id})
    session.commit()
    
    # 4. Verify cascade delete and nullification
    # Since foreign_keys = ON:
    # - UserImage should be cascaded and deleted (0 remaining)
    # - CheckInLog should have user_id nullified (user_id is None)
    img_count = session.query(UserImage).filter_by(user_id=user_id).count()
    assert img_count == 0
    
    log_after = session.query(CheckInLog).filter_by(student_id="S555").first()
    assert log_after is not None
    assert log_after.user_id is None
    
    session.close()


def test_delete_student_sqlite_transaction_safety(in_memory_db, tmp_path):
    """Test that if SQLite commit fails, local files are NOT deleted on disk."""
    import os
    from unittest.mock import patch
    from app.database import (
        delete_student_from_db,
        upsert_user,
        _get_sqlite_session
    )
    from app.models import User, UserImage
    from sqlalchemy.orm import Session

    # Setup: insert user and images
    upsert_user("S999_FAIL", "Test Delete User Fail")
    session = next(_get_sqlite_session())
    user = session.query(User).filter(User.student_id == "S999_FAIL").first()
    assert user is not None
    user_id = user.id

    user_img_file = tmp_path / "user_img_fail.jpg"
    user_img_file.write_bytes(b"dummy image data")
    
    user_image = UserImage(user_id=user_id, image_path=str(user_img_file))
    session.add(user_image)
    session.commit()
    session.close()

    assert os.path.exists(user_img_file)

    # Patch Session.commit to raise an exception
    with patch.object(Session, 'commit', side_effect=Exception("Simulated commit failure")):
        success = delete_student_from_db("S999_FAIL")
        assert success is False

    # Verify physical file is NOT deleted!
    assert os.path.exists(user_img_file)

    # Verify database record is still present (rollback succeeded)
    session = next(_get_sqlite_session())
    user_after = session.query(User).filter(User.student_id == "S999_FAIL").first()
    assert user_after is not None
    session.close()


