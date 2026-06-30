# Project Restructuring Design Spec
**Date:** 2026-06-29  
**Scope:** `ai_server/` (Python/FastAPI) + `app_face_capture/` (Flutter)  
**Approach:** Server-first sequential — fix and restructure `ai_server` completely, then enhance `app_face_capture`.

---

## 1. Context & Goals

The server (`ai_server`) is the AI engine and API gateway mediating between the Flutter app, Supabase, and ESP32 hardware. The Flutter app (`app_face_capture`) captures face photos for student/instructor registration.

### Problems Being Solved

| # | Problem | Module |
|---|---|---|
| 1 | `get_pending_queue_items()` returns `[]` in Supabase mode — `/train-now` is fully broken | `ai_server` |
| 2 | Supabase image URLs fed to `cv2.imread()` — returns `None` silently during training | `ai_server` |
| 3 | `match_face()` missing `student_id` key — fragile name-as-id workaround in routes | `ai_server` |
| 4 | `main.py` is a 341-line monolith mixing routing, business logic, and legacy endpoints | `ai_server` |
| 5 | `database.py` conflates SQLite ORM model definitions with the routing/delegation layer | `ai_server` |
| 6 | `/train-now` is fully public — documented as admin-only but has zero authentication | `ai_server` |
| 7 | `.pkl` file re-read from disk on every `/verify` request — performance bottleneck | `ai_server` |
| 8 | Option 2 (direct Supabase upload) not implemented in the Flutter app | `app_face_capture` |
| 9 | No admin UI for triggering model training | `app_face_capture` |
| 10 | Backup/temp files committed to working tree | `app_face_capture` |
| 11 | Non-atomic `upsert_user` — race condition on concurrent registrations | `ai_server` |
| 12 | `pandas` is an unused dependency in `requirements.txt` | `ai_server` |
| 13 | `README.md` does not reflect Supabase architecture or new endpoints | `ai_server` |

### Out of Scope
- Redis / distributed embedding cache
- Background queue worker / cron job (admin triggers manually)
- User authentication in Flutter (admin PIN only)
- Admin web dashboard
- ESP32 firmware changes
- Moving embeddings from `.pkl` to Supabase DB

---

## 2. `ai_server` — New Architecture

### 2.1 Folder Structure

```
ai_server/
├── app/
│   ├── main.py              # Thin: FastAPI init + router registration only (~30 lines)
│   ├── config.py            # Unchanged
│   ├── schemas.py           # NEW: all Pydantic request/response models
│   ├── dependencies.py      # NEW: X-Admin-Key auth guard, FaceProcessor DI
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── registration.py  # POST /register, GET /register/status/{student_id}
│   │   ├── training.py      # POST /train-now (admin-guarded)
│   │   ├── verification.py  # POST /verify
│   │   ├── logs.py          # GET /logs
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── users.py     # Legacy (deprecated): /v1/users, /v1/users/{id}/images, /v1/train
│   ├── services/
│   │   ├── __init__.py
│   │   ├── registration_service.py  # Image upload, queue entry creation, embedding ingestion
│   │   ├── training_service.py      # Process pending queue, update .pkl, invalidate cache
│   │   └── verification_service.py  # Face match + attendance log
│   ├── database.py          # Routing layer only — no ORM model definitions
│   ├── models.py            # NEW: SQLAlchemy ORM model classes (User, RegistrationQueue, CheckInLog)
│   ├── supabase_client.py   # Fixed (see section 3)
│   ├── face_processor.py    # Fixed: use image_utils.decode_image_from_source()
│   ├── matcher.py           # Fixed: student_id key + in-memory cache
│   ├── trainer.py           # Retired: stub only, kept for reference, not imported
│   └── utils/
│       └── image_utils.py   # NEW: decode_image_bytes, decode_image_from_source (URL-aware)
├── requirements.txt         # pandas removed
├── .env.example             # NEW: template for all required env vars
└── README.md                # Updated: Supabase architecture, new endpoints, hybrid mode
```

### 2.2 Layer Responsibilities

