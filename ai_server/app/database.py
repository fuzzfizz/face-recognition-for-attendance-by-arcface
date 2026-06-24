"""
Database layer with dual-mode support:
1. Supabase (cloud) — primary when SUPABASE_URL is configured
2. SQLite (local) — fallback for offline development/testing

Face embeddings stay in .pkl file for fast local matching regardless of DB mode.
"""
import datetime
import os
from typing import Optional, List, Dict, Any

from app.config import DATABASE_URL
from app.matcher import load_embeddings, save_embeddings, match_face
from app.supabase_client import (
    is_available as supabase_available,
    upsert_user as sb_upsert_user,
    get_user as sb_get_user,
    insert_log as sb_insert_log,
    get_logs as sb_get_logs,
    insert_queue_item as sb_insert_queue,
    update_queue_item as sb_update_queue,
    upload_image as sb_upload_image,
)

# ──────────────────────────────────────────────
# SQLite Fallback (only when Supabase is NOT available)
# ──────────────────────────────────────────────
_sqlite_engine = None
_SessionLocal = None
_Base = None
_UserModel = None
_UserImageModel = None
_QueueModel = None
_LogModel = None
_IMAGES_DIR = None


def _init_sqlite():
    """Lazy-init SQLAlchemy models and engine."""
    global _sqlite_engine, _SessionLocal, _Base, _UserModel, _UserImageModel, _QueueModel, _LogModel, _IMAGES_DIR

    if _sqlite_engine is not None:
        return  # Already initialized

    from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text
    from sqlalchemy.orm import declarative_base, sessionmaker, relationship
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _IMAGES_DIR = DATA_DIR / "uploads"
    _IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    _sqlite_engine = create_engine(DATABASE_URL, connect_args=connect_args)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_sqlite_engine)
    _Base = declarative_base()

    class User(_Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True, index=True)
        student_id = Column(String(20), unique=True, nullable=False, index=True)
        created_at = Column(DateTime, default=datetime.datetime.utcnow)
        images = relationship("UserImage", back_populates="user", cascade="all, delete-orphan")
        logs = relationship("CheckInLog", back_populates="user")

    class UserImage(_Base):
        __tablename__ = "user_images"
        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
        image_path = Column(String(255), nullable=True)
        image_base64 = Column(Text, nullable=True)
        created_at = Column(DateTime, default=datetime.datetime.utcnow)
        user = relationship("User", back_populates="images")

    class RegistrationQueue(_Base):
        __tablename__ = "registration_queue"
        id = Column(Integer, primary_key=True, index=True)
        student_id = Column(String(20), nullable=False, index=True)
        image_path = Column(String(255), nullable=False)
        status = Column(String(20), nullable=False, default="pending")
        error_message = Column(Text, nullable=True)
        created_at = Column(DateTime, default=datetime.datetime.utcnow)
        processed_at = Column(DateTime, nullable=True)

    class CheckInLog(_Base):
        __tablename__ = "check_in_logs"
        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
        student_id = Column(String(20), nullable=True)
        similarity_score = Column(Float, nullable=True)
        device_id = Column(String(50), nullable=True)
        timestamp = Column(DateTime, default=datetime.datetime.utcnow)
        user = relationship("User", back_populates="logs")

    _UserModel = User
    _UserImageModel = UserImage
    _QueueModel = RegistrationQueue
    _LogModel = CheckInLog

    _Base.metadata.create_all(bind=_sqlite_engine)


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
    return supabase_available()


def init_db():
    """Initialize the database (SQLite only if Supabase not available)."""
    if not supabase_available():
        _init_sqlite()


def get_db():
    """
    Get a database session.
    Returns Supabase client functions (via supabase_client) when available,
    otherwise falls back to SQLite session generator.
    """
    if supabase_available():
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
def upsert_user(student_id: str):
    """Create user if not exists. Returns user dict/object."""
    if supabase_available():
        return sb_upsert_user(student_id)
    else:
        _init_sqlite()
        session = next(_get_sqlite_session())
        try:
            user = session.query(_UserModel).filter(_UserModel.student_id == student_id).first()
            if not user:
                user = _UserModel(student_id=student_id)
                session.add(user)
                session.commit()
                session.refresh(user)
            return {"id": user.id, "student_id": user.student_id}
        finally:
            session.close()


def get_user_by_student_id(student_id: str):
    if supabase_available():
        return sb_get_user(student_id)
    else:
        _init_sqlite()
        session = next(_get_sqlite_session())
        try:
            user = session.query(_UserModel).filter(_UserModel.student_id == student_id).first()
            return {"id": user.id, "student_id": user.student_id} if user else None
        finally:
            session.close()


# ──────────────────────────────────────────────
# Check-in logs
# ──────────────────────────────────────────────
def insert_log(student_id, similarity_score, device_id, user_id=None):
    if supabase_available():
        return sb_insert_log(student_id, similarity_score, device_id, user_id)
    else:
        _init_sqlite()
        session = next(_get_sqlite_session())
        try:
            log = _LogModel(
                user_id=user_id,
                student_id=student_id,
                similarity_score=similarity_score,
                device_id=device_id,
            )
            session.add(log)
            session.commit()
            return True
        except Exception as e:
            print(f"[SQLite] insert_log error: {e}")
            return False
        finally:
            session.close()


def get_logs(limit=50):
    if supabase_available():
        return sb_get_logs(limit)
    else:
        _init_sqlite()
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
                }
                for log in logs
            ]
        finally:
            session.close()


# ──────────────────────────────────────────────
# Registration Queue
# ──────────────────────────────────────────────
def insert_queue_item(student_id, image_path):
    if supabase_available():
        return sb_insert_queue(student_id, image_path)
    else:
        _init_sqlite()
        session = next(_get_sqlite_session())
        try:
            item = _QueueModel(student_id=student_id, image_path=image_path, status="pending")
            session.add(item)
            session.commit()
            return True
        except Exception as e:
            print(f"[SQLite] insert_queue_item error: {e}")
            return False
        finally:
            session.close()


def get_pending_queue_items():
    if supabase_available():
        # For Supabase, we handle this differently (query + mark as processing)
        return []
    else:
        _init_sqlite()
        session = next(_get_sqlite_session())
        try:
            items = session.query(_QueueModel).filter(_QueueModel.status == "pending").all()
            return [
                {"id": item.id, "student_id": item.student_id, "image_path": item.image_path}
                for item in items
            ]
        finally:
            session.close()


def update_queue_item_status(queue_id, status, error_message=None):
    if supabase_available():
        return sb_update_queue(queue_id, status, error_message)
    else:
        _init_sqlite()
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
    """Upload image. Returns public URL (Supabase) or local path (SQLite)."""
    if supabase_available():
        return sb_upload_image(file_bytes, student_id, ext)
    else:
        _init_sqlite()
        import uuid
        filename = f"{student_id}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = _IMAGES_DIR / filename
        with open(filepath, "wb") as f:
            f.write(file_bytes)
        return str(filepath)


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