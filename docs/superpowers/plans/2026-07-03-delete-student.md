# Delete Student Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Implement a "Delete Student" feature allowing administrators to delete a student, their photos, and face recognition embeddings from the Web Dashboard while preserving historical check-in logs.

**Architecture:** A secure DELETE endpoint on the FastAPI server handles cascading DB deletions (users, user_images, registration_queue) and file/embeddings purges. The PHP dashboard acts as a cURL proxy to trigger this delete endpoint securely.

**Tech Stack:** Python (FastAPI, SQLAlchemy, Supabase Storage), PHP (cURL), HTML/JavaScript.

## Global Constraints
- Naming rules: Deletion endpoint should be `/register/student/{student_id}`.
- Authorization: Secure deletion endpoint with `require_admin` dependency.
- DB cascading: Preserved attendance logs should have their `user_id` set to `NULL` (handled by SQLite/PostgreSQL foreign key constraints).

---

### Task 1: Backend Database & Storage Deletion Logic

**Files:**
- Create: `ai_server/tests/test_database.py` (add SQLite delete assertions)
- Modify: `ai_server/app/supabase_client.py` (add `delete_student_from_supabase` function)
- Modify: `ai_server/app/database.py` (add `delete_student_from_db` wrapper)

**Interfaces:**
- Produces: `delete_student_from_db(student_id: str) -> bool`

- [x] **Step 1: Write database deletion tests**
  Add unit tests in `ai_server/tests/test_database.py` to verify that `delete_student_from_db` deletes users and queue items from SQLite, and triggers file deletions.
  ```python
  from app.database import delete_student_from_db, insert_queue_item, upsert_user
  
  def test_delete_student_sqlite():
      # Setup: insert user and queue items
      upsert_user("S999", "Test Delete User")
      insert_queue_item("S999", "/data/S999_test.jpg")
      
      # Perform deletion
      success = delete_student_from_db("S999")
      assert success is True
  ```

- [x] **Step 2: Run tests to verify they fail**
  Run: `venv\Scripts\python -m pytest tests/test_database.py`
  Expected: FAIL with `ImportError` or `AttributeError` (function not defined)

- [x] **Step 3: Implement Supabase Storage and DB delete logic**
  In `ai_server/app/supabase_client.py`, add `delete_student_from_supabase(student_id: str) -> bool`:
  ```python
  def delete_student_from_supabase(student_id: str) -> bool:
      if not is_available():
          return False
      try:
          sb = get_supabase()
          # 1. Fetch paths from user_images and registration_queue to delete files
          user_res = sb.table("users").select("id").eq("student_id", student_id).execute()
          if user_res.data:
              user_id = user_res.data[0]["id"]
              img_res = sb.table("user_images").select("image_path").eq("user_id", user_id).execute()
              paths = [row["image_path"] for row in img_res.data if row.get("image_path")]
              q_res = sb.table("registration_queue").select("image_path").eq("student_id", student_id).execute()
              paths.extend([row["image_path"] for row in q_res.data if row.get("image_path")])

              # Extract filenames to remove from Supabase Storage
              filenames = list(set([p.split("/")[-1] for p in paths if "/" in p]))
              if filenames:
                  sb.storage.from_(SUPABASE_STORAGE_BUCKET).remove(filenames)

          # 2. Delete user and queue history
          sb.table("users").delete().eq("student_id", student_id).execute()
          sb.table("registration_queue").delete().eq("student_id", student_id).execute()
          return True
      except Exception as e:
          print(f"[Supabase] delete_student_from_supabase error: {e}")
          return False
  ```

