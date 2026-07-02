# AI Server Training Optimization & Check-in Cooldown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Optimize AI Server training queue processing via batching/periodic saving and implement a 5-minute face verification check-in cooldown.

**Architecture:** Update database retrieval layers in SQLite and Supabase to support query limits and latest log lookups. Process the training queue in student-grouped batches with incremental pickle saving. Enforce a 5-minute elapsed check-in limit prior to inserting successful match logs.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Supabase Python Client, SQLite, pytest

## Global Constraints

* Database must support dual-mode (SQLite fallback when Supabase is unavailable).
* Face embeddings must stay in local pickle file for fast local matching.
* Cooldown logic must bypass DB inserts and return a warning message if a student verified successfully within the last 5 minutes.
* Database updates in training queue must occur AFTER saving pickle embeddings to ensure crash resilience.

---

### Task 1: Database Layer Upgrades

**Files:**
- Modify: `ai_server/app/supabase_client.py`
- Modify: `ai_server/app/database.py`
- Test: `ai_server/tests/test_supabase_client.py`

**Interfaces:**
- Consumes: Existing table models and connections.
- Produces: `get_pending_queue_items(limit: Optional[int] = None)` and `get_latest_check_in_log(student_id: str)`

- [ ] **Step 1: Write test cases in test_supabase_client.py**
  Add mock tests verifying `get_pending_queue_items` with a limit and `get_latest_check_in_log`.
  Add these to `ai_server/tests/test_supabase_client.py`:
  ```python
  def test_get_pending_queue_items_with_limit(mock_supabase):
      from app.supabase_client import get_pending_queue_items
      mock_supabase.table().select().eq().execute.return_value.data = [{"id": 1}]
      res = get_pending_queue_items(limit=5)
      assert len(res) == 1

  def test_get_latest_check_in_log(mock_supabase):
      from app.supabase_client import get_latest_check_in_log
      mock_supabase.table().select().eq().order().limit().execute.return_value.data = [{"id": 42, "student_id": "S123", "timestamp": "2026-07-02T12:00:00Z"}]
      res = get_latest_check_in_log("S123")
      assert res["id"] == 42
  ```

- [ ] **Step 2: Run tests to verify they fail or error out**
  Run: `$env:PYTHONPATH="ai_server"; D:\AIproject\ai_server\venv\Scripts\python.exe -m pytest ai_server/tests/test_supabase_client.py -v`
  Expected: Error due to missing or unsupported limit arguments.

- [ ] **Step 3: Modify app/supabase_client.py**
  Update `get_pending_queue_items` to support limit, and add `get_latest_check_in_log`:
  ```python
  def get_pending_queue_items(limit: Optional[int] = None) -> List[Dict[str, Any]]:
      if not is_available():
          return []
      try:
          query = get_supabase().table("registration_queue").select("*").eq("status", "pending")
          if limit is not None:
              query = query.limit(limit)
          response = query.execute()
          return response.data or []
      except Exception as e:
          print(f"[Supabase] get_pending_queue_items error: {e}")
          return []

  def get_latest_check_in_log(student_id: str) -> Optional[Dict[str, Any]]:
      if not is_available():
          return None
      try:
          response = get_supabase().table("check_in_logs") \
              .select("*") \
              .eq("student_id", student_id) \
              .order("timestamp", desc=True) \
              .limit(1) \
              .execute()
          return response.data[0] if response.data else None
      except Exception as e:
          print(f"[Supabase] get_latest_check_in_log error: {e}")
          return None
  ```

- [ ] **Step 4: Modify app/database.py**
  Expose both functions with dual-mode (SQLite fallback support):
  ```python
  # Add sb_get_latest_check_in_log to imports from app.supabase_client
  from app.supabase_client import (
      ...
      get_pending_queue_items as sb_get_pending_queue_items,
      get_latest_check_in_log as sb_get_latest_check_in_log,
  )

  def get_pending_queue_items(limit: Optional[int] = None):
      if supabase_available():
          return sb_get_pending_queue_items(limit)
      else:
          _init_sqlite()
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

  def get_latest_check_in_log(student_id: str) -> Optional[dict]:
      if supabase_available():
          return sb_get_latest_check_in_log(student_id)
      else:
          _init_sqlite()
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
                      "timestamp": log.timestamp
                  }
              return None
          finally:
              session.close()
  ```

