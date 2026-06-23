import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from app.config import DATABASE_URL

# Setup SQLAlchemy engine and session
# "connect_args" is only needed for SQLite to allow multi-thread access
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    images = relationship("UserImage", back_populates="user", cascade="all, delete-orphan")
    logs = relationship("CheckInLog", back_populates="user")

class UserImage(Base):
    __tablename__ = "user_images"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # image_path: stores local path if images are saved on disk
    image_path = Column(String(255), nullable=True)
    # image_base64: stores the base64 encoded image content for easy database-only storage
    image_base64 = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="images")

class CheckInLog(Base):
    __tablename__ = "check_in_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    similarity_score = Column(Float, nullable=True)
    device_id = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="logs")

# Helper to initialize DB tables
def init_db():
    Base.metadata.create_all(bind=engine)

# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
