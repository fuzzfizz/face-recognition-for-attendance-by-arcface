# Student Deletion Feature Design

## Overview
This specification outlines the implementation of the "Delete Student" feature. Administrators will be able to delete a registered student directly from the Web Dashboard. This operation will purge the student's personal records, uploaded face photos, and trained facial recognition embeddings to respect privacy and free up storage, while retaining their check-in/attendance history logs (with a nullified user association) for auditing and reporting purposes.

---

## Architectural & Data Changes

### 1. Database Cascades
- The `User` table has a cascade relationship with `UserImage`:
  - `images = relationship("UserImage", back_populates="user", cascade="all, delete-orphan")`
  - In PostgreSQL (Supabase), the foreign key on `user_images.user_id` has `ON DELETE CASCADE`.
  - When a `User` record is deleted, all matching database rows in `user_images` are automatically deleted.
- The `CheckInLog` table has a nullable foreign key referencing `users.id` with `ON DELETE SET NULL`:
  - When the user is deleted, their check-in logs remain in the database, with `user_id` set to `NULL`, preserving the raw string `student_id`, `similarity_score`, `device_id`, and `timestamp`. This meets the requirement of keeping historical check-in logs.

### 2. Physical File Deletion (Storage)
- We will retrieve all image paths associated with the student from both the `user_images` table and `registration_queue` table before deleting the records.
- We will parse the filenames from these paths and invoke a deletion method on Supabase Storage or the local folder to permanently purge the files.

### 3. Queue History Cleanup
- Any records matching the `student_id` in the `registration_queue` table will be explicitly deleted to keep the registration queue clean.

### 4. Embedding Purging & Invalidation
- The student's embeddings will be loaded from the local `.pkl` file, filtered out, and the updated list will be saved back.
- The server matcher cache will be invalidated.

---

## Detailed Components

### 1. Backend Service Layer (`ai_server`)

#### Database Layer (`app/database.py` and `app/supabase_client.py`)
- We will define a `delete_student_from_db` function:
  - If Supabase is available:
    - Get all user image paths from `user_images` for the student.
    - Get all image paths from `registration_queue` for the student.
    - Purge all retrieved files from the Supabase Storage bucket.
    - Delete the user from the `users` table (cascade takes care of `user_images`).
    - Delete records for this `student_id` from the `registration_queue` table.
  - If SQLite (local fallback) is used:
    - Get all image paths.
    - Delete files from the local directory.
    - Run SQL deletes on `users` and `registration_queue`.

#### Service Layer (`app/services/registration_service.py`)
- Add `delete_student(student_id: str)`:
  - Invoke `delete_student_from_db(student_id)`.
  - Load all embeddings using `get_all_embeddings()`.
  - Filter out the entry where `student_id == student_id`.
  - Save the updated list using `save_all_embeddings(existing)`.
  - Invalidate the matcher cache using `invalidate_cache()`.

#### Router Layer (`app/routers/registration.py`)
- Expose a `DELETE` endpoint:
  ```python
  @router.delete("/register/student/{student_id}", status_code=status.HTTP_200_OK)
  def delete_student_endpoint(student_id: str, _ = Depends(require_admin)):
      return registration_service.delete_student(student_id)
  ```

---

### 2. Frontend / Proxy Layer (`web_dashboard`)

#### Secure Proxy (`api/delete_student.php`)
- Accept `POST` requests containing a `student_id` parameter.
- Forward a `DELETE` request to `AI_SERVER_URL + "/register/student/" + urlencode($studentId)`.
- Pass the `X-Admin-Key` header with `ADMIN_API_KEY`.
- Return the server status code and JSON response.

#### User Interface (`index.php`)
- Add a new "Actions" column to the `Students` table header.
- Render a red "Delete" button in the table rows.
- Define a javascript function `deleteStudent(studentId)`:
  - Show a confirmation prompt: `"Are you sure you want to permanently delete student ID: ${studentId}? This will delete their photos and face recognition data but keep their check-in log history."`
  - Send a POST request to `api/delete_student.php` with `student_id`.
  - On success, display an alert/toast and call `loadStudents()`, `loadStats()`, and `loadQueue()` to refresh the dashboard.

---

## Verification Plan

### Automated Tests
- Implement new integration tests in `ai_server/tests/test_services.py` verifying that:
  - Deleting a student calls database deletes and storage file deletes.
  - Deleting a student removes their embeddings from the list.
  - The router endpoint accepts the delete requests and enforces the `require_admin` dependency.

### Manual Verification
- Deploy changes to the dashboard.
- Register a test student with images.
- Force training to complete and verify check-in works.
- Click "Delete" on the Web Dashboard for the test student, and verify:
  - The student is removed from the dashboard tables.
  - The physical images are deleted from the storage bucket.
  - Future face verification check-ins for the deleted face return a non-match.
  - Past check-in log records for that student ID are still preserved in the check-in table.
