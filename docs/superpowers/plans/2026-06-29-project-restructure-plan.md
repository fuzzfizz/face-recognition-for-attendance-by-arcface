# Project Restructure Implementation Plan
**Branch:** feat/project-restructure  
**Spec:** docs/superpowers/specs/2026-06-29-project-restructuring-design.md  
**Date:** 2026-06-29

---

## Global Constraints

- All Python code lives in `ai_server/app/` (and sub-packages).
- All Dart code lives in `app_face_capture/lib/`.
- Layer rule: routes call services; services call data-access or domain; domain (matcher, face_processor) has no HTTP/DB imports.
- Admin auth: `POST /train-now` requires `X-Admin-Key` header matching `ADMIN_API_KEY` env var; returns 401 if missing/wrong.
- Legacy endpoints are re-mounted under `/v1/` prefix (not deleted).
- `pandas` must be removed from `requirements.txt`.
- `match_face()` must return a `student_id` key.
- `get_pending_queue_items()` in Supabase mode must query the `registration_queue` table (not return `[]`).
- `decode_image_from_source()` in `utils/image_utils.py` must handle both local file paths and `https://` URLs.
- Matcher in-memory cache: reload only when `.pkl` mtime changes; `invalidate_cache()` called after save.
- Flutter: `UploadMethod` enum in `core/constants/storage_constants.dart` with values `viaServer` and `directSupabase`.
- Flutter: `FaceRepository.uploadPhotos` routes by `UploadMethod`.
- Flutter: settings persisted via `SharedPreferences`.
- Flutter: admin screen accessible only via long-press on home screen logo; PIN stored as compile-time constant.
- No new features beyond the spec — YAGNI strictly.

---

## Phase 1 — ai_server

### Task 1: Extract SQLAlchemy ORM models to `models.py`

**Goal:** Move the inline ORM class definitions out of `database.py` into a new dedicated `app/models.py`.

**Steps:**
1. Read `ai_server/app/database.py` and identify the SQLAlchemy model classes (`User`, `UserImage`, `RegistrationQueue`, `CheckInLog`) defined inside `_init_sqlite()`.
2. Create `ai_server/app/models.py` with:
   - `Base = declarative_base()`
   - Class `User(Base)` — columns: `id`, `student_id` (unique), `name`, `created_at`
   - Class `UserImage(Base)` — columns: `id`, `user_id` (FK), `image_path`, `created_at`
   - Class `RegistrationQueue(Base)` — columns: `id`, `student_id`, `image_path`, `status`, `error_message`, `created_at`
   - Class `CheckInLog(Base)` — columns: `id`, `student_id`, `similarity_score`, `device_id`, `timestamp`
3. Update `database.py` to import from `models.py` instead of defining inline.
4. Verify: `python -c "from app.database import init_db; init_db()"` runs without errors.
5. Commit: `refactor(ai_server): extract ORM models to models.py`

**Acceptance:** `models.py` exists with 4 model classes; `database.py` imports them; `init_db()` works.

---

### Task 2: Create `utils/image_utils.py` (URL-aware image decoder)

**Goal:** Create the shared image utility module that handles both local file paths and HTTPS URLs.

**Steps:**
1. Create directory `ai_server/app/utils/` with `__init__.py`.
2. Create `ai_server/app/utils/image_utils.py` with:
   - `decode_image_from_source(source: str) -> np.ndarray | None` — if source starts with `http://` or `https://`, download via `requests.get(source, timeout=10)` then `cv2.imdecode`; otherwise use `cv2.imread(source)`.
   - `decode_image_bytes(data: bytes) -> np.ndarray | None` — `np.frombuffer` then `cv2.imdecode`.
   - `decode_base64_image(b64: str) -> np.ndarray | None` — handle optional `data:image/...;base64,` prefix, base64-decode, then call `decode_image_bytes`. (Moved from `trainer.py`.)
3. Add `requests` to requirements if not already present (it is a supabase dependency, but add explicitly).
4. Write a minimal test `ai_server/tests/test_image_utils.py`:
   - Test `decode_image_bytes` with a small valid JPEG byte sequence.
   - Test `decode_image_from_source` with a local path (use a temp PNG file).
   - Test `decode_base64_image` with a known base64 string.
