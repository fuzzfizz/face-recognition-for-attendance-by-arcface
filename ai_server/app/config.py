import os
import sys
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDINGS_PATH = DATA_DIR / "face_embeddings.pkl"

# Exclusive MySQL Database Configuration
MYSQL_URL = os.getenv("MYSQL_URL", "")

# Throws a clean error if missing in production, or fallback to empty string for local/testing override
is_local_or_test = (
    "pytest" in sys.modules or
    "unittest" in sys.modules or
    os.getenv("ENV") in ("local", "testing", "development") or 
    os.getenv("APP_ENV") in ("local", "testing", "development") or 
    os.getenv("TESTING") == "true"
)

if os.getenv("FORCE_PROD_CHECK") == "true":
    is_local_or_test = False

if not MYSQL_URL and not is_local_or_test:
    raise RuntimeError(
        "MYSQL_URL environment variable is not set. "
        "In production, a valid MySQL connection URL is required (e.g. mysql+pymysql://user:pass@host:port/dbname)."
    )

# Face Recognition Configuration
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.45"))
MODEL_NAME = os.getenv("MODEL_NAME", "buffalo_l")

TRAINING_SCHEDULE_INFO = os.getenv("TRAINING_SCHEDULE_INFO", "daily at 19:00")
TRAINING_SCHEDULE_TIMES = os.getenv("TRAINING_SCHEDULE_TIMES", "19:00")

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))