- [ ] **Step 5: Run tests and verify they pass**
  Run: `$env:PYTHONPATH="ai_server"; D:\AIproject\ai_server\venv\Scripts\python.exe -m pytest ai_server/tests/test_supabase_client.py -v`
  Expected: PASS

- [ ] **Step 6: Commit**
  ```bash
  git add ai_server/app/supabase_client.py ai_server/app/database.py ai_server/tests/test_supabase_client.py
  git commit -m "feat(ai_server): add batch limiting and latest log queries to DB layer"
  ```

---

### Task 2: Service/Routing layers for training optimization

**Files:**
- Modify: `ai_server/app/services/training_service.py`
- Modify: `ai_server/app/routers/training.py`
- Modify: `ai_server/app/routers/v1/users.py`
- Modify: `ai_server/tests/test_services.py`

**Interfaces:**
- Consumes: `get_pending_queue_items(limit)` from DB layer.
- Produces: Optimized `process_pending_queue(limit: int = 50)`

- [ ] **Step 1: Write test cases in test_services.py**
  Add mock tests verifying `process_pending_queue` groups by student, updates pickle file atomically per student, and updates database statuses.
  Add these to `ai_server/tests/test_services.py`:
  ```python
  @patch("app.services.training_service.get_pending_queue_items")
  @patch("app.services.training_service.get_face_processor")
  @patch("app.services.training_service.update_queue_item_status")
  @patch("app.services.training_service.get_all_embeddings")
  @patch("app.services.training_service.save_all_embeddings")
  @patch("app.services.training_service.invalidate_cache")
  def test_process_pending_queue_batching(
      mock_invalidate, mock_save, mock_get_all, mock_update_status, mock_get_processor, mock_get_pending
  ):
      mock_get_pending.return_value = [
          {"id": 1, "student_id": "S123", "image_path": "/path/1.jpg"},
          {"id": 2, "student_id": "S123", "image_path": "/path/2.jpg"},
          {"id": 3, "student_id": "S456", "image_path": "/path/3.jpg"}
      ]
      mock_processor = MagicMock()
      mock_processor.decode_image_path.return_value = MagicMock()
      mock_processor.extract_face_embedding.return_value = {"embedding": [0.1] * 512}
      mock_get_processor.return_value = mock_processor
      mock_get_all.return_value = []

      result = process_pending_queue(limit=50)

      assert result["message"] == "Training completed for batch"
      assert "S123" in result["processed_students"]
      assert "S456" in result["processed_students"]
      assert mock_save.call_count == 2  # Once for S123, once for S456 (periodic saving)
      assert mock_update_status.call_count == 3
  ```

- [ ] **Step 2: Run tests to verify they fail**
  Run: `$env:PYTHONPATH="ai_server"; D:\AIproject\ai_server\venv\Scripts\python.exe -m pytest ai_server/tests/test_services.py -k test_process_pending_queue_batching -v`
  Expected: FAIL

