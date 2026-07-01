import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDINGS_PATH = DATA_DIR / "face_embeddings.pkl"

# Fallback to SQLite for completely offline dev (optional)
# If no Supabase config is provided, the app falls back to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./face_recognition.db")

# ──────────────────────────────────────────────
# Supabase Configuration
# ──────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "face-images")

# Face Recognition Configuration
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.60"))
MODEL_NAME = os.getenv("MODEL_NAME", "buffalo_l")

TRAINING_SCHEDULE_INFO = os.getenv("TRAINING_SCHEDULE_INFO", "daily at 19:00")
TRAINING_SCHEDULE_TIMES = os.getenv("TRAINING_SCHEDULE_TIMES", "19:00")

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))