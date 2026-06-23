import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDINGS_PATH = DATA_DIR / "face_embeddings.pkl"

# Database Configuration
# Default to SQLite for easy development/testing, but can be overridden with MySQL/PostgreSQL URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./face_recognition.db")

# Face Recognition Configuration
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.60"))
MODEL_NAME = os.getenv("MODEL_NAME", "buffalo_l")

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