- [x] **Step 4: Implement SQLite deletion logic**
  In `ai_server/app/database.py`, add `delete_student_from_db(student_id: str) -> bool` that wraps both SQLite and Supabase deletion:
  ```python
  def delete_student_from_db(student_id: str) -> bool:
      if supabase_available():
          from app.supabase_client import delete_student_from_supabase
          return delete_student_from_supabase(student_id)
      else:
          _init_sqlite()
          session = next(_get_sqlite_session())
          try:
              user = session.query(_UserModel).filter(_UserModel.student_id == student_id).first()
              if user:
                  import os
                  images = session.query(_UserImageModel).filter(_UserImageModel.user_id == user.id).all()
                  for img in images:
                      if img.image_path and os.path.exists(img.image_path):
                          try:
                              os.remove(img.image_path)
                          except Exception:
                              pass
                  session.delete(user)

              q_items = session.query(_QueueModel).filter(_QueueModel.student_id == student_id).all()
              for item in q_items:
                  if item.image_path and os.path.exists(item.image_path):
                      try:
                          os.remove(item.image_path)
                      except Exception:
                          pass
                  session.delete(item)

              session.commit()
              return True
          except Exception as e:
              print(f"[SQLite] delete_student_from_db error: {e}")
              session.rollback()
              return False
          finally:
              session.close()
  ```

- [x] **Step 5: Run tests and verify they pass**
  Run: `venv\Scripts\python -m pytest tests/test_database.py`
  Expected: PASS

- [x] **Step 6: Commit**
  Run:
  ```bash
  git add ai_server/app/supabase_client.py ai_server/app/database.py ai_server/tests/test_database.py
  git commit -m "feat(ai_server): implement database and storage deletion helpers"
  ```

---

### Task 2: Service Layer & Endpoint Definition

**Files:**
- Modify: `ai_server/app/services/registration_service.py` (add `delete_student` service method)
- Modify: `ai_server/app/routers/registration.py` (add DELETE endpoint)
- Modify: `ai_server/tests/test_services.py` (add unit tests for service deletion)

**Interfaces:**
- Consumes: `delete_student_from_db(student_id: str) -> bool`
- Produces: `DELETE /register/student/{student_id}`

- [x] **Step 1: Write service deletion tests**
  Add unit tests in `ai_server/tests/test_services.py` to check that deletion calls db deletes, saves updated embeddings (with the target student filtered out), and invalidates cache:
  ```python
  @patch("app.services.registration_service.delete_student_from_db")
  @patch("app.services.registration_service.get_all_embeddings")
  @patch("app.services.registration_service.save_all_embeddings")
  @patch("app.services.registration_service.invalidate_cache")
  def test_delete_student_service(mock_invalidate, mock_save, mock_get_all, mock_db_delete):
      mock_db_delete.return_value = True
      mock_get_all.return_value = [
          {"student_id": "S123", "embeddings": []},
          {"student_id": "S456", "embeddings": []}
      ]
      
      from app.services.registration_service import delete_student
      result = delete_student("S123")
      
      assert result["student_id"] == "S123"
      mock_save.assert_called_once_with([{"student_id": "S456", "embeddings": []}])
      mock_invalidate.assert_called_once()
  ```

- [x] **Step 2: Run tests to verify they fail**
  Run: `venv\Scripts\python -m pytest tests/test_services.py`
  Expected: FAIL

- [x] **Step 3: Implement service layer delete orchestration**
  In `ai_server/app/services/registration_service.py`, implement `delete_student(student_id: str) -> dict`:
  ```python
  def delete_student(student_id: str) -> dict:
      from app.database import delete_student_from_db
      from app.matcher import invalidate_cache
  
      success = delete_student_from_db(student_id)
      if not success:
          raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail="Failed to delete student database/storage records"
          )
  
      existing = get_all_embeddings()
      updated = [e for e in existing if e.get("student_id") != student_id]
      save_all_embeddings(updated)
      
      invalidate_cache()
      
      return {
          "message": "Student registration data deleted successfully",
          "student_id": student_id
      }
  ```

- [x] **Step 4: Add HTTP DELETE endpoint**
  In `ai_server/app/routers/registration.py`, register the route:
  ```python
  from fastapi import Depends
  from app.dependencies import require_admin
  
  @router.delete("/register/student/{student_id}", status_code=status.HTTP_200_OK)
  def delete_student_endpoint(student_id: str, _ = Depends(require_admin)):
      """Delete a student, their images, queue records, and embeddings."""
      return registration_service.delete_student(student_id)
  ```

- [x] **Step 5: Run tests to verify they pass**
  Run: `venv\Scripts\python -m pytest tests/test_services.py`
  Expected: PASS

- [x] **Step 6: Commit**
  Run:
  ```bash
  git add ai_server/app/services/registration_service.py ai_server/app/routers/registration.py ai_server/tests/test_services.py
  git commit -m "feat(ai_server): add student delete endpoint and service orchestration"
  ```