5. Run `pytest ai_server/tests/test_image_utils.py -v`.
6. Commit: `feat(ai_server): add utils/image_utils with URL-aware decoder`

**Acceptance:** All 3 functions exist and pass tests; no import errors.

---

### Task 3: Fix `supabase_client.py` — queue query + atomic upsert

**Goal:** Fix Bug 1 (queue always returns []) and the race condition in upsert_user.

**Steps:**
1. Read `ai_server/app/supabase_client.py`.
2. Fix `get_pending_queue_items()`: replace the `return []` stub with a real Supabase query:
   ```python
   response = get_supabase().table("registration_queue").select("*").eq("status", "pending").execute()
   return response.data or []
   ```
3. Fix `upsert_user()`: replace the SELECT→INSERT two-step with a single atomic upsert:
   ```python
   response = get_supabase().table("users").upsert(
       {"student_id": student_id}, on_conflict="student_id"
   ).execute()
   return response.data[0] if response.data else None
   ```
4. Write tests in `ai_server/tests/test_supabase_client.py` using a mock Supabase client:
   - `get_pending_queue_items()` calls the table with `eq("status", "pending")`.
   - `upsert_user()` calls `upsert` with `on_conflict="student_id"`.
5. Run `pytest ai_server/tests/test_supabase_client.py -v`.
6. Commit: `fix(ai_server): fix get_pending_queue_items and atomic upsert_user`

**Acceptance:** Both functions fixed; tests pass.

---

### Task 4: Fix `matcher.py` — add `student_id` key + in-memory cache

**Goal:** Fix Bug 3 (missing student_id in match result) and add mtime-based in-memory cache.

**Steps:**
1. Read `ai_server/app/matcher.py`.
2. Add module-level cache:
   ```python
   _cache: list | None = None
   _cache_mtime: float = 0.0
   ```
3. Update `load_embeddings()` to use mtime-based cache:
   - Check `EMBEDDINGS_PATH.stat().st_mtime`; reload only if `_cache is None` or mtime changed.
4. Add `invalidate_cache()` function that sets `_cache = None`.
5. Update `match_face()` (or `match_face_embedding()`) to return `student_id` key explicitly in the result dict. The embedding dicts stored in the pkl already have `student_id` (will be guaranteed after Task 8 fixes training). For now, fall back: `student_id = entry.get("student_id") or entry.get("name", "unknown")`.
6. Write/update tests in `ai_server/tests/test_matcher.py`:
   - Cache invalidation test: call `load_embeddings` twice with same mtime → single file read.
   - `invalidate_cache` causes reload on next call.
   - `match_face` result contains `student_id` key.
7. Run `pytest ai_server/tests/test_matcher.py -v`.
8. Commit: `fix(ai_server): add student_id to match result + mtime cache`

**Acceptance:** Cache works; `match_face` returns `student_id`; tests pass.

---

### Task 5: Fix `face_processor.py` — delegate to `image_utils`

**Goal:** Fix Bug 2 — `decode_image_path()` must handle HTTPS URLs via `decode_image_from_source`.

**Steps:**
1. Read `ai_server/app/face_processor.py`.
2. Replace `cv2.imread(path)` inside `decode_image_path()` with a call to `utils.image_utils.decode_image_from_source(path)`.
3. Replace `np.frombuffer` + `cv2.imdecode` in `decode_image()` with a call to `utils.image_utils.decode_image_bytes(data)`.
4. Keep `get_face_processor()` singleton and `extract_face_embedding()` unchanged.
5. Write/update tests in `ai_server/tests/test_face_processor.py`:
   - `decode_image()` correctly decodes valid bytes.
   - `decode_image_path()` correctly decodes a local image file.
   - (No live HTTP test — that is covered by test_image_utils.)
6. Run `pytest ai_server/tests/test_face_processor.py -v`.
7. Commit: `fix(ai_server): face_processor delegates to image_utils for URL-aware decoding`

**Acceptance:** `face_processor.py` no longer calls `cv2.imread` directly; tests pass.

---

### Task 6: Create `schemas.py` — extract Pydantic models

