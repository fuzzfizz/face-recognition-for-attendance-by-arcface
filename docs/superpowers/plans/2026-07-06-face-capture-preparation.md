# Face Capture Preparation and Schema Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean up the deleted `user_images` table references in the backend server and introduce a 3-second preparation countdown overlay in the Flutter face capture screen.

**Architecture:** 
- In the backend (`ai_server`), refactor `supabase_client.py` to remove queries to the `user_images` table when deleting students, and update corresponding unit tests.
- In the frontend (`app_face_capture`), add timer-based preparation state and overlay to the face capture screen, replace specific pose instructions with progress-based guides, and update retake prompt strings.

**Tech Stack:** Python (pytest, MagicMock), Dart/Flutter (camera, GoRouter).

## Global Constraints
- Do not affect check-in, verification, or registration queue functionality.
- Ensure all SQLite and PostgreSQL database queries remain syntax-valid and tested.
- Keep the Flutter app tests passing.

---

### Task 1: Backend Database Schema Cleanup

**Files:**
- Modify: `ai_server/app/supabase_client.py:234-262`
- Modify: `ai_server/tests/test_supabase_client.py:146-307`

**Interfaces:**
- Consumes: None (Removes unused table reference)
- Produces: Cleaned `delete_student_from_supabase` function.

- [ ] **Step 1: Modify `supabase_client.py`**
  Open `ai_server/app/supabase_client.py` and replace the `delete_student_from_supabase` function with the following implementation (removing queries to `user_images`):
  ```python
  def delete_student_from_supabase(student_id: str) -> bool:
      if not is_available():
          return False
      try:
          sb = get_supabase()
          # 1. Fetch paths from registration_queue to delete files
          paths = []
          q_res = sb.table("registration_queue").select("image_path").eq("student_id", student_id).execute()
          paths.extend([row["image_path"] for row in q_res.data if row.get("image_path")])

          # 2. Delete user and queue history first
          sb.table("users").delete().eq("student_id", student_id).execute()
          sb.table("registration_queue").delete().eq("student_id", student_id).execute()

          # 3. Extract filenames and remove from Supabase Storage only after successful DB deletion
          filenames = list(set([p.split("/")[-1] for p in paths if p]))
          if filenames:
              sb.storage.from_(SUPABASE_STORAGE_BUCKET).remove(filenames)

          return True
      except Exception as e:
          print(f"[Supabase] delete_student_from_supabase error: {e}")
          return False
  ```

