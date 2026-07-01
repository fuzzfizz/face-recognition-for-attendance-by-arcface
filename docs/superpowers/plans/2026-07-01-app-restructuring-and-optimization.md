# Face Registration & Administration System Refactoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement navigation updates (back stack), unified PIN lock, student name collection, server-side fail-fast face validation, background training scheduling, dynamic status checking, and web dashboard force training controls.

**Architecture:** We use an auth-guarded routing setup in `GoRouter` using `push` navigation, collect names and persist them across DB modes, perform fast face analysis on upload, self-schedule background training tasks, and provide a secure dashboard-to-API trigger.

**Tech Stack:** Flutter / Dart, FastAPI / Python, PHP / JS

## Global Constraints

- Avoid hardcoding any API keys or PINs in the client app logic.
- Maintain compatibility with both SQLite and Supabase database layers.
- Avoid external Python scheduler dependencies (use Python's `asyncio` loop).
- Ensure all Flutter tests pass.

---

### Task 1: Mobile App Navigation & Route Guarding

**Files:**
- Modify: `app_face_capture/lib/routing/app_router.dart`
- Modify: `app_face_capture/lib/presentation/viewmodels/settings_viewmodel.dart`
- Modify: `app_face_capture/lib/presentation/views/home_screen.dart`
- Create: `app_face_capture/lib/presentation/views/pin_dialog.dart`

**Interfaces:**
- Consumes: `appRouter`, `SettingsViewModel`
- Produces: `context.push()` navigation, Route guard for `/settings` and `/admin`, unified PIN Dialog

- [ ] **Step 1: Create PinInputDialog Widget**

Create `app_face_capture/lib/presentation/views/pin_dialog.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:app_face_capture/core/constants/api_constants.dart';

class PinInputDialog extends StatefulWidget {
  const PinInputDialog({super.key});

  @override
  State<PinInputDialog> createState() => _PinInputDialogState();
}

class _PinInputDialogState extends State<PinInputDialog> {
  final _controller = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  bool _isIncorrect = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Admin Authentication'),
      content: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Please enter the Admin PIN to proceed:'),
            const SizedBox(height: 16),
            TextFormField(
              controller: _controller,
              obscureText: true,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Admin PIN',
                border: OutlineInputBorder(),
              ),
              validator: (val) {
                if (val == null || val.isEmpty) return 'PIN required';
                if (val != ApiConstants.adminPin) {
                  setState(() => _isIncorrect = true);
                  return 'Incorrect PIN';
                }
                return null;
              },
            ),
            if (_isIncorrect) ...[
              const SizedBox(height: 8),
              const Text('Incorrect PIN. Try again.', style: TextStyle(color: Colors.red)),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () {
            if (_formKey.currentState!.validate()) {
              Navigator.of(context).pop(true);
            }
          },
          child: const Text('Unlock'),
        ),
      ],
    );
  }
}
```

- [ ] **Step 2: Add Session Authentication to SettingsViewModel**

In [settings_viewmodel.dart](file:///D:/AIproject/app_face_capture/lib/presentation/viewmodels/settings_viewmodel.dart):
Add authentication state:
```dart
  bool _isAdminAuthenticated = false;
  bool get isAdminAuthenticated => _isAdminAuthenticated;

  void authenticateAdmin(bool authenticated) {
    _isAdminAuthenticated = authenticated;
    notifyListeners();
  }
```

- [ ] **Step 3: Update app_router.dart for Guards**

In [app_router.dart](file:///D:/AIproject/app_face_capture/lib/routing/app_router.dart):
Implement a redirect route guard for `/settings` and `/admin`:
```dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:app_face_capture/presentation/viewmodels/settings_viewmodel.dart';
// ... other imports ...

final GoRouter appRouter = GoRouter(
  initialLocation: '/',
  redirect: (context, state) {
    final settingsModel = context.read<SettingsViewModel>();
    final path = state.uri.path;
    
    if ((path == '/admin' || path == '/settings') && !settingsModel.isAdminAuthenticated) {
      return '/'; // Redirect to home if not unlocked
    }
    return null;
  },
  routes: [
    // Keep routes unchanged, just use the redirect
```

- [ ] **Step 4: Update home_screen.dart Navigation and Dialog**

In [home_screen.dart](file:///D:/AIproject/app_face_capture/lib/presentation/views/home_screen.dart):
Update `build` to show PIN dialog before Settings/Admin navigation and use `context.push()`:
```dart
import 'package:app_face_capture/presentation/views/pin_dialog.dart';
import 'package:app_face_capture/presentation/viewmodels/settings_viewmodel.dart';
import 'package:provider/provider.dart';

// ...
  void _navigateToSettings() async {
    final authenticated = await showDialog<bool>(
      context: context,
      builder: (context) => const PinInputDialog(),
    );
    if (authenticated == true && mounted) {
      context.read<SettingsViewModel>().authenticateAdmin(true);
      context.push('/settings');
    }
  }

  void _navigateToAdmin() async {
    final authenticated = await showDialog<bool>(
      context: context,
      builder: (context) => const PinInputDialog(),
    );
    if (authenticated == true && mounted) {
      context.read<SettingsViewModel>().authenticateAdmin(true);
      context.push('/admin');
    }
  }

  // Update capture navigation:
  void _startCapture() {
    if (_formKey.currentState!.validate()) {
      context.pushNamed('capture', extra: _studentIdController.text.trim());
    }
  }

  // Update AppBar actions settings button and Admin long press:
  // onPressed: _navigateToSettings
  // onLongPress: _navigateToAdmin
```

- [ ] **Step 5: Run tests**
Run: `flutter test` in `app_face_capture`
Expected: PASS

- [ ] **Step 6: Commit**
```bash
git add app_face_capture/
git commit -m "feat: implement navigation updates, PIN lock, and route guards"
```

---

### Task 2: Student Name Field & Database Integration

**Files:**
- Modify: `app_face_capture/lib/presentation/views/home_screen.dart`
- Modify: `app_face_capture/lib/routing/app_router.dart`
- Modify: `app_face_capture/lib/presentation/views/capture_screen.dart`
- Modify: `app_face_capture/lib/presentation/views/review_screen.dart`
- Modify: `app_face_capture/lib/presentation/views/upload_screen.dart`
- Modify: `app_face_capture/lib/presentation/viewmodels/upload_viewmodel.dart`
- Modify: `app_face_capture/lib/data/repositories/face_repository.dart`
- Modify: `app_face_capture/lib/data/services/face_api_service.dart`
- Modify: `ai_server/app/routers/registration.py`
- Modify: `ai_server/app/services/registration_service.py`
- Modify: `ai_server/app/database.py`
- Modify: `ai_server/app/supabase_client.py`

**Interfaces:**
- Consumes: `/register` API, `upsert_user` DB APIs, Kiosk Capture flow
- Produces: Name parameter stored in DB on registration.

- [ ] **Step 1: Update home_screen.dart with Student Name field**

In [home_screen.dart](file:///D:/AIproject/app_face_capture/lib/presentation/views/home_screen.dart):
Add a Name field and pass it in state arguments:
```dart
  final _studentNameController = TextEditingController();
  
  // Inside disposing, dispose _studentNameController
  
  // In _startCapture:
  void _startCapture() {
    if (_formKey.currentState!.validate()) {
      context.pushNamed(
        'capture', 
        extra: {
          'studentId': _studentIdController.text.trim(),
          'studentName': _studentNameController.text.trim(),
        }
      );
    }
  }

  // Inside Form Column, add:
  TextFormField(
    controller: _studentNameController,
    decoration: const InputDecoration(
      labelText: 'Student Name',
      prefixIcon: Icon(Icons.person),
      border: OutlineInputBorder(),
    ),
    validator: (value) {
      if (value == null || value.trim().isEmpty) return 'Please enter student name';
      return null;
    },
  )
```

- [ ] **Step 2: Update capture, review, and upload screen routing**

In [app_router.dart](file:///D:/AIproject/app_face_capture/lib/routing/app_router.dart):
```dart
    GoRoute(
      path: '/capture',
      name: 'capture',
      builder: (context, state) {
        final args = state.extra as Map<String, dynamic>;
        return CaptureScreen(
          studentId: args['studentId'] as String,
          studentName: args['studentName'] as String,
        );
      },
    ),
```

In [capture_screen.dart](file:///D:/AIproject/app_face_capture/lib/presentation/views/capture_screen.dart):
Add `final String studentName;` constructor parameter and pass it to ReviewScreen:
```dart
context.push('/review', extra: {
  'studentId': widget.studentId,
  'studentName': widget.studentName,
  'imagePaths': _capturedImages,
});
```

In [review_screen.dart](file:///D:/AIproject/app_face_capture/lib/presentation/views/review_screen.dart):
Add `final String studentName;` constructor parameter and pass it to UploadScreen:
```dart
context.push('/upload', extra: {
  'studentId': widget.studentId,
  'studentName': widget.studentName,
  'imagePaths': widget.imagePaths,
});
```

In [upload_screen.dart](file:///D:/AIproject/app_face_capture/lib/presentation/views/upload_screen.dart):
Add `final String studentName;` constructor parameter and pass it to `UploadViewModel`:
```dart
      create: (_) => UploadViewModel(
        repository: FaceRepository(),
        studentId: studentId,
        studentName: studentName,
        imagePaths: imagePaths,
        method: settingsViewModel.uploadMethod,
      )..startUpload(),
```

- [ ] **Step 3: Update UploadViewModel and FaceRepository API Clients**

In [upload_viewmodel.dart](file:///D:/AIproject/app_face_capture/lib/presentation/viewmodels/upload_viewmodel.dart):
```dart
  final String studentName;
  // in constructor: required this.studentName,
  // in startUpload():
  await _repository.uploadPhotos(studentId, studentName, files, method);
```

In [face_repository.dart](file:///D:/AIproject/app_face_capture/lib/data/repositories/face_repository.dart):
```dart
  Future<RegistrationResponse> uploadPhotos(
    String studentId,
    String studentName,
    List<File> images,
    UploadMethod method,
  ) async {
    // For directSupabase: we also save user record to Supabase, but wait, Supabase service can upsert student
    // For viaServer:
    return await _apiService.register(studentId, studentName, batch);
```

In [face_api_service.dart](file:///D:/AIproject/app_face_capture/lib/data/services/face_api_service.dart):
```dart
  Future<RegistrationResponse> register(String studentId, String studentName, List<File> images) async {
    final uri = Uri.parse('$_baseUrl${ApiConstants.register}');
    final request = http.MultipartRequest('POST', uri);
    request.fields['student_id'] = studentId;
    request.fields['name'] = studentName;
```

- [ ] **Step 4: Update Backend endpoints and Database helpers**

In [registration.py](file:///D:/AIproject/ai_server/app/routers/registration.py):
```python
@router.post("/register", response_model=RegisterResponse)
async def register(
    student_id: str = Form(...),
    name: str = Form(None),
    files: List[UploadFile] = File(...),
):
    return await registration_service.register_images(student_id, name, files)
```

In [registration_service.py](file:///D:/AIproject/ai_server/app/services/registration_service.py):
```python
async def register_images(student_id: str, name: str, files: List[UploadFile]) -> dict:
    user = upsert_user(student_id, name)
```

In [database.py](file:///D:/AIproject/ai_server/app/database.py):
```python
def upsert_user(student_id: str, name: str = None):
    if supabase_available():
        return sb_upsert_user(student_id, name)
    else:
        # SQLite
        user = session.query(_UserModel).filter(_UserModel.student_id == student_id).first()
        if not user:
            user = _UserModel(student_id=student_id, name=name)
            # add, commit, etc.
        elif name:
            user.name = name
            session.commit()
```

In [supabase_client.py](file:///D:/AIproject/ai_server/app/supabase_client.py):
```python
def upsert_user(student_id: str, name: str = None) -> Optional[Dict[str, Any]]:
    # ...
    response = sb.table("users").upsert(
        {"student_id": student_id, "name": name}, on_conflict="student_id"
    ).execute()
```

- [ ] **Step 5: Run tests**
Run: `flutter test` in `app_face_capture` and `pytest` in `ai_server`
Expected: PASS

- [ ] **Step 6: Commit**
```bash
git add app_face_capture/ ai_server/
git commit -m "feat: implement student name collection, API parameters, and database upserts"
```

---

### Task 3: Lightweight Face Verification & Non-blocking Status checking

**Files:**
- Modify: `ai_server/app/services/registration_service.py`
- Modify: `ai_server/app/config.py`
- Modify: `ai_server/.env`
- Modify: `app_face_capture/lib/presentation/viewmodels/upload_viewmodel.dart`
- Modify: `app_face_capture/lib/presentation/views/upload_screen.dart`

**Interfaces:**
- Consumes: FaceProcessor
- Produces: HTTP 400 when face missing, dynamic schedule pending messages, instant success screen transitions

- [ ] **Step 1: Add immediate face validation check on upload**

In [registration_service.py](file:///D:/AIproject/ai_server/app/services/registration_service.py):
Import `get_face_processor`. In `register_images`:
```python
    from app.face_processor import get_face_processor
    processor = get_face_processor()

    # Pre-read and check faces first:
    decoded_images = []
    for file in files:
        file_bytes = await file.read()
        if not file_bytes:
            continue
        cv_img = processor.decode_image(file_bytes)
        if cv_img is None:
            raise HTTPException(status_code=400, detail="Cannot parse one of the image files.")
        faces = processor.app.get(cv_img)
        if not faces:
            raise HTTPException(status_code=400, detail=f"No face detected in photo ({file.filename}). Please align your face in the camera.")
        # Store for saving
        decoded_images.append((file.filename, file_bytes))

    # Then continue with saving the verified images to DB/queue:
    # Use decoded_images instead of files list
```

- [ ] **Step 2: Add Configurable schedule info message**

In [config.py](file:///D:/AIproject/ai_server/app/config.py):
```python
TRAINING_SCHEDULE_INFO = os.getenv("TRAINING_SCHEDULE_INFO", "daily at 19:00")
```

In [registration_service.py](file:///D:/AIproject/ai_server/app/services/registration_service.py):
Modify `get_registration_status`:
```python
    from app.config import TRAINING_SCHEDULE_INFO
    # in return dict for pending status:
    return {
        "student_id": student_id,
        "status": "pending",
        "message": f"Waiting for AI processing. Scheduled updates run {TRAINING_SCHEDULE_INFO}."
    }
```

- [ ] **Step 3: Update mobile app to fail-fast and success immediately**

In [upload_viewmodel.dart](file:///D:/AIproject/app_face_capture/lib/presentation/viewmodels/upload_viewmodel.dart):
Remove status polling loop `_pollStatus()`. Once `uploadPhotos` returns, change state to success:
```dart
  Future<void> startUpload() async {
    // ...
    try {
      final files = imagePaths.map((p) => File(p)).toList();
      await _repository.uploadPhotos(studentId, studentName, files, method);
      _uploadedCount = imagePaths.length;
      _state = UploadState.success;
      notifyListeners();
    } catch (e) {
      _state = UploadState.failed;
      _errorMessage = e.toString();
      notifyListeners();
    }
  }
```

In [upload_screen.dart](file:///D:/AIproject/app_face_capture/lib/presentation/views/upload_screen.dart):
Update the success text under `_buildBody`:
```dart
          Text(
            'Upload successful! Your photos are queued for processing.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey[600]),
            textAlign: TextAlign.center,
          ),
```

- [ ] **Step 4: Run tests**
Run: `pytest` and `flutter test`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add ai_server/ app_face_capture/
git commit -m "feat: implement immediate face validation and async upload queue"
```

---

### Task 4: Self-Scheduling Background Loop & `/train-now` Header Fix

**Files:**
- Modify: `ai_server/app/main.py`
- Modify: `ai_server/app/config.py`
- Modify: `ai_server/app/dependencies.py`

**Interfaces:**
- Consumes: `lifespan` FastAPI, `require_admin` dependency
- Produces: Background loop runner, 401 response instead of 422 for unauthorized `/train-now`

- [ ] **Step 1: Update config.py with schedule hours**

In [config.py](file:///D:/AIproject/ai_server/app/config.py):
```python
TRAINING_SCHEDULE_TIMES = os.getenv("TRAINING_SCHEDULE_TIMES", "19:00")
```

- [ ] **Step 2: Add background loop runner in main.py**

In [main.py](file:///D:/AIproject/ai_server/app/main.py):
```python
import asyncio
import datetime
from app.config import TRAINING_SCHEDULE_TIMES

async def run_training_scheduler():
    times = [t.strip() for t in TRAINING_SCHEDULE_TIMES.split(",") if t.strip()]
    if not times:
        print("[Scheduler] No training schedule configured.")
        return

    print(f"[Scheduler] Active. Schedule slots: {times}")
    while True:
        now = datetime.datetime.now()
        current_time_str = now.strftime("%H:%M")
        if current_time_str in times:
            print(f"[Scheduler] Running scheduled queue training at {current_time_str}...")
            try:
                from app.services.training_service import process_pending_queue
                process_pending_queue()
            except Exception as e:
                print(f"[Scheduler] Scheduled training failed: {e}")
            await asyncio.sleep(61)  # Skip remainder of the minute
        else:
            await asyncio.sleep(20)  # Check every 20 seconds
```

Include it in `lifespan` context manager:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler_task = asyncio.create_task(run_training_scheduler())
    yield
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass
```

- [ ] **Step 3: Update require_admin to prevent 422 Header validation error**

In [dependencies.py](file:///D:/AIproject/ai_server/app/dependencies.py):
```python
from typing import Optional

def require_admin(x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")):
    if not ADMIN_KEY or not x_admin_key or x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
```

- [ ] **Step 4: Run tests**
Run: `pytest`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add ai_server/
git commit -m "feat: implement self-scheduling background training and fix 422 API header error"
```

---

### Task 5: Mobile App "Check Status" Feature & Control Cleanup

**Files:**
- Modify: `app_face_capture/lib/presentation/views/home_screen.dart`
- Modify: `app_face_capture/lib/presentation/views/admin_screen.dart`
- Modify: `app_face_capture/lib/presentation/viewmodels/admin_viewmodel.dart`

**Interfaces:**
- Consumes: `/register/status/{id}` via `FaceRepository`
- Produces: UI card/dialog displaying registration status, Removed force-training controls from Kiosk app.

- [ ] **Step 1: Implement Check Status UI on home_screen.dart**

In [home_screen.dart](file:///D:/AIproject/app_face_capture/lib/presentation/views/home_screen.dart):
Add a "Check Status" button next to "Start Capture". Show a dialog indicating status:
```dart
  bool _isCheckingStatus = false;

  void _checkStatus() async {
    final studentId = _studentIdController.text.trim();
    if (studentId.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a Student ID to check status.')),
      );
      return;
    }

    setState(() => _isCheckingStatus = true);
    try {
      final repository = FaceRepository();
      final status = await repository.checkStatus(studentId);
      if (mounted) {
        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: Text('Registration Status'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Student ID: ${status.studentId}'),
                const SizedBox(height: 8),
                Text('Status: ${status.status.toUpperCase()}', style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 12),
                Text(status.message),
              ],
            ),
            actions: [
              TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('OK')),
            ],
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: Text('Error'),
            content: Text('Could not retrieve status: ${e.toString()}'),
            actions: [
              TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('OK')),
            ],
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isCheckingStatus = false);
      }
    }
  }

  // Under the Form buttons row, place:
  Row(
    children: [
      Expanded(
        child: OutlinedButton.icon(
          onPressed: _isCheckingStatus ? null : _checkStatus,
          icon: _isCheckingStatus 
            ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
            : const Icon(Icons.search),
          label: const Text('Check Status'),
        ),
      ),
      const SizedBox(width: 16),
      Expanded(
        child: FilledButton.icon(
          onPressed: _startCapture,
          icon: const Icon(Icons.camera_alt),
          label: const Text('Start Capture'),
        ),
      ),
    ],
  )
```

- [ ] **Step 2: Remove Force Training controls from Kiosk Admin views**

In [admin_screen.dart](file:///D:/AIproject/app_face_capture/lib/presentation/views/admin_screen.dart):
Remove the entire model training triggers section (`Model Training Control` Card and its associated button / loader). Only keep logs, settings redirection, and device status features if any, or general info.

- [ ] **Step 3: Run tests**
Run: `flutter test`
Expected: PASS

- [ ] **Step 4: Commit**
```bash
git add app_face_capture/
git commit -m "feat: implement Check Status UI and remove Force Training from Kiosk app"
```

---

### Task 6: Web Dashboard Integration

**Files:**
- Modify: `web_dashboard/index.php`
- Modify: `web_dashboard/config.example.php`
- Create: `web_dashboard/api/train.php`

**Interfaces:**
- Consumes: PHP curl / POST to AI Server
- Produces: "Force Training Now" button on Queue tab, JSON API trigger endpoint.

- [ ] **Step 1: Update config.example.php**

In [config.example.php](file:///D:/AIproject/web_dashboard/config.example.php):
```php
define('AI_SERVER_URL', 'http://localhost:8000');
define('ADMIN_API_KEY', 'your-secret-admin-key');
```

- [ ] **Step 2: Create api/train.php**

Create `web_dashboard/api/train.php`:
```php
<?php
require_once __DIR__ . '/../config.php';

header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method Not Allowed']);
    exit;
}

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, AI_SERVER_URL . '/train-now');
curl_setopt($ch, CURLOPT_POST, 1);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    'X-Admin-Key: ' . ADMIN_API_KEY,
    'Content-Type: application/json'
]);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($httpCode !== 200) {
    http_response_code($httpCode);
    if ($response) {
        echo $response;
    } else {
        echo json_encode(['error' => 'Failed to reach AI Server']);
    }
    exit;
}

echo $response;
```

- [ ] **Step 3: Add Force Training controls to web index.php**

In [index.php](file:///D:/AIproject/web_dashboard/index.php):
Under the Queue tab filter-bar (`content-queue` element), add a **Force Training** button:
```html
<button class="btn-refresh" style="background:#a78bfa;color:#0f1117" onclick="triggerForceTraining()">⚙️ Force Training Now</button>
```

Add the JavaScript handler in the `<script>` tag:
```javascript
async function triggerForceTraining() {
  if (!confirm('This will process all pending registrations in the queue immediately. Proceed?')) {
    return;
  }
  
  const btn = document.querySelector('[onclick="triggerForceTraining()"]');
  const oldText = btn.textContent;
  btn.textContent = 'Processing...';
  btn.disabled = true;
  
  try {
    const res = await fetch('api/train.php', { method: 'POST' });
    const d = await res.json();
    if (!res.ok) throw new Error(d.detail || d.error || 'Server error');
    
    alert('Training completed successfully! Processed students: ' + (d.processed_students?.join(', ') || 'None'));
    loadQueue();
    loadStats();
  } catch (e) {
    alert('Training failed: ' + e.message);
  } finally {
    btn.textContent = oldText;
    btn.disabled = false;
  }
}
```

- [ ] **Step 4: Commit**
```bash
git add web_dashboard/
git commit -m "feat: add Force Training action and secure API bridge to Web Dashboard"
```