**Goal:** Move all Pydantic model definitions out of `main.py` into a dedicated `schemas.py`.

**Steps:**
1. Read `ai_server/app/main.py` to find all Pydantic models (`UserCreate`, `ImageUploadBase64`).
2. Create `ai_server/app/schemas.py` with all existing Pydantic models plus new response schemas:
   - `UserCreate(BaseModel)`: `name: str`
   - `ImageUploadBase64(BaseModel)`: `image_base64: str`
   - `RegisterResponse(BaseModel)`: `message: str`, `student_id: str`, `status: str`
   - `TrainResponse(BaseModel)`: `message: str`, `processed_students: list[str]`, `total_pending: int`
   - `VerifyResponse(BaseModel)`: `match: bool`, `student_id: str | None`, `similarity_score: float`, `timestamp: str`
   - `RegistrationStatusResponse(BaseModel)`: `student_id: str`, `status: str`, `message: str`
3. Do NOT remove models from `main.py` yet (that happens in Task 10).
4. Verify `from app.schemas import RegisterResponse` works.
5. Commit: `feat(ai_server): add schemas.py with all Pydantic request/response models`

**Acceptance:** `schemas.py` exists with 6 model classes; importable.

---

### Task 7: Create `dependencies.py` — admin auth guard

**Goal:** Create the FastAPI dependency that enforces the `X-Admin-Key` header on protected endpoints.

**Steps:**
1. Create `ai_server/app/dependencies.py`:
   ```python
   import os
   from fastapi import Header, HTTPException

   ADMIN_KEY = os.getenv("ADMIN_API_KEY", "")

   def require_admin(x_admin_key: str = Header(..., alias="X-Admin-Key")):
       if not ADMIN_KEY or x_admin_key != ADMIN_KEY:
           raise HTTPException(status_code=401, detail="Unauthorized")
   ```
2. Write tests in `ai_server/tests/test_dependencies.py` using FastAPI `TestClient`:
   - Request with correct key → passes through (200 from a dummy route).
   - Request with wrong key → 401.
   - Request with missing header → 422 (FastAPI validation).
   - Empty `ADMIN_API_KEY` env var → always 401.
3. Run `pytest ai_server/tests/test_dependencies.py -v`.
4. Commit: `feat(ai_server): add dependencies.py with require_admin guard`

**Acceptance:** `require_admin` dependency works; tests pass.

---

### Task 8: Create `services/` layer — extract business logic from `main.py`

**Goal:** Extract the business logic from `main.py` route handlers into three focused service modules.

**Steps:**
1. Create `ai_server/app/services/__init__.py` (empty).
2. Create `ai_server/app/services/registration_service.py`:
   - `register_images(student_id: str, files: list[UploadFile]) -> dict` — upsert user, upload images, insert queue entries, return `{student_id, queued_count}`.
   - `get_registration_status(student_id: str) -> dict` — check user exists, check embeddings in pkl, return `{student_id, status, message}`.
3. Create `ai_server/app/services/training_service.py`:
   - `process_pending_queue() -> dict` — get pending items, decode image from source (using `decode_image_from_source`), extract embedding, update queue status, merge into pkl, call `invalidate_cache()`, return `{processed_students, total_pending}`.
4. Create `ai_server/app/services/verification_service.py`:
   - `verify_face(image_data: bytes | None, image_base64: str | None, device_id: str) -> dict` — decode image, extract embedding, match face, insert log, return `{match, student_id, similarity_score, timestamp}`.
5. Write unit tests in `ai_server/tests/test_services.py` with mocked DB, processor, and matcher.
6. Run `pytest ai_server/tests/test_services.py -v`.
7. Commit: `feat(ai_server): add services/ layer (registration, training, verification)`

**Acceptance:** Three service files exist; business logic is out of `main.py` (verified when Task 9/10 rewire the routes); unit tests pass.

---

### Task 9: Create `routers/` — split routes + `/v1/` prefix for legacy

**Goal:** Split all route definitions out of `main.py` into focused router modules.

