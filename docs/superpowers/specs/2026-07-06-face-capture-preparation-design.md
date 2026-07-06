# Design Spec: Face Capture Preparation Countdown and Schema Cleanup

## Goals
- Clean up references to the deleted `user_images` table in the backend server (`ai_server`) and its unit tests.
- Remove specific face pose prompts ("Smile naturally", "Turn left/right", etc.) from the Flutter application (`app_face_capture`).
- Introduce an automatic 3-second preparation countdown screen/overlay when the face capture session starts so the user can align their face.
- Display progress-based instructions ("Capturing photo X of 10...") during photo capture.
- Provide a generic, friendly prompt for individual photo retakes.

## Background & Context
The project was previously updated to drop the `user_images` table. However, some references remained in the backend server code (`supabase_client.py`), which will cause issues when deleting students. Additionally, users found the pose-guiding text prompts confusing or unnecessary. Replacing them with an initial preparation phase (countdown) and progress-based guides simplifies the UI and improves user experience.

---

## 1. Backend Schema Clean-up

### Files Modified:
- `ai_server/app/supabase_client.py`
- `ai_server/tests/test_supabase_client.py`

### Changes in `supabase_client.py`:
In the `delete_student_from_supabase` function:
- Remove the block that queries `user_images`.
- Only query `registration_queue` to find the image paths.
- Proceed with deletion of student and queue records and then delete the corresponding files from storage.

```python
def delete_student_from_supabase(student_id: str) -> bool:
    if not is_available():
        return False
    try:
        sb = get_supabase()
        # Fetch paths from registration_queue to delete files
        paths = []
        q_res = sb.table("registration_queue").select("image_path").eq("student_id", student_id).execute()
        paths.extend([row["image_path"] for row in q_res.data if row.get("image_path")])

        # Delete user and queue history first
        sb.table("users").delete().eq("student_id", student_id).execute()
        sb.table("registration_queue").delete().eq("student_id", student_id).execute()

        # Extract filenames and remove from Supabase Storage
        filenames = list(set([p.split("/")[-1] for p in paths if p]))
        if filenames:
            sb.storage.from_(SUPABASE_STORAGE_BUCKET).remove(filenames)

        return True
    except Exception as e:
        print(f"[Supabase] delete_student_from_supabase error: {e}")
        return False
```

### Changes in `test_supabase_client.py`:
- Update `test_delete_student_from_supabase_success` and other related tests.
- Remove references, mocks, and assertions for the `user_images` table query.

---

## 2. Flutter App Face Capture Prep Phase & UI Update

### Files Modified:
- `app_face_capture/lib/presentation/views/capture_screen.dart`
- `app_face_capture/lib/presentation/views/upload_screen.dart`

### Changes in `capture_screen.dart`:

#### State Variables
We will add preparation states inside `_CaptureScreenState`:
```dart
bool _isPreparing = true;
int _countdownSeconds = 3;
Timer? _countdownTimer; // We'll import 'dart:async' if not present
```

#### Camera Initialization & Timer Trigger
Modify `_initCamera` or state setup to start the countdown once the camera is initialized:
```dart
Future<void> _initCamera() async {
  try {
    // Existing camera initialization logic...
    await _cameraController!.initialize();
    
    // Start preparation countdown
    _startPreparationCountdown();
  } catch (e) {
    debugPrint('Camera init error: $e');
  } finally {
    if (mounted) setState(() => _isInitializing = false);
  }
}

void _startPreparationCountdown() {
  _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
    if (!mounted) {
      timer.cancel();
      return;
    }
    setState(() {
      if (_countdownSeconds > 1) {
        _countdownSeconds--;
      } else {
        _isPreparing = false;
        timer.cancel();
      }
    });
  });
}
```

Make sure to cancel `_countdownTimer` in `dispose()`:
```dart
@override
void dispose() {
  _countdownTimer?.cancel();
  _cameraController?.dispose();
  super.dispose();
}
```

#### UI Overlay & Progress Guide
- Disable the Capture Button while `_isPreparing` is true.
- Replace `_getPromptText` in `CaptureScreen` to return:
  ```dart
  String _getPromptText(int count, int total) {
    return 'Capturing photo ${count + 1} of $total';
  }
  ```
- If `_isPreparing` is true, show a centered countdown overlay with instructions:
  - Big text: `$_countdownSeconds` (or `Go!` when transitioning)
  - Subtitle: `"Get ready! Align your face in the frame."`
- The `FaceGuideOverlay` and standard `INSTRUCTION` box will display the updated guide text.

### Changes in `upload_screen.dart`:
- Change `_getPromptText` (used for retakes) to return a generic prompt:
  ```dart
  String _getPromptText(int count) {
    return 'Look straight at the camera to retake';
  }
  ```
