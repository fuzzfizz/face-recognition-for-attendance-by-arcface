# Remove Unused User Images Table and Clean Code Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the completely unused `user_images` database table, its corresponding `UserImage` ORM model, and related dead code to streamline the codebase and database schema.

**Architecture:** Remove `UserImage` model definitions from `models.py`, update clean-up and delete operations in `database.py`, adjust tests in `test_database.py` to match the updated schema, and execute SQL commands to drop the table in Supabase.

**Tech Stack:** Python (SQLAlchemy, FastAPI), PostgreSQL (Supabase), SQLite.

## Global Constraints
- Do not affect check-in, verification, or registration queue functionality.
- Ensure all SQLite and PostgreSQL database queries remain syntax-valid and tested.
- Do not delete deprecated legacy `/v1/` routes.

---

### Task 1: Remove `UserImage` from Models and Database Logic

**Files:**
- Modify: `ai_server/app/models.py`
- Modify: `ai_server/app/database.py`

**Interfaces:**
- Consumes: SQLAlchemy Models.
- Produces: Cleaner `User` schema and `delete_student_from_db` without references to `UserImage`.

- [ ] **Step 1: Modify models.py**
  In `ai_server/app/models.py`, delete the `UserImage` class and remove the `images` relationship from the `User` class (lines 24 and 28-38):
  - Remove: `images = relationship("UserImage", back_populates="user", cascade="all, delete-orphan")` from `User`.

- [ ] **Step 2: Modify database.py**
  In `ai_server/app/database.py`:
  - Remove `UserImage` import from `app.models`.
  - Remove `_UserImageModel = UserImage` definition.
  - In `delete_student_from_db`, remove the query and file extraction block referencing `_UserImageModel` (lines 366-369):
    ```python
    images = session.query(_UserImageModel).filter(_UserImageModel.user_id == user.id).all()
    for img in images:
        if img.image_path:
            files_to_delete.append(img.image_path)
    ```

- [ ] **Step 3: Commit changes**
  ```bash
  git add ai_server/app/models.py ai_server/app/database.py
  git commit -m "refactor(db): remove UserImage model and clean up references"
  ```

---

### Task 2: Update Database Unit Tests

**Files:**
- Modify: `ai_server/tests/test_database.py`

**Interfaces:**
- Consumes: Updated database models.
- Produces: Test assertions checking `users` and `registration_queue` cleanup without `UserImage`.

- [ ] **Step 1: Modify test_database.py**
  Update `ai_server/tests/test_database.py`:
  - In `test_delete_student_sqlite` (lines 76-125), remove all imports, instantiations, queries, and assertions related to `UserImage`. Only test the deletion of `User`, `RegistrationQueue`, and their files.
  - In `test_sqlite_foreign_keys_enforcement` (lines 138-176), remove `UserImage` model references and assertions (e.g. `img = UserImage(...)` and `img_count = ...`). Keep `CheckInLog` foreign key cascade testing intact.
  - In `test_delete_student_sqlite_transaction_safety` (lines 178-210), remove `UserImage` instantiation and assertions. Instead of `UserImage`, verify transaction rollback safety using a dummy file in `RegistrationQueue`.

- [ ] **Step 2: Run pytest to verify all tests pass**
  Run: `venv\Scripts\python -m pytest`
  Expected: PASS

- [ ] **Step 3: Commit changes**
  ```bash
  git add ai_server/tests/test_database.py
  git commit -m "test(db): update database tests to match removed UserImage schema"
  ```

---

### Task 3: Drop the `user_images` Table in Supabase

**Files:**
- Execute SQL command against the Supabase database.

- [ ] **Step 1: Execute DROP TABLE command**
  Run SQL script via MCP tool or DB console:
  ```sql
  DROP TABLE IF EXISTS user_images CASCADE;
  ```

- [ ] **Step 2: Verify database table list**
  Query database to verify `user_images` is successfully removed.
