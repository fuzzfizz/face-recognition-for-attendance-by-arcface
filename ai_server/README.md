# Face Recognition AI Server

A high-accuracy AI-powered attendance system using **ArcFace** (via InsightFace) for face recognition. The system consists of a FastAPI backend server with **MySQL-only** persistence and in-memory, local face matching using serialized .pkl embeddings for ultra-fast, zero-network verification.

## Features

- **MySQL-Only Architecture**: All data is persisted in MySQL 8. Images are stored as `LONGBLOB` columns directly in the database. No filesystem paths, no Supabase, no SQLite.
- **URL-Aware Image Processing**: Automatically handles face images from raw byte streams and base64-encoded strings.
- **Admin Auth Guard**: Key administration actions (like triggering training and deleting students) are protected via the `X-Admin-Key` header.
- **Non-blocking Registration**: Registration endpoint stores images as BLOBs in the database and queues them immediately, returning a status to the client without blocking.
- **Scheduled Training**: Automatically processes pending face registration queue items at configurable daily times (e.g., `19:00` or `12:00, 17:00`).
- **Self-Healing Orphaned Embeddings**: On registration and training, the system automatically detects and prunes orphaned face embeddings (students deleted from the database but still present in the `.pkl` embeddings file).
- **Clean Layered Architecture**:
  - **Routers**: API routing and request/response validation.
  - **Services**: Business logic.
  - **Data Access & Models**: SQLAlchemy 2.0 ORM with PyMySQL driver.
  - **Domain modules**: Image processing & face matching (no DB/HTTP dependencies).


## Project Structure

```
ai_server/
├── app/
│   ├── routers/             # API route controllers
│   │   ├── v1/              # Legacy endpoints (deprecated)
│   │   ├── registration.py  # Registration, status, and delete endpoints
│   │   ├── training.py      # Admin training trigger endpoints
│   │   ├── verification.py  # Real-time face verification
│   │   └── logs.py          # Attendance logs retrieval
│   ├── services/            # Business logic
│   │   ├── registration_service.py
│   │   ├── training_service.py
│   │   └── verification_service.py
│   ├── utils/               # Image loading and decoding utility functions
│   │   └── image_utils.py
│   ├── config.py            # Global settings & config (MYSQL_URL, etc.)
│   ├── database.py          # SQLAlchemy MySQL access layer (PyMySQL)
│   ├── face_processor.py    # InsightFace wrapper for embeddings
│   ├── matcher.py           # Dot product Cosine similarity matching
│   ├── models.py            # SQLAlchemy ORM model definitions (LONGBLOB, etc.)
│   ├── schemas.py           # Pydantic request & response validators
│   ├── dependencies.py      # FastAPI dependency injection (admin auth guard)
│   └── main.py              # Application entrypoint & startup lifecycle
├── data/
│   └── face_embeddings.pkl  # Local face embeddings database (serialized pickle)
├── tests/                   # Python test suite (pytest)
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
├── docker-compose.yml       # Docker Compose deployment
└── README.md                # This documentation file
```



## Database Schema (MySQL)

The system uses three tables, all managed by SQLAlchemy's `Base.metadata.create_all()` on startup.

### `users`
| Column | Type | Constraints |
| :--- | :--- | :--- |
| `id` | `INTEGER` | PRIMARY KEY, AUTO_INCREMENT |
| `student_id` | `VARCHAR(20)` | UNIQUE, NOT NULL, INDEXED |
| `name` | `VARCHAR(100)` | NULLABLE |
| `created_at` | `DATETIME` | DEFAULT CURRENT_TIMESTAMP |

### `registration_queue`
| Column | Type | Constraints |
| :--- | :--- | :--- |
| `id` | `INTEGER` | PRIMARY KEY, AUTO_INCREMENT |
| `student_id` | `VARCHAR(20)` | NOT NULL, INDEXED |
| `image_blob` | `LONGBLOB` | NOT NULL |
| `status` | `VARCHAR(20)` | NOT NULL, DEFAULT 'pending' |
| `error_message` | `TEXT` | NULLABLE |
| `created_at` | `DATETIME` | DEFAULT CURRENT_TIMESTAMP |
| `processed_at` | `DATETIME` | NULLABLE |

