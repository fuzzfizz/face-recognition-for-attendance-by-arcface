# Self-Healing Orphaned Embeddings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement self-healing in the AI server to automatically prune orphaned embeddings from `face_embeddings.pkl` when a student ID does not exist in the database during registration or training duplicate checks.

**Architecture:** Add db-existence checks when loading student counts and when matching duplicate faces. If the student ID exists in the local pickle file but is absent from the SQL database, automatically delete their embeddings from `face_embeddings.pkl` and invalidate the memory cache.

**Tech Stack:** Python (FastAPI, SQLAlchemy)

## Global Constraints
- Naming rules: Follow existing code naming and functions in `registration_service.py` and `training_service.py`.
- Environment constraints: Only run self-healing when `is_local_or_test` from `app.config` is False, to prevent interfering with mock-based unit tests.

---

### Task 1: Self-healing during registration photo quota check

**Files:**
- Modify: [registration_service.py](file:///D:/AIproject/ai_server/app/services/registration_service.py)
- Test: [test_services.py](file:///D:/AIproject/ai_server/tests/test_services.py)

**Interfaces:**
- Consumes: `get_user_by_student_id(student_id: str)` and `is_local_or_test`
- Produces: Automatic pruning of orphaned `.pkl` records during `/register` requests.

- [ ] **Step 1: Write unit test to verify that self-healing does not run during tests**
  We already have tests that mock database and pickle layers. We will run pytest to ensure our changes do not break any existing tests.

- [ ] **Step 2: Add self-healing logic to `register_images` in `registration_service.py`**
  Modify the quota check to check if the user exists in the database. If not, prune.
  
  ```python
      # Self-healing: if not in test mode, check database existence and prune orphaned embeddings
      from app.config import is_local_or_test
      if not is_local_or_test:
          db_user = get_user_by_student_id(student_id)
          if not db_user:
              # User is not in DB, but embeddings exist in pickle -> prune
              existing_all = get_all_embeddings()
              updated = [e for e in existing_all if e.get("student_id") != student_id]
              if len(updated) < len(existing_all):
                  save_all_embeddings(updated)
                  invalidate_cache()
  ```

- [ ] **Step 3: Run pytest to verify all tests pass**
  Run: `venv\Scripts\pytest`
  Expected: All 94 tests PASS.

---

### Task 2: Self-healing during duplicate checks (Registration & Training)

**Files:**
- Modify: [registration_service.py](file:///D:/AIproject/ai_server/app/services/registration_service.py)
- Modify: [training_service.py](file:///D:/AIproject/ai_server/app/services/training_service.py)
- Test: [test_services.py](file:///D:/AIproject/ai_server/tests/test_services.py)

- [ ] **Step 1: Implement self-healing in duplicate checks in `registration_service.py`**
  Modify `register_images` duplicate check to query database existence and ignore/prune matches that belong to non-existent students.
  
  ```python
              if face_data and "embedding" in face_data:
                  match = match_face_embedding(face_data["embedding"])
                  if match and match.get("student_id") != student_id:
                      matched_student_id = match.get("student_id")
                      from app.config import is_local_or_test
                      is_orphaned = False
                      if not is_local_or_test:
                          matched_user = get_user_by_student_id(matched_student_id)
                          if not matched_user:
                              is_orphaned = True
                              existing_all = get_all_embeddings()
                              updated = [e for e in existing_all if e.get("student_id") != matched_student_id]
                              if len(updated) < len(existing_all):
                                  save_all_embeddings(updated)
                                  invalidate_cache()
                      
                      if not is_orphaned:
                          raise HTTPException(
                              status_code=status.HTTP_400_BAD_REQUEST,
                              detail={
                                  "message": "This face is already registered",
                                  "results": []
                              }
                          )
  ```

- [ ] **Step 2: Implement self-healing in duplicate checks in `training_service.py`**
  Modify `process_pending_queue` duplicate check:
  
  ```python
                  if result and "embedding" in result:
                      # Check for duplicate face matching a different student
                      from app.matcher import match_face
                      match = match_face(result["embedding"])
                      if match and match["student_id"] != student_id:
                          matched_student_id = match["student_id"]
                          from app.config import is_local_or_test
                          from app.database import get_user_by_student_id
                          is_orphaned = False
                          if not is_local_or_test:
                              matched_user = get_user_by_student_id(matched_student_id)
                              if not matched_user:
                                  is_orphaned = True
                                  existing_all = get_all_embeddings()
                                  updated = [e for e in existing_all if e.get("student_id") != matched_student_id]
                                  if len(updated) < len(existing_all):
                                      save_all_embeddings(updated)
                                      invalidate_cache()
                          
                          if not is_orphaned:
                              all_item_statuses.append((item["id"], "failed", "This face is already registered"))
                          else:
                              new_embeddings.append(result["embedding"])
                              all_item_statuses.append((item["id"], "completed", None))
                      else:
                          new_embeddings.append(result["embedding"])
                          all_item_statuses.append((item["id"], "completed", None))
  ```

- [ ] **Step 3: Run pytest to verify all tests pass**
  Run: `venv\Scripts\pytest`
  Expected: All 94 tests PASS.
