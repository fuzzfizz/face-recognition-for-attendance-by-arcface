# Remove Supabase and Integrate MySQL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decommission Supabase completely and establish direct MySQL connection across the AI server, Flutter app, and PHP web dashboard.

**Architecture:** We will strip the supabase client and dual-mode code paths from the AI Server, rewrite the PHP Web Dashboard to execute queries directly via PDO to the MySQL database, and remove direct-to-Supabase uploads in the Flutter App in favor of the FastAPI REST API.

**Tech Stack:** FastAPI, SQLAlchemy, PyMySQL, Flutter/Dart, PHP (PDO), MySQL.

## Global Constraints

* Decommission all Supabase references.
* Standardize on MySQL as the production database backend.
* Use REST API exclusively for Flutter app registrations.
* Use PHP PDO in the web dashboard APIs.

---

### Task 1: Update MySQL Database Schema

**Files:**
- Modify: [database_mysql/init_schema.sql](file:///D:/AIproject/database_mysql/init_schema.sql)

**Interfaces:**
- Consumes: None
- Produces: The modified database schema in MySQL containing `image_path` column and nullable `image_blob` column in `registration_queue`.

- [ ] **Step 1: Modify MySQL database schema**
  Update [init_schema.sql](file:///D:/AIproject/database_mysql/init_schema.sql#L15-L25) to add `image_path` column and change `image_blob` to be nullable (`NULL`).

  ```sql
  -- 2. Create 'registration_queue' table (stores pending registration photos)
  CREATE TABLE IF NOT EXISTS registration_queue (
      id INT AUTO_INCREMENT PRIMARY KEY,
      student_id VARCHAR(50) NOT NULL,
      image_path VARCHAR(255) NULL,
      image_blob LONGBLOB NULL,
      status VARCHAR(20) NOT NULL DEFAULT 'pending',
      error_message TEXT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      processed_at TIMESTAMP NULL,
      INDEX idx_registration_queue_student_id (student_id),
      INDEX idx_registration_queue_status (status)
  );
  ```

- [ ] **Step 2: Restart Docker container and verify database schema updates**
  Apply the schema changes to the running database instance:
  ```powershell
  cd D:/AIproject/database_mysql
  docker-compose down -v
  docker-compose up -d --build
  ```

- [ ] **Step 3: Verify schema using MySQL CLI**
  Run the describe command on the table inside the container:
  ```powershell
  docker exec -i face-recognition-ai-database mysql -u root -pSecurePassword123! -e "DESCRIBE face_attendance.registration_queue;"
  ```
  Ensure `image_path` column exists as `varchar(255)` and `image_blob` is marked as `YES` under the `Null` column.

- [ ] **Step 4: Commit schema changes**
  ```powershell
  git add database_mysql/init_schema.sql
  git commit -m "db: add image_path column and make image_blob nullable in registration_queue"
  ```

---

### Task 2: Refactor FastAPI AI Server

**Files:**
- Delete: [ai_server/app/supabase_client.py](file:///D:/AIproject/ai_server/app/supabase_client.py)
- Delete: [ai_server/tests/test_supabase_client.py](file:///D:/AIproject/ai_server/tests/test_supabase_client.py)
- Modify: [ai_server/app/config.py](file:///D:/AIproject/ai_server/app/config.py)
- Modify: [ai_server/app/database.py](file:///D:/AIproject/ai_server/app/database.py)
- Modify: [ai_server/app/main.py](file:///D:/AIproject/ai_server/app/main.py)
- Modify: [ai_server/requirements.txt](file:///D:/AIproject/ai_server/requirements.txt)
- Modify: [ai_server/tests/test_database.py](file:///D:/AIproject/ai_server/tests/test_database.py)
- Modify: [ai_server/tests/conftest.py](file:///D:/AIproject/ai_server/tests/conftest.py)

**Interfaces:**
- Consumes: Database schema from Task 1.
- Produces: A pure SQL/SQLAlchemy database connection layer supporting MySQL (and local SQLite fallback for tests) with zero Supabase library integration.

- [ ] **Step 1: Delete Supabase client and tests**
  Remove [supabase_client.py](file:///D:/AIproject/ai_server/app/supabase_client.py) and [test_supabase_client.py](file:///D:/AIproject/ai_server/tests/test_supabase_client.py) files:
  ```powershell
  Remove-Item D:/AIproject/ai_server/app/supabase_client.py -Force
  Remove-Item D:/AIproject/ai_server/tests/test_supabase_client.py -Force
  ```

- [ ] **Step 2: Clean Python requirements**
  Remove `supabase==2.31.0` from [requirements.txt](file:///D:/AIproject/ai_server/requirements.txt).
  ```text
  fastapi==0.110.0
  uvicorn==0.28.0
  insightface==0.7.3
  onnxruntime==1.17.1
  opencv-python-headless==4.9.0.80
  numpy==1.26.4
  sqlalchemy==2.0.28
  pillow==10.2.0
  python-multipart==0.0.9
  pytest==8.1.1
  httpx==0.27.0
  requests>=2.31.0
  pymysql
  cryptography
  ```

- [ ] **Step 3: Modify app configuration**
  Remove Supabase properties from [config.py](file:///D:/AIproject/ai_server/app/config.py#L22-L28).
  ```python
  import os
  from pathlib import Path

  # Paths
  BASE_DIR = Path(__file__).resolve().parent.parent
  DATA_DIR = BASE_DIR / "data"
  DATA_DIR.mkdir(parents=True, exist_ok=True)

  EMBEDDINGS_PATH = DATA_DIR / "face_embeddings.pkl"

  # Fallback to SQLite for completely offline dev (optional)
  # If no MySQL config is provided, the app falls back to SQLite
  DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./face_recognition.db")

  # Database Mode Configuration
  # Defaults to "mysql" in production, or fallback to SQLite.
  DB_MODE = os.getenv("DB_MODE", "mysql")

  # Dedicated MYSQL_URL, fallback to DATABASE_URL
  MYSQL_URL = os.getenv("MYSQL_URL") or os.getenv("DATABASE_URL", "")

  # Face Recognition Configuration
  SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.45"))
  MODEL_NAME = os.getenv("MODEL_NAME", "buffalo_l")

  TRAINING_SCHEDULE_INFO = os.getenv("TRAINING_SCHEDULE_INFO", "daily at 19:00")
  TRAINING_SCHEDULE_TIMES = os.getenv("TRAINING_SCHEDULE_TIMES", "19:00")

  # Server Configuration
  HOST = os.getenv("HOST", "0.0.0.0")
  PORT = int(os.getenv("PORT", "8000"))
  ```

- [ ] **Step 4: Refactor database client code**
  Rewrite [database.py](file:///D:/AIproject/ai_server/app/database.py) to remove the dual-mode Supabase code paths and use direct SQL connection exclusively.
  ```python
  """
  Database layer supporting SQLAlchemy:
  1. MySQL (production)
  2. SQLite (offline development/testing)
  """
  import datetime
  import os
  from typing import Optional, List, Dict, Any

  from app.config import DATABASE_URL, DB_MODE, MYSQL_URL
  from app.matcher import load_embeddings, save_embeddings, match_face
  from app.models import Base, User, RegistrationQueue, CheckInLog

  _sqlite_engine = None
  _SessionLocal = None
  _IMAGES_DIR = None

  _UserModel = User
  _QueueModel = RegistrationQueue
  _LogModel = CheckInLog

  def _init_sql_db():
      """Lazy-init SQLAlchemy engine and session factory, then create all tables."""
      global _sqlite_engine, _SessionLocal, _IMAGES_DIR

      if _sqlite_engine is not None:
          return

      from sqlalchemy import create_engine, text
      from sqlalchemy.orm import sessionmaker
      from pathlib import Path

      BASE_DIR = Path(__file__).resolve().parent.parent
      DATA_DIR = BASE_DIR / "data"
      DATA_DIR.mkdir(parents=True, exist_ok=True)
      _IMAGES_DIR = DATA_DIR / "uploads"
      _IMAGES_DIR.mkdir(parents=True, exist_ok=True)

      url = MYSQL_URL if DB_MODE == "mysql" else DATABASE_URL
      if not url:
          url = DATABASE_URL

      connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
      _sqlite_engine = create_engine(url, connect_args=connect_args)

      if url.startswith("sqlite"):
          from sqlalchemy import event
          @event.listens_for(_sqlite_engine, "connect")
          def set_sqlite_pragma(dbapi_connection, connection_record):
              cursor = dbapi_connection.cursor()
              cursor.execute("PRAGMA foreign_keys=ON")
              cursor.close()

      _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_sqlite_engine)
      Base.metadata.create_all(bind=_sqlite_engine)

      # Migrations for local SQLite offline DB
      if url.startswith("sqlite"):
          with _sqlite_engine.begin() as conn:
              res = conn.execute(text("PRAGMA table_info(check_in_logs);")).fetchall()
              cols = [col[1] for col in res]
              if "error_message" not in cols:
                  conn.execute(text("ALTER TABLE check_in_logs ADD COLUMN error_message VARCHAR;"))
              
              q_res = conn.execute(text("PRAGMA table_info(registration_queue);")).fetchall()
              q_cols = [col[1] for col in q_res]
              if "error_message" not in q_cols:
                  conn.execute(text("ALTER TABLE registration_queue ADD COLUMN error_message VARCHAR;"))
              if "image_blob" not in q_cols:
                  conn.execute(text("ALTER TABLE registration_queue ADD COLUMN image_blob BLOB;"))
              if "image_path" not in q_cols:
                  conn.execute(text("ALTER TABLE registration_queue ADD COLUMN image_path VARCHAR;"))

  def init_db():
      _init_sql_db()

  def _get_sqlite_session():
      _init_sql_db()
      db = _SessionLocal()
      try:
          yield db
      finally:
          db.close()

  def get_db():
      return _get_sqlite_session()

  def upsert_user(student_id: str, name: str = None):
      _init_sql_db()
      session = next(_get_sqlite_session())
      try:
          user = session.query(_UserModel).filter(_UserModel.student_id == student_id).first()
          if not user:
              user = _UserModel(student_id=student_id, name=name)
              session.add(user)
              session.commit()
              session.refresh(user)
          elif name:
              user.name = name
              session.commit()
              session.refresh(user)
          return {"id": user.id, "student_id": user.student_id, "name": user.name}
      finally:
          session.close()

  def get_user_by_student_id(student_id: str):
      _init_sql_db()
      session = next(_get_sqlite_session())
      try:
          user = session.query(_UserModel).filter(_UserModel.student_id == student_id).first()
          return {"id": user.id, "student_id": user.student_id} if user else None
      finally:
          session.close()

  def insert_log(
      student_id: Optional[str],
      similarity_score: float,
      device_id: str,
      user_id: Optional[int] = None,
      error_message: Optional[str] = None
  ):
      _init_sql_db()
      session = next(_get_sqlite_session())
      try:
          actual_user_id = None
          if student_id:
              user = session.query(_UserModel).filter(_UserModel.student_id == student_id).first()
              if user:
                  actual_user_id = user.id

          log = _LogModel(
              user_id=actual_user_id,
              student_id=student_id,
              similarity_score=similarity_score,
              device_id=device_id,
              error_message=error_message,
          )
          session.add(log)
          session.commit()
          return True
      except Exception as e:
          print(f"[SQL] insert_log error: {e}")
          return False
      finally:
          session.close()

  def get_logs(limit=50):
      _init_sql_db()
      session = next(_get_sqlite_session())
      try:
          logs = session.query(_LogModel).order_by(_LogModel.timestamp.desc()).limit(limit).all()
          return [
              {
                  "id": log.id,
                  "student_id": log.student_id if log.student_id else "Unknown",
                  "similarity_score": log.similarity_score,
                  "device_id": log.device_id,
                  "timestamp": log.timestamp,
                  "error_message": log.error_message,
              }
              for log in logs
          ]
      finally:
          session.close()

  def get_latest_check_in_log(student_id: str) -> Optional[dict]:
      _init_sql_db()
      session = next(_get_sqlite_session())
      try:
          log = session.query(_LogModel) \
              .filter(_LogModel.student_id == student_id) \
              .order_by(_LogModel.timestamp.desc()) \
              .first()
          if log:
              return {
                  "id": log.id,
                  "student_id": log.student_id,
                  "similarity_score": log.similarity_score,
                  "device_id": log.device_id,
                  "timestamp": log.timestamp.isoformat() if hasattr(log.timestamp, "isoformat") else log.timestamp,
                  "error_message": log.error_message
              }
          return None
      finally:
          session.close()

  def insert_queue_item(student_id, image_path):
      _init_sql_db()
      session = next(_get_sqlite_session())
      try:
          if DB_MODE == "mysql" and image_path and image_path.startswith("db://registration_queue/"):
              try:
                  row_id = int(image_path.split("/")[-1])
              except ValueError:
                  return False
              item = session.query(_QueueModel).filter(_QueueModel.id == row_id).first()
              if item:
                  item.status = "pending"
                  item.image_path = image_path
                  session.commit()
                  return True
              return False
          else:
              item = _QueueModel(student_id=student_id, image_path=image_path, status="pending")
              session.add(item)
              session.commit()
              return True
      except Exception as e:
          print(f"[SQL] insert_queue_item error: {e}")
          session.rollback()
          return False
      finally:
          session.close()

  def get_pending_queue_items(limit: Optional[int] = None):
      _init_sql_db()
      session = next(_get_sqlite_session())
      try:
          query = session.query(_QueueModel).filter(_QueueModel.status == "pending")
          if limit is not None:
              query = query.limit(limit)
          items = query.all()
          return [
              {"id": item.id, "student_id": item.student_id, "image_path": item.image_path}
              for item in items
          ]
      finally:
          session.close()

  def update_queue_item_status(queue_id, status, error_message=None):
      _init_sql_db()
      session = next(_get_sqlite_session())
      try:
          item = session.query(_QueueModel).filter(_QueueModel.id == queue_id).first()
          if item:
              item.status = status
              item.processed_at = datetime.datetime.utcnow()
              if error_message:
                  item.error_message = error_message
              session.commit()
              return True
          return False
      finally:
          session.close()

  def upload_image(file_bytes, student_id, ext="jpg"):
      """Upload image. Returns database URI (MySQL) or local path (SQLite)."""
      if DB_MODE == "mysql":
          _init_sql_db()
          session = next(_get_sqlite_session())
          try:
              item = _QueueModel(
                  student_id=student_id,
                  image_blob=file_bytes,
                  status="uploading",
                  image_path=None
              )
              session.add(item)
              session.commit()
              session.refresh(item)
              return f"db://registration_queue/{item.id}"
          except Exception as e:
              print(f"[MySQL] upload_image error: {e}")
              session.rollback()
              return None
          finally:
              session.close()
      else:
          _init_sql_db()
          import uuid
          filename = f"{student_id}_{uuid.uuid4().hex[:8]}.{ext}"
          filepath = _IMAGES_DIR / filename
          with open(filepath, "wb") as f:
              f.write(file_bytes)
          return str(filepath)

  def get_image_blob_by_ref(ref_uri: str) -> Optional[bytes]:
      if not ref_uri or not ref_uri.startswith("db://"):
          return None

      try:
          parts = ref_uri[5:].split("/")
          if len(parts) != 2:
              return None
          table_name, row_id_str = parts
          row_id = int(row_id_str)
      except (ValueError, IndexError):
          return None

      if table_name != "registration_queue":
          return None

      _init_sql_db()
      session = next(_get_sqlite_session())
      try:
          item = session.query(_QueueModel).filter(_QueueModel.id == row_id).first()
          return item.image_blob if item else None
      except Exception as e:
          print(f"[SQL] get_image_blob_by_ref error: {e}")
          return None
      finally:
          session.close()

  def get_all_embeddings():
      return load_embeddings()

  def save_all_embeddings(embeddings_data):
      return save_embeddings(embeddings_data)

  def match_face_embedding(query_embedding):
      return match_face(query_embedding)

  def delete_student_from_db(student_id: str) -> bool:
      _init_sql_db()
      session = next(_get_sqlite_session())
      try:
          import os
          files_to_delete = []

          # 1. Delete associated logs
          user = session.query(_UserModel).filter(_UserModel.student_id == student_id).first()
          
          logs_by_sid = session.query(_LogModel).filter(_LogModel.student_id == student_id).all()
          for log in logs_by_sid:
              session.delete(log)
          
          if user:
              logs_by_uid = session.query(_LogModel).filter(_LogModel.user_id == user.id).all()
              for log in logs_by_uid:
                  session.delete(log)

          # 2. Delete queue items
          q_items = session.query(_QueueModel).filter(_QueueModel.student_id == student_id).all()
          for item in q_items:
              if item.image_path and not item.image_path.startswith("db://"):
                  files_to_delete.append(item.image_path)
              session.delete(item)

          # 3. Delete user
          if user:
              session.delete(user)

          session.commit()

          # Delete physical files from disk only after successful commit
          for filepath in files_to_delete:
              if os.path.exists(filepath):
                  try:
                      os.remove(filepath)
                  except Exception:
                      pass

          return True
      except Exception as e:
          print(f"[SQL] delete_student_from_db error: {e}")
          session.rollback()
          return False
      finally:
          session.close()
  ```

- [ ] **Step 5: Modify main application endpoints**
  Update the root health endpoint in [main.py](file:///D:/AIproject/ai_server/app/main.py#L49-L53) to return DB_MODE.
  ```python
  @app.get("/", tags=["health"])
  def health():
      from app.config import DB_MODE
      return {"status": "ok", "mode": DB_MODE}
  ```

- [ ] **Step 6: Update database tests**
  Modify [test_database.py](file:///D:/AIproject/ai_server/tests/test_database.py#L22-L26) to remove the mock patch for `supabase_available`.
  ```python
  @pytest.fixture()
  def in_memory_db():
      """Set up an in-memory SQLite database for testing SQLite database paths."""
      # Save original settings
      orig_engine = database._sqlite_engine
      orig_session_local = database._SessionLocal

      # Force reset
      database._sqlite_engine = None
      database._SessionLocal = None

      # Patch config
      with patch("app.database.DATABASE_URL", "sqlite:///:memory:"):
          database._init_sqlite()
          yield

      # Clean up and restore original settings
      if database._sqlite_engine:
          database._sqlite_engine.dispose()
      database._sqlite_engine = orig_engine
      database._SessionLocal = orig_session_local
  ```

  Also replace:
  ```python
  with patch("app.database.supabase_available", return_value=False), \
       patch("app.database.DATABASE_URL", db_url):
  ```
  with:
  ```python
  with patch("app.database.DATABASE_URL", db_url):
  ```
  in the `test_sqlite_dynamic_migration` test at [test_database.py:L260-264](file:///D:/AIproject/ai_server/tests/test_database.py#L260-L264).

- [ ] **Step 7: Update conftest.py**
  Remove the `SUPABASE_URL` and `SUPABASE_KEY` deletion mocks in [conftest.py](file:///D:/AIproject/ai_server/tests/conftest.py#L13-L20).
  ```python
  @pytest.fixture(autouse=True)
  def clean_env(monkeypatch):
      """Ensure tests run in pure SQLite offline mode."""
      monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
      monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
  ```

- [ ] **Step 8: Verify Python server tests**
  Enter the virtual environment, install local packages, and execute the tests to ensure database operations continue to succeed:
  ```powershell
  cd D:/AIproject/ai_server
  venv\Scripts\activate
  pip install -r requirements.txt
  pytest tests/ -v
  ```
  Expected output: All database tests should pass successfully.

- [ ] **Step 9: Commit FastAPI changes**
  ```powershell
  git add ai_server/app/config.py ai_server/app/database.py ai_server/app/main.py ai_server/requirements.txt ai_server/tests/test_database.py ai_server/tests/conftest.py
  git commit -m "feat: decommission supabase code, client, tests, and configuration from FastAPI AI server"
  ```

---

### Task 3: Rewrite PHP Web Dashboard

**Files:**
- Modify: [web_dashboard/config.php](file:///D:/AIproject/web_dashboard/config.php)
- Modify: [web_dashboard/api/stats.php](file:///D:/AIproject/web_dashboard/api/stats.php)
- Modify: [web_dashboard/api/attendance.php](file:///D:/AIproject/web_dashboard/api/attendance.php)
- Modify: [web_dashboard/api/students.php](file:///D:/AIproject/web_dashboard/api/students.php)
- Modify: [web_dashboard/api/queue.php](file:///D:/AIproject/web_dashboard/api/queue.php)

**Interfaces:**
- Consumes: MySQL database schema from Task 1.
- Produces: Fully functional PHP API endpoints using PDO to execute direct SQL queries against MySQL database.

- [ ] **Step 1: Rewrite config.php**
  Replace Supabase constants with MySQL variables and initialize a PDO helper inside [config.php](file:///D:/AIproject/web_dashboard/config.php).
  ```php
  <?php
  define('DB_HOST', 'localhost');
  define('DB_USER', 'root');
  define('DB_PASS', 'SecurePassword123!');
  define('DB_NAME', 'face_attendance');
  define('AI_SERVER_URL', 'http://localhost:8000');
  define('ADMIN_API_KEY', 'my-secure-admin-token-12345');

  function get_db_connection() {
      static $pdo = null;
      if ($pdo === null) {
          try {
              $dsn = "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=utf8mb4";
              $options = [
                  PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
                  PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                  PDO::ATTR_EMULATE_PREPARES   => false,
              ];
              $pdo = new PDO($dsn, DB_USER, DB_PASS, $options);
          } catch (PDOException $e) {
              header('Content-Type: application/json');
              http_response_code(500);
              echo json_encode(['error' => 'Database connection failed: ' . $e->getMessage()]);
              exit;
          }
      }
      return $pdo;
  }
  ```

- [ ] **Step 2: Rewrite api/stats.php**
  Rewrite [stats.php](file:///D:/AIproject/web_dashboard/api/stats.php) to use direct PDO queries.
  ```php
  <?php
  require_once __DIR__ . '/../config.php';
  header('Content-Type: application/json');
  header('Cache-Control: no-store');

  try {
      $pdo = get_db_connection();

      // 1. Total students count
      $stmt = $pdo->query("SELECT COUNT(*) FROM users");
      $totalStudents = (int)$stmt->fetchColumn();

      // 2. Pending queue count
      $stmt = $pdo->prepare("SELECT COUNT(*) FROM registration_queue WHERE status = ?");
      $stmt->execute(['pending']);
      $pendingQueue = (int)$stmt->fetchColumn();

      // 3. Today's check-ins
      $todayStart = date('Y-m-d 00:00:00');
      $todayEnd = date('Y-m-d 23:59:59');
      $stmt = $pdo->prepare("SELECT COUNT(*) FROM check_in_logs WHERE timestamp >= ? AND timestamp <= ? AND student_id IS NOT NULL");
      $stmt->execute([$todayStart, $todayEnd]);
      $todayCheckins = (int)$stmt->fetchColumn();

      // 4. Last check-in
      $stmt = $pdo->query("SELECT student_id, timestamp FROM check_in_logs WHERE student_id IS NOT NULL ORDER BY timestamp DESC LIMIT 1");
      $lastCheckin = $stmt->fetch();
      if (!$lastCheckin) {
          $lastCheckin = null;
      } else {
          // Format timestamp to ISO 8601 to match frontend expectations
          $lastCheckin['timestamp'] = str_replace(' ', 'T', $lastCheckin['timestamp']) . 'Z';
      }

      echo json_encode([
          'total_students' => $totalStudents,
          'today_checkins' => $todayCheckins,
          'pending_queue'  => $pendingQueue,
          'last_checkin'   => $lastCheckin,
      ]);
  } catch (PDOException $e) {
      http_response_code(503);
      echo json_encode(['error' => 'Database query error: ' . $e->getMessage()]);
      exit;
  }
  ```

- [ ] **Step 3: Rewrite api/attendance.php**
  Rewrite [attendance.php](file:///D:/AIproject/web_dashboard/api/attendance.php) to retrieve check-in logs and user names using a single LEFT JOIN query.
  ```php
  <?php
  require_once __DIR__ . '/../config.php';
  header('Content-Type: application/json');
  header('Cache-Control: no-store');

  $date     = $_GET['date']      ?? date('Y-m-d');
  $deviceId = $_GET['device_id'] ?? '';
  $page     = max(1, (int)($_GET['page']     ?? 1));
  $perPage  = max(1, min(100, (int)($_GET['per_page'] ?? 20)));
  $offset   = ($page - 1) * $perPage;

  // Validate date format
  if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $date)) {
      http_response_code(400);
      echo json_encode(['error' => 'Invalid date format. Use YYYY-MM-DD.']);
      exit;
  }

  $dayStart = $date . ' 00:00:00';
  $dayEnd   = $date . ' 23:59:59';

  try {
      $pdo = get_db_connection();

      $sql = "SELECT l.id, l.student_id, l.similarity_score, l.device_id, l.timestamp, u.name
              FROM check_in_logs l
              LEFT JOIN users u ON l.student_id = u.student_id
              WHERE l.timestamp >= :day_start AND l.timestamp <= :day_end AND l.student_id IS NOT NULL";
      
      $countSql = "SELECT COUNT(*) FROM check_in_logs l WHERE l.timestamp >= :day_start AND l.timestamp <= :day_end AND l.student_id IS NOT NULL";

      if ($deviceId !== '') {
          $sql .= " AND l.device_id = :device_id";
          $countSql .= " AND l.device_id = :device_id";
      }

      $sql .= " ORDER BY l.timestamp DESC LIMIT :limit OFFSET :offset";

      // Bind values
      $stmt = $pdo->prepare($sql);
      $stmt->bindValue(':day_start', $dayStart, PDO::PARAM_STR);
      $stmt->bindValue(':day_end', $dayEnd, PDO::PARAM_STR);
      if ($deviceId !== '') {
          $stmt->bindValue(':device_id', $deviceId, PDO::PARAM_STR);
      }
      $stmt->bindValue(':limit', $perPage, PDO::PARAM_INT);
      $stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
      $stmt->execute();
      $logs = $stmt->fetchAll();

      // Bind count values
      $countStmt = $pdo->prepare($countSql);
      $countStmt->bindValue(':day_start', $dayStart, PDO::PARAM_STR);
      $countStmt->bindValue(':day_end', $dayEnd, PDO::PARAM_STR);
      if ($deviceId !== '') {
          $countStmt->bindValue(':device_id', $deviceId, PDO::PARAM_STR);
      }
      $countStmt->execute();
      $total = (int)$countStmt->fetchColumn();

      // Format timestamps to match ISO format
      foreach ($logs as &$log) {
          if ($log['timestamp']) {
              $log['timestamp'] = str_replace(' ', 'T', $log['timestamp']) . 'Z';
          }
      }
      unset($log);

      echo json_encode([
          'data'  => $logs,
          'total' => $total,
          'page'  => $page,
      ]);
  } catch (PDOException $e) {
      http_response_code(503);
      echo json_encode(['error' => 'Database query error: ' . $e->getMessage()]);
      exit;
  }
  ```

- [ ] **Step 4: Rewrite api/students.php**
  Rewrite [students.php](file:///D:/AIproject/web_dashboard/api/students.php) to retrieve students and their latest queue status.
  ```php
  <?php
  require_once __DIR__ . '/../config.php';
  header('Content-Type: application/json');
  header('Cache-Control: no-store');

  try {
      $pdo = get_db_connection();

      // Fetch users and their latest registration status via nested query
      $sql = "SELECT u.student_id, u.name, u.created_at, q.status AS queue_status
              FROM users u
              LEFT JOIN (
                  SELECT rq.student_id, rq.status
                  FROM registration_queue rq
                  INNER JOIN (
                      SELECT student_id, MAX(id) as max_id
                      FROM registration_queue
                      GROUP BY student_id
                  ) latest ON rq.id = latest.max_id
              ) q ON u.student_id = q.student_id
              ORDER BY u.created_at DESC";

      $stmt = $pdo->query($sql);
      $users = $stmt->fetchAll();

      // Format timestamps to match ISO format
      foreach ($users as &$user) {
          if ($user['created_at']) {
              $user['created_at'] = str_replace(' ', 'T', $user['created_at']) . 'Z';
          }
      }
      unset($user);

      echo json_encode(['data' => $users]);
  } catch (PDOException $e) {
      http_response_code(503);
      echo json_encode(['error' => 'Database query error: ' . $e->getMessage()]);
      exit;
  }
  ```

- [ ] **Step 5: Rewrite api/queue.php**
  Rewrite [queue.php](file:///D:/AIproject/web_dashboard/api/queue.php) to fetch items from `registration_queue`.
  ```php
  <?php
  require_once __DIR__ . '/../config.php';
  header('Content-Type: application/json');
  header('Cache-Control: no-store');

  try {
      $pdo = get_db_connection();

      $status = $_GET['status'] ?? '';
      $allowed = ['pending', 'completed', 'failed'];

      $sql = "SELECT id, student_id, image_path, status, created_at, processed_at, error_message
              FROM registration_queue";
      
      $params = [];
      if ($status !== '' && in_array($status, $allowed, true)) {
          $sql .= " WHERE status = :status";
          $params[':status'] = $status;
      }

      $sql .= " ORDER BY created_at DESC";

      $stmt = $pdo->prepare($sql);
      $stmt->execute($params);
      $rows = $stmt->fetchAll();

      // Format timestamps to match ISO format
      foreach ($rows as &$row) {
          if ($row['created_at']) {
              $row['created_at'] = str_replace(' ', 'T', $row['created_at']) . 'Z';
          }
          if ($row['processed_at']) {
              $row['processed_at'] = str_replace(' ', 'T', $row['processed_at']) . 'Z';
          }
      }
      unset($row);

      echo json_encode(['data' => $rows]);
  } catch (PDOException $e) {
      http_response_code(503);
      echo json_encode(['error' => 'Database query error: ' . $e->getMessage()]);
      exit;
  }
  ```

- [ ] **Step 6: Verification of PHP dashboard APIs**
  Run local verification requests to test connection and responses:
  ```powershell
  # Test Stats API
  curl -G http://localhost/web_dashboard/api/stats.php

  # Test Attendance API
  curl -G "http://localhost/web_dashboard/api/attendance.php?date=2026-07-08"

  # Test Students API
  curl -G http://localhost/web_dashboard/api/students.php

  # Test Queue API
  curl -G "http://localhost/web_dashboard/api/queue.php?status=pending"
  ```
  Ensure all return HTTP status `200 OK` and a correctly structured JSON object without errors.

- [ ] **Step 7: Commit PHP changes**
  ```powershell
  git add web_dashboard/config.php web_dashboard/api/stats.php web_dashboard/api/attendance.php web_dashboard/api/students.php web_dashboard/api/queue.php
  git commit -m "feat: rewrite PHP web dashboard APIs to query MySQL directly via PDO"
  ```

---

### Task 4: Refactor Flutter App (app_face_capture)

**Files:**
- Delete: [app_face_capture/lib/data/services/supabase_storage_service.dart](file:///D:/AIproject/app_face_capture/lib/data/services/supabase_storage_service.dart)
- Delete: [app_face_capture/test/supabase_storage_service_test.dart](file:///D:/AIproject/app_face_capture/test/supabase_storage_service_test.dart)
- Modify: [app_face_capture/pubspec.yaml](file:///D:/AIproject/app_face_capture/pubspec.yaml)
- Modify: [app_face_capture/lib/main.dart](file:///D:/AIproject/app_face_capture/lib/main.dart)
- Modify: [app_face_capture/lib/core/constants/api_constants.dart](file:///D:/AIproject/app_face_capture/lib/core/constants/api_constants.dart)
- Modify: [app_face_capture/lib/core/constants/storage_constants.dart](file:///D:/AIproject/app_face_capture/lib/core/constants/storage_constants.dart)
- Modify: [app_face_capture/lib/data/repositories/face_repository.dart](file:///D:/AIproject/app_face_capture/lib/data/repositories/face_repository.dart)
- Modify: [app_face_capture/lib/presentation/viewmodels/settings_viewmodel.dart](file:///D:/AIproject/app_face_capture/lib/presentation/viewmodels/settings_viewmodel.dart)
- Modify: [app_face_capture/lib/presentation/viewmodels/upload_viewmodel.dart](file:///D:/AIproject/app_face_capture/lib/presentation/viewmodels/upload_viewmodel.dart)
- Modify: [app_face_capture/lib/presentation/views/settings_screen.dart](file:///D:/AIproject/app_face_capture/lib/presentation/views/settings_screen.dart)
- Modify: [app_face_capture/lib/presentation/views/upload_screen.dart](file:///D:/AIproject/app_face_capture/lib/presentation/views/upload_screen.dart)
- Modify: [app_face_capture/test/face_repository_test.dart](file:///D:/AIproject/app_face_capture/test/face_repository_test.dart)
- Modify: [app_face_capture/test/settings_viewmodel_test.dart](file:///D:/AIproject/app_face_capture/test/settings_viewmodel_test.dart)
- Modify: [app_face_capture/test/upload_viewmodel_test.dart](file:///D:/AIproject/app_face_capture/test/upload_viewmodel_test.dart)

**Interfaces:**
- Consumes: FastAPI REST API from Task 2.
- Produces: A pure API-driven face capture Flutter app that registers users and uploads image files exclusively via standard HTTP POST calls.

- [ ] **Step 1: Delete Supabase storage service files**
  Delete the Dart service file and its associated unit test file:
  ```powershell
  Remove-Item D:/AIproject/app_face_capture/lib/data/services/supabase_storage_service.dart -Force
  Remove-Item D:/AIproject/app_face_capture/test/supabase_storage_service_test.dart -Force
  ```

- [ ] **Step 2: Update Flutter pubspec.yaml**
  Remove `supabase_flutter: ^2.0.0` from dependencies in [pubspec.yaml](file:///D:/AIproject/app_face_capture/pubspec.yaml#L19).
  ```yaml
  dependencies:
    flutter:
      sdk: flutter
    cupertino_icons: ^1.0.8
    http: ^1.2.0
    go_router: ^14.0.0
    provider: ^6.1.0
    camera: ^0.11.0
    path_provider: ^2.1.0
    path: ^1.9.0
    shared_preferences: ^2.2.0
    uuid: ^4.3.3
  ```

- [ ] **Step 3: Modify main.dart**
  Remove imports and calls to `SupabaseStorageService` initialization from [main.dart](file:///D:/AIproject/app_face_capture/lib/main.dart).
  ```dart
  import 'package:flutter/material.dart';
  import 'app.dart';

  void main() async {
    WidgetsFlutterBinding.ensureInitialized();
    runApp(const App());
  }
  ```

- [ ] **Step 4: Clean API Constants**
  Remove `supabaseUrl` and `supabaseAnonKey` from [api_constants.dart](file:///D:/AIproject/app_face_capture/lib/core/constants/api_constants.dart#L18-L26).
  ```dart
  class ApiConstants {
    static const String baseUrl = String.fromEnvironment(
      'BASE_URL',
      defaultValue: '',
    );
    static const String register = '/register';
    static const String registerStatus = '/register/status';
    static const String trainNow = '/train-now';
    static const String verify = '/verify';
    static const String logs = '/logs';
    static const String health = '/';

    // App constants
    static const int requiredPhotos = 10;
    static const int maxPhotosPerUpload = 3;
    static const double faceConfidenceThreshold = 0.8;

    static const String adminPin = String.fromEnvironment(
      'ADMIN_PIN',
      defaultValue: '1234',
    );
    static const String adminApiKey = String.fromEnvironment(
      'ADMIN_API_KEY',
      defaultValue: '',
    );
  }
  ```

- [ ] **Step 5: Clean Storage Constants**
  Decommission the `UploadMethod` enum and remove Supabase bucket configuration from [storage_constants.dart](file:///D:/AIproject/app_face_capture/lib/core/constants/storage_constants.dart).
  ```dart
  class StorageConstants {
    static const String registrationPathPrefix = 'registrations';

    static String imagePath(String studentId, String uuid) =>
        '$registrationPathPrefix/$studentId/$uuid.jpg';
  }
  ```

- [ ] **Step 6: Rewrite FaceRepository**
  Remove the `SupabaseStorageService` dependency, remove `UploadMethod` parameters, and make all operations go through `FaceApiService` inside [face_repository.dart](file:///D:/AIproject/app_face_capture/lib/data/repositories/face_repository.dart).
  ```dart
  import 'dart:io';
  import 'package:app_face_capture/data/models/registration_response.dart';
  import 'package:app_face_capture/data/models/registration_status.dart';
  import 'package:app_face_capture/data/services/face_api_service.dart';
  import 'package:app_face_capture/core/constants/api_constants.dart';

  class FaceRepository {
    final FaceApiService _apiService;

    FaceRepository({
      FaceApiService? apiService,
    })  : _apiService = apiService ?? FaceApiService();

    Future<RegistrationResponse> uploadPhotos(
      String studentId,
      String studentName,
      List<File> images,
    ) async {
      final batches = _batchImages(images, ApiConstants.maxPhotosPerUpload);
      RegistrationResponse? lastResponse;

      for (final batch in batches) {
        lastResponse = await _apiService.register(studentId, studentName, batch);
      }

      return lastResponse!;
    }

    Future<RegistrationStatus> checkStatus(String studentId) async {
      return await _apiService.checkStatus(studentId);
    }

    Future<bool> checkServerHealth() async {
      return await _apiService.healthCheck();
    }

    List<List<File>> _batchImages(List<File> images, int batchSize) {
      final batches = <List<File>>[];
      for (var i = 0; i < images.length; i += batchSize) {
        final end = (i + batchSize > images.length) ? images.length : i + batchSize;
        batches.add(images.sublist(i, end));
      }
      return batches;
    }

    void dispose() {
      _apiService.dispose();
    }
  }
  ```

- [ ] **Step 7: Clean SettingsViewModel**
  Remove all mentions of `UploadMethod` and persisting `upload_method` in [settings_viewmodel.dart](file:///D:/AIproject/app_face_capture/lib/presentation/viewmodels/settings_viewmodel.dart).
  ```dart
  import 'package:flutter/foundation.dart';
  import 'package:shared_preferences/shared_preferences.dart';

  import 'package:app_face_capture/core/constants/api_constants.dart';
  import 'package:app_face_capture/data/repositories/face_repository.dart';

  class SettingsViewModel extends ChangeNotifier {
    final FaceRepository _repository;
    
    String _serverUrl = ApiConstants.baseUrl;

    SettingsViewModel({FaceRepository? repository})
        : _repository = repository ?? FaceRepository();

    String get serverUrl => _serverUrl;

    bool _isAdminAuthenticated = false;
    bool get isAdminAuthenticated => _isAdminAuthenticated;

    void authenticateAdmin(bool authenticated) {
      _isAdminAuthenticated = authenticated;
      notifyListeners();
    }

    /// Load settings from SharedPreferences.
    Future<void> load() async {
      final prefs = await SharedPreferences.getInstance();
      _serverUrl = prefs.getString('server_url') ?? ApiConstants.baseUrl;
      notifyListeners();
    }

    /// Sets and persists the Server URL.
    Future<void> setServerUrl(String url) async {
      _serverUrl = url;
      notifyListeners();
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('server_url', url);
    }

    /// Test server connection health.
    Future<bool> checkServerHealth() async {
      return await _repository.checkServerHealth();
    }
  }
  ```

- [ ] **Step 8: Clean UploadViewModel**
  Remove the `method` parameter and adjust constructor calls in [upload_viewmodel.dart](file:///D:/AIproject/app_face_capture/lib/presentation/viewmodels/upload_viewmodel.dart).
  ```dart
  import 'dart:io';
  import 'package:flutter/foundation.dart';
  import 'package:app_face_capture/data/repositories/face_repository.dart';
  import 'package:app_face_capture/data/models/registration_status.dart';

  enum UploadState { idle, uploading, success, failed }

  class UploadViewModel extends ChangeNotifier {
    final FaceRepository _repository;
    final String studentId;
    final String studentName;
    final List<String> _imagePaths;

    UploadState _state = UploadState.idle;
    int _uploadedCount = 0;
    String? _errorMessage;
    List<FaceValidationResult> _validationResults = [];

    UploadViewModel({
      required FaceRepository repository,
      required this.studentId,
      required this.studentName,
      required List<String> imagePaths,
    })  : _repository = repository,
          _imagePaths = List.from(imagePaths);

    UploadState get state => _state;
    bool get isUploading => _state == UploadState.uploading;
    bool get isSuccess => _state == UploadState.success;
    bool get isFailed => _state == UploadState.failed;
    int get uploadedCount => _uploadedCount;
    List<String> get imagePaths => List.unmodifiable(_imagePaths);
    int get totalCount => _imagePaths.length;
    double get progress => totalCount > 0 ? _uploadedCount / totalCount : 0.0;
    String? get errorMessage => _errorMessage;
    List<FaceValidationResult> get validationResults => _validationResults;

    Future<void> startUpload() async {
      _state = UploadState.uploading;
      _uploadedCount = 0;
      _errorMessage = null;
      _validationResults = [];
      notifyListeners();

      try {
        final files = _imagePaths.map((p) => File(p)).toList();
        await _repository.uploadPhotos(studentId, studentName, files);
        _uploadedCount = _imagePaths.length;
        _state = UploadState.success;
        notifyListeners();
      } on FaceVerificationException catch (e) {
        _state = UploadState.failed;
        _errorMessage = e.message;
        _validationResults = e.results;
        notifyListeners();
      } catch (e) {
        _state = UploadState.failed;
        _errorMessage = e.toString();
        notifyListeners();
      }
    }

    void replacePhoto(int index, String newPath) {
      if (index >= 0 && index < _imagePaths.length) {
        _imagePaths[index] = newPath;
        notifyListeners();
      }
    }

    @override
    void dispose() {
      _repository.dispose();
      super.dispose();
    }
  }
  ```

- [ ] **Step 9: Strip Upload Method Selection from SettingsScreen**
  Remove the `Upload Method` Card from [settings_screen.dart](file:///D:/AIproject/app_face_capture/lib/presentation/views/settings_screen.dart#L63-L103) entirely.
  ```dart
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: Consumer<SettingsViewModel>(
        builder: (context, model, child) {
          return Form(
            key: _formKey,
            child: ListView(
              padding: const EdgeInsets.all(16.0),
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Backend Server URL',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 8),
                        TextFormField(
                          controller: _urlController,
                          decoration: const InputDecoration(
                            labelText: 'Server Base URL',
                            hintText: 'http://10.0.2.2:8000',
                            border: OutlineInputBorder(),
                          ),
                          validator: (value) {
                            if (value == null || value.trim().isEmpty) {
                              return 'Please enter a URL';
                            }
                            return null;
                          },
                          onChanged: (value) {
                            if (_formKey.currentState!.validate()) {
                              model.setServerUrl(value.trim());
                            }
                          },
                        ),
                        const SizedBox(height: 16),
                        ElevatedButton.icon(
                          onPressed: () => _testConnection(model),
                          icon: const Icon(Icons.swap_horiz),
                          label: const Text('Test Connection'),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
  ```

- [ ] **Step 10: Clean UploadScreen**
  Remove the method badge and method constructors from [upload_screen.dart](file:///D:/AIproject/app_face_capture/lib/presentation/views/upload_screen.dart#L25-L89).
  ```dart
  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => UploadViewModel(
        repository: FaceRepository(),
        studentId: studentId,
        studentName: studentName,
        imagePaths: imagePaths,
      )..startUpload(),
      child: Consumer<UploadViewModel>(
        builder: (context, viewModel, _) {
          return PopScope(
            canPop: viewModel.isSuccess || viewModel.isFailed,
            child: Scaffold(
              appBar: AppBar(
                title: Text(_appBarTitle(viewModel)),
                automaticallyImplyLeading:
                    viewModel.isSuccess || viewModel.isFailed,
              ),
              body: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 400),
                  child: Padding(
                    padding: const EdgeInsets.all(24.0),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const SizedBox(height: 24),
                        Expanded(child: _buildBody(context, viewModel)),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
  ```

- [ ] **Step 11: Update Flutter Unit Tests**
  Modify tests to match the removed `UploadMethod` and `SupabaseStorageService` implementations.
  
  In [face_repository_test.dart](file:///D:/AIproject/app_face_capture/test/face_repository_test.dart):
  ```dart
  import 'dart:io';
  import 'package:flutter_test/flutter_test.dart';
  import 'package:mocktail/mocktail.dart';

  import 'package:app_face_capture/data/models/registration_response.dart';
  import 'package:app_face_capture/data/models/registration_status.dart';
  import 'package:app_face_capture/data/repositories/face_repository.dart';
  import 'package:app_face_capture/data/services/face_api_service.dart';

  class MockFaceApiService extends Mock implements FaceApiService {}

  void main() {
    group('FaceRepository Tests', () {
      late MockFaceApiService mockApiService;
      late FaceRepository repository;

      setUp(() {
        mockApiService = MockFaceApiService();
        repository = FaceRepository(
          apiService: mockApiService,
        );
      });

      test('uploadPhotos routes to FaceApiService', () async {
        final fakeResponse = RegistrationResponse(
          message: 'Success',
          studentId: 'S001',
          status: 'pending',
        );

        when(() => mockApiService.register(any(), any(), any()))
            .thenAnswer((_) async => fakeResponse);

        final files = [File('dummy1.jpg')];
        final response = await repository.uploadPhotos('S001', 'John Doe', files);

        expect(response, fakeResponse);
        verify(() => mockApiService.register('S001', 'John Doe', files)).called(1);
      });

      test('checkStatus routes to FaceApiService', () async {
        final fakeStatus = RegistrationStatus(
          studentId: 'S001',
          status: 'pending',
          message: 'queued',
        );

        when(() => mockApiService.checkStatus(any()))
            .thenAnswer((_) async => fakeStatus);

        final status = await repository.checkStatus('S001');

        expect(status, fakeStatus);
        verify(() => mockApiService.checkStatus('S001')).called(1);
      });
    });
  }
  ```

  In [settings_viewmodel_test.dart](file:///D:/AIproject/app_face_capture/test/settings_viewmodel_test.dart):
  ```dart
  import 'package:flutter_test/flutter_test.dart';
  import 'package:mocktail/mocktail.dart';
  import 'package:shared_preferences/shared_preferences.dart';

  import 'package:app_face_capture/core/constants/api_constants.dart';
  import 'package:app_face_capture/data/repositories/face_repository.dart';
  import 'package:app_face_capture/presentation/viewmodels/settings_viewmodel.dart';

  class MockFaceRepository extends Mock implements FaceRepository {}

  void main() {
    group('SettingsViewModel Tests', () {
      late MockFaceRepository mockRepository;
      late SettingsViewModel viewModel;

      setUp(() {
        mockRepository = MockFaceRepository();
        viewModel = SettingsViewModel(repository: mockRepository);
      });

      test('load retrieves default values when SharedPreferences is empty', () async {
        SharedPreferences.setMockInitialValues({});
        await viewModel.load();

        expect(viewModel.serverUrl, ApiConstants.baseUrl);
      });

      test('load retrieves saved values correctly', () async {
        SharedPreferences.setMockInitialValues({
          'server_url': 'http://my-server.com',
        });
        await viewModel.load();

        expect(viewModel.serverUrl, 'http://my-server.com');
      });

      test('setServerUrl updates value and persists to SharedPreferences', () async {
        SharedPreferences.setMockInitialValues({});
        await viewModel.load();

        await viewModel.setServerUrl('http://new-url.com');
        expect(viewModel.serverUrl, 'http://new-url.com');

        final prefs = await SharedPreferences.getInstance();
        expect(prefs.getString('server_url'), 'http://new-url.com');
      });

      test('checkServerHealth delegates to repository', () async {
        when(() => mockRepository.checkServerHealth()).thenAnswer((_) async => true);

        final result = await viewModel.checkServerHealth();

        expect(result, true);
        verify(() => mockRepository.checkServerHealth()).called(1);
      });

      test('isAdminAuthenticated defaults to false', () {
        expect(viewModel.isAdminAuthenticated, false);
      });

      test('authenticateAdmin updates authenticated state and notifies listeners', () {
        bool notified = false;
        viewModel.addListener(() {
          notified = true;
        });

        viewModel.authenticateAdmin(true);
        expect(viewModel.isAdminAuthenticated, true);
        expect(notified, true);
      });
    });
  }
  ```

  In [upload_viewmodel_test.dart](file:///D:/AIproject/app_face_capture/test/upload_viewmodel_test.dart):
  ```dart
  import 'package:flutter_test/flutter_test.dart';
  import 'package:mocktail/mocktail.dart';
  import 'package:fake_async/fake_async.dart';

  import 'package:app_face_capture/data/models/registration_response.dart';
  import 'package:app_face_capture/data/repositories/face_repository.dart';
  import 'package:app_face_capture/presentation/viewmodels/upload_viewmodel.dart';

  class MockFaceRepository extends Mock implements FaceRepository {}

  void main() {
    group('UploadViewModel Tests', () {
      late MockFaceRepository mockRepository;
      late UploadViewModel viewModel;

      setUp(() {
        mockRepository = MockFaceRepository();
        viewModel = UploadViewModel(
          repository: mockRepository,
          studentId: 'S001',
          studentName: 'John Doe',
          imagePaths: ['dummy_path.jpg'],
        );
        
        when(() => mockRepository.dispose()).thenAnswer((_) {});
      });

      test('initial state is idle', () {
        expect(viewModel.state, UploadState.idle);
        expect(viewModel.isUploading, false);
        expect(viewModel.isSuccess, false);
        expect(viewModel.isFailed, false);
        expect(viewModel.uploadedCount, 0);
        expect(viewModel.progress, 0.0);
      });

      test('startUpload success transitions: uploading -> success', () {
        fakeAsync((async) {
          final fakeResponse = RegistrationResponse(
            message: 'Success',
            studentId: 'S001',
            status: 'pending',
          );

          when(() => mockRepository.uploadPhotos(any(), any(), any()))
              .thenAnswer((_) async => fakeResponse);

          viewModel.startUpload();
          
          async.elapse(const Duration(seconds: 1));

          expect(viewModel.state, UploadState.success);
          expect(viewModel.uploadedCount, 1);
          expect(viewModel.progress, 1.0);
          
          verify(() => mockRepository.uploadPhotos('S001', 'John Doe', any())).called(1);
          verifyNever(() => mockRepository.checkStatus(any()));
        });
      });

      test('startUpload upload failure sets state to failed', () {
        fakeAsync((async) {
          when(() => mockRepository.uploadPhotos(any(), any(), any()))
              .thenThrow(Exception('Connection error'));

          viewModel.startUpload();
          
          async.elapse(const Duration(seconds: 1));

          expect(viewModel.state, UploadState.failed);
          expect(viewModel.errorMessage, contains('Connection error'));
          verify(() => mockRepository.uploadPhotos('S001', 'John Doe', any())).called(1);
          verifyNever(() => mockRepository.checkStatus(any()));
        });
      });
    });
  }
  ```

- [ ] **Step 12: Run Flutter App Tests**
  Confirm all dependencies fetch and the tests pass:
  ```powershell
  cd D:/AIproject/app_face_capture
  flutter pub get
  flutter test
  ```
  Expected output: All 35+ test files should pass successfully.

- [ ] **Step 13: Commit Flutter App changes**
  ```powershell
  git add app_face_capture/pubspec.yaml app_face_capture/lib/main.dart app_face_capture/lib/core/constants/api_constants.dart app_face_capture/lib/core/constants/storage_constants.dart app_face_capture/lib/data/repositories/face_repository.dart app_face_capture/lib/presentation/viewmodels/settings_viewmodel.dart app_face_capture/lib/presentation/viewmodels/upload_viewmodel.dart app_face_capture/lib/presentation/views/settings_screen.dart app_face_capture/lib/presentation/views/upload_screen.dart app_face_capture/test/face_repository_test.dart app_face_capture/test/settings_viewmodel_test.dart app_face_capture/test/upload_viewmodel_test.dart
  git commit -m "feat: decommission supabase SDK, upload methods, and view selections in Flutter app"
  ```
