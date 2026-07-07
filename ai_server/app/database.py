"""
Database layer with dual-mode support:
1. Supabase (cloud) — primary when SUPABASE_URL is configured
2. SQLite (local) — fallback for offline development/testing

Face embeddings stay in .pkl file for fast local matching regardless of DB mode.
"""
import datetime
import os
from typing import Optional, List, Dict, Any

from app.config import DATABASE_URL, DB_MODE, MYSQL_URL
from app.matcher import load_embeddings, save_embeddings, match_face
from app.models import Base, User, RegistrationQueue, CheckInLog
from app.supabase_client import (
    is_available as supabase_available,
    upsert_user as sb_upsert_user,
    get_user as sb_get_user,
    insert_log as sb_insert_log,
    get_logs as sb_get_logs,
    get_latest_check_in_log as sb_get_latest_check_in_log,
    insert_queue_item as sb_insert_queue,
    get_pending_queue_items as sb_get_pending_queue_items,
    update_queue_item as sb_update_queue,
    upload_image as sb_upload_image,
)

# ──────────────────────────────────────────────
# SQLite Fallback (only when Supabase is NOT available)
# ──────────────────────────────────────────────
_sqlite_engine = None
_SessionLocal = None
_IMAGES_DIR = None

# Aliases kept for internal use — models live in app.models
_UserModel = User
_QueueModel = RegistrationQueue
_LogModel = CheckInLog


def _init_sql_db():
    """Lazy-init SQLAlchemy engine and session factory, then create all tables."""
    global _sqlite_engine, _SessionLocal, _IMAGES_DIR

    if _sqlite_engine is not None:
        return  # Already initialized

    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _IMAGES_DIR = DATA_DIR / "uploads"
    _IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    url = MYSQL_URL if DB_MODE == "mysql" else DATABASE_URL
    if not url:
        url = DATABASE_URL

    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    _sqlite_engine = create_engine(url, connect_args=connect_args)

    if url.startswith("sqlite"):
        from sqlalchemy import event
        @event.listens_for(_sqlite_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_sqlite_engine)

    Base.metadata.create_all(bind=_sqlite_engine)

    # Dynamic migrations for SQLite fallback
    if url.startswith("sqlite"):
        with _sqlite_engine.begin() as conn:
            # Check if error_message column exists in check_in_logs
            res = conn.execute(text("PRAGMA table_info(check_in_logs);")).fetchall()
            cols = [col[1] for col in res]
            if "error_message" not in cols:
                conn.execute(text("ALTER TABLE check_in_logs ADD COLUMN error_message VARCHAR;"))
            
            # Check if error_message column exists in registration_queue
            q_res = conn.execute(text("PRAGMA table_info(registration_queue);")).fetchall()
            q_cols = [col[1] for col in q_res]
            if "error_message" not in q_cols:
                conn.execute(text("ALTER TABLE registration_queue ADD COLUMN error_message VARCHAR;"))
            if "image_blob" not in q_cols:
                conn.execute(text("ALTER TABLE registration_queue ADD COLUMN image_blob BLOB;"))


def _init_sqlite():
    _init_sql_db()



def _get_sqlite_session():
    _init_sqlite()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ──────────────────────────────────────────────
# Public API — auto-selects Supabase or SQLite
# ──────────────────────────────────────────────
def using_supabase() -> bool:
    """Returns True if Supabase is available and will be used as primary storage."""
    if DB_MODE == "supabase":
        return True
    if DB_MODE in ("mysql", "sqlite"):
        return False
    return supabase_available()


def init_db():
    """Initialize the database (SQLite/MySQL only if Supabase not used)."""
    if not using_supabase():
        _init_sql_db()


def get_db():
    """
    Get a database session.
    Returns Supabase client functions (via supabase_client) when available,
    otherwise falls back to SQLite/MySQL session generator.
    """
    if using_supabase():
        # Return a dummy context manager for Supabase mode
        class SupabaseDBSession:
            def __enter__(self):
                return None
            def __exit__(self, *args):
                pass
        return SupabaseDBSession()
    else:
        return _get_sqlite_session()