### `check_in_logs`
| Column | Type | Constraints |
| :--- | :--- | :--- |
| `id` | `INTEGER` | PRIMARY KEY, AUTO_INCREMENT |
| `user_id` | `INTEGER` | FOREIGN KEY -> `users.id` ON DELETE SET NULL |
| `student_id` | `VARCHAR(20)` | NULLABLE |
| `similarity_score` | `FLOAT` | NULLABLE |
| `device_id` | `VARCHAR(50)` | NULLABLE |
| `error_message` | `VARCHAR(255)` | NULLABLE |
| `timestamp` | `DATETIME` | DEFAULT CURRENT_TIMESTAMP |





## Setup & Installation

### 1. Prerequisites

- Python 3.10+
- MySQL 8.0+
- A MySQL database created (e.g., `face_attendance`)

### 2. Create a Virtual Environment and Install Dependencies

```bash
python -m venv venv
# On Windows:
.\venv\Scripts\Activate.ps1
# On macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Environment Variables Configuration

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Define the configuration values:

```ini
# MySQL Database URL (Required)
MYSQL_URL=mysql+pymysql://user:password@localhost:3306/face_attendance

# Admin Auth Key
ADMIN_API_KEY=your-secret-admin-key

# Face Recognition Configuration
SIMILARITY_THRESHOLD=0.45
MODEL_NAME=buffalo_l

# Server Binding
HOST=0.0.0.0
PORT=8000

# Scheduled Training (24-hour format, comma-separated)
TRAINING_SCHEDULE_TIMES=19:00
```

> **Note:** The `MYSQL_URL` must use the `mysql+pymysql://` scheme. Example: `mysql+pymysql://root:my_password@127.0.0.1:3306/face_attendance`

### 4. Run the Server

```bash
python app/main.py
```

The server starts on `http://localhost:8000`. Swagger API docs are available at `http://localhost:8000/docs`.
## API Endpoints

### Core Endpoints

| Method | Endpoint | Description | Auth |
| :--- | :--- | :--- | :--- |
| `POST` | `/register` | Register a student by uploading face images (Multipart Form). Non-blocking. | None |
| `GET` | `/register/status/{student_id}` | Check the registration processing status for a student. | None |
| `DELETE` | `/register/student/{student_id}` | Delete a student's database records, queue items, and embeddings. | `X-Admin-Key` |
| `POST` | `/train-now` | Trigger training for all pending queue items immediately. | `X-Admin-Key` |
| `POST` | `/verify` | Verify a face image (Multipart or Base64) and log attendance. | None |
| `GET` | `/logs` | Retrieve recent check-in logs (`?limit=N`, default 50). | None |
| `GET` | `/` | Health check. Returns server status and database mode. | None |

### Legacy v1 Endpoints (Deprecated)

Mounted under the `/v1` prefix:

- `POST /v1/users`
- `GET /v1/users`
- `POST /v1/users/{user_id}/images`
- `POST /v1/train` (Protected by `X-Admin-Key` header)

## Authentication

Admin endpoints (`/train-now`, `/register/student/{student_id}`, and `/v1/train`) require the `X-Admin-Key` header to match the `ADMIN_API_KEY` defined in the server's environment:

```bash
curl -X DELETE "http://localhost:8000/register/student/S001" -H "X-Admin-Key: your-secret-admin-key"
```

```bash
curl -X POST "http://localhost:8000/train-now" -H "X-Admin-Key: your-secret-admin-key"
```

## Registration Flow

1. **Upload**: `POST /register` with `student_id`, optional `name`, and image `files` (Multipart Form).
2. **Validation**: Each image is validated for face presence and single-face. Face embedding extraction checks for duplicates.
3. **Self-Healing Check**: If the student has no DB record but orphaned embeddings exist in the `.pkl` file, they are pruned automatically.
4. **Quota Check**: Max 10 photos per student (existing embeddings + pending queue items).
5. **Storage**: Images stored as `LONGBLOB` in `registration_queue` with `status = 'pending'`.
6. **Response**: Returns immediately with `{"status": "pending", ...}`.

## Training Flow

Training extracts face embeddings from queued images and saves to `face_embeddings.pkl` for instant matching.

### Manual Training

```bash
curl -X POST "http://localhost:8000/train-now" -H "X-Admin-Key: your-secret-admin-key"
```

### Scheduled Training

The server processes pending queue items at configured daily times. Set `TRAINING_SCHEDULE_TIMES` in `.env`:

