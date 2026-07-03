# Image Quality Validation and Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a robust 7-step face quality validation pipeline (No Face, Multiple Faces, Blur, Size, Orientation, Obstructions, and Database Match) in the FastAPI backend, log failure reasons, and expose a 2-tab expandable panel on the Web Dashboard queue list.

**Architecture:** Extend the `FaceProcessor` utility to run OpenCV and keypoint heuristics. Store validation failure details in a new `error_message` DB column. Expose details through the APIs and render a responsive, tabbed slide-down view in the PHP dashboard.

**Tech Stack:** Python (FastAPI, OpenCV, InsightFace, SQLAlchemy), PHP, HTML, CSS, JavaScript.

## Global Constraints
- Thresholds: Blur Laplacian variance < 100, Face size < 120x120 pixels, Pose roll/yaw/pitch > 20°, Obstruction det_score < 0.6.
- Database: Column `error_message` must be added to `check_in_logs` and `registration_queue` tables.
- Dashboard tabs: Expandable row must show two tabs: "⚠️ Failure Checklist" and "📊 Raw Data" (No Photo Preview).

---

### Task 1: Backend Image Quality Check Logic

**Files:**
- Create: `ai_server/tests/test_quality_checks.py`
- Modify: `ai_server/app/utils/image_utils.py` (add Laplacian variance calculator)
- Modify: `ai_server/app/face_processor.py` (implement validation checks method)

**Interfaces:**
- Produces: `calculate_blur_variance(cv_img: np.ndarray) -> float`
- Produces: `FaceProcessor.validate_image_quality(self, cv_img: np.ndarray) -> dict` returning:
  ```python
  {
      "passed": bool,
      "failed_step": Optional[int],
      "error_message": Optional[str],
      "results": {
          "face_detected": bool,
          "single_face": bool,
          "blur_passed": bool,
          "distance_passed": bool,
          "orientation_passed": bool,
          "obstruction_passed": bool
      }
  }
  ```

- [ ] **Step 1: Write image validation unit tests**
  Create `ai_server/tests/test_quality_checks.py`:
  ```python
  import pytest
  import numpy as np
  from app.face_processor import get_face_processor

  def test_blur_variance_calculation():
      from app.utils.image_utils import calculate_blur_variance
      # Generate flat gray image (zero variance)
      img = np.zeros((100, 100, 3), dtype=np.uint8)
      assert calculate_blur_variance(img) == 0.0

  def test_quality_checks_no_face():
      processor = get_face_processor()
      blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
      res = processor.validate_image_quality(blank_img)
      assert res["passed"] is False
      assert res["failed_step"] == 1
      assert "No face detected" in res["error_message"]
  ```

- [ ] **Step 2: Run tests to verify they fail**
  Run: `venv\Scripts\python -m pytest tests/test_quality_checks.py`
  Expected: FAIL (missing methods/imports)

- [ ] **Step 3: Implement blur calculation in image_utils.py**
  In `ai_server/app/utils/image_utils.py`, add:
  ```python
  import cv2
  import numpy as np

  def calculate_blur_variance(cv_img: np.ndarray) -> float:
      if cv_img is None or cv_img.size == 0:
          return 0.0
      gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
      return float(cv2.Laplacian(gray, cv2.CV_64F).var())
  ```

