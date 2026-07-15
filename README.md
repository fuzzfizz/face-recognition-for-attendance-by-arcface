# Face Recognition Attendance System (FaceAttend)

An end-to-end, high-accuracy, AI-powered attendance system featuring local-edge verification and MySQL-based cloud database persistence. The system bridges a **Flutter registration client**, an **ESP32 hardware camera module**, a **FastAPI AI inference server**, and a **PHP-based web administration dashboard** — all backed by a single **MySQL** database that stores student records, registration images (as `LONGBLOB`), and attendance logs.

---

## System Architecture

```mermaid
graph TD
    subgraph Client Applications
        A[Flutter App: app_face_capture] -->|Register Students / Upload Photos| B[FastAPI AI Server: ai_server]
        D[ESP32 Hardware Module] -->|Sends Live Photo to /verify/face_recognition/{device_id}| B
    end

    subgraph AI Server and In-Memory Matching
        B -->|Read/Write| C[(MySQL Database<br/>database_mysql)]
        B -->|Cache in RAM| E(face_embeddings.pkl)
        B -->|Trigger Training| B
    end

    subgraph Administration
        F[PHP Web Dashboard: web_dashboard] -->|Read/Write via PDO| C
        F -->|Trigger Training via API| B
    end

    subgraph MySQL Data Persistence
        C --> T1[(users)]
        C --> T2[(registration_queue<br/>image_blob LONGBLOB)]
        C --> T3[(check_in_logs)]
    end
```

### How It Works

| Layer | Technology | Role |
| :--- | :--- | :--- |
| **Database** | MySQL (Docker) | Single source of truth — stores student profiles, registration photos as `LONGBLOB` blobs, and all check-in logs. |
| **AI Inference** | FastAPI + InsightFace (ArcFace) | Extracts 512-dim face embeddings, performs cosine-similarity matching, manages the training pipeline and scheduled queue processing. |
| **In-Memory Cache** | `face_embeddings.pkl` (RAM) | All trained embeddings are loaded into memory on server start. Verification runs against this cache for sub-second latency — zero database hits during matching. |
| **Registration Client** | Flutter (cross-platform) | Captures 10 quality-checked face photos per student and uploads them to the AI server. |
| **Admin Dashboard** | PHP 8+ (PDO to MySQL) | Live attendance monitoring, student management, registration queue inspection, and one-click force-training. |
| **Edge Hardware** | ESP32-CAM (Arduino C++) | Captures a face at the entrance and POSTs the image to `/verify/face_recognition/{device_id}` for real-time check-in. |

---

## Project Structure

