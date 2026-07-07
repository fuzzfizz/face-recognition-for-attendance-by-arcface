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
    from app.models import User, RegistrationQueue

    # 1. Setup: insert user and queue items, and create physical dummy files on disk
    upsert_user("S999", "Test Delete User")
    
    # Let's get the user id
    session = next(_get_sqlite_session())
    user = session.query(User).filter(User.student_id == "S999").first()
    assert user is not None

    # Create dummy file
    queue_img_file = tmp_path / "queue_img.jpg"
    queue_img_file.write_bytes(b"dummy queue data")

    assert os.path.exists(queue_img_file)

    insert_queue_item("S999", str(queue_img_file))
    session.close()

    # 2. Perform deletion
    success = delete_student_from_db("S999")
    assert success is True

    # 3. Verify database clean up
    session = next(_get_sqlite_session())
    user_after = session.query(User).filter(User.student_id == "S999").first()
    assert user_after is None

    queue_after = session.query(RegistrationQueue).filter(RegistrationQueue.student_id == "S999").all()
    assert len(queue_after) == 0
    session.close()

    # 4. Verify physical files are deleted
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
    """Test that foreign key cascading (ondelete="SET NULL") is enforced in SQLite."""
    from sqlalchemy import text
    from app.models import User, CheckInLog
    session = next(database._get_sqlite_session())
    
    # 1. Create a user
    user = User(student_id="S555", name="FK Test")
    session.add(user)
    session.commit()
    user_id = user.id
    
    # 2. Add a check-in log
    log = CheckInLog(user_id=user_id, student_id="S555", similarity_score=0.95)
    session.add(log)
    session.commit()
    
    # Verify it exists
    assert session.query(CheckInLog).filter_by(user_id=user_id).count() == 1
    
    # 3. Perform raw SQL delete to bypass SQLAlchemy's default cascades
    session.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": user_id})
    session.commit()
    
    # 4. Verify cascade nullification
    # Since foreign_keys = ON:
    # - CheckInLog should have user_id nullified (user_id is None)
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
        insert_queue_item,
        upsert_user,
        _get_sqlite_session
    )
    from app.models import User, RegistrationQueue
    from sqlalchemy.orm import Session

    # Setup: insert user and queue item with a dummy image
    upsert_user("S999_FAIL", "Test Delete User Fail")
    
    queue_img_file = tmp_path / "queue_img_fail.jpg"
    queue_img_file.write_bytes(b"dummy queue data")
    
    insert_queue_item("S999_FAIL", str(queue_img_file))

    assert os.path.exists(queue_img_file)

    # Patch Session.commit to raise an exception
    with patch.object(Session, 'commit', side_effect=Exception("Simulated commit failure")):
        success = delete_student_from_db("S999_FAIL")
        assert success is False

    # Verify physical file is NOT deleted!
    assert os.path.exists(queue_img_file)

    # Verify database record is still present (rollback succeeded)
    session = next(_get_sqlite_session())
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


def test_sqlite_dynamic_migration(tmp_path):
    """Test that SQLite initialization automatically performs ALTER TABLE when error_message is missing."""
    import sqlite3
    from unittest.mock import patch
    from sqlalchemy import text
    from app import database
    
    # 1. Create a dummy sqlite database file with old schemas (missing error_message)
    db_file = tmp_path / "old_face_recognition.db"
    conn_raw = sqlite3.connect(db_file)
    cursor = conn_raw.cursor()
    
    # Create tables without error_message
    cursor.execute("""
        CREATE TABLE check_in_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            student_id VARCHAR(20),
            similarity_score FLOAT,
            device_id VARCHAR(50),
            timestamp DATETIME
        );
    """)
    cursor.execute("""
        CREATE TABLE registration_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id VARCHAR(20),
            image_path VARCHAR(255),
            status VARCHAR(20),
            created_at DATETIME,
            processed_at DATETIME
        );
    """)
    conn_raw.commit()
    conn_raw.close()
    
    # 2. Run _init_sqlite() pointing to this temporary database file
    orig_engine = database._sqlite_engine
    orig_session_local = database._SessionLocal
    database._sqlite_engine = None
    database._SessionLocal = None
    
    db_url = f"sqlite:///{db_file}"
    
    try:
        with patch("app.database.supabase_available", return_value=False), \
             patch("app.database.DATABASE_URL", db_url):
            
            # This should trigger _init_sqlite and run the migration code
            database._init_sqlite()
            
            # Connect using the new engine to verify columns
            with database._sqlite_engine.connect() as conn:
                res = conn.execute(text("PRAGMA table_info(check_in_logs);")).fetchall()
                cols = [col[1] for col in res]
                assert "error_message" in cols
                
                q_res = conn.execute(text("PRAGMA table_info(registration_queue);")).fetchall()
                q_cols = [col[1] for col in q_res]
                assert "error_message" in q_cols
                assert "image_blob" in q_cols
    finally:
        # Restore settings
        if database._sqlite_engine:
            database._sqlite_engine.dispose()
        database._sqlite_engine = orig_engine
        database._SessionLocal = orig_session_local