```ini
# Single slot -- runs daily at 19:00
TRAINING_SCHEDULE_TIMES=19:00

# Multiple slots
TRAINING_SCHEDULE_TIMES=12:00, 17:00, 22:30
```

The scheduler runs as an `async` background task during the server's lifespan, checking every 20 seconds.

## Self-Healing (Orphaned Embedding Cleanup)

The system automatically prunes orphaned embeddings in these scenarios:

1. **Registration**: If the student being registered has no DB record but embeddings exist in `.pkl`, they are pruned silently.
2. **Duplicate Check**: If a matched embedding belongs to a deleted student, the orphan is pruned.
3. **Training**: Queue items for a deleted student are marked `failed` and any lingering embeddings are pruned from `.pkl`.

## Deleting a Student

`DELETE /register/student/{student_id}` (requires `X-Admin-Key`):

1. Deletes `check_in_logs` entries for the student.
2. Deletes `registration_queue` entries.
3. Deletes the `users` record.
4. Prunes embeddings from `.pkl` and invalidates the cache.

```bash
curl -X DELETE "http://localhost:8000/register/student/S001" -H "X-Admin-Key: your-secret-admin-key"
```

## Verification & Attendance Logging

`POST /verify` accepts a Multipart file upload or a base64-encoded image:

```bash
# With image file
curl -X POST "http://localhost:8000/verify" -F "file=@face.jpg" -F "device_id=ESP32-S3-01"

# With base64
curl -X POST "http://localhost:8000/verify" -d "image_base64=<base64>&device_id=ESP32-S3-01"
```

The flow:
1. **Quality Validation**: Checks for face presence and single face.
2. **Embedding Extraction**: 512-dimensional ArcFace embedding.
3. **Matching**: Cosine similarity against all stored embeddings (dot product of L2-normalized vectors).
4. **Duplicate Check**: If same student checked in within 5 minutes, returns match without duplicate log.
5. **Logging**: All successful matches and failures are logged to `check_in_logs`.

## API Documentation

Full interactive API documentation is auto-generated at **http://localhost:8000/docs** (Swagger UI).

## Running Tests

Run the full pytest suite from the project root:

```bash
$env:PYTHONPATH="ai_server"
python -m pytest ai_server/tests/ -v
```

## Testing & API Usage with Postman

We provide a Postman Collection and Environment file.

### How to Setup:
1. **Import the Collection:**
   - Import [`FaceAttend_AI_Server.postman_collection.json`](./FaceAttend_AI_Server.postman_collection.json) into Postman.
2. **Import the Environment:**
   - Import [`FaceAttend_AI_Server.postman_environment.json`](./FaceAttend_AI_Server.postman_environment.json) into Postman.
3. **Select the Environment:**
   - Choose **"FaceAttend AI Server Environment"** in top-right dropdown.
4. **Configure Variables:**
   - `base_url`: Server address (default `http://localhost:8000`).
   - `admin_key`: Must match `ADMIN_API_KEY` in `.env`.
   - `student_id`: For testing (default `S001`).

## Architecture Overview

```
+----------------+     +----------------+     +----------------+
|   Routers      | --> |   Services     | --> |  Database      |
|  (FastAPI)     |     |  (Business     |     |  (SQLAlchemy   |
|                |     |   Logic)       |     |   + PyMySQL)   |
+----------------+     +--------+-------+     |   --> MySQL    |
                                |             +----------------+
                                v
                       +----------------+
                       |  Domain        |
                       |  +----------+  |
                       |  |Face Proc |  |  InsightFace (ArcFace)
                       |  |Matcher   |  |  .pkl embeddings + cache
                       |  +----------+  |
                       +----------------+
```

- **Routers** (`app/routers/`): HTTP request/response, validation, dependency injection.
- **Services** (`app/services/`): Business logic -- registration, training, verification.
- **Database** (`app/database.py`): SQLAlchemy ORM with PyMySQL for MySQL. CRUD for users, queue, logs.
- **Face Processor** (`app/face_processor.py`): InsightFace `FaceAnalysis` wrapper for face detection, quality checks, and 512-d ArcFace embedding extraction.
- **Matcher** (`app/matcher.py`): Loads `.pkl` embeddings (mtime-based cache), cosine similarity matching against configured threshold.