```
face-recognition-for-attendance-by-arcface/
│
├── ai_server/                          # Python FastAPI AI inference engine
│   ├── app/                            # Application source
│   │   ├── routers/                    #   API route controllers
│   │   │   ├── v1/                     #     Legacy endpoints (deprecated)
│   │   │   ├── registration.py         #     Student registration and queue status
│   │   │   ├── training.py             #     Admin training trigger
│   │   │   ├── verification.py         #     Real-time face verification
│   │   │   └── logs.py                 #     Attendance log retrieval
│   │   ├── services/                   #   Business logic
│   │   │   ├── registration_service.py
│   │   │   ├── training_service.py
│   │   │   └── verification_service.py
│   │   ├── utils/                      #   Image loading and decoding helpers
│   │   ├── config.py                   #   Global settings (MySQL URL, threshold, etc.)
│   │   ├── database.py                 #   SQLAlchemy-based MySQL access layer
│   │   ├── face_processor.py           #   InsightFace wrapper (ArcFace)
│   │   ├── matcher.py                  #   Cosine-similarity matching and .pkl cache
│   │   ├── models.py                   #   SQLAlchemy ORM models
│   │   ├── schemas.py                  #   Pydantic request/response models
│   │   └── main.py                     #   FastAPI app entrypoint and lifecycle
│   ├── data/                           #   Runtime data
│   │   └── face_embeddings.pkl         #     Serialised embedding cache
│   ├── tests/                          #   pytest suite
│   ├── requirements.txt                #   Python dependencies
│   ├── Dockerfile                      #   Container build (production)
│   ├── docker-compose.yml              #   Multi-service orchestration
│   ├── .env.example                    #   Environment template
│   └── README.md                       #   Server-specific documentation
│
├── app_face_capture/                   # Flutter cross-platform registration app
│   ├── lib/
│   │   ├── core/constants/             #   API endpoints, PINs, storage paths
│   │   ├── data/models/                #   Data transfer objects
│   │   ├── data/repositories/          #   Upload routing logic
│   │   ├── data/services/              #   HTTP client
│   │   ├── presentation/viewmodels/    #   State management (Provider)
│   │   ├── presentation/views/         #   Screens (Home, Capture, Upload, Admin)
│   │   ├── presentation/widgets/       #   Reusable UI components
│   │   └── routing/                    #   GoRouter configuration
│   ├── test/                           #   Flutter unit and widget tests
│   ├── pubspec.yaml                    #   Dart dependencies
│   └── README.md                       #   App-specific documentation
│
├── web_dashboard/                      # PHP 8+ admin control panel
│   ├── api/                            #   Server-side API handlers
│   ├── assets/                         #   CSS and JavaScript
│   ├── config.example.php              #   Configuration template
│   ├── index.php                       #   Dashboard entrypoint (SPA)
│   ├── Dockerfile                      #   Container build (Apache + PHP)
│   ├── docker-compose.yml              #   Orchestration
│   ├── DEPLOY.md                       #   Deployment guide
│   └── README.md                       #   Dashboard-specific documentation
│
├── database_mysql/                     # MySQL database provisioning
│   ├── init_schema.sql                 #   Full schema (users, registration_queue, check_in_logs)
│   ├── docker-compose.yml              #   Standalone MySQL container
│   ├── Dockerfile                      #   Custom MySQL image with init script
│   ├── .env.example                    #   Environment template
│   ├── connection_test.py              #   Connectivity validation script
│   ├── setup_vm.sh                     #   Automated VM bootstrap (Ubuntu)
│   └── DEPLOY_GUIDE.md                 #   Split-VM deployment walk-through
│
├── esp32_system/                       # ESP32-CAM hardware firmware (placeholder)
│   └── ...                             #   Arduino C++ source (coming soon)
│
├── docs/                               # Design documents and superpowers specs
├── .gitignore
└── README.md                           # This file
```
---

## Core Flows

### 1. Student Face Registration

```
[Admin] to Flutter App to 3s countdown to 10 photos captured to POST /register to AI Server
                                                                                |
                                                                                v
                                                                       MySQL registration_queue
                                                                       (image_blob LONGBLOB, status='pending')
```

1. The admin enters a student ID (and optional name) in the **Flutter App**.
2. The app displays a **3-second alignment countdown**, then captures **10 photos** sequentially with progress feedback.
3. Photos are sent as `multipart/form-data` to the AI server`s `/register` endpoint.
4. The server runs **face detection** and **single-face quality validation** on each image.
5. Valid images are stored as **`LONGBLOB`** entries in the `registration_queue` table with `status = 'pending'`.
6. The student record is created or updated in the `users` table (via `upsert_user`).

### 2. Model Training

```
Scheduled (cron-like) or Manual (admin trigger) to Process pending queue
                                                      |
                                                      v
                                           For each queue item:
                                             decode BLOB to ArcFace to embedding
                                                      |
                                                      v
                                           Write to data/face_embeddings.pkl
                                           Invalidate RAM cache to reload
                                                      |
                                                      v
                                           Mark queue item status='completed'
```

- **Automated**: The AI server runs an `asyncio` scheduler that checks the queue at configured times (e.g. `12:00, 17:00`) and processes all pending items.
- **Manual**: An admin can trigger immediate training from the **Flutter App** (long-press logo to PIN to "Train Now") or from the **Web Dashboard** ("Force Training Now" button). Both call `POST /train-now` with the `X-Admin-Key` header.
- The trainer fetches each `image_blob` from MySQL, runs it through **ArcFace (InsightFace)** to extract a 512-dimension embedding, and appends it to `data/face_embeddings.pkl`.
- After saving, the in-memory cache is invalidated so the next verification loads the fresh embeddings.

### 3. Face Verification (Check-In)

```
ESP32-CAM to capture to POST /verify/face_recognition/{device_id} to AI Server
                                        |
                           +------------+------------+
                           |                         |
                           v                         v
                    Extract embedding           Compare against
                    (InsightFace)                RAM .pkl cache
                           |                         |
                           +------------+------------+
                                        |
                                 Cosine similarity
                                 > threshold (0.60)?
                                        |
                          +-------------+-------------+
                          |                           |
                          v                           v
                     Match found                 No match
                     Return: student_id           Return: unknown
                          |                           |
                          v                           v
                     Log to MySQL                Log with
                     check_in_logs                error_message