- [ ] **Step 4: Implement quality validation in face_processor.py**
  In `ai_server/app/face_processor.py`, add:
  ```python
  import math
  from app.utils.image_utils import calculate_blur_variance

  def validate_image_quality(self, cv_img: np.ndarray) -> dict:
      results = {
          "face_detected": False,
          "single_face": False,
          "blur_passed": False,
          "distance_passed": False,
          "orientation_passed": False,
          "obstruction_passed": False
      }
      
      if cv_img is None or cv_img.size == 0:
          return {"passed": False, "failed_step": 1, "error_message": "Invalid image data", "results": results}
          
      faces = self.app.get(cv_img)
      if not faces:
          return {"passed": False, "failed_step": 1, "error_message": "No face detected in the image", "results": results}
      results["face_detected"] = True

      if len(faces) > 1:
          return {"passed": False, "failed_step": 2, "error_message": "Multiple faces detected in the frame", "results": results}
      results["single_face"] = True

      # 3. Blur Check
      variance = calculate_blur_variance(cv_img)
      if variance < 100:
          return {"passed": False, "failed_step": 3, "error_message": f"Image is blurry / motion detected (variance: {variance:.1f} < 100)", "results": results}
      results["blur_passed"] = True

      primary = faces[0]
      bbox = primary.bbox # [x1, y1, x2, y2]
      w = bbox[2] - bbox[0]
      h = bbox[3] - bbox[1]

      # 4. Distance (Size) Check
      if w < 120 or h < 120:
          return {"passed": False, "failed_step": 4, "error_message": f"Face is too far or too small (size: {int(w)}x{int(h)} px < 120x120 px)", "results": results}
      results["distance_passed"] = True

      # 5. Orientation (Pose) Check using 5 keypoints
      if hasattr(primary, "kps") and primary.kps is not None and len(primary.kps) >= 5:
          kps = primary.kps
          left_eye, right_eye, nose = kps[0], kps[1], kps[2]
          
          # Roll (tilt) calculation
          dy = right_eye[1] - left_eye[1]
          dx = right_eye[0] - left_eye[0]
          roll_angle = abs(math.atan2(dy, dx)) * 180 / math.pi
          if roll_angle > 20:
              return {"passed": False, "failed_step": 5, "error_message": f"Face is not straight (tilted: {roll_angle:.1f}° > 20°)", "results": results}
              
          # Yaw (turn) ratio calculation
          left_dist = abs(nose[0] - left_eye[0])
          right_dist = abs(right_eye[0] - nose[0])
          if left_dist == 0 or right_dist == 0:
              return {"passed": False, "failed_step": 5, "error_message": "Face is not straight (profile view detected)", "results": results}
          yaw_ratio = left_dist / right_dist
          if yaw_ratio < 0.5 or yaw_ratio > 2.0:
              return {"passed": False, "failed_step": 5, "error_message": f"Face is not straight (turned sideways)", "results": results}
      results["orientation_passed"] = True

      # 6. Obstruction Check (Det score)
      if hasattr(primary, "det_score") and primary.det_score < 0.6:
          return {"passed": False, "failed_step": 6, "error_message": f"Obstructions detected (confidence: {primary.det_score:.2f} < 0.6)", "results": results}
      results["obstruction_passed"] = True

      return {"passed": True, "failed_step": None, "error_message": None, "results": results}
  ```

- [ ] **Step 5: Run tests and verify they pass**
  Run: `venv\Scripts\python -m pytest tests/test_quality_checks.py`
  Expected: PASS

- [ ] **Step 6: Commit**
  ```bash
  git add ai_server/app/utils/image_utils.py ai_server/app/face_processor.py ai_server/tests/test_quality_checks.py
  git commit -m "feat(ai_server): implement 7-step image quality validation checks"
  ```

---

### Task 2: Database Schema & Migration for Logs

**Files:**
- Modify: `ai_server/app/models.py` (add `error_message` column)
- Modify: `ai_server/app/database.py` (add column in local fallback SQLite initialization)
- Modify: `ai_server/app/supabase_client.py` (insert column support)

**Interfaces:**
- Consumes: Database engines and connection models

- [ ] **Step 1: Write SQLite database migration tests**
  In `ai_server/tests/test_database.py`, add assertions for `error_message` check:
  ```python
  def test_insert_log_with_error_message():
      from app.database import insert_log
      # Log check-in with an error message
      insert_log(student_id=None, similarity_score=0.0, device_id="TEST-DEV", error_message="Blur Check Failed")
  ```

