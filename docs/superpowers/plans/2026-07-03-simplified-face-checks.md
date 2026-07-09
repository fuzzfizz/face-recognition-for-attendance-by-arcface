# Simplified Face Checks and Registration Quota Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify quality validation checks for verification and registration to optimize for low-quality camera modules, implement duplicate and quota checks on registration, and update the Web Dashboard queue checklist.

**Architecture:** Modify `FaceProcessor.validate_image_quality` to run only face detection and single face checks. Add duplicate and quota validation inside `registration_service.py`. Update JavaScript rendering inside `web_dashboard/index.php` to display the simplified 4-check list.

**Tech Stack:** Python (FastAPI, InsightFace), PHP, HTML, JavaScript.

## Global Constraints
- Target check points for verify: No Face, Multiple Faces, and Database Match.
- Return error messages: `"Please look at the camera"`, `"One person at a time"`, and `"Employee data not found"`.
- Target checks for register: No Face, Multiple Faces, Duplicate Check, Quota Check (limit 10).
- Dashboard list: Show exactly 4 check items: Face Detection, Single Face Check, Duplicate Check, Quota Check.

---

### Task 1: Backend Quality Check & Verification Simplified

**Files:**
- Modify: `ai_server/app/face_processor.py` (keep only face presence and single face checks)
- Modify: `ai_server/app/services/verification_service.py` (simplify verify_face logic, update output messages)
- Modify: `ai_server/tests/test_quality_checks.py` (update unit tests)
- Modify: `ai_server/tests/test_services.py` (update unit tests)

**Interfaces:**
- Produces: `FaceProcessor.validate_image_quality(self, cv_img: np.ndarray) -> dict` with only checks 1-2.
- Produces: `verify_face(image_data, image_base64, device_id) -> dict` returning simplified messages.

- [ ] **Step 1: Update quality check and verification tests**
  Modify tests in `ai_server/tests/test_quality_checks.py` and `ai_server/tests/test_services.py` to match the removed blur/size/orientation check behaviors and verify simplified check-in return messages:
  - Assert that "Please look at the camera", "One person at a time", and "Employee data not found" are returned.

- [ ] **Step 2: Run tests to verify they fail**
  Run: `venv\Scripts\python -m pytest`
  Expected: FAIL

- [ ] **Step 3: Simplify `validate_image_quality` checks**
  In `ai_server/app/face_processor.py`, remove steps 3, 4, 5, 6 and return results mapping only `face_detected` and `single_face`.

- [ ] **Step 4: Update `verify_face` logic**
  In `ai_server/app/services/verification_service.py`, handle failures using target messages:
  - If no face: log and return `"Please look at the camera"`.
  - If multiple faces: log and return `"One person at a time"`.
  - If no match: log and return `"Employee data not found"`.

- [ ] **Step 5: Run tests and verify they pass**
  Run: `venv\Scripts\python -m pytest`
  Expected: PASS

- [ ] **Step 6: Commit**
  ```bash
  git add ai_server/app/face_processor.py ai_server/app/services/verification_service.py ai_server/tests/test_quality_checks.py ai_server/tests/test_services.py
  git commit -m "feat(ai_server): simplify verification checkpoints and messages"
  ```

---

### Task 2: Duplicate Face & Quota Check on Registration

**Files:**
- Modify: `ai_server/app/services/registration_service.py` (implement duplicate and quota checks)
- Modify: `ai_server/tests/test_services.py` (add tests for quota and duplicate validations)

**Interfaces:**
- Consumes: `/register` uploads.
- Produces: Registration checks throwing HTTPException 400 on duplicate or quota exceeded.

- [ ] **Step 1: Write duplicate and quota registration tests**
  In `ai_server/tests/test_services.py`, add tests:
  - Verify that uploading when the student already has 10 images raises HTTP 400: `"Already registered 10 photos (Quota full)"`.
  - Verify that uploading when the student has 8 images and tries to upload 3 images raises HTTP 400: `"Cannot register 3 photos. Already registered 8 photos. Remaining quota is 2 photos."`.
  - Verify duplicate check blocks face matching other student IDs with `"This face is already registered"`.

- [ ] **Step 2: Run tests to verify they fail**
  Run: `venv\Scripts\python -m pytest`
  Expected: FAIL

- [ ] **Step 3: Implement Quota Check**
  In `ai_server/app/services/registration_service.py`, count user images + pending queue records. Verify if the count + new files count exceeds 10, and return the corresponding remaining quota message.

- [ ] **Step 4: Implement Duplicate Check**
  In `register_images` (before queueing), extract face embedding and run matching. If similarity > `SIMILARITY_THRESHOLD` and matches a *different* `student_id`, reject with `"This face is already registered"`.

- [ ] **Step 5: Run tests and verify they pass**
  Run: `venv\Scripts\python -m pytest`
  Expected: PASS

- [ ] **Step 6: Commit**
  ```bash
  git add ai_server/app/services/registration_service.py ai_server/tests/test_services.py
  git commit -m "feat(registration): enforce duplicate checks and 10-photo quota limits with remaining quota feedback"
  ```

---

### Task 3: Web Dashboard Queue UI Checklist Updates

**Files:**
- Modify: `web_dashboard/index.php` (update JS checklist renderer to show 4 items)

- [ ] **Step 1: Update CSS and HTML table headers**
  If needed, align any table column widths.

- [ ] **Step 2: Update checklist parsing and HTML rendering**
  In `web_dashboard/index.php`:
  - Update `parseValidationChecks(item)` to return 4 checks: Face Detection, Single Face Check, Duplicate Check, Quota Check.
  - Map `"please look at the camera"` / `"face not found"` to step 1 failure.
  - Map `"one person at a time"` / `"multiple faces"` to step 2 failure.
  - Map `"already registered"` to step 3 failure.
  - Map `"quota"` to step 4 failure.
  - Render labels to match.

- [ ] **Step 3: Verify syntax**
  Run: `php -l web_dashboard/index.php`
  Expected: No syntax errors detected in web_dashboard/index.php

- [ ] **Step 4: Commit**
  ```bash
  git add web_dashboard/index.php
  git commit -m "feat(dashboard): simplify queue collapse checklist to 4 items"
  ```
