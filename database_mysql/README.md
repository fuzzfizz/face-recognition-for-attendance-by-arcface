# FaceAttend - MySQL Database Module

> MySQL-backed persistence layer for the Face Recognition Attendance System (FaceAttend).
> Handles user registration, face photo queueing, and check-in audit logging with full BLOB support.

---

## Table of Contents

- [Overview](#overview)
- [Module Contents](#module-contents)
- [Quick Start with Docker](#quick-start-with-docker)
- [Environment Variables](#environment-variables)
- [Database Schema](#database-schema)
- [Connection Test](#connection-test)
- [Deployment Options](#deployment-options)
- [Security Notes](#security-notes)
- [Troubleshooting](#troubleshooting)

---

## Overview


The `database_mysql` module provides the complete MySQL database setup for the FaceAttend system. It ships with:

- A **Docker Compose** configuration for one-command local or cloud deployment.
- A **custom Dockerfile** that bundles the schema init script so tables are auto-created on first start.
- A **well-normalised schema** with three tables covering users, pending registration photos, and attendance check-in logs.
- A **connection test tool** that verifies MySQL connectivity and exercises all CRUD operations -- including LONGBLOB storage and foreign-key cascade behaviour.
- A **VM setup script** for bare-metal / VM installations.
- A **detailed GCP deployment guide** for a split-architecture (database VM + application VM).

**Key features:**

- MySQL 8.0 base image.
- Persistent volume for data survival across restarts.
- `LONGBLOB` column for storing face image data directly in the database.
- Foreign key with `ON DELETE SET NULL` -- deleting a user preserves their historical check-in logs.
- Indexed columns for fast lookups on `student_id`, `status`, and `timestamp DESC`.

---

## Module Contents

| File | Purpose |
|------|---------|
| `.env` / `.env.example` | Environment variable definitions (database name, user, passwords) |
| `docker-compose.yml` | Docker Compose service definition for MySQL 8.0 |
| `Dockerfile` | Custom image that copies `init_schema.sql` into the auto-init directory |
| `init_schema.sql` | Database and table creation script (idempotent -- uses `IF NOT EXISTS`) |
| `connection_test.py` | Python script for connectivity and CRUD verification |
| `setup_vm.sh` | Bash script for installing MySQL directly on a Linux VM |
| `DEPLOY_GUIDE.md` | Step-by-step Google Cloud Platform split-VM deployment guide |
---

## Quick Start with Docker

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed.

### Steps

```bash
# 1. Navigate to the module
cd database_mysql

# 2. (Optional) Edit environment variables
cp .env.example .env

# 3. Launch the database container
docker-compose up --build -d

# 4. Verify it is running
docker-compose ps

# 5. Check the logs for schema initialisation
docker-compose logs db
```

The container will:

1. Start a MySQL 8.0 server.
2. Create the `face_attendance` database.
3. Run `init_schema.sql` to create the three tables.
4. Expose port `3306` on your host.

Stop the container:

```bash
docker-compose down
```

To destroy the data volume as well:

```bash
docker-compose down -v
```
---

## Environment Variables

These are consumed by `docker-compose.yml` and `setup_vm.sh`:

| Variable | Description | Default |
|----------|-------------|---------|
| `MYSQL_DATABASE` | Name of the attendance database | `face_attendance` |
| `MYSQL_USER` | Application database user | `face_admin` |
| `MYSQL_PASSWORD` | Password for the application user | `your_secure_password` |
| `MYSQL_ROOT_PASSWORD` | Root password for the MySQL server | `your_root_password` |

Example `.env`:

```ini
MYSQL_DATABASE=face_attendance
MYSQL_USER=face_admin
MYSQL_PASSWORD=SecurePassword123!
MYSQL_ROOT_PASSWORD=SuperRootPass!
```
---

## Database Schema

The schema is auto-initialised by `init_schema.sql` on first container start. It contains three tables:

### `users`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `INT` | PRIMARY KEY, AUTO_INCREMENT |
| `student_id` | `VARCHAR(50)` | UNIQUE, NOT NULL, INDEXED |
| `name` | `VARCHAR(100)` | NULLABLE |
| `created_at` | `TIMESTAMP` | DEFAULT CURRENT_TIMESTAMP |

### `registration_queue`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `INT` | PRIMARY KEY, AUTO_INCREMENT |
| `student_id` | `VARCHAR(50)` | NOT NULL, INDEXED |
| `image_path` | `VARCHAR(255)` | NULLABLE |
| `image_blob` | `LONGBLOB` | Raw face image bytes stored inline |
| `status` | `VARCHAR(20)` | DEFAULT `pending` |
| `error_message` | `TEXT` | NULLABLE |
| `created_at` | `TIMESTAMP` | DEFAULT CURRENT_TIMESTAMP |
| `processed_at` | `TIMESTAMP` | NULLABLE |

### `check_in_logs`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `INT` | PRIMARY KEY, AUTO_INCREMENT |
| `user_id` | `INT` | FOREIGN KEY -> users.id ON DELETE SET NULL |
| `student_id` | `VARCHAR(50)` | NULLABLE |
| `similarity_score` | `DOUBLE` | NULLABLE |
| `device_id` | `VARCHAR(50)` | NULLABLE |
| `error_message` | `VARCHAR(255)` | NULLABLE |
| `timestamp` | `TIMESTAMP` | DEFAULT CURRENT_TIMESTAMP, INDEXED DESC |
---

## Connection Test

`connection_test.py` validates connectivity and exercises CRUD + BLOB operations.

Usage:

```bash
# Test local SQLite fallback (does not require MySQL running)
python connection_test.py --sqlite

# Test MySQL on localhost:3306
python connection_test.py \
  --host localhost \
  --port 3306 \
  --user face_admin \
  --password SecurePassword123! \
  --database face_attendance
```

What it checks:

1. Inserts a test user and verifies the record.
2. Inserts a registration queue item with a sample BLOB payload and updates its status.
3. Inserts a check-in log and verifies the similarity score and device ID.
4. Deletes the test user and confirms that `check_in_logs.user_id` is set to `NULL` (cascade).
---

## Deployment Options

### Local Development (Docker)

Use the Quick Start above. Point `ai_server` to `localhost:3306` via `MYSQL_URL`.

### VM Setup (`setup_vm.sh`)

For bare-metal Ubuntu VMs without Docker:

```bash
sudo bash setup_vm.sh
```

This script:

1. Installs `mysql-server` and `python3-pip`.
2. Binds MySQL to `0.0.0.0:3306` for remote application access.
3. Creates the `face_attendance` database and `face_admin` user.
4. Runs `init_schema.sql`.
5. Prints the connection details.

### Google Cloud Platform (Split VM)

See [`DEPLOY_GUIDE.md`](DEPLOY_GUIDE.md) for production guidance.

Recommended topology:

```
+---------------------------+       +-------------------------------+
|   Database VM             |       |   Application VM              |
|   MySQL Docker            |<------+   FastAPI AI Server           |
|   Port 3306               |       |   PHP Web Dashboard           |
|   (internal VPC only)     |       |   Port 8000 and 8080          |
+---------------------------+       +-------------------------------+
```
---

## Security Notes

- **Passwords**: The default passwords in `.env.example` and `DEPLOY_GUIDE.md` are placeholders. Change them before exposing the database to any network.
- **Network**: In production, allow MySQL port `3306` only from the application VM IP. Never open it to `0.0.0.0/0` on the public internet.
- **Volume backups**: The `mysql_data` Docker volume persists row data. Back it up periodically.
- **Least privilege**: The `face_admin` user is granted only `ALL PRIVILEGES ON face_attendance.*` rather than global access.
---

## Troubleshooting

| Problem | Likely Cause | Solution |
|---------|--------------|----------|
| `Can't connect to MySQL server` | Wrong host/port, firewall, or password | Run `docker-compose ps`, check firewall rules, verify `.env` |
| `Unknown column 'image_blob'` | Schema init did not run | Remove the container/volume and restart with `docker-compose up --build -d` |
| `Access denied for user 'face_admin'` | Password mismatch | Inspect `.env` and `docker-compose.yml` for consistency |
| `LONGBLOB truncation warning` | Client MySQL connector buffer too small | Increase `max_allowed_packet` in the MySQL server config |
| Volume keeps old data | Schema changed but volume not reset | Run `docker-compose down -v` and restart |
---

## Related Documentation

- [`../ai_server/README.md`](ai_server/README.md) -- AI server setup, API reference, and self-healing behaviour
- [`../web_dashboard/README.md`](web_dashboard/README.md) -- PHP dashboard configuration and deployment
- [`DEPLOY_GUIDE.md`](DEPLOY_GUIDE.md) -- Full Google Cloud split-VM deployment guide
- [`../README.md`](README.md) -- Project overview and architecture
