# Simplified Face Checks & Registration Quota Design Spec

This spec outlines the design for simplifying the face verification and registration checkpoints to be faster, more scan-friendly, and highly optimized for low-quality camera modules (e.g. ESP32-CAM).

---

## 1. Goal & Context
Low-quality camera sensors produce noise, blur, and lighting variance that frequently trigger false rejections under strict quality checks (blur, size, pose angles). 

This design removes complex quality checks (blur, size, pose angles) and simplifies verification and registration into a few lightweight checkpoints, while adding duplicate and photo quota security checks during registration.

---

## 2. Technical Architecture

### A. AI Server (Python)

#### 1. Simplified Checkpoints in `verify` (Check-in)
In [verification_service.py](file:///D:/AIproject/ai_server/app/services/verification_service.py):
- **No Face Detected**: If `len(faces) == 0`, log and return message: `"Please look at the camera"`.
- **Multiple Faces**: If `len(faces) > 1`, log and return message: `"One person at a time"`.
- **Face Not Found**: If no match is found against local embeddings, log and return message: `"Employee data not found"`.

#### 2. Simplified Checkpoints in `register` (Registration)
In [registration_service.py](file:///D:/AIproject/ai_server/app/services/registration_service.py):
- **No Face Detected**: Return error: `"Face not found, please retake"`.
- **Multiple Faces**: Return error: `"Multiple faces in frame"`.
- **Duplicate Check (Case 3.1)**: Check if the face matches another student (with a different `student_id`). If similarity > `SIMILARITY_THRESHOLD`, block with error: `"This face is already registered"`.
- **Quota Check (Case 3.2)**: Check the student's existing registered photos count (both in `users` and `registration_queue` pending items). If `existing_count + new_files_count > 10`:
  - If `existing_count == 10`, return: `"Already registered 10 photos (Quota full)"`.
  - Else, return: `"Cannot register X photos. Already registered Y photos. Remaining quota is Z photos."`

---

### B. Web Dashboard (PHP & JS)

#### 1. Expandable Queue Rows
- In [index.php](file:///D:/AIproject/web_dashboard/index.php), update the expandable details checklist to show only the 4 simplified checks:
  1. **Face Detection**
  2. **Single Face Check**
  3. **Duplicate Check**
  4. **Quota Check**
- Update JS `parseValidationChecks` and `renderChecklistsHtml` to parse and render these 4 checks based on the database `error_message`.

---

## 3. Verification Plan

### Automated Tests
- Test verify failures return the simplified string messages `"Please look at the camera"`, `"One person at a time"`, and `"Employee data not found"`.
- Test register checks for duplicates against other student IDs.
- Test register quota checks correctly block uploads exceeding 10 photos and calculate the remaining quota in the error message.

### Manual Verification
- Upload more than 10 photos for a student and check that the registration is rejected with the exact remaining quota message.
- Verify using a face that belongs to another student, and verify that registration is blocked as a duplicate.
