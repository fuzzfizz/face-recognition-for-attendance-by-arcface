# Design Spec: Face Registration & Administration System Refactoring

Comprehensive redesign of the face registration workflow, access controls, scheduled training, name collection, and administration integration.

## 1. Objectives & Overview
This specification addresses 6 distinct problems identified in [Problem.md](file:///D:/AIproject/Problem.md):
1. Transition from active status polling to an asynchronous queue with status checking on-demand.
2. Fix navigation back buttons by using `context.push()` instead of `context.go()` and implement web URL route guards.
3. Protect settings and admin views behind a unified Admin PIN dialog.
4. Collect the Student Name on registration and persist it in the database.
5. Perform immediate face detection on upload (fail-fast) and run scheduled training at configurable times.
6. Relocate "Force Training" to the Web Dashboard and resolve the 422 error on the `/train-now` API.

---

## 2. Component Design & Changes

### A. Mobile App (Flutter)

#### 1. Navigation & Route Guarding
- **Navigation Stack:** Update routing transitions from `context.go()` to `context.push()` across [home_screen.dart](file:///D:/AIproject/app_face_capture/lib/presentation/views/home_screen.dart), [capture_screen.dart](file:///D:/AIproject/app_face_capture/lib/presentation/views/capture_screen.dart), and [review_screen.dart](file:///D:/AIproject/app_face_capture/lib/presentation/views/review_screen.dart).
- **Session Authentication:** Store an `isAdminAuthenticated` session boolean in [settings_viewmodel.dart](file:///D:/AIproject/app_face_capture/lib/presentation/viewmodels/settings_viewmodel.dart) or similar.
- **Route Guard:** Update [app_router.dart](file:///D:/AIproject/app_face_capture/lib/routing/app_router.dart) to check session authentication before resolving `/admin` or `/settings`. Redirect to `/` if unauthorized.
- **PIN Dialog:** Implement a generic `PinInputDialog` in `app_face_capture`. Prompt the user for the PIN on the home screen when they tap **Settings** or long-press the **Admin** entry point.

#### 2. Student Name Collection
- **Home UI:** Add a required `Student Name` text field to [home_screen.dart](file:///D:/AIproject/app_face_capture/lib/presentation/views/home_screen.dart).
- **Pass Arguments:** Pass both `studentId` and `studentName` to `/capture` -> `/review` -> `/upload`.
- **API Form Payload:** Update `UploadViewModel` and `FaceRepository` to accept name. Update `FaceApiService.register()` to include the `name` field in the multipart request body.

#### 3. Status Checking
- **Status Button:** Add a **Check Status** button next to **Start Capture** on [home_screen.dart](file:///D:/AIproject/app_face_capture/lib/presentation/views/home_screen.dart) (requires only Student ID).
- **Dialog Info:** Ping `/register/status/{id}` via `FaceRepository.checkStatus()` and show a dialog with the status:
  - `completed`: Success info.
  - `pending`: Dynamic message from server (e.g. `"Waiting for AI processing. Scheduled updates run daily at 19:00."`).
  - `failed`: Show error reason.
  - Not found: Show `"No registration found."`

#### 4. Upload Finish Screen
- Remove status polling loop from `UploadViewModel` on upload completion. Immediately transition to `success` once photos are sent, prompting the user: `"Upload successful! Your photos are queued for processing. Please check back later."`
- Remove the "Force Training" section from [admin_screen.dart](file:///D:/AIproject/app_face_capture/lib/presentation/views/admin_screen.dart).

---

### B. AI Server (FastAPI)

#### 1. API Changes
- **Register Endpoint:** In [registration.py](file:///D:/AIproject/ai_server/app/routers/registration.py), accept `name: str = Form(None)`.
- **Database Upsert:** Update `upsert_user` in [database.py](file:///D:/AIproject/ai_server/app/database.py) and [supabase_client.py](file:///D:/AIproject/ai_server/app/supabase_client.py) to save `name` into the `users` table.

#### 2. Immediate Upload Face Validation
- In `register_images` in [registration_service.py](file:///D:/AIproject/ai_server/app/services/registration_service.py), decode each upload. If the face processor detects 0 faces, abort and return a `400 Bad Request` immediately.

#### 3. Self-Scheduling Background Loop
- Read `TRAINING_SCHEDULE_TIMES` (e.g. `"12:00,19:00"`) from `.env`.
- In [main.py](file:///D:/AIproject/ai_server/app/main.py)'s lifespan startup, launch an `asyncio` loop task that wakes up every minute. If local server time matches one of the times, run `process_pending_queue()`.
- Return the configured times in the status API message.

#### 4. Fix `/train-now` 422 Error
- Update `require_admin` in [dependencies.py](file:///D:/AIproject/ai_server/app/dependencies.py) to accept `x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")`. If missing or mismatch, raise HTTP 401 instead of letting FastAPI fail validation with 422.

---

### C. Web Dashboard (PHP)

#### 1. Configuration
- Update `web_dashboard/config.php` and `config.example.php` to define `AI_SERVER_URL` and `ADMIN_API_KEY`.

#### 2. Train Endpoint (`api/train.php`)
- Implement a PHP endpoint that sends an authorized POST request to `AI_SERVER_URL/train-now` using curl/stream context and forwards the JSON result.

#### 3. Frontend Controls
- Add a **Force Training Now** button on the **Queue** tab in [index.php](file:///D:/AIproject/web_dashboard/index.php). Securely trigger `api/train.php` and show results/errors.