```

1. The **ESP32-CAM module** captures a face at the entrance and sends a POST request with the image payload to the server`s `/verify/face_recognition/{device_id}` endpoint.
2. The server uses **InsightFace** to extract a face embedding from the incoming image.
3. The embedding is compared against all embeddings in the in-memory `.pkl` cache using **cosine similarity**.
4. If the highest similarity score exceeds the configured threshold (`SIMILARITY_THRESHOLD`, default `0.60`), the user is identified, a check-in success response is returned to the ESP32 (to trigger a buzzer or open a door), and an attendance record is inserted into the `check_in_logs` table.
5. If no match exceeds the threshold, a failure is logged with an error message.
---

## Quick Start Guide

### Prerequisites

| Tool | Version (minimum) |
| :--- | :--- |
| Python | 3.10+ |
| Flutter SDK | 3.x (latest stable) |
| PHP | 8.0+ (with `pdo_mysql` extension) |
| Docker and Docker Compose | Latest |
| MySQL client (optional) | Any |

---

### Step 1: Start the MySQL Database

The system uses **MySQL exclusively**. The easiest way to get a database running is via Docker:

```bash
cd database_mysql

# Copy and edit the environment file
cp .env.example .env
# Edit .env to set your passwords

# Start the MySQL container
docker-compose up --build -d
```

This will:
- Pull/build the MySQL image
- Expose port `3306`
- Automatically run `init_schema.sql` to create the `face_attendance` database with three tables:
  - **`users`** — student profiles (`student_id`, `name`, `created_at`)
  - **`registration_queue`** — pending registration photos (`image_blob LONGBLOB`, `status`, `error_message`)
  - **`check_in_logs`** — attendance records (`student_id`, `similarity_score`, `device_id`, `timestamp`)

**Verify the database is running:**

```bash
docker-compose ps
```

### Step 2: Start the AI Server

```bash
cd ai_server

# 1. Create a virtual environment and install dependencies
python -m venv venv
# Windows:
.\venv\Scripts\Activate.ps1
# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt

# 2. Configure the environment
cp .env.example .env
```

Edit `.env` with your MySQL connection details:

```ini
# Exclusive MySQL Configuration
MYSQL_URL=mysql+pymysql://face_admin:SecurePassword123!@localhost:3306/face_attendance

# Admin API Key (used to protect /train-now)
ADMIN_API_KEY=my-secure-admin-token-12345

# Face Recognition
SIMILARITY_THRESHOLD=0.60
MODEL_NAME=buffalo_l

# Scheduled Training
TRAINING_SCHEDULE_TIMES=12:00, 17:00

# Server Binding
HOST=0.0.0.0
PORT=8000
```

**3. Run the server:**

```bash
python app/main.py
```

The server starts on `http://0.0.0.0:8000`. Verify with:

```bash
curl http://localhost:8000/
# Expected: {"status": "ok", "mode": "mysql"}
```

### Step 3: Run the Web Dashboard

```bash
cd web_dashboard

# 1. Copy the config template
cp config.example.php config.php

# 2. Edit config.php with your MySQL and AI server details
#    (DB_HOST, DB_USER, DB_PASS, DB_NAME, AI_SERVER_URL, ADMIN_API_KEY)

# 3. Start the PHP built-in server
php -S localhost:8080
```

Open **http://localhost:8080** in your browser to see:
- Live attendance log (auto-refreshes every 5 seconds)
- Student list and registration status
- Registration queue inspector with status filters
- **"Force Training Now"** button to trigger immediate model training

> **Security**: The `.htaccess` file blocks direct HTTP access to `config.php`. In production, point Apache or Nginx to the `web_dashboard/` directory.

### Step 4: Run the Face Capture App

```bash
cd app_face_capture

flutter pub get
flutter run
```

On first launch:
1. Tap the **gear icon** (Settings) and set the **Server Base URL** to your AI server address (e.g. `http://10.0.2.2:8000` for Android emulator, or `http://<YOUR_IP>:8000` for a physical device).
2. Enter a student ID and optional name, then tap **Capture**.
3. A 3-second countdown appears, followed by automatic capture of 10 photos.
4. Photos are uploaded to the AI server and queued in MySQL for training.

**Admin portal** (hidden): Long-press the app logo on the home screen, enter the PIN (defined in `api_constants.dart`), and you can trigger model training directly from the app.

### Step 5: Deploy the ESP32 Module (Optional)