**Steps:**
1. Create `ai_server/app/routers/__init__.py` (empty).
2. Create `ai_server/app/routers/registration.py`:
   - `router = APIRouter(tags=["registration"])`
   - `POST /register` → calls `registration_service.register_images()`
   - `GET /register/status/{student_id}` → calls `registration_service.get_registration_status()`
3. Create `ai_server/app/routers/training.py`:
   - `router = APIRouter(tags=["training"])`
   - `POST /train-now` with `Depends(require_admin)` → calls `training_service.process_pending_queue()`
4. Create `ai_server/app/routers/verification.py`:
   - `router = APIRouter(tags=["verification"])`
   - `POST /verify` → calls `verification_service.verify_face()`
5. Create `ai_server/app/routers/logs.py`:
   - `router = APIRouter(tags=["logs"])`
   - `GET /logs` → calls `database.get_logs(limit)`
6. Create `ai_server/app/routers/v1/__init__.py` (empty).
7. Create `ai_server/app/routers/v1/users.py`:
   - `router = APIRouter(tags=["legacy-v1"])`
   - `POST /users` — legacy create user (keep existing logic)
   - `GET /users` — legacy list users
   - `POST /users/{user_id}/images` — legacy image upload
   - `POST /train` with `Depends(require_admin)` — legacy train (calls `training_service.process_pending_queue()`)
8. Write integration tests in `ai_server/tests/test_routers.py` using FastAPI `TestClient` with SQLite mode:
   - `GET /` → 200
   - `POST /register` with valid multipart → 200
   - `POST /train-now` without header → 401
   - `POST /train-now` with correct header and empty queue → 400
   - `POST /verify` with no image → 400
   - `GET /logs` → 200 list
9. Run `pytest ai_server/tests/test_routers.py -v`.
10. Commit: `feat(ai_server): add routers/ package with registration, training, verification, logs, v1`

**Acceptance:** All routers created; integration tests pass.

---

### Task 10: Slim down `main.py` + wire everything together

**Goal:** Reduce `main.py` to ~30 lines — just app init, lifespan, and router registration.

**Steps:**
1. Rewrite `ai_server/app/main.py`:
   ```python
   from contextlib import asynccontextmanager
   from fastapi import FastAPI
   from app.database import init_db
   from app.routers import registration, training, verification, logs
   from app.routers.v1 import users as v1_users

   @asynccontextmanager
   async def lifespan(app: FastAPI):
       init_db()
       yield

   app = FastAPI(
       title="Face Recognition AI Server",
       description="ArcFace + Supabase hybrid attendance system",
       version="5.0.0",
       lifespan=lifespan,
   )

   @app.get("/", tags=["health"])
   def health():
       from app.database import using_supabase
       return {"status": "ok", "mode": "supabase" if using_supabase() else "sqlite"}

   app.include_router(registration.router)
   app.include_router(training.router)
   app.include_router(verification.router)
   app.include_router(logs.router)
   app.include_router(v1_users.router, prefix="/v1", tags=["legacy-v1"])

   if __name__ == "__main__":
       import uvicorn
       from app.config import HOST, PORT
       uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
   ```
2. Remove all Pydantic model definitions, route handlers, and business logic that have been moved to services/routers.
3. Remove legacy `trainer.py` import from main (the router handles it).
4. Run full test suite: `pytest ai_server/tests/ -v`.
5. Commit: `refactor(ai_server): slim main.py to app init + router registration only`

**Acceptance:** `main.py` ≤ 35 lines; all tests pass; `uvicorn app.main:app` starts without errors.

---

### Task 11: Update `requirements.txt`, create `.env.example`, update `README.md`

**Goal:** Clean up dependencies, document env vars, update README to reflect new architecture.

**Steps:**
1. Remove `pandas` from `ai_server/requirements.txt`.
2. Ensure `requests` is listed explicitly (needed by `image_utils`).
3. Create `ai_server/.env.example`:
   ```
   # Supabase
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-or-service-role-key
   SUPABASE_STORAGE_BUCKET=face-images

   # Admin
   ADMIN_API_KEY=your-secret-admin-key

   # Face recognition
   SIMILARITY_THRESHOLD=0.60
   MODEL_NAME=buffalo_l

   # Server
   HOST=0.0.0.0
   PORT=8000

   # Fallback (SQLite, used when Supabase vars are not set)
   DATABASE_URL=sqlite:///./data/face_recognition.db
   ```