| Layer | Files | Rule |
|---|---|---|
| **Route** | `routers/*.py` | HTTP in/out only — validate input, call one service, return response |
| **Service** | `services/*.py` | Business logic — orchestrates DB calls, processor, matcher |
| **Data Access** | `database.py`, `supabase_client.py` | Storage only — no business rules |
| **Domain** | `matcher.py`, `face_processor.py` | Pure AI logic — no HTTP, no DB |
| **Shared** | `schemas.py`, `dependencies.py`, `utils/` | Cross-cutting concerns |

### 2.3 `main.py` After Restructuring

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_db
from app.routers import registration, training, verification, logs
from app.routers.v1 import users as v1_users

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # startup only — not at module import time
    yield

app = FastAPI(
    title="Face Recognition AI Server",
    version="5.0.0",
    lifespan=lifespan
)

app.include_router(registration.router)
app.include_router(training.router)
app.include_router(verification.router)
app.include_router(logs.router)
app.include_router(v1_users.router, prefix="/v1", tags=["legacy-v1"])
```

### 2.4 Admin Authentication (`dependencies.py`)

`ADMIN_API_KEY` is read from `.env`. Applied as a FastAPI dependency on `POST /train-now` and `POST /v1/train`.

```python
def require_admin(x_admin_key: str = Header(...)):
    if not ADMIN_KEY or x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
