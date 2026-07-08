"""
Database layer supporting SQLAlchemy:
1. MySQL (production)
2. SQLite (offline development/testing)
"""
import datetime
import os
from typing import Optional, List, Dict, Any

from app.config import MYSQL_URL
from app.matcher import load_embeddings, save_embeddings, match_face
from app.models import Base, User, RegistrationQueue, CheckInLog

_sqlite_engine = None
_SessionLocal = None
_IMAGES_DIR = None

_UserModel = User
_QueueModel = RegistrationQueue
_LogModel = CheckInLog

def _init_sql_db():
    """Lazy-init SQLAlchemy engine and session factory, then create all tables."""
    global _sqlite_engine, _SessionLocal, _IMAGES_DIR

    if _sqlite_engine is not None:
        return

    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _IMAGES_DIR = DATA_DIR / "uploads"
    _IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    url = MYSQL_URL or "sqlite:///./data/face_recognition.db"

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

    # Migrations for local SQLite offline DB
    if url.startswith("sqlite"):
        with _sqlite_engine.begin() as conn:
            res = conn.execute(text("PRAGMA table_info(check_in_logs);")).fetchall()
            cols = [col[1] for col in res]
            if "error_message" not in cols:
                conn.execute(text("ALTER TABLE check_in_logs ADD COLUMN error_message VARCHAR;"))
            
            q_res = conn.execute(text("PRAGMA table_info(registration_queue);")).fetchall()
            q_cols = [col[1] for col in q_res]
            if "error_message" not in q_cols:
                conn.execute(text("ALTER TABLE registration_queue ADD COLUMN error_message VARCHAR;"))
            if "image_blob" not in q_cols:
                conn.execute(text("ALTER TABLE registration_queue ADD COLUMN image_blob BLOB;"))

def init_db():
    _init_sql_db()

def _init_sqlite():
    _init_sql_db()

def _get_db_session():
    _init_sql_db()
    return _SessionLocal()

def _get_sqlite_session():
    db = _get_db_session()
    try:
        yield db
    finally:
        db.close()

def get_db():
    return _get_sqlite_session()

def upsert_user(student_id: str, name: str = None):
    session = _get_db_session()
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
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_user_by_student_id(student_id: str):
    session = _get_db_session()
    try:
        user = session.query(_UserModel).filter(_UserModel.student_id == student_id).first()
        return {"id": user.id, "student_id": user.student_id} if user else None
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def insert_log(
    student_id: Optional[str],
    similarity_score: float,
    device_id: str,
    user_id: Optional[int] = None,
    error_message: Optional[str] = None
):
    session = _get_db_session()
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
        session.rollback()
        print(f"[SQL] insert_log error: {e}")
        return False
    finally:
        session.close()

def get_logs(limit=50):
    session = _get_db_session()
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
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_latest_check_in_log(student_id: str) -> Optional[dict]:
    session = _get_db_session()
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
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def insert_queue_item(student_id, image_path):
    session = _get_db_session()
    try:
        if image_path and isinstance(image_path, str) and image_path.startswith("db://registration_queue/"):
            try:
                row_id = int(image_path.split("/")[-1])
            except ValueError:
                return False
            item = session.query(_QueueModel).filter(_QueueModel.id == row_id).first()
            if item:
                item.status = "pending"
                session.commit()
                return True
            session.rollback()
            return False
        else:
            # Fallback for local files/tests
            blob_bytes = None
            if image_path:
                import os
                if isinstance(image_path, str) and os.path.exists(image_path):
                    with open(image_path, "rb") as f:
                        blob_bytes = f.read()
                elif isinstance(image_path, bytes):
                    blob_bytes = image_path
                else:
                    blob_bytes = str(image_path).encode("utf-8")
            
            if not blob_bytes:
                blob_bytes = b"dummy_image_bytes"

            item = _QueueModel(student_id=student_id, image_blob=blob_bytes, status="pending")
            session.add(item)
            session.commit()
            return True
    except Exception as e:
        session.rollback()
        print(f"[SQL] insert_queue_item error: {e}")
        return False
    finally:
        session.close()

def get_pending_queue_items(limit: Optional[int] = None):
    session = _get_db_session()
    try:
        query = session.query(_QueueModel).filter(_QueueModel.status == "pending")
        if limit is not None:
            query = query.limit(limit)
        items = query.all()
        return [
            {
                "id": item.id,
                "student_id": item.student_id,
                "image_path": f"db://registration_queue/{item.id}"
            }
            for item in items
        ]
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def update_queue_item_status(queue_id, status, error_message=None):
    session = _get_db_session()
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
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def upload_image(file_bytes, student_id, ext="jpg"):
    """Upload image. Returns database URI (MySQL/SQLite)."""
    session = _get_db_session()
    try:
        item = _QueueModel(
            student_id=student_id,
            image_blob=file_bytes,
            status="uploading"
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        return f"db://registration_queue/{item.id}"
    except Exception as e:
        session.rollback()
        print(f"[SQL] upload_image error: {e}")
        return None
    finally:
        session.close()

def get_image_blob_by_ref(ref_uri: str) -> Optional[bytes]:
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

    session = _get_db_session()
    try:
        item = session.query(_QueueModel).filter(_QueueModel.id == row_id).first()
        return item.image_blob if item else None
    except Exception as e:
        session.rollback()
        print(f"[SQL] get_image_blob_by_ref error: {e}")
        return None
    finally:
        session.close()

def get_all_embeddings():
    return load_embeddings()

def save_all_embeddings(embeddings_data):
    return save_embeddings(embeddings_data)

def match_face_embedding(query_embedding):
    return match_face(query_embedding)

def delete_student_from_db(student_id: str) -> bool:
    session = _get_db_session()
    try:
        import os
        files_to_delete = []

        # 1. Delete associated logs
        user = session.query(_UserModel).filter(_UserModel.student_id == student_id).first()
        
        logs_by_sid = session.query(_LogModel).filter(_LogModel.student_id == student_id).all()
        for log in logs_by_sid:
            session.delete(log)
        
        if user:
            logs_by_uid = session.query(_LogModel).filter(_LogModel.user_id == user.id).all()
            for log in logs_by_uid:
                session.delete(log)

        # 2. Delete queue items
        q_items = session.query(_QueueModel).filter(_QueueModel.student_id == student_id).all()
        for item in q_items:
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
        session.rollback()
        print(f"[SQL] delete_student_from_db error: {e}")
        return False
    finally:
        session.close()