- [ ] **Step 2: Update `test_supabase_client.py`**
  Open `ai_server/tests/test_supabase_client.py` and update the test cases in class `TestDeleteStudentFromSupabase` to remove queries and assertions for `user_images`:
  - Update `test_delete_student_success` to only mock `registration_queue` select query and storage delete.
  - Update `test_delete_student_no_user` to remove `users` mock checks where unnecessary.
  - Make sure mock side effects do not handle `user_images` table.
  Here is the updated class `TestDeleteStudentFromSupabase`:
  ```python
  class TestDeleteStudentFromSupabase:
      def test_delete_student_success(self, mock_sb):
          from app.supabase_client import delete_student_from_supabase, SUPABASE_STORAGE_BUCKET
          
          # Mock database response for registration_queue select image_path
          mock_queue_query = MagicMock()
          mock_queue_query.eq.return_value.execute.return_value.data = [
              {"image_path": "https://supabase.co/storage/v1/object/public/bucket/img3.jpg"}
          ]
          
          # Delete queries
          mock_delete_query1 = MagicMock()
          mock_delete_query1.eq.return_value.execute.return_value = MagicMock()
          
          mock_delete_query2 = MagicMock()
          mock_delete_query2.eq.return_value.execute.return_value = MagicMock()

          # Storage mock
          mock_bucket = MagicMock()
          mock_sb.storage.from_.return_value = mock_bucket

          # Wire mock_sb.table to return our queries sequentially or by table name
          def table_mock_side_effect(table_name):
              if table_name == "users":
                  table_obj = MagicMock()
                  table_obj.delete.return_value = mock_delete_query1
                  return table_obj
              elif table_name == "registration_queue":
                  table_obj = MagicMock()
                  table_obj.select.return_value = mock_queue_query
                  table_obj.delete.return_value = mock_delete_query2
                  return table_obj
              return MagicMock()

          mock_sb.table.side_effect = table_mock_side_effect

          # Call function
          res = delete_student_from_supabase("S001")

          # Verify
          assert res is True
          
          # Verify storage removal
          mock_sb.storage.from_.assert_called_with(SUPABASE_STORAGE_BUCKET)
          removed_files = mock_bucket.remove.call_args[0][0]
          assert set(removed_files) == {"img3.jpg"}

          # Verify DB deletes
          mock_delete_query1.eq.assert_called_with("student_id", "S001")
          mock_delete_query2.eq.assert_called_with("student_id", "S001")

      def test_delete_student_no_user(self, mock_sb):
          from app.supabase_client import delete_student_from_supabase
          
          # Mock database response where queue doesn't exist
          mock_queue_select = MagicMock()
          mock_queue_select.eq.return_value.execute.return_value.data = []

          mock_delete_query1 = MagicMock()
          mock_delete_query1.eq.return_value.execute.return_value = MagicMock()

          mock_delete_query2 = MagicMock()
          mock_delete_query2.eq.return_value.execute.return_value = MagicMock()

          def table_mock_side_effect(table_name):
              if table_name == "users":
                  table_obj = MagicMock()
                  table_obj.delete.return_value = mock_delete_query1
                  return table_obj
              elif table_name == "registration_queue":
                  table_obj = MagicMock()
                  table_obj.select.return_value = mock_queue_select
                  table_obj.delete.return_value = mock_delete_query2
                  return table_obj
              return MagicMock()

          mock_sb.table.side_effect = table_mock_side_effect

          res = delete_student_from_supabase("S999")
          assert res is True
          
          # Storage should NOT be called since no files existed
          mock_sb.storage.from_.assert_not_called()

          # DB deletes should still be called to ensure any remaining records are cleared
          mock_delete_query1.eq.assert_called_with("student_id", "S999")
          mock_delete_query2.eq.assert_called_with("student_id", "S999")

      def test_delete_student_queue_only(self, mock_sb):
          from app.supabase_client import delete_student_from_supabase, SUPABASE_STORAGE_BUCKET
          
          # registration_queue has pending items
          mock_queue_select = MagicMock()
          mock_queue_select.eq.return_value.execute.return_value.data = [
              {"image_path": "https://supabase.co/storage/v1/object/public/bucket/img_queue.jpg"}
          ]

          mock_delete_query1 = MagicMock()
          mock_delete_query1.eq.return_value.execute.return_value = MagicMock()

          mock_delete_query2 = MagicMock()
          mock_delete_query2.eq.return_value.execute.return_value = MagicMock()

          mock_bucket = MagicMock()
          mock_sb.storage.from_.return_value = mock_bucket

          def table_mock_side_effect(table_name):
              if table_name == "users":
                  table_obj = MagicMock()
                  table_obj.delete.return_value = mock_delete_query1
                  return table_obj
              elif table_name == "registration_queue":
                  table_obj = MagicMock()
                  table_obj.select.return_value = mock_queue_select
                  table_obj.delete.return_value = mock_delete_query2
                  return table_obj
              return MagicMock()

          mock_sb.table.side_effect = table_mock_side_effect

          res = delete_student_from_supabase("S777")
          assert res is True
          
          # Storage should be called for the queue file
          mock_sb.storage.from_.assert_called_with(SUPABASE_STORAGE_BUCKET)
          removed_files = mock_bucket.remove.call_args[0][0]
          assert set(removed_files) == {"img_queue.jpg"}

          # DB deletes should still be called to ensure any remaining records are cleared
          mock_delete_query1.eq.assert_called_with("student_id", "S777")
          mock_delete_query2.eq.assert_called_with("student_id", "S777")
  ```

- [ ] **Step 3: Run unit tests**
  In `ai_server`, run the tests:
  ```bash
  venv\Scripts\python -m pytest tests/test_supabase_client.py -v
  ```
  Expected: PASS

- [ ] **Step 4: Commit changes**
  ```bash
  git add ai_server/app/supabase_client.py ai_server/tests/test_supabase_client.py
  git commit -m "refactor(backend): clean up deleted user_images references and update tests"
  ```

---

### Task 2: Implement Countdown and Progress UI in Flutter App