- [ ] **Step 3: Implement optimized process_pending_queue**
  Update `ai_server/app/services/training_service.py` to match the student-grouped batching and periodic saving:
  ```python
  from fastapi import HTTPException, status
  from app.database import (
      get_pending_queue_items,
      update_queue_item_status,
      get_all_embeddings,
      save_all_embeddings,
  )
  from app.face_processor import get_face_processor
  from app.matcher import invalidate_cache

  def process_pending_queue(limit: int = 50) -> dict:
      pending_items = get_pending_queue_items(limit=limit)

      if not pending_items:
          raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="No pending images in queue. Upload images via /register first."
          )

      items_by_student = {}
      for item in pending_items:
          student_id = item["student_id"]
          if student_id not in items_by_student:
              items_by_student[student_id] = []
          items_by_student[student_id].append(item)

      processor = get_face_processor()
      processed_students = []

      for student_id, student_items in items_by_student.items():
          new_embeddings = []
          item_statuses = []

          for item in student_items:
              try:
                  cv_img = processor.decode_image_path(item["image_path"])
                  if cv_img is None:
                      item_statuses.append((item["id"], "failed", "Could not read image file"))
                      continue

                  result = processor.extract_face_embedding(cv_img)
                  if result and "embedding" in result:
                      new_embeddings.append(result["embedding"])
                      item_statuses.append((item["id"], "completed", None))
                  else:
                      item_statuses.append((item["id"], "failed", "No face detected"))

              except Exception as e:
                  item_statuses.append((item["id"], "failed", str(e)))

          if new_embeddings:
              existing = get_all_embeddings()
              existing = [e for e in existing if e.get("student_id") != student_id]
              existing.append({
                  "user_id": student_id,
                  "name": student_id,
                  "student_id": student_id,
                  "embeddings": new_embeddings
              })
              save_all_embeddings(existing)
              invalidate_cache()
              processed_students.append(student_id)

          for item_id, db_status, err_msg in item_statuses:
              update_queue_item_status(item_id, db_status, err_msg)

      return {
          "message": "Training completed for batch",
          "processed_students": processed_students,
          "total_pending": len(pending_items)
      }
  ```

- [ ] **Step 4: Update routers to expose training services**
  Verify `/train-now` and `/train` endpoints in `ai_server/app/routers/training.py` and `ai_server/app/routers/v1/users.py` support the optimized call.

- [ ] **Step 5: Run tests and verify they pass**
  Run: `$env:PYTHONPATH="ai_server"; D:\AIproject\ai_server\venv\Scripts\python.exe -m pytest ai_server/tests/test_services.py -v`
  Expected: PASS

- [ ] **Step 6: Commit**
  ```bash
  git add ai_server/app/services/training_service.py ai_server/app/routers/training.py ai_server/app/routers/v1/users.py ai_server/tests/test_services.py
  git commit -m "feat(ai_server): optimize training service with student-level atomic batch saving"
  ```

---

### Task 3: Service/Routing layers for verification cooldown

**Files:**
- Modify: `ai_server/app/schemas.py`
- Modify: `ai_server/app/services/verification_service.py`
- Modify: `ai_server/tests/test_services.py`

**Interfaces:**
- Consumes: `get_latest_check_in_log(student_id)`
- Produces: Updated schema `VerifyResponse` with `message: Optional[str]` and 5-min cooldown logic in `verify_face()`

- [ ] **Step 1: Write test case in test_services.py**
  Add mock test verifying that if a check-in occurred within the last 5 minutes, `verify_face` returns `match: True`, skips database logging, and sets the cooldown message.
  Add these to `ai_server/tests/test_services.py`:
  ```python
  @patch("app.services.verification_service.get_face_processor")
  @patch("app.services.verification_service.decode_image_bytes")
  @patch("app.services.verification_service.match_face_embedding")
  @patch("app.services.verification_service.get_latest_check_in_log")
  @patch("app.services.verification_service.insert_log")
  def test_verify_face_cooldown_active(mock_insert, mock_get_latest, mock_match, mock_decode, mock_get_processor):
      import datetime
      mock_decode.return_value = MagicMock()
      mock_processor = MagicMock()
      mock_processor.extract_face_embedding.return_value = {"embedding": [0.1] * 512}
      mock_get_processor.return_value = mock_processor
      mock_match.return_value = {"student_id": "S123", "similarity": 0.85, "user_id": 1}
      
      # Mock check-in 2 minutes ago (120 seconds ago)
      two_mins_ago = datetime.datetime.utcnow() - datetime.timedelta(minutes=2)
      mock_get_latest.return_value = {"timestamp": two_mins_ago}

      result = verify_face(image_data=b"image_bytes", device_id="ESP-TEST")

      assert result["match"] is True
      assert "already checked in" in result["message"]
      mock_insert.assert_not_called()  # Bypassed DB insert
  ```

- [ ] **Step 2: Run tests to verify failure**
  Run: `$env:PYTHONPATH="ai_server"; D:\AIproject\ai_server\venv\Scripts\python.exe -m pytest ai_server/tests/test_services.py -k test_verify_face_cooldown_active -v`
  Expected: FAIL