- [ ] **Step 2: Run tests to verify they fail**
  Run: `venv\Scripts\python -m pytest tests/test_database.py`
  Expected: FAIL (SQLite table doesn't have the column yet)

- [ ] **Step 3: Update SQLite schema initialization**
  In `ai_server/app/database.py`, update `_init_sqlite()` to run an migration `ALTER TABLE` if column is missing:
  ```python
  # After metadata.create_all(_sqlite_engine):
  with _sqlite_engine.connect() as conn:
      # Check if error_message column exists
      res = conn.execute(text("PRAGMA table_info(check_in_logs);")).fetchall()
      cols = [col[1] for col in res]
      if "error_message" not in cols:
          conn.execute(text("ALTER TABLE check_in_logs ADD COLUMN error_message VARCHAR;"))
      
      q_res = conn.execute(text("PRAGMA table_info(registration_queue);")).fetchall()
      q_cols = [col[1] for col in q_res]
      if "error_message" not in q_cols:
          conn.execute(text("ALTER TABLE registration_queue ADD COLUMN error_message VARCHAR;"))
  ```

- [ ] **Step 4: Update SQLAlchemy models**
  In `ai_server/app/models.py`, add `error_message` field:
  ```python
  class CheckInLog(Base):
      ...
      error_message = Column(String, nullable=True)

  class RegistrationQueue(Base):
      ...
      error_message = Column(String, nullable=True)
  ```

- [ ] **Step 5: Update `insert_log` signature**
  In `ai_server/app/database.py`, update `insert_log` to support `error_message`:
  ```python
  def insert_log(student_id: Optional[str], similarity_score: float, device_id: str, user_id: Optional[int] = None, error_message: Optional[str] = None):
      ...
      # inside sqlite fallback insert logic
      new_log = _CheckInLogModel(
          student_id=student_id,
          similarity_score=similarity_score,
          device_id=device_id,
          user_id=user_id,
          error_message=error_message
      )
  ```

- [ ] **Step 6: Update Supabase Client**
  In `ai_server/app/supabase_client.py`, update log inserts to support `error_message`.

- [ ] **Step 7: Run database tests**
  Run: `venv\Scripts\python -m pytest tests/test_database.py`
  Expected: PASS

- [ ] **Step 8: Commit**
  ```bash
  git add ai_server/app/models.py ai_server/app/database.py ai_server/app/supabase_client.py
  git commit -m "feat(database): support error_message field in check-in logs and registration queue"
  ```

---

### Task 3: API Integration for Register & Verify

**Files:**
- Modify: `ai_server/app/services/verification_service.py` (run quality checks before match)
- Modify: `ai_server/app/services/registration_service.py` (pre-validate uploads and log failed queue)
- Modify: `ai_server/app/schemas.py` (update HTTP response schemas)

**Interfaces:**
- Produces: `POST /verify` updated schema returning checklist
- Produces: `POST /register` updated schema returning checklist

- [ ] **Step 1: Write endpoint validation tests**
  In `ai_server/tests/test_routers.py`, add tests asserting `/verify` validation failures return HTTP checklist and log them to DB.

- [ ] **Step 2: Run tests to verify they fail**
  Run: `venv\Scripts\python -m pytest tests/test_routers.py`
  Expected: FAIL

- [ ] **Step 3: Update `verify_face` in verification_service.py**
  Run `validate_image_quality` first:
  ```python
  # inside verify_face
  val_res = processor.validate_image_quality(cv_img)
  if not val_res["passed"]:
      insert_log(student_id=None, similarity_score=0.0, device_id=device_id, error_message=val_res["error_message"])
      return {
          "match": False,
          "student_id": None,
          "similarity_score": 0.0,
          "timestamp": datetime.datetime.utcnow().isoformat(),
          "message": val_res["error_message"],
          "validation_checklist": val_res["results"]
      }
  ```

- [ ] **Step 4: Update schemas.py**
  Define response models containing `validation_checklist`.

- [ ] **Step 5: Run tests and verify they pass**
  Run: `venv\Scripts\python -m pytest`
  Expected: PASS (All 70+ tests pass)

- [ ] **Step 6: Commit**
  ```bash
  git add ai_server/app/services/verification_service.py ai_server/app/services/registration_service.py ai_server/app/schemas.py
  git commit -m "feat(api): integrate quality checkpoints into verification and registration pipelines"
  ```

---

### Task 4: Web Dashboard Diagnostics & Expandable Checklist

**Files:**
- Modify: `web_dashboard/index.php` (render list collapse UI, 2 tabs panel)

- [ ] **Step 1: Add style rule for expandable details**
  Add inline CSS/classes in `web_dashboard/index.php` for slide down animation:
  ```css
  .details-container {
      max-height: 0;
      overflow: hidden;
      transition: max-height 0.3s ease-out;
  }
  .details-container.expanded {
      max-height: 500px;
  }
  ```

- [ ] **Step 2: Update row rendering with ▶/▼ arrow and expandable checklist markup**
  Inject dataset fields and toggle click triggers into rows.
  Render horizontal tabs: `Failure Checklist` and `Raw Data`.

- [ ] **Step 3: Verify syntax of index.php**
  Run: `php -l web_dashboard/index.php`
  Expected: No syntax errors detected in index.php

- [ ] **Step 4: Commit**
  ```bash
  git add web_dashboard/index.php
  git commit -m "feat(dashboard): add expandable row checklist and metadata tabs to queue list"
  ```