# ──────────────────────────────────────────────
# User operations
# ──────────────────────────────────────────────
def upsert_user(student_id: str, name: str = None):
    """Create user if not exists. Returns user dict/object."""
    if using_supabase():
        return sb_upsert_user(student_id, name)
    else:
        _init_sql_db()
        session = next(_get_sqlite_session())
        try:
            user = session.query(_UserModel).filter(_UserModel.student_id == student_id).first()
            if not user:
                user = _UserModel(student_id=student_id, name=name)
                session.add(user)
                session.commit()
                session.refresh(user)
            elif name:
                user.name = name
                session.commit()
                session.refresh(user)
            return {"id": user.id, "student_id": user.student_id, "name": user.name}
        finally:
            session.close()


def get_user_by_student_id(student_id: str):
    if using_supabase():
        return sb_get_user(student_id)
    else:
        _init_sql_db()
        session = next(_get_sqlite_session())
        try:
            user = session.query(_UserModel).filter(_UserModel.student_id == student_id).first()
            return {"id": user.id, "student_id": user.student_id} if user else None
        finally:
            session.close()


# ──────────────────────────────────────────────
# Check-in logs
# ──────────────────────────────────────────────
def insert_log(
    student_id: Optional[str],
    similarity_score: float,
    device_id: str,
    user_id: Optional[int] = None,
    error_message: Optional[str] = None
):
    if using_supabase():
        return sb_insert_log(student_id, similarity_score, device_id, user_id, error_message=error_message)
    else:
        _init_sql_db()
        session = next(_get_sqlite_session())
        try:
            actual_user_id = None
            if student_id:
                user = session.query(_UserModel).filter(_UserModel.student_id == student_id).first()
                if user:
                    actual_user_id = user.id

            log = _LogModel(
                user_id=actual_user_id,
                student_id=student_id,
                similarity_score=similarity_score,
                device_id=device_id,
                error_message=error_message,
            )
            session.add(log)
            session.commit()
            return True
        except Exception as e:
            print(f"[SQL] insert_log error: {e}")
            return False
        finally:
            session.close()



def get_logs(limit=50):
    if using_supabase():
        return sb_get_logs(limit)
    else:
        _init_sql_db()
        session = next(_get_sqlite_session())
        try:
            logs = session.query(_LogModel).order_by(_LogModel.timestamp.desc()).limit(limit).all()
            return [
                {
                    "id": log.id,
                    "student_id": log.student_id if log.student_id else "Unknown",
                    "similarity_score": log.similarity_score,
                    "device_id": log.device_id,
                    "timestamp": log.timestamp,
                    "error_message": log.error_message,
                }
                for log in logs
            ]
        finally:
            session.close()


def get_latest_check_in_log(student_id: str) -> Optional[dict]:
    if using_supabase():
        return sb_get_latest_check_in_log(student_id)
    else:
        _init_sql_db()
        session = next(_get_sqlite_session())
        try:
            log = session.query(_LogModel) \
                .filter(_LogModel.student_id == student_id) \
                .order_by(_LogModel.timestamp.desc()) \
                .first()
            if log:
                return {
                    "id": log.id,
                    "student_id": log.student_id,
                    "similarity_score": log.similarity_score,
                    "device_id": log.device_id,
                    "timestamp": log.timestamp.isoformat() if hasattr(log.timestamp, "isoformat") else log.timestamp,
                    "error_message": log.error_message
                }
            return None
        finally:
            session.close()