---

### Task 3: Web Dashboard Proxy Endpoint

**Files:**
- Create: `web_dashboard/api/delete_student.php`

**Interfaces:**
- Consumes: `DELETE /register/student/{student_id}`
- Produces: `POST /api/delete_student.php`

- [x] **Step 1: Write delete proxy code**
  Create `web_dashboard/api/delete_student.php` with the following content:
  ```php
  <?php
  require_once __DIR__ . '/../config.php';
  
  header('Content-Type: application/json');
  
  if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
      http_response_code(405);
      echo json_encode(['error' => 'Method Not Allowed']);
      exit;
  }
  
  $studentId = $_POST['student_id'] ?? $_GET['student_id'] ?? null;
  if (!$studentId) {
      $input = json_decode(file_get_contents('php://input'), true);
      $studentId = $input['student_id'] ?? null;
  }
  
  if (!$studentId) {
      http_response_code(400);
      echo json_encode(['error' => 'Missing student_id parameter']);
      exit;
  }
  
  $ch = curl_init();
  curl_setopt($ch, CURLOPT_URL, AI_SERVER_URL . '/register/student/' . urlencode($studentId));
  curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'DELETE');
  curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
  curl_setopt($ch, CURLOPT_HTTPHEADER, [
      'X-Admin-Key: ' . ADMIN_API_KEY,
      'Content-Type: application/json'
  ]);
  
  $response = curl_exec($ch);
  $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
  curl_close($ch);
  
  if ($httpCode === 0) {
      $httpCode = 500;
  }
  
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

- [x] **Step 2: Commit**
  Run:
  ```bash
  git add web_dashboard/api/delete_student.php
  git commit -m "feat(dashboard): add secure delete_student.php api proxy"
  ```

---

### Task 4: Web Dashboard UI Integration

**Files:**
- Modify: `web_dashboard/index.php`

- [x] **Step 1: Update Students table headers**
  In `web_dashboard/index.php`, update the `Students` table `<thead>` to include an `Actions` header column.
  ```html
  <thead>
    <tr><th>Student ID</th><th>Name</th><th>Registered At</th><th>Status</th><th>Actions</th></tr>
  </thead>
  ```

- [x] **Step 2: Add Delete button to table rows**
  In `web_dashboard/index.php`, inside `loadStudents()`, update row template rendering:
  ```javascript
  tbody.innerHTML = rows.map(row => `
    <tr>
      <td><span class="cell-id">${escapeHtml(row.student_id) || '—'}</span></td>
      <td>${row.name ? escapeHtml(row.name) : '<span style="color:#64748b">—</span>'}</td>
      <td>${escapeHtml(formatDateTime(row.created_at))}</td>
      <td>${statusBadge(row.queue_status)}</td>
      <td>
        <button class="btn-delete" style="background:#ef4444;color:white;padding:4px 8px;border:none;border-radius:4px;cursor:pointer;font-size:11px;" onclick="deleteStudent('${escapeHtml(row.student_id)}')">Delete</button>
      </td>
    </tr>
  `).join('');
  ```

- [x] **Step 3: Define deleteStudent JS function**
  In `web_dashboard/index.php`, add `deleteStudent(studentId)`:
  ```javascript
  async function deleteStudent(studentId) {
    if (!confirm(`Are you sure you want to permanently delete student ID: ${studentId}?\nThis will delete their photos and face recognition data but keep their check-in log history.`)) {
      return;
    }
    
    try {
      const res = await fetch('api/delete_student.php', {
        method: 'POST',
        headers: { 'Content-Type: 'application/json' },
        body: JSON.stringify({ student_id: studentId })
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.error || d.detail || 'Delete failed');
      
      alert(`Student ${studentId} has been successfully deleted.`);
      loadStudents();
      loadStats();
      loadQueue();
    } catch (e) {
      alert('Error: ' + e.message);
    }
  }
  ```

- [x] **Step 4: Commit**
  Run:
  ```bash
  git add web_dashboard/index.php
  git commit -m "feat(dashboard): integrate Delete button and javascript client logic in index.php"
  ```
