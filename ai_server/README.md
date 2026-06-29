# Face Recognition AI Server

A high-accuracy AI-powered attendance system using **ArcFace** (via InsightFace) for face recognition. The system consists of a FastAPI backend server featuring a hybrid architecture: data persistence using Supabase (or SQLite fallback) and in-memory, local face matching using serialized `.pkl` embeddings for ultra-fast, zero-network verification.

## Features

- **Hybrid Architecture**: Data is persisted in Supabase (primary) or local SQLite (fallback), while face matching is performed locally using memory-cached `.pkl` embeddings for high speed.
- **URL-Aware Image Processing**: Automatically handles face images from local files, HTTP/HTTPS URLs, raw byte streams, and base64-encoded strings.
- **Admin Auth Guard**: Key administration actions (like triggering training) are protected via the `X-Admin-Key` header.
- **Non-blocking Registration**: Registration endpoint stores images and queues them immediately, returning a status to the client without blocking.
- **Clean Layered Architecture**:
  - **Routers**: API routing and request/response validation.
  - **Services**: Business logic.
  - **Data Access & Models**: Supabase client wrapper & SQLAlchemy models.
  - **Domain modules**: Image processing & face matching (no DB/HTTP dependencies).

## Project Structure

```
ai_server/
├── app/
│   ├── routers/             # API route controllers
│   │   ├── v1/              # Legacy endpoints (deprecated)
│   │   ├── registration.py  # User registration status and queue endpoints
│   │   ├── training.py      # Admin training trigger endpoints
│   │   ├── verification.py  # Real-time face verification
│   │   └── logs.py          # Attendance logs retrieval
│   ├── services/            # Business logic
│   │   ├── registration_service.py
│   │   ├── training_service.py
│   │   └── verification_service.py
│   ├── utils/               # Image loading and decoding utility functions
│   │   └── image_utils.py
│   ├── config.py            # Global settings & config
│   ├── database.py          # SQLite/Supabase unified access layer
│   ├── face_processor.py    # InsightFace wrapper for embeddings
│   ├── matcher.py           # Dot product Cosine similarity matching
│   ├── models.py            # SQLAlchemy database tables mapping
│   ├── schemas.py           # Pydantic request & response validators
│   └── main.py              # Application entrypoint & startup lifecycle
├── data/
│   └── face_embeddings.pkl  # Local face embeddings database
├── tests/                   # Python test suite
├── requirements.txt         # Python dependencies
└── README.md                # This documentation file
```

## Setup & Installation

### 1. Create a Virtual Environment and Install Dependencies

```bash
python -m venv venv
# On Windows:
.\venv\Scripts\Activate.ps1
# On macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Environment Variables configuration

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Define the configuration values:

```ini
# Supabase (Set these to activate Supabase mode, otherwise SQLite is used)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key
SUPABASE_STORAGE_BUCKET=face-images

# Admin Auth Key
ADMIN_API_KEY=your-secret-admin-key

# Server binding
HOST=0.0.0.0
PORT=8000
```

### 3. Run the Server

```bash
python app/main.py
```

## API Endpoints

### Core Endpoints

| Method | Endpoint | Description | Auth |
| :--- | :--- | :--- | :--- |
| `POST` | `/register` | Register user by student_id with uploaded image files (Multipart Form). Non-blocking. | None |
| `GET` | `/register/status/{student_id}` | Check registration processing status for a student. | None |
| `POST` | `/train-now` | Trigger training for all pending queue items immediately. | `X-Admin-Key` header |
| `POST` | `/verify` | Verify face image (Multipart or Base64 Form) and log attendance. | None |
| `GET` | `/logs` | Get recent check-in logs. | None |

### Legacy v1 Endpoints (Deprecated)

Mounted under the `/v1` prefix:

- `POST /v1/users`
- `GET /v1/users`
- `POST /v1/users/{user_id}/images`
- `POST /v1/train` (Protected by `X-Admin-Key` header)

## Authentication

Admin endpoints (`/train-now` and `/v1/train`) require the `X-Admin-Key` header to match the `ADMIN_API_KEY` defined in the server's environment:

```bash
curl -X POST "http://localhost:8000/train-now" \
  -H "X-Admin-Key: your-secret-admin-key"
```

## Running Tests

Run the full pytest suite:

```bash
$env:PYTHONPATH="ai_server"
python -m pytest ai_server/tests/ -v
```
