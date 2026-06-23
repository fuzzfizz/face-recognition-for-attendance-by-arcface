# Face Recognition Attendance System by ArcFace

A high-accuracy AI-powered attendance system using **ArcFace** (via InsightFace) for face recognition. The system consists of a FastAPI backend server, an ESP32-S3 CAM edge device for real-time face capture, and a companion face capture application for user registration.

## Features

- **Face Recognition with ArcFace**: Uses InsightFace's ArcFace model (buffalo_l) for state-of-the-art face embedding extraction (512-dimensional vectors)
- **Real-time Attendance Verification**: ESP32-S3 CAM captures faces and sends them to the server for instant identification
- **User Management**: Register users with up to 10 face images per person for robust recognition
- **Training Pipeline**: Batch-process all registered images to generate optimized `.pkl` embedding files
- **Attendance Logging**: Automatically logs all check-in events with timestamps, similarity scores, and device IDs
- **Cosine Similarity Matching**: L2-normalized embeddings enable fast and accurate face comparison
- **REST API**: Clean FastAPI endpoints for easy integration with web, mobile, or IoT clients

## System Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  app_face_capture│         │   ai_server       │         │  ESP32-S3 CAM   │
│  (Registration)  │────────▶│   (FastAPI)       │◀────────│  (Attendance)   │
│                  │  Upload │                   │  Verify │                 │
│  Capture 10      │  Images │  • Face Alignment  │  Image  │  OV5640 Camera   │
│  photos per user │         │  • ArcFace Extract │         │  Real-time Scan  │
└─────────────────┘         │  • .pkl Training   │         └─────────────────┘
                             │  • Cosine Match    │
                             │  • SQLite/MySQL DB │
                             └──────────────────┘
```

## Project Structure

```
ai_server/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application & REST endpoints
│   ├── config.py            # Configuration (DB, model, thresholds)
│   ├── database.py          # SQLAlchemy ORM models (User, UserImage, CheckInLog)
│   ├── face_processor.py    # InsightFace wrapper (detect, align, embed)
│   ├── matcher.py           # Cosine similarity search against .pkl
│   └── trainer.py           # Batch training: DB images → face_embeddings.pkl
├── data/
│   └── face_embeddings.pkl  # Serialized face embeddings (generated after training)
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Technology Stack

| Component         | Technology                               |
| ----------------- | ---------------------------------------- |
| Backend Framework | FastAPI + Uvicorn                        |
| Face Recognition  | InsightFace (ArcFace / buffalo_l model)  |
| Embedding Storage | Pickle (.pkl)                            |
| Database          | SQLAlchemy (SQLite / MySQL / PostgreSQL) |
| Image Processing  | OpenCV, NumPy                            |
| Edge Device       | ESP32-S3 CAM (OV5640 5MP)                |

## Prerequisites

- Python 3.8+
- pip package manager
- (Windows only) Visual Studio Community with **Desktop development with C++** workload — required to compile InsightFace's C++ extensions

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd AIproject/ai_server
```

### 2. Create & Activate Virtual Environment

```bash
# Create venv
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate (Windows Command Prompt)
.\venv\Scripts\activate.bat

# Activate (macOS / Linux)
source venv/bin/activate
```

### 3. Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> **Note for Windows users**: If `pip install insightface` fails, download a pre-built wheel (.whl) matching your Python version from [InsightFace releases](https://github.com/deepinsight/insightface/releases) and install it with:
>
> ```bash
> pip install <path_to_insightface_wheel>.whl
> ```

### 4. First-Run Model Download

On the first run, InsightFace will automatically download the `buffalo_l` model into `~/.insightface/models/`. This is a one-time download (~20 MB).

## Quick Start

### Start the Server

```bash
# With auto-reload for development
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Or run directly
python app/main.py
```

The API will be available at `http://localhost:8000`.