4. Rewrite `ai_server/README.md` to reflect:
   - New architecture (Supabase primary, SQLite fallback)
   - Updated project structure (services/, routers/, utils/, models.py, schemas.py)
   - All current endpoints (POST /register, GET /register/status/{id}, POST /train-now, POST /verify, GET /logs) and their purpose
   - Legacy /v1/ endpoints noted as deprecated
   - How to set up `.env` from `.env.example`
   - How admin auth works (X-Admin-Key header)
5. Commit: `docs(ai_server): update requirements, add .env.example, rewrite README`

**Acceptance:** `pandas` gone from requirements; `.env.example` exists with all vars; README documents new architecture.

---

### Task 12: Write ai_server test suite

**Goal:** Ensure comprehensive test coverage for the full ai_server restructure.

**Steps:**
1. Create/update `ai_server/tests/conftest.py` with:
   - `test_client` fixture: FastAPI `TestClient` with SQLite mode (no Supabase env vars).
   - Temp dir fixture for test images and `.pkl` files.
2. Ensure the following test files exist and are comprehensive (from prior tasks they may already exist — fill gaps):
   - `test_image_utils.py` — decode bytes, local path, base64, HTTPS URL (mocked with `responses` or `unittest.mock`)
   - `test_supabase_client.py` — queue query, atomic upsert (mocked)
   - `test_matcher.py` — cache, invalidate, student_id in result
   - `test_face_processor.py` — decode delegates to image_utils
   - `test_dependencies.py` — auth guard correct/wrong/missing key
   - `test_services.py` — unit tests for registration, training, verification services
   - `test_routers.py` — integration tests for all endpoints
3. Run full suite: `pytest ai_server/tests/ -v --tb=short`.
4. Fix any failures.
5. Commit: `test(ai_server): complete test suite for restructured codebase`

**Acceptance:** All tests pass; no skipped tests; output pristine.

---

## Phase 2 — app_face_capture

### Task 13: Delete backup/temp files + add new dependencies

**Goal:** Clean up the working tree of stale files and add required Flutter packages.

**Steps:**
1. Delete the following files:
   - `app_face_capture/lib/presentation/viewmodels/upload_viewmodel.dart.backup`
   - `app_face_capture/lib/presentation/viewmodels/upload_viewmodel.dart.old`
   - `app_face_capture/lib/presentation/viewmodels/upload_viewmodel_temp.dart`
   - `app_face_capture/lib/presentation/viewmodels/upload_viewmodel_debug.txt`
   - `app_face_capture/lib/data/repositories/face_repository.dart.backup`
2. Add to `app_face_capture/pubspec.yaml` under `dependencies`:
   - `supabase_flutter: ^2.0.0`
   - `shared_preferences: ^2.2.0`
3. Run `flutter pub get` in `app_face_capture/`.
4. Verify no analysis errors: `flutter analyze` in `app_face_capture/`.
5. Commit: `chore(app): delete backup files, add supabase_flutter + shared_preferences`

**Acceptance:** 5 stale files deleted; pubspec updated; `flutter pub get` succeeds; no analysis errors.

---

### Task 14: Create `storage_constants.dart` + `UploadMethod` enum

**Goal:** Add the Supabase storage configuration and the upload method enum.

**Steps:**
1. Create `app_face_capture/lib/core/constants/storage_constants.dart`:
   ```dart
   enum UploadMethod { viaServer, directSupabase }

   class StorageConstants {
     static const String bucketName = 'face-images';
     static const String registrationPathPrefix = 'registrations';

     static String imagePath(String studentId, String uuid) =>
         '$registrationPathPrefix/$studentId/$uuid.jpg';
   }
   ```
2. Verify the file is importable with `flutter analyze`.
3. Commit: `feat(app): add storage_constants.dart with UploadMethod enum`

**Acceptance:** File exists with `UploadMethod` enum and `StorageConstants` class; no analysis errors.

---

### Task 15: Create `SupabaseStorageService`

**Goal:** Implement Option 2 — direct Supabase Storage upload service.

