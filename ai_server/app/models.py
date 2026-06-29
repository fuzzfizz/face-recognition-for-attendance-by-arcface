"""
SQLAlchemy ORM model definitions.

This module is the single source of truth for all database table schemas.
It has zero imports from supabase_client, face_processor, or matcher.
"""
import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

# Shared declarative base — all models must use this instance.
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    images = relationship("UserImage", back_populates="user", cascade="all, delete-orphan")
    logs = relationship("CheckInLog", back_populates="user")


class UserImage(Base):
    __tablename__ = "user_images"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    image_path = Column(String(255), nullable=True)
    image_base64 = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="images")


class RegistrationQueue(Base):
    __tablename__ = "registration_queue"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(20), nullable=False, index=True)
    image_path = Column(String(255), nullable=False)
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
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="logs")
