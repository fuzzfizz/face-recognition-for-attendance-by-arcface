"""
Database layer supporting SQLAlchemy:
1. MySQL (production)
"""
import datetime
from typing import Optional, List, Dict, Any

from app.config import MYSQL_URL
from app.matcher import load_embeddings, save_embeddings, match_face, invalidate_cache
from app.models import Base, User, RegistrationQueue, CheckInLog

_engine = None
_SessionLocal = None

_UserModel = User
_QueueModel = RegistrationQueue
_LogModel = CheckInLog

def _init_sql_db():
    global _engine, _SessionLocal
    if _engine is not None:
        return

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    if not MYSQL_URL:
        raise RuntimeError(
            "MYSQL_URL environment variable is not set. "
            "Please configure it to point to your MySQL database."
        )

    if MYSQL_URL.startswith("sqlite://"):
        from sqlalchemy.pool import StaticPool
        _engine = create_engine(
            MYSQL_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
    else:
        _engine = create_engine(MYSQL_URL)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    Base.metadata.create_all(bind=_engine)

def init_db():
    _init_sql_db()

def _get_db_session():
    _init_sql_db()
    return _SessionLocal()

def get_db():
    db = _get_db_session()
    try:
        yield db
    finally:
        db.close()

def _get_sqlite_session():
    return get_db()


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

def upload_image(file_bytes, student_id):
    """Upload image directly as blob to MySQL with status 'pending'."""
    session = _get_db_session()
    try:
        item = _QueueModel(
            student_id=student_id,
            image_blob=file_bytes,
            status="pending"
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        return item.id
    except Exception as e:
        session.rollback()
        print(f"[MySQL] upload_image error: {e}")
        return None
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
            {"id": item.id, "student_id": item.student_id, "image_blob": item.image_blob}
            for item in items
        ]
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_all_embeddings():
    return load_embeddings()

def save_all_embeddings(embeddings_data):
    return save_embeddings(embeddings_data)

def prune_student_embeddings(student_id: str) -> None:
    """Remove a student's embeddings from local storage and clear cache."""
    existing = get_all_embeddings()
    updated = [e for e in existing if e.get("student_id") != student_id]
    if len(updated) < len(existing):
        save_all_embeddings(updated)
        invalidate_cache()

def match_face_embedding(query_embedding):
    return match_face(query_embedding)

def delete_student_from_db(student_id: str) -> bool:
    session = _get_db_session()
    try:
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
        return True
    except Exception as e:
        session.rollback()
        print(f"[SQL] delete_student_from_db error: {e}")
        return False
    finally:
        session.close()