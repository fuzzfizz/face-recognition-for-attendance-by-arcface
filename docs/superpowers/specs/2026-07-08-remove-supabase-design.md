# Design Specification: Supabase Removal and Direct MySQL Integration

**Author:** Antigravity  
**Date:** 2026-07-08  
**Status:** Draft for Review  
**Target Spec File:** [2026-07-08-remove-supabase-design.md](file:///D:/AIproject/docs/superpowers/specs/2026-07-08-remove-supabase-design.md)

---

## 1. Executive Summary & Goals

This specification outlines the strategy, architecture, and step-by-step plan to decommission Supabase (PostgreSQL database + Cloud Storage) from the monorepo. It replaces the hybrid storage architecture with direct MySQL connectivity, leveraging SQLite for local development and testing.

### Key Objectives
* **Consolidation**: Standardize on a single operational database backend (MySQL) for production deployments, retaining SQLite as an offline/testing fallback.
* **Simplification**: Remove unused cloud integrations (Supabase Client, Supabase Storage, and associated environment variables) from all services.
* **REST-Only Flow**: Transition the Flutter app ([app_face_capture](file:///D:/AIproject/app_face_capture)) to register students and upload photos *exclusively* via the AI Server REST endpoints, removing the direct-to-cloud path.
* **Direct Database Queries**: Rewrite the PHP Web Dashboard ([web_dashboard](file:///D:/AIproject/web_dashboard)) to connect directly to the MySQL database container via PHP PDO using host-level environment credentials.

---

## 2. Core System Architecture

### 2.1 Target Architecture Diagram

```mermaid
graph TD
    subgraph "Client Devices"
        FlutterApp["Flutter App (app_face_capture)"]
        ESP32["ESP32 Verification Unit"]
    end

    subgraph "Application VM"
        FastAPI["FastAPI AI Server (ai_server)"]
        LocalPKL["Local Embeddings File (face_embeddings.pkl)"]
        SQLiteDB["Local SQLite DB (fallback/dev)"]
    end

    subgraph "Database VM"
        MySQLContainer["MySQL DB (face_attendance)"]
    end

    subgraph "Web Dashboard VM"
        PHPDashboard["PHP Web Dashboard (web_dashboard)"]
    end

    %% Client communication
    FlutterApp -->|REST API: Register & Status| FastAPI
    ESP32 -->|REST API: Verify & Logs| FastAPI
    PHPDashboard -->|REST API: Trigger Train| FastAPI

    %% Backend integrations
    FastAPI -->|SQLAlchemy ORM| MySQLContainer
    FastAPI -.->|SQLAlchemy ORM (fallback)| SQLiteDB
    FastAPI -->|Local Read/Write| LocalPKL

    %% Dashboard Direct Database Querying
    PHPDashboard -->|PHP PDO| MySQLContainer
```

### 2.2 Refactored Data Flow
1. **Student Registration**: The Flutter App captures 10 photos of a student. It sends the student ID, name, and image files in batches (max 3 images per batch) to the AI Server via `POST /register`.
2. **AI Server Processing**: 
   * The AI Server receives the images and stores them in the database.
   * Under MySQL mode, the images are stored as `LONGBLOB` in the `registration_queue` table.
   * Under SQLite mode, images are written to a local directory (`data/uploads`) and the path is recorded.
   * A queue entry is marked `pending`.
3. **Training & Inference**:
   * The backend scheduled task or a manual `/train-now` call processes the pending queue.
   * The face processor extracts a 512-dimensional embedding using ArcFace.
   * Embeddings are stored in the local `face_embeddings.pkl` file for zero-network matching latency.
   * The queue status updates to `completed`.
4. **Attendance Verification**:
   * The ESP32 device captures a photo and hits `POST /verify`.
   * The AI Server matches the face against loaded pickle embeddings.
   * The match log is persisted in the `check_in_logs` table (MySQL or SQLite fallback).
5. **Dashboard Rendering**:
   * The PHP Dashboard queries the MySQL database directly using PDO to retrieve stats, students, and check-in history.

---

## 3. Refactoring Strategy by Module

### 3.1 AI Server
The goal is to strip the Supabase Python SDK client completely, remove dual-mode configuration properties, and streamline the database adapter.

#### 3.1.1 Files to Delete
* **Client Implementation**: Delete [app/supabase_client.py](file:///D:/AIproject/ai_server/app/supabase_client.py)
* **Unit Tests**: Delete [tests/test_supabase_client.py](file:///D:/AIproject/ai_server/tests/test_supabase_client.py)

#### 3.1.2 Code Cleanups

##### [app/config.py](file:///D:/AIproject/ai_server/app/config.py)
* Remove Supabase configuration constants:
  ```python
  # Delete these lines:
  SUPABASE_URL = os.getenv("SUPABASE_URL", "")
  SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
  SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "face-images")
  ```
* Ensure `DB_MODE` supports only `"mysql"` and `"sqlite"`.

##### [app/database.py](file:///D:/AIproject/ai_server/app/database.py)
* Remove imports from `app.supabase_client`.
* Remove the `using_supabase()` helper function and replace all conditional checks (`if using_supabase():`) with their corresponding SQL database/SQLAlchemy paths.
* Simplify `get_db()` to return the standard SQLAlchemy session:
  ```python
  def get_db():
      return _get_sqlite_session()
  ```
* Simplify `init_db()` to always run `_init_sql_db()`.
* Rewrite `delete_student_from_db` to only run the SQLAlchemy transaction path (dropping cascade records for `users`, `registration_queue`, and `check_in_logs`).

##### [app/main.py](file:///D:/AIproject/ai_server/app/main.py)
* Update the health-check endpoint `/` to return the actual SQL database mode:
  ```python
  @app.get("/", tags=["health"])
  def health():
      from app.config import DB_MODE
      return {"status": "ok", "mode": DB_MODE}
  ```

##### [tests/test_database.py](file:///D:/AIproject/ai_server/tests/test_database.py)
* Remove any patches targeting `supabase_available` or `using_supabase`.
* Focus tests purely on SQLite (for dev validation) and MySQL integration.

##### Environment Variables (`.env.example`, `.env`)
* Remove:
  ```ini
  SUPABASE_URL=https://your-project.supabase.co
  SUPABASE_KEY=your-anon-or-service-role-key
  SUPABASE_STORAGE_BUCKET=face-images
  ```

---

### 3.2 Web Dashboard
The dashboard will switch from hitting the Supabase REST API via cURL to querying the MySQL database directly via PHP Data Objects (PDO).

#### 3.2.1 Configuration: [config.php](file:///D:/AIproject/web_dashboard/config.php)
Replace Supabase constants with MySQL host, database, username, and password constants:

```php
<?php
// Copy this template to config.php
define('MYSQL_HOST', '127.0.0.1'); // Database VM IP
define('MYSQL_DB', 'face_attendance');
define('MYSQL_USER', 'face_admin');
define('MYSQL_PASS', 'SecurePassword123!');

define('AI_SERVER_URL', 'http://localhost:8000'); // FastAPI URL
define('ADMIN_API_KEY', 'my-secure-admin-token-12345');

// Database Connection Helper
function get_db_connection(): PDO {
    static $pdo = null;
    if ($pdo === null) {
        $dsn = "mysql:host=" . MYSQL_HOST . ";dbname=" . MYSQL_DB . ";charset=utf8mb4";
        $options = [
            PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES   => false,
        ];
        try {
            $pdo = new PDO($dsn, MYSQL_USER, MYSQL_PASS, $options);
        } catch (PDOException $e) {
            http_response_code(503);
            echo json_encode(['error' => 'Database connection failed: ' . $e->getMessage()]);
            exit;
        }
    }
    return $pdo;
}
```

#### 3.2.2 Rewrite API Endpoints

##### 1. [api/attendance.php](file:///D:/AIproject/web_dashboard/api/attendance.php)
* **Goal**: Query check-ins with pagination and date filters, performing a SQL `LEFT JOIN` on `users` to fetch the student's name in one query instead of hitting two separate endpoints.
* **SQL Query**:
  ```sql
  SELECT l.id, l.student_id, l.similarity_score, l.device_id, l.timestamp, u.name
  FROM check_in_logs l
  LEFT JOIN users u ON l.student_id = u.student_id
  WHERE l.timestamp >= :dayStart AND l.timestamp <= :dayEnd AND l.student_id IS NOT NULL
  [AND l.device_id = :device_id]
  ORDER BY l.timestamp DESC
  LIMIT :limit OFFSET :offset
  ```
* **Count Query**:
  ```sql
  SELECT COUNT(*) 
  FROM check_in_logs 
  WHERE timestamp >= :dayStart AND timestamp <= :dayEnd AND student_id IS NOT NULL
  [AND device_id = :device_id]
  ```

##### 2. [api/queue.php](file:///D:/AIproject/web_dashboard/api/queue.php)
* **Goal**: Retrieve the registration queue history from `registration_queue`.
* **SQL Query**:
  ```sql
  SELECT id, student_id, image_path, status, created_at, processed_at, error_message
  FROM registration_queue
  [WHERE status = :status]
  ORDER BY created_at DESC
  ```

##### 3. [api/stats.php](file:///D:/AIproject/web_dashboard/api/stats.php)
* **Goal**: Fetch summary metrics.
* **SQL Queries**:
  * Total students count: `SELECT COUNT(*) FROM users`
  * Pending queue count: `SELECT COUNT(*) FROM registration_queue WHERE status = 'pending'`
  * Today's check-ins: `SELECT COUNT(*) FROM check_in_logs WHERE timestamp >= :todayStart AND timestamp <= :todayEnd AND student_id IS NOT NULL`
  * Latest check-in: `SELECT student_id, timestamp FROM check_in_logs WHERE student_id IS NOT NULL ORDER BY timestamp DESC LIMIT 1`

##### 4. [api/students.php](file:///D:/AIproject/web_dashboard/api/students.php)
* **Goal**: Retrieve all users and their latest queue status.
* **SQL Query**:
  Query users joined with their most recent registration queue entry:
  ```sql
  SELECT u.student_id, u.name, u.created_at, q.status AS queue_status
  FROM users u
  LEFT JOIN (
      SELECT q1.student_id, q1.status
      FROM registration_queue q1
      INNER JOIN (
          SELECT student_id, MAX(created_at) as max_created
          FROM registration_queue
          GROUP BY student_id
      ) q2 ON q1.student_id = q2.student_id AND q1.created_at = q2.max_created
  ) q ON u.student_id = q.student_id
  ORDER BY u.created_at DESC
  ```

---

### 3.3 Flutter App (app_face_capture)
The Flutter application must be stripped of `supabase_flutter` and modified to ensure the `UploadMethod.viaServer` route is the only functional path.

#### 3.3.1 Clean Dependencies: [pubspec.yaml](file:///D:/AIproject/app_face_capture/pubspec.yaml)
Remove:
```yaml
dependencies:
  supabase_flutter: ^2.0.0
```
Run `flutter pub get` to clean references in `pubspec.lock`.

#### 3.3.2 File Removals
* **Storage client**: Delete [lib/data/services/supabase_storage_service.dart](file:///D:/AIproject/app_face_capture/lib/data/services/supabase_storage_service.dart)

#### 3.3.3 Modify Constants
* **[api_constants.dart](file:///D:/AIproject/app_face_capture/lib/core/constants/api_constants.dart)**: Delete `supabaseUrl` and `supabaseAnonKey`.
* **[storage_constants.dart](file:///D:/AIproject/app_face_capture/lib/core/constants/storage_constants.dart)**: Remove `enum UploadMethod { viaServer, directSupabase }` or deprecate it entirely. We will remove it and refactor references to default to server uploads.

#### 3.3.4 Refactor Repositories and ViewModels
* **[face_repository.dart](file:///D:/AIproject/app_face_capture/lib/data/repositories/face_repository.dart)**:
  * Remove `SupabaseStorageService` imports and dependency injection from the constructor.
  * In `uploadPhotos`, strip out the `if (method == UploadMethod.directSupabase)` check. Batch images and forward them exclusively using `_apiService.register`.
  * Simplify `checkStatus` to query the AI Server API directly.
* **[settings_viewmodel.dart](file:///D:/AIproject/app_face_capture/lib/presentation/viewmodels/settings_viewmodel.dart)**:
  * Remove `uploadMethod` state and references to `SharedPreferences` setting `upload_method`.
* **[upload_viewmodel.dart](file:///D:/AIproject/app_face_capture/lib/presentation/viewmodels/upload_viewmodel.dart)**:
  * Remove the `UploadMethod method` property from the constructor. Update the repository calls to not pass `method`.

#### 3.3.5 UI Simplifications
* **[settings_screen.dart](file:///D:/AIproject/app_face_capture/lib/presentation/views/settings_screen.dart)**:
  * Remove the entire Card element containing the "Upload Method" radio buttons (`RadioListTile<UploadMethod>`).
  * Only keep the "Backend Server URL" input and connection testing utilities.
* **[upload_screen.dart](file:///D:/AIproject/app_face_capture/lib/presentation/views/upload_screen.dart)**:
  * Remove `_buildMethodBadge` and references to `viewModel.method` from the status layout.

---

## 4. Architectural Findings & Database Schema Alignment

> [!WARNING]
> **Database Schema Discrepancy Found**
> 
> During structural analysis of [init_schema.sql](file:///D:/AIproject/database_mysql/init_schema.sql) (MySQL setup script) versus [models.py](file:///D:/AIproject/ai_server/app/models.py) (SQLAlchemy Model Definition), a discrepancy was found:
> 
> * `ai_server/app/database.py` expects the `registration_queue` table to contain an `image_path` column. In MySQL mode, if the path prefix matches `db://registration_queue/{id}`, it updates this column.
> * However, [database_mysql/init_schema.sql](file:///D:/AIproject/database_mysql/init_schema.sql) **does not define** the `image_path` column (it only has `image_blob`).
> 
> If the MySQL database is initialized via the SQL script and queried by SQLAlchemy, it will throw an `Unknown column 'registration_queue.image_path'` SQL syntax error.

### Solution
Update [database_mysql/init_schema.sql](file:///D:/AIproject/database_mysql/init_schema.sql) to align with SQLAlchemy models:
```sql
CREATE TABLE IF NOT EXISTS registration_queue (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(50) NOT NULL,
    image_path VARCHAR(255) NULL, -- Added to align schemas
    image_blob LONGBLOB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP NULL,
    INDEX idx_registration_queue_student_id (student_id),
    INDEX idx_registration_queue_status (status)
);
```

---

## 5. Phased Implementation Sequence

To ensure codebase integrity during the refactoring process, the following sequence is recommended:

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Update MySQL Database Schema                       │
│ (Add image_path in init_schema.sql)                         │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Refactor AI Server                                 │
│ (Remove supabase_client, tests, clean database.py, config.py)│
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: Rewrite Web Dashboard                              │
│ (Update config.php and api/*.php to use PHP PDO + MySQL)    │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 4: Flutter App Refactoring                            │
│ (Remove supabase dependencies, storage service, clean UI)   │
└─────────────────────────────────────────────────────────────┘
```

### Verification Checklist
- [ ] Run AI Server unit tests using `pytest` inside virtual environment (ensure `test_database.py` passes completely).
- [ ] Spin up the Docker database container inside `database_mysql` using `docker-compose up --build -d` and check table structures.
- [ ] Run the database connection tests in `database_mysql/connection_test.py`.
- [ ] Start the FastAPI server in `DB_MODE=mysql` and call the health check endpoint `/` to confirm it returns `{"status": "ok", "mode": "mysql"}`.
- [ ] Test student registrations from the Swagger UI (`/docs`) and verify blobs are correctly populated in MySQL.
- [ ] Run the PHP web server locally (`php -S localhost:8080` in `web_dashboard/`) and load stats, students, and queue histories to verify database PDO querying works.
- [ ] Rebuild and run the Flutter app to ensure it compiles and registers students successfully via the backend API.