- [ ] **Step 3: Modify app/schemas.py**
  Add `message` to `VerifyResponse`:
  ```python
  class VerifyResponse(BaseModel):
      match: bool
      student_id: Optional[str]
      similarity_score: float
      timestamp: str
      message: Optional[str] = None
  ```

- [ ] **Step 4: Modify app/services/verification_service.py**
  Implement the cooldown timestamp parsing and bypass check in `verify_face()`:
  ```python
  import datetime
  from fastapi import HTTPException, status
  from typing import Optional

  from app.database import (
      insert_log,
      match_face_embedding,
      get_latest_check_in_log,
  )
  from app.face_processor import get_face_processor
  from app.utils.image_utils import decode_image_bytes, decode_base64_image

  def verify_face(
      image_data: Optional[bytes] = None,
      image_base64: Optional[str] = None,
      device_id: str = "ESP32-S3-01"
  ) -> dict:
      processor = get_face_processor()
      cv_img = None

      if image_data:
          cv_img = decode_image_bytes(image_data)
      elif image_base64:
          try:
              cv_img = decode_base64_image(image_base64)
          except Exception as e:
              raise HTTPException(
                  status_code=status.HTTP_400_BAD_REQUEST,
                  detail=f"Failed to decode base64 image: {str(e)}"
              )
      else:
          raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="No image provided. Send an image file or base64 parameter."
          )

      if cv_img is None:
          raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="Invalid image content."
          )

      face_data = processor.extract_face_embedding(cv_img)
      if not face_data:
          insert_log(student_id=None, similarity_score=0.0, device_id=device_id)
          return {
              "match": False,
              "student_id": None,
              "similarity_score": 0.0,
              "timestamp": datetime.datetime.utcnow().isoformat(),
              "message": None
          }

      match = match_face_embedding(face_data["embedding"])

      if match:
          student_id = match.get("student_id") or match.get("name", "Unknown")
          user_id = match.get("user_id")

          latest_log = get_latest_check_in_log(student_id)
          if latest_log:
              latest_time = latest_log["timestamp"]
              if isinstance(latest_time, str):
                  if latest_time.endswith('Z'):
                      latest_time = latest_time[:-1] + '+00:00'
                  try:
                      latest_dt = datetime.datetime.fromisoformat(latest_time)
                  except ValueError:
                      try:
                          latest_dt = datetime.datetime.strptime(latest_time, "%Y-%m-%d %H:%M:%S.%f")
                      except ValueError:
                          latest_dt = datetime.datetime.strptime(latest_time[:19], "%Y-%m-%dT%H:%M:%S")
                  if latest_dt.tzinfo is not None:
                      latest_dt = latest_dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
              else:
                  latest_dt = latest_time

              elapsed = (datetime.datetime.utcnow() - latest_dt).total_seconds()
              if elapsed < 300:
                  return {
                      "match": True,
                      "student_id": student_id,
                      "similarity_score": match["similarity"],
                      "timestamp": datetime.datetime.utcnow().isoformat(),
                      "message": "Student has already checked in within the last 5 minutes."
                  }

          insert_log(
              student_id=student_id,
              similarity_score=match["similarity"],
              device_id=device_id,
              user_id=user_id,
          )

          return {
              "match": True,
              "student_id": student_id,
              "similarity_score": match["similarity"],
              "timestamp": datetime.datetime.utcnow().isoformat(),
              "message": None
          }
      else:
          insert_log(student_id=None, similarity_score=0.0, device_id=device_id)
          return {
              "match": False,
              "student_id": None,
              "similarity_score": 0.0,
              "timestamp": datetime.datetime.utcnow().isoformat(),
              "message": None
          }
  ```

- [ ] **Step 5: Run tests and verify they pass**
  Run: `$env:PYTHONPATH="ai_server"; D:\AIproject\ai_server\venv\Scripts\python.exe -m pytest ai_server/tests/test_services.py -v`
  Expected: PASS

- [ ] **Step 6: Commit**
  ```bash
  git add ai_server/app/schemas.py ai_server/app/services/verification_service.py ai_server/tests/test_services.py
  git commit -m "feat(ai_server): enforce 5-minute cooldown check-in bypass in verification service"
  ```