**Steps:**
1. Create `app_face_capture/lib/data/services/supabase_storage_service.dart`:
   - Class `SupabaseStorageService`
   - Constructor: `SupabaseStorageService({SupabaseClient? client})` — uses `Supabase.instance.client` if not provided.
   - Method: `Future<RegistrationResponse> uploadPhotos(String studentId, List<File> images)`:
     - For each image: generate UUID, upload to `StorageConstants.imagePath(studentId, uuid)` in `StorageConstants.bucketName`.
     - On all success: return `RegistrationResponse` with `status: 'completed'` and `studentId`.
     - On partial failure: throw `Exception('N/M images uploaded successfully')`.
   - Method: `static Future<void> initialize()` — calls `Supabase.initialize(url: ..., anonKey: ...)` using constants from `api_constants.dart` or environment. Add `SUPABASE_URL` and `SUPABASE_ANON_KEY` constants to `api_constants.dart`.
2. Add to `app_face_capture/lib/core/constants/api_constants.dart`:
   ```dart
   static const String supabaseUrl = String.fromEnvironment('SUPABASE_URL', defaultValue: '');
   static const String supabaseAnonKey = String.fromEnvironment('SUPABASE_ANON_KEY', defaultValue: '');
   static const String adminPin = String.fromEnvironment('ADMIN_PIN', defaultValue: '1234');
   static const String adminApiKey = String.fromEnvironment('ADMIN_API_KEY', defaultValue: '');
   ```
3. Write tests in `app_face_capture/test/supabase_storage_service_test.dart` with mocked `SupabaseClient`.
4. Run `flutter test test/supabase_storage_service_test.dart`.
5. Commit: `feat(app): add SupabaseStorageService for direct Supabase upload`

**Acceptance:** Service exists; uploadPhotos returns RegistrationResponse; tests pass.

---

### Task 16: Update `FaceRepository` to route by `UploadMethod`

**Goal:** Make `FaceRepository` delegate to the correct service based on the selected upload method.

**Steps:**
1. Read `app_face_capture/lib/data/repositories/face_repository.dart`.
2. Update the class:
   - Add `SupabaseStorageService _supabaseService` field.
   - Update constructor to accept optional `SupabaseStorageService`.
   - Update `uploadPhotos` signature: `Future<RegistrationResponse> uploadPhotos(String studentId, List<File> images, UploadMethod method)`.
   - Route: `viaServer` → existing `_apiService.register()` batching logic; `directSupabase` → `_supabaseService.uploadPhotos()`.
   - `checkStatus()` only callable in `viaServer` mode; in `directSupabase` mode, throw `UnsupportedError` or return a completed status immediately.
3. Update tests in `app_face_capture/test/face_repository_test.dart`:
   - `viaServer` routes to `FaceApiService`.
   - `directSupabase` routes to `SupabaseStorageService`.
4. Run `flutter test test/face_repository_test.dart`.
5. Run `flutter analyze`.
6. Commit: `feat(app): FaceRepository routes uploadPhotos by UploadMethod`

**Acceptance:** Both routing paths work; tests pass; no analysis errors.

---

### Task 17: Create `SettingsViewModel` + `SettingsScreen`

**Goal:** Add settings persistence and UI for upload method selection.

**Steps:**
1. Create `app_face_capture/lib/presentation/viewmodels/settings_viewmodel.dart`:
   - `SettingsViewModel extends ChangeNotifier`
   - Fields: `UploadMethod _uploadMethod`, `String _serverUrl`
   - `load()` — reads from `SharedPreferences`
   - `setUploadMethod(UploadMethod)` — updates + persists
   - `setServerUrl(String)` — updates + persists
   - `Future<bool> checkServerHealth()` — calls `FaceRepository.checkServerHealth()`
2. Create `app_face_capture/lib/presentation/views/settings_screen.dart`:
   - `AppBar` with title "Settings"
   - `SwitchListTile` or `SegmentedButton` to toggle `UploadMethod`
   - `TextFormField` for server URL
   - "Test Connection" button → calls `checkServerHealth()` → shows snackbar
   - Note text when `directSupabase` active: "Images uploaded directly. Training must be triggered by an admin."