**Files:**
- Modify: `app_face_capture/lib/presentation/views/capture_screen.dart`

**Interfaces:**
- Consumes: Camera controller initializations.
- Produces: Countdown UI and simplified progress guide message.

- [ ] **Step 1: Add Timer Import and Countdown State**
  Add `import 'dart:async';` to imports. Add countdown state variables to `_CaptureScreenState` (lines 27-30):
  ```dart
  CameraController? _cameraController;
  bool _isInitializing = true;
  bool _isTakingPicture = false;
  
  // Countdown state variables
  bool _isPreparing = true;
  int _countdownSeconds = 3;
  Timer? _countdownTimer;
  ```

- [ ] **Step 2: Trigger Countdown Timer on Camera Init**
  Modify `_initCamera` to start the countdown timer as soon as `_cameraController` is initialized successfully:
  ```dart
  Future<void> _initCamera() async {
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        if (mounted) setState(() => _isInitializing = false);
        return;
      }

      final frontCamera = cameras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.front,
        orElse: () => cameras.first,
      );

      _cameraController = CameraController(
        frontCamera,
        ResolutionPreset.high,
        enableAudio: false,
      );
      await _cameraController!.initialize();
      if (mounted) {
        _startPreparationCountdown();
      }
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

- [ ] **Step 3: Update `dispose` to clean up the timer**
  Update the `dispose` method to cancel `_countdownTimer`:
  ```dart
  @override
  void dispose() {
    _countdownTimer?.cancel();
    _cameraController?.dispose();
    super.dispose();
  }
  ```

- [ ] **Step 4: Update Guide Text**
  Replace `_getPromptText(int count)` with:
  ```dart
  String _getPromptText(int count, int total) {
    if (_isPreparing) {
      return 'Get ready...';
    }
    return 'Capturing photo ${count + 1} of $total';
  }
  ```
  Update usages of `_getPromptText` in `build`:
  - In `FaceGuideOverlay`:
    `guideText: _getPromptText(viewModel.capturedCount, viewModel.requiredPhotos),`
  - In instructions `Text`:
    `_getPromptText(viewModel.capturedCount, viewModel.requiredPhotos),`

- [ ] **Step 5: Disable Capture Button while Preparing**
  Update the CaptureButton initialization:
  ```dart
  // Capture button
  Padding(
    padding: const EdgeInsets.symmetric(vertical: 16.0),
    child: CaptureButton(
      isEnabled: !_isPreparing && !viewModel.isComplete && !_isTakingPicture,
      onPressed: () => _capturePhoto(viewModel),
    ),
  ),
  ```

- [ ] **Step 6: Render Visual Countdown Overlay**
  In the `Stack` of `build`, render a semi-transparent countdown container over the camera preview:
  ```dart
  CameraPreviewWidget(controller: _cameraController!),
  FaceGuideOverlay(
    guideText: _getPromptText(viewModel.capturedCount, viewModel.requiredPhotos),
  ),
  if (_isPreparing)
    Positioned.fill(
      child: Container(
        color: Colors.black.withOpacity(0.6),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                '$_countdownSeconds',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 72,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                'Get ready! Align your face in the frame.',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    ),
  ```

- [ ] **Step 7: Commit changes**
  ```bash
  git add app_face_capture/lib/presentation/views/capture_screen.dart
  git commit -m "feat(capture): add preparation countdown and progress guides"
  ```

---

### Task 3: Update Retake Prompt Text in Review & Retake Screen

**Files:**
- Modify: `app_face_capture/lib/presentation/views/upload_screen.dart`

**Interfaces:**
- Consumes: None.
- Produces: Simplified prompt text passed to retake screen.

- [ ] **Step 1: Simplify prompt text**
  In `app_face_capture/lib/presentation/views/upload_screen.dart`, update `_getPromptText`:
  ```dart
  String _getPromptText(int count) {
    return 'Look straight at the camera to retake';
  }
  ```

- [ ] **Step 2: Run Flutter unit tests**
  Run Flutter tests:
  ```bash
  flutter test
  ```
  Expected: PASS

- [ ] **Step 3: Commit changes**
  ```bash
  git add app_face_capture/lib/presentation/views/upload_screen.dart
  git commit -m "feat(retake): update retake prompts to be simple and neutral"
  ```
