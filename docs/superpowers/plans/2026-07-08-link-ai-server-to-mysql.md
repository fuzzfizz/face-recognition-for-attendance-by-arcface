# Link AI Server to MySQL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Configure the FastAPI AI Server to connect to the MySQL database.

**Architecture:** We will configure the database mode in the AI server `.env` file to use `mysql` and supply the MySQL connection URI string pointing to the remote DB VM.

**Tech Stack:** Python 3, FastAPI, SQLAlchemy, PyMySQL.

## Global Constraints

* The database configuration must use `DB_MODE=mysql`.
* The connection string must use `pymysql` driver (`mysql+pymysql://`).

---

### Task 1: Update AI Server Env Configuration

**Files:**
- Modify: `ai_server/.env`

**Interfaces:**
- Consumes: None
- Produces: Configure database connectivity to remote MySQL instance

- [ ] **Step 1: Backup current `.env` file**

Create a backup of the existing `ai_server/.env` file to `ai_server/.env.bak` to preserve the original Supabase settings.

Run:
```powershell
Copy-Item ai_server/.env ai_server/.env.bak
```

- [ ] **Step 2: Update configuration in `ai_server/.env`**

Modify the contents of `ai_server/.env` to include the MySQL database configuration. Replace the Supabase credentials or append these lines:

```ini
# Database Mode Configuration
DB_MODE=mysql

# MySQL Database URL
MYSQL_URL=mysql+pymysql://face_admin:SecurePassword123!@136.110.6.161:3306/face_attendance
```

- [ ] **Step 3: Run test suite to verify no regressions**

Run the existing tests in `ai_server/tests` to make sure all units function correctly and that loading the environment works.

Run:
```powershell
cd ai_server
pytest tests/ -v
```
Expected: All tests pass.

- [ ] **Step 4: Commit changes to Git**

Commit the updated `.env` example or configuration changes. Since `.env` is typically gitignored, we will also verify if `.env.example` has been updated or check `git status`. Let's commit the updated files (such as `.env.example` if applicable, or we can just commit our change to a local testing branch/docs).

Run:
```bash
git add ai_server/.env.example
git commit -m "config: update env.example with MySQL database link"
```