def test_mysql_mode_upload_image_and_insert_queue_item(in_memory_db):
    """Test upload_image and insert_queue_item in MySQL DB_MODE."""
    from app.database import upload_image, insert_queue_item, _get_sqlite_session
    from app.models import RegistrationQueue
    from unittest.mock import patch

    with patch("app.database.DB_MODE", "mysql"):
        # 1. Test upload_image (inserts temporary row)
        image_bytes = b"mysql_dummy_image_bytes"
        ref_path = upload_image(image_bytes, "S100")
        assert ref_path is not None
        assert ref_path.startswith("db://registration_queue/")
        
        # Verify temporary row exists in DB
        session = next(_get_sqlite_session())
        row_id = int(ref_path.split("/")[-1])
        item = session.query(RegistrationQueue).filter(RegistrationQueue.id == row_id).first()
        assert item is not None
        assert item.student_id == "S100"
        assert item.image_blob == image_bytes
        assert item.status == "uploading"
        session.close()

        # 2. Test insert_queue_item (updates status to pending and sets image_path)
        success = insert_queue_item("S100", ref_path)
        assert success is True

        # Verify row status was updated
        session = next(_get_sqlite_session())
        item_updated = session.query(RegistrationQueue).filter(RegistrationQueue.id == row_id).first()
        assert item_updated is not None
        assert item_updated.status == "pending"
        assert item_updated.image_path == ref_path
        session.close()


def test_get_image_blob_by_ref(in_memory_db):
    """Test get_image_blob_by_ref fetches blob bytes from registration_queue and user_images."""
    from app.database import get_image_blob_by_ref, _get_sqlite_session
    from app.models import RegistrationQueue, User, UserImage

    session = next(_get_sqlite_session())
    
    # 1. Setup registration_queue item
    q_item = RegistrationQueue(student_id="S101", image_blob=b"queue_blob_data", status="pending")
    session.add(q_item)
    session.commit()
    q_id = q_item.id

    # 2. Setup user and user_images item
    user = User(student_id="S101", name="Blob User")
    session.add(user)
    session.commit()
    u_id = user.id
    
    u_img = UserImage(user_id=u_id, image_blob=b"user_blob_data")
    session.add(u_img)
    session.commit()
    ui_id = u_img.id

    session.close()

    # 3. Test retrieving from registration_queue
    blob1 = get_image_blob_by_ref(f"db://registration_queue/{q_id}")
    assert blob1 == b"queue_blob_data"

    # 4. Test retrieving from user_images
    blob2 = get_image_blob_by_ref(f"db://user_images/{ui_id}")
    assert blob2 == b"user_blob_data"

    # 5. Test invalid table name
    blob3 = get_image_blob_by_ref(f"db://invalid_table/{q_id}")
    assert blob3 is None

    # 6. Test invalid formats
    assert get_image_blob_by_ref("db://registration_queue/invalid_id") is None
    assert get_image_blob_by_ref("db://registration_queue") is None
    assert get_image_blob_by_ref("invalid_prefix://registration_queue/1") is None


def test_delete_student_cascade_sql(in_memory_db):
    """Test cascade deletion of user records, queue items, and logs cleanly in SQL mode."""
    from app.database import delete_student_from_db, _get_sqlite_session
    from app.models import User, RegistrationQueue, CheckInLog, UserImage

    session = next(_get_sqlite_session())
    
    # Setup
    user = User(student_id="S102", name="Cascade User")
    session.add(user)
    session.commit()
    u_id = user.id

    q_item = RegistrationQueue(student_id="S102", image_path="db://registration_queue/1", status="pending")
    session.add(q_item)
    
    u_img = UserImage(user_id=u_id, image_blob=b"img")
    session.add(u_img)
    
    log1 = CheckInLog(student_id="S102", similarity_score=0.9, device_id="D1")
    session.add(log1)
    
    log2 = CheckInLog(user_id=u_id, student_id="S102", similarity_score=0.95, device_id="D2")
    session.add(log2)

    session.commit()
    session.close()

    # Verify everything exists before deletion
    session = next(_get_sqlite_session())
    assert session.query(User).filter(User.student_id == "S102").count() == 1
    assert session.query(RegistrationQueue).filter(RegistrationQueue.student_id == "S102").count() == 1
    assert session.query(UserImage).filter(UserImage.user_id == u_id).count() == 1
    assert session.query(CheckInLog).filter(CheckInLog.student_id == "S102").count() == 2
    session.close()

    # Delete student
    success = delete_student_from_db("S102")
    assert success is True

    # Verify cascade deletion
    session = next(_get_sqlite_session())
    assert session.query(User).filter(User.student_id == "S102").count() == 0
    assert session.query(RegistrationQueue).filter(RegistrationQueue.student_id == "S102").count() == 0
    assert session.query(UserImage).filter(UserImage.user_id == u_id).count() == 0
    assert session.query(CheckInLog).filter(CheckInLog.student_id == "S102").count() == 0
    session.close()