### Interactive API Docs

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                  | Description                                                            |
| ------ | ------------------------- | ---------------------------------------------------------------------- |
| `GET`  | `/`                       | Health check                                                           |
| `POST` | `/users`                  | Create a new user                                                      |
| `GET`  | `/users`                  | List all registered users                                              |
| `POST` | `/users/{user_id}/images` | Upload face image(s) for a user (multipart or base64)                  |
| `POST` | `/train`                  | Trigger training: extract embeddings from all user images → `.pkl`     |
| `POST` | `/verify`                 | Verify a face (upload image or base64) → returns user match or unknown |
| `GET`  | `/logs`                   | Retrieve recent attendance check-in logs                               |

### Example: Create User & Upload Image

```bash
# 1. Create user
curl -X POST "http://localhost:8000/users" \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe"}'

# 2. Upload image (multipart)
curl -X POST "http://localhost:8000/users/1/images" \
  -F "file=@/path/to/photo.jpg"

# 3. Train the system
curl -X POST "http://localhost:8000/train"

# 4. Verify a face
curl -X POST "http://localhost:8000/verify" \
  -F "file=@/path/to/verify.jpg"
```

### Example: Verify with Base64

```bash
curl -X POST "http://localhost:8000/verify" \
  -F "image_base64=data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ..."
```

## Configuration

Edit `app/config.py` or set environment variables:

| Variable               | Default                           | Description                                        |
| ---------------------- | --------------------------------- | -------------------------------------------------- |
| `DATABASE_URL`         | `sqlite:///./face_recognition.db` | Database connection string                         |
| `SIMILARITY_THRESHOLD` | `0.60`                            | Cosine similarity threshold for matching (0.0–1.0) |
| `MODEL_NAME`           | `buffalo_l`                       | InsightFace model name                             |
| `HOST`                 | `0.0.0.0`                         | Server bind host                                   |
| `PORT`                 | `8000`                            | Server bind port                                   |

### Using MySQL / PostgreSQL

```bash
# MySQL example
export DATABASE_URL="mysql+pymysql://user:password@localhost/face_attendance"

# PostgreSQL example
export DATABASE_URL="postgresql://user:password@localhost/face_attendance"
```

## How It Works

### Training Phase

1. Users are registered via `/users` and their face images are uploaded via `/users/{id}/images`.
2. Calling `/train` triggers the trainer:
   - Fetches all users and their images from the database.
   - Runs **Face Alignment** (landmark-based rotation/scaling) on each image.
   - Extracts a **512-d ArcFace embedding** from the primary (largest) face.
   - Saves all embeddings into `data/face_embeddings.pkl` grouped by user.

### Inference / Verification Phase

1. ESP32-S3 CAM (or any client) sends a photo to `/verify`.
2. The server runs face detection, alignment, and ArcFace embedding extraction.
3. The query embedding is compared against every stored embedding using **Cosine Similarity** (dot product of L2-normalized vectors).
4. If the highest similarity ≥ `SIMILARITY_THRESHOLD`, the user is identified; otherwise marked as unknown.
5. The result (user ID, name, similarity score) is returned and a check-in log is persisted.

## Attendance Log Schema

Each check-in log entry contains:

- `id` — Log entry ID
- `user_id` — Matched user ID (nullable for unknown faces)
- `name` — User name or `"Unknown"`
- `similarity_score` — Cosine similarity of the best match
- `device_id` — ESP32 device identifier
- `timestamp` — UTC time of check-in

## Testing

```bash
# Run the test suite
pytest ai_server/tests/ -v
```

## Troubleshooting

| Issue                                  | Solution                                                                                          |
| -------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `insightface` install fails on Windows | Install Visual Studio C++ build tools, or use a pre-built `.whl`                                  |
| Model download hangs                   | Ensure internet connectivity; model is cached in `~/.insightface/models/`                         |
| Low recognition accuracy               | Increase training images (up to 10 per user), ensure good lighting, adjust `SIMILARITY_THRESHOLD` |
| Database locked (SQLite)               | Use MySQL/PostgreSQL for concurrent access, or ensure single-process usage                        |

## License

MIT

## Contributing

Contributions are welcome. Please open an issue or pull request.