1. Open the source code inside `esp32_system/` (once available) in Arduino IDE or PlatformIO.
2. Configure your WiFi credentials and the AI server URL: `http://<SERVER_IP>:8000/verify/face_recognition/{device_id}`.
3. Flash the device.

---

## API Endpoints Overview

| Method | Endpoint | Description | Auth |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Health check — returns `{"status": "ok", "mode": "mysql"}` | None |
| `POST` | `/register` | Register student with uploaded face images (multipart) | None |
| `GET` | `/register/status/{student_id}` | Check registration processing status | None |
| `POST` | `/train-now` | Process all pending queue items immediately | `X-Admin-Key` |
| `POST` | `/verify/face_recognition/{device_id}` | Verify a face image and log attendance | None |
| `GET` | `/logs` | Retrieve recent attendance logs (with pagination) | None |
| `DELETE` | `/student/{student_id}` | Delete a student and all associated data | `X-Admin-Key` |

Full API documentation is auto-generated at **http://localhost:8000/docs** (Swagger UI).

---

## Deployment Guide

For production deployment on **Google Cloud Platform** (or any cloud provider), see the detailed guides:

| Guide | Location |
| :--- | :--- |
| **Database VM Deployment** (MySQL Docker) | [`database_mysql/DEPLOY_GUIDE.md`](database_mysql/DEPLOY_GUIDE.md) |
| **AI Server Deployment** (FastAPI) | [`ai_server/DEPLOYMENT_GUIDE.md`](ai_server/DEPLOYMENT_GUIDE.md) |
| **Web Dashboard Deployment** | [`web_dashboard/DEPLOY.md`](web_dashboard/DEPLOY.md) |

The recommended production topology uses **two separate VMs**:

```
+---------------------------+       +-------------------------------+
|   Database VM             |       |   Application VM              |
|   MySQL Docker            |<------+   FastAPI AI Server           |
|   Port 3306               |       |   PHP Web Dashboard           |
|   (internal VPC only)     |       |   Port 8000 and 8080          |
+---------------------------+       +-------------------------------+
                                           |
                                           v
                                    ESP32-CAM / Flutter App
                                    (external clients)
```

---

## Key Design Decisions

| Decision | Rationale |
| :--- | :--- |
| **MySQL-only persistence** | Single, reliable relational database for all data — no cloud dependency, no fallback complexity. Images stored as `LONGBLOB` for portability and simplified backup. |
| **BLOB image storage** | Avoids file-system management and external object storage. Every registration photo lives inside the database transactionally alongside its metadata. |
| **In-memory .pkl embedding cache** | All trained embeddings are loaded into RAM at startup. Verification runs in-process with zero I/O — achieving sub-100ms latency even with thousands of registered students. |
| **Scheduled + manual training** | Queue processing can run on a cron-like schedule (configurable via `TRAINING_SCHEDULE_TIMES`) or be triggered instantly by an admin — balancing automation with control. |
| **Admin API key guard** | Sensitive operations (`/train-now`, `/student/{id}`) require the `X-Admin-Key` header, preventing unauthorised access. |

---

## Tech Stack

| Component | Technology |
| :--- | :--- |
| **Face Recognition Model** | ArcFace (InsightFace `buffalo_l`) |
| **AI Framework** | ONNX Runtime |
| **API Framework** | FastAPI + uvicorn |
| **Database ORM** | SQLAlchemy 2.0 + PyMySQL |
| **Database** | MySQL 8 (Docker container) |
| **Registration Client** | Flutter / Dart (Provider pattern) |
| **Admin Dashboard** | PHP 8+ (PDO) + vanilla JS |
| **Edge Hardware** | ESP32-CAM (OV2640) |
| **Infrastructure** | Docker Compose, GCP Compute Engine |

---

## Testing

### AI Server

```bash
cd ai_server
$env:PYTHONPATH="ai_server"
python -m pytest tests/ -v
```

### Flutter App

```bash
cd app_face_capture
flutter test
```

---

## Related Documentation

- [`ai_server/README.md`](ai_server/README.md) — Detailed server setup, API reference, and Postman usage
- [`app_face_capture/README.md`](app_face_capture/README.md) — Flutter app architecture and configuration
- [`web_dashboard/README.md`](web_dashboard/README.md) — PHP dashboard setup and security notes
- [`database_mysql/DEPLOY_GUIDE.md`](database_mysql/DEPLOY_GUIDE.md) — Full MySQL deployment (single-VM and split-VM)
- [`docs/`](docs/) — Design specs, superpowers plans, and architectural decisions