# ──────────────────────────────────────────────
# Registration Queue
# ──────────────────────────────────────────────
def insert_queue_item(student_id, image_path):
    if using_supabase():
        return sb_insert_queue(student_id, image_path)
    
    _init_sql_db()
    session = next(_get_sqlite_session())
    try:
        if DB_MODE == "mysql" and image_path and image_path.startswith("db://registration_queue/"):
            try:
                row_id = int(image_path.split("/")[-1])
            except ValueError:
                return False
            item = session.query(_QueueModel).filter(_QueueModel.id == row_id).first()
            if item:
                item.status = "pending"
                item.image_path = image_path
                session.commit()
                return True
            return False
        else:
            item = _QueueModel(student_id=student_id, image_path=image_path, status="pending")
            session.add(item)
            session.commit()
            return True
    except Exception as e:
        print(f"[SQL] insert_queue_item error: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def get_pending_queue_items(limit: Optional[int] = None):
    if using_supabase():
        return sb_get_pending_queue_items(limit)
    else:
        _init_sql_db()
        session = next(_get_sqlite_session())
        try:
            query = session.query(_QueueModel).filter(_QueueModel.status == "pending")
            if limit is not None:
                query = query.limit(limit)
            items = query.all()
            return [
                {"id": item.id, "student_id": item.student_id, "image_path": item.image_path}
                for item in items
            ]
        finally:
            session.close()


def update_queue_item_status(queue_id, status, error_message=None):
    if using_supabase():
        return sb_update_queue(queue_id, status, error_message)
    else:
        _init_sql_db()
        session = next(_get_sqlite_session())
        try:
            item = session.query(_QueueModel).filter(_QueueModel.id == queue_id).first()
            if item:
                item.status = status
                item.processed_at = datetime.datetime.utcnow()
                if error_message:
                    item.error_message = error_message
                session.commit()
                return True
            return False
        finally:
            session.close()


# ──────────────────────────────────────────────
# Image upload
# ──────────────────────────────────────────────
def upload_image(file_bytes, student_id, ext="jpg"):
    """Upload image. Returns public URL (Supabase), database URI (MySQL), or local path (SQLite)."""
    if using_supabase():
        return sb_upload_image(file_bytes, student_id, ext)
    
    if DB_MODE == "mysql":
        _init_sql_db()
        session = next(_get_sqlite_session())
        try:
            item = _QueueModel(
                student_id=student_id,
                image_blob=file_bytes,
                status="uploading",
                image_path=None
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            return f"db://registration_queue/{item.id}"
        except Exception as e:
            print(f"[MySQL] upload_image error: {e}")
            session.rollback()
            return None
        finally:
            session.close()
    else:
        _init_sql_db()
        import uuid
        filename = f"{student_id}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = _IMAGES_DIR / filename
        with open(filepath, "wb") as f:
            f.write(file_bytes)
        return str(filepath)


def get_image_blob_by_ref(ref_uri: str) -> Optional[bytes]:
    """
    Fetch image blob from database using the reference URI.
    Supported URIs:
    - db://registration_queue/{id}
    """
    if not ref_uri or not ref_uri.startswith("db://"):
        return None

    try:
        parts = ref_uri[5:].split("/")
        if len(parts) != 2:
            return None
        table_name, row_id_str = parts
        row_id = int(row_id_str)
    except (ValueError, IndexError):
        return None

    if table_name != "registration_queue":
        return None

    _init_sql_db()
    session = next(_get_sqlite_session())
    try:
        from app.models import RegistrationQueue
        item = session.query(RegistrationQueue).filter(RegistrationQueue.id == row_id).first()
        return item.image_blob if item else None
    except Exception as e:
        print(f"[SQL] get_image_blob_by_ref error: {e}")
        return None
    finally:
        session.close()


# ──────────────────────────────────────────────

# Embeddings (always local .pkl — never sent to cloud)
# ──────────────────────────────────────────────
def get_all_embeddings():
    """Load face embeddings from local .pkl file."""
    return load_embeddings()


def save_all_embeddings(embeddings_data):
    """Save face embeddings to local .pkl file."""
    return save_embeddings(embeddings_data)


def match_face_embedding(query_embedding):
    """Match a face embedding against local .pkl (fast, no network)."""
    return match_face(query_embedding)


def delete_student_from_db(student_id: str) -> bool:
    if using_supabase():
        from app.supabase_client import delete_student_from_supabase
        return delete_student_from_supabase(student_id)
    else:
        _init_sql_db()
        session = next(_get_sqlite_session())
        try:
            import os
            files_to_delete = []

            # 1. Delete associated logs
            user = session.query(_UserModel).filter(_UserModel.student_id == student_id).first()
            
            # Query logs by student_id
            logs_by_sid = session.query(_LogModel).filter(_LogModel.student_id == student_id).all()
            for log in logs_by_sid:
                session.delete(log)
            
            # Query logs by user_id if user exists
            if user:
                logs_by_uid = session.query(_LogModel).filter(_LogModel.user_id == user.id).all()
                for log in logs_by_uid:
                    session.delete(log)

            # 2. Delete queue items
            q_items = session.query(_QueueModel).filter(_QueueModel.student_id == student_id).all()
            for item in q_items:
                if item.image_path and not item.image_path.startswith("db://"):
                    files_to_delete.append(item.image_path)
                session.delete(item)

            # 3. Delete user
            if user:
                session.delete(user)

            session.commit()

            # Delete physical files from disk only after successful commit
            for filepath in files_to_delete:
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except Exception:
                        pass

            return True
        except Exception as e:
            print(f"[SQL] delete_student_from_db error: {e}")
            session.rollback()
            return False
        finally:
            session.close()