```

---

## 3. Critical Bug Fixes

### Bug 1 — `get_pending_queue_items()` always returns `[]` in Supabase mode

Fix in `supabase_client.py`: query the `registration_queue` table with `.eq("status", "pending")` instead of returning an empty list.

### Bug 2 — `cv2.imread()` called on Supabase HTTPS URLs

New file `utils/image_utils.py`:

```python
def decode_image_from_source(source: str) -> np.ndarray | None:
    """Read an image from a local file path or an HTTPS URL."""
    if source.startswith("http://") or source.startswith("https://"):
        resp = requests.get(source, timeout=10)
        resp.raise_for_status()
        arr = np.frombuffer(resp.content, np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return cv2.imread(source)

def decode_image_bytes(data: bytes) -> np.ndarray | None:
    arr = np.frombuffer(data, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)
```

`face_processor.py`'s `decode_image_path()` delegates to `decode_image_from_source()`.
`decode_base64_image()` moves from `trainer.py` to `image_utils.py`.

### Bug 3 — `match_face()` missing `student_id` key

`training_service.py` stores embeddings with an explicit `student_id` field:
```python
{"user_id": student_id, "student_id": student_id, "name": student_id, "embeddings": emb_list}
```

`matcher.py`'s `match_face()` returns `student_id` directly — the name-as-id hack in `main.py` is removed.

### Bonus — Non-atomic `upsert_user` race condition

Fix in `supabase_client.py`: use Supabase native upsert with `on_conflict="student_id"` for a single atomic operation.

---

## 4. Matcher In-Memory Cache

```python
_cache: list | None = None
_cache_mtime: float = 0.0

def load_embeddings() -> list:
    global _cache, _cache_mtime
    if not EMBEDDINGS_PATH.exists():
        return []
    mtime = EMBEDDINGS_PATH.stat().st_mtime
    if _cache is None or mtime != _cache_mtime:
        with open(EMBEDDINGS_PATH, "rb") as f:
            _cache = pickle.load(f)
        _cache_mtime = mtime
    return _cache

def invalidate_cache() -> None:
    global _cache
    _cache = None  # called by training_service.py after save_embeddings()
```

- Normal operation: `.pkl` loaded once into memory, served from RAM on every `/verify`
- After training: `training_service.py` calls `invalidate_cache()` — next request reloads
- No external dependency required

---

## 5. `app_face_capture` — New Architecture

### 5.1 Changes to Folder Structure

```
lib/
├── core/
│   └── constants/
│       └── storage_constants.dart         # NEW: Supabase bucket name, image path pattern
├── data/
│   ├── repositories/
│   │   └── face_repository.dart           # Updated: routes by UploadMethod
│   └── services/
│       ├── face_api_service.dart          # Unchanged (Option 1 — via server)
│       └── supabase_storage_service.dart  # NEW (Option 2 — direct Supabase)
├── presentation/
│   ├── viewmodels/
│   │   ├── upload_viewmodel.dart          # Unchanged (backup/temp files deleted)
│   │   ├── settings_viewmodel.dart        # NEW: persist UploadMethod to SharedPreferences
│   │   └── admin_viewmodel.dart           # NEW: PIN auth + train trigger
│   ├── views/
│   │   ├── home_screen.dart               # Updated: settings icon + long-press admin entry
│   │   ├── upload_screen.dart             # Updated: active method badge
│   │   ├── settings_screen.dart           # NEW: method toggle + server URL field
│   │   └── admin_screen.dart              # NEW: PIN prompt + train button
└── routing/
    └── app_router.dart                    # Updated: /settings and /admin routes
```

### 5.2 Files to Delete

- `lib/presentation/viewmodels/upload_viewmodel.dart.backup`
- `lib/presentation/viewmodels/upload_viewmodel.dart.old`
- `lib/presentation/viewmodels/upload_viewmodel_temp.dart`
- `lib/presentation/viewmodels/upload_viewmodel_debug.txt`
- `lib/data/repositories/face_repository.dart.backup`

### 5.3 New Dependencies (`pubspec.yaml`)

```yaml
supabase_flutter: ^2.0.0
shared_preferences: ^2.2.0
```

### 5.4 `UploadMethod` Enum

```dart
enum UploadMethod { viaServer, directSupabase }
```

Defined in `core/constants/storage_constants.dart`.

### 5.5 `FaceRepository` Update

```dart
Future<RegistrationResponse> uploadPhotos(
  String studentId,
  List<File> images,
  UploadMethod method,
) async {
  return switch (method) {
    UploadMethod.viaServer       => _uploadViaServer(studentId, images),
    UploadMethod.directSupabase  => _uploadDirectToSupabase(studentId, images),
  };
}
```

`checkStatus()` only applies to `viaServer` mode — `directSupabase` resolves immediately.

### 5.6 `SupabaseStorageService`

- Uploads each image to Supabase Storage bucket
- Path: `registrations/{studentId}/{uuid}.jpg`
- Returns a `RegistrationResponse`-compatible result (uniform interface with Option 1)
- No status polling: result is synchronous (success or per-image failure)

### 5.7 `AdminScreen`

- Entry: long-press on app logo on `HomeScreen` (hidden from normal navigation)
- Route: `/admin` (go_router, not in nav bar)
- PIN stored as a compile-time constant in `api_constants.dart`
- On correct PIN: shows "Trigger Training Now" button
- Calls `FaceApiService.triggerTraining()` with `X-Admin-Key` header
- Displays result: processed students count or error message

### 5.8 `SettingsScreen`

- Toggle: "Upload via Server API" / "Upload directly to Supabase"
- Server base URL field (editable, persisted)
- Note when `directSupabase` active: "Images uploaded directly. Training must be triggered separately by an admin."
- Health check performed on server URL save
- All values persisted via `SharedPreferences`

---

## 6. Data Flows

### Flow A — Registration via Server (Option 1)

```
App (viaServer)
  FaceRepository → FaceApiService.register()
    POST /register ──────────────────────────► registration_service.py
                                                 upsert_user()       → Supabase users (atomic)
                                                 upload_image()      → Supabase Storage
                                                 insert_queue_item() → registration_queue
    {status: "pending"} ◄───────────────────

  UploadViewModel._pollStatus() every 2s (max 60s)
    GET /register/status/{id} ───────────────►
    {status: "pending"|"completed"} ◄────────

  [Admin triggers POST /train-now to process queue]
```

### Flow B — Registration Direct to Supabase (Option 2)

```
App (directSupabase)
  FaceRepository → SupabaseStorageService.uploadPhotos()
    Upload images directly ───────────────────► Supabase Storage
    Path: registrations/{studentId}/{uuid}.jpg
    Result: success/failure per image (synchronous, no polling)

  [Admin uses DB-driven ingestion for training — no queue entry created]
```

### Flow C — Face Verification (ESP32)

```
ESP32
  POST /verify (multipart or base64) ──────────► verification_service.py
                                                   decode_image_from_source() [URL-aware]
                                                   extract_face_embedding()
                                                   match_face()               [RAM cache]
                                                   insert_log()             → check_in_logs
  {match, student_id, similarity, timestamp} ◄──
```

### Flow D — Admin Training Trigger

```
App (admin_screen, correct PIN)
  AdminViewModel → FaceApiService.triggerTraining()
    POST /train-now
    Header: X-Admin-Key: <secret> ───────────► dependencies.py verifies key
                                                training_service.py
                                                  get_pending_queue_items() → Supabase (fixed)
                                                  decode_image_from_source() (URL-aware, fixed)
                                                  extract_face_embedding()
                                                  save_embeddings() + invalidate_cache()
    {processed_students, total_pending} ◄────
```

---

## 7. Error Handling

| Scenario | Server | App |
|---|---|---|
| No face detected in image | Mark queue item `failed`, continue batch | Poll returns `failed` → "No face detected" |
| Supabase unreachable | 503 with detail | Retry button; Option 2 shows "Switch to server mode" hint |
| `/train-now` wrong admin key | 401 Unauthorized | Admin screen: "Incorrect key" (no lockout) |
| Upload timeout Option 1 | Queue stays `pending` | After 60s: "Images uploaded. Training pending — admin will process soon." |
| Option 2 partial failure | Per-image error | "3/5 uploaded. 2 failed." with retry option |
| Invalid/corrupt image | Skip + mark `failed` | Reflected in status poll |
| Server URL misconfigured | — | Settings screen highlights URL field; health check on save |

---

## 8. Testing

### `ai_server` (pytest + httpx, SQLite fallback mode)

| File | Coverage |
|---|---|
| `tests/test_registration.py` | POST /register: happy path, missing fields, empty image |
| `tests/test_training.py` | POST /train-now: valid queue, empty queue, missing auth, wrong auth |
| `tests/test_verification.py` | POST /verify: match found, no face, no match, base64 path |
| `tests/test_services.py` | Unit tests per service function with mocked DB |
| `tests/test_matcher.py` | Cache invalidation, mtime-based reload, cosine similarity |

All tests run in SQLite fallback mode. Supabase paths tested with a mock client.

### `app_face_capture` (flutter_test, mocked HTTP)

| File | Coverage |
|---|---|
| `test/upload_viewmodel_test.dart` | idle → uploading → checking → success/failed transitions |
| `test/settings_viewmodel_test.dart` | Persist/load UploadMethod from SharedPreferences |
| `test/admin_viewmodel_test.dart` | Correct PIN succeeds; wrong PIN stays locked |
| `test/face_repository_test.dart` | Routes to correct service by UploadMethod |
| `test/supabase_storage_service_test.dart` | Upload path construction, error handling |

---

## 9. Implementation Order

### Phase 1 — `ai_server`
1. Create `models.py` (extract ORM models from `database.py`)
2. Create `utils/image_utils.py` (URL-aware decoder + bytes decoder)
3. Fix `supabase_client.py` (Bug 1 + atomic upsert)
4. Fix `matcher.py` (Bug 3 + in-memory cache)
5. Fix `face_processor.py` (Bug 2 — delegate to `image_utils`)
6. Create `schemas.py` (extract Pydantic models from `main.py`)
7. Create `dependencies.py` (admin auth guard)
8. Create `services/` layer (extract business logic from `main.py`)
9. Create `routers/` (split routes, add `/v1/` prefix for legacy)
10. Slim down `main.py` to ~30 lines
11. Update `requirements.txt`, create `.env.example`, update `README.md`
12. Write tests

### Phase 2 — `app_face_capture`
1. Delete backup/temp files
2. Add `supabase_flutter` + `shared_preferences` to `pubspec.yaml`
3. Create `storage_constants.dart`
4. Create `SupabaseStorageService`
5. Update `FaceRepository` (UploadMethod routing)
6. Create `SettingsViewModel` + `SettingsScreen`
7. Create `AdminViewModel` + `AdminScreen`
8. Update `HomeScreen` (settings icon + long-press admin entry)
9. Update `UploadScreen` (active method badge)
10. Update `app_router.dart`
11. Write tests