3. Write tests in `app_face_capture/test/settings_viewmodel_test.dart`:
   - `setUploadMethod` persists to SharedPreferences.
   - `load()` restores persisted values.
4. Run `flutter test test/settings_viewmodel_test.dart`.
5. Run `flutter analyze`.
6. Commit: `feat(app): add SettingsViewModel + SettingsScreen`

**Acceptance:** Settings persisted and loaded correctly; screen renders without errors; tests pass.

---

### Task 18: Create `AdminViewModel` + `AdminScreen`

**Goal:** Add the hidden admin screen for triggering model training.

**Steps:**
1. Create `app_face_capture/lib/presentation/viewmodels/admin_viewmodel.dart`:
   - `AdminViewModel extends ChangeNotifier`
   - `bool _authenticated = false`
   - `String? _result`
   - `bool _isLoading = false`
   - `bool authenticate(String pin)` — compare against `ApiConstants.adminPin`; set `_authenticated = true` if correct.
   - `Future<void> triggerTraining()` — calls `FaceApiService.triggerTraining()`; sets `_result`; handles errors.
2. Create `app_face_capture/lib/presentation/views/admin_screen.dart`:
   - If `!_authenticated`: show PIN entry field + "Unlock" button.
   - If `_authenticated`: show "Trigger Training Now" button + result display.
   - On wrong PIN: show "Incorrect PIN" message (no lockout).
3. Write tests in `app_face_capture/test/admin_viewmodel_test.dart`:
   - Correct PIN sets `_authenticated = true`.
   - Wrong PIN leaves `_authenticated = false`.
   - `triggerTraining()` calls service and updates `_result`.
4. Run `flutter test test/admin_viewmodel_test.dart`.
5. Run `flutter analyze`.
6. Commit: `feat(app): add AdminViewModel + AdminScreen with PIN auth`

**Acceptance:** PIN gate works; training trigger works; tests pass; no analysis errors.

---

### Task 19: Update `HomeScreen`, `UploadScreen`, and `app_router.dart`

**Goal:** Wire all new screens into the app — settings icon, long-press admin entry, method badge, new routes.

**Steps:**
1. Update `app_face_capture/lib/presentation/views/home_screen.dart`:
   - Add settings ⚙ `IconButton` in `AppBar` → navigates to `/settings`.
   - Add `GestureDetector` wrapping the app logo with `onLongPress` → navigates to `/admin`.
2. Update `app_face_capture/lib/presentation/views/upload_screen.dart`:
   - Show a small badge/chip indicating the active upload method: "Via Server" or "Direct Supabase".
   - Read method from `SettingsViewModel` via `Provider`.
   - Pass `method` to `UploadViewModel` (or `FaceRepository`) when starting upload.
3. Update `app_face_capture/lib/routing/app_router.dart`:
   - Add route `/settings` → `SettingsScreen`.
   - Add route `/admin` → `AdminScreen`.
4. Ensure `SettingsViewModel` is provided at the app level in `main.dart` or `app.dart`.
5. Run `flutter analyze`.
6. Run `flutter test` (all tests).
7. Commit: `feat(app): wire settings + admin routes, upload method badge on UploadScreen`

**Acceptance:** Settings and admin routes navigable; method badge visible on UploadScreen; all tests pass.

---

### Task 20: Write app_face_capture test suite (fill gaps)

**Goal:** Ensure comprehensive test coverage across all new Flutter components.

**Steps:**
1. Review existing tests; fill any gaps:
   - `test/upload_viewmodel_test.dart` — verify state transitions: idle → uploading → checking → success/failed for both UploadMethods.
   - `test/settings_viewmodel_test.dart` — persist/load, health check.
   - `test/admin_viewmodel_test.dart` — PIN logic, training trigger.
   - `test/face_repository_test.dart` — routing by UploadMethod.
   - `test/supabase_storage_service_test.dart` — upload path, error handling.
2. Run full test suite: `flutter test --coverage`.
3. Fix any failures.
4. Run `flutter analyze` — zero errors.
5. Commit: `test(app): complete test suite for app_face_capture restructure`

**Acceptance:** All tests pass; `flutter analyze` clean; output pristine.
