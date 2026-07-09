"""
SQLAlchemy ORM model definitions.

This module is the single source of truth for all database table schemas.
It has zero imports from supabase_client, face_processor, or matcher.
"""
import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import declarative_base, relationship

# Shared declarative base — all models must use this instance.
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    logs = relationship("CheckInLog", back_populates="user")


class RegistrationQueue(Base):
    __tablename__ = "registration_queue"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(20), nullable=False, index=True)
    image_blob = Column(LargeBinary, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)


class CheckInLog(Base):
    __tablename__ = "check_in_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    student_id = Column(String(20), nullable=True)
    similarity_score = Column(Float, nullable=True)
    device_id = Column(String(50), nullable=True)
    error_message = Column(String(255), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="logs")

