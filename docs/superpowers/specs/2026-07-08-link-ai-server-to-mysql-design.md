# Design Spec: Link AI Server to MySQL Database

* **Date**: 2026-07-08
* **Status**: Approved by User
* **Target File**: `ai_server/.env`

## 1. Overview
The goal is to configure the FastAPI AI Server to connect to the MySQL database instance running on a remote GCP VM at `136.110.6.161:3306` using the database credentials defined in `database_mysql/.env`.

## 2. Configuration Details
We will edit `ai_server/.env` to:
1. Set the database mode to MySQL: `DB_MODE=mysql`
2. Define the database URL using `mysql+pymysql` protocol:
   ```ini
   MYSQL_URL=mysql+pymysql://face_admin:SecurePassword123!@136.110.6.161:3306/face_attendance
   ```

## 3. Implementation Verification
We can verify the connectivity by running:
1. `database_mysql/connection_test.py` with the appropriate host parameter.
2. The AI server locally (or on the VM) to ensure it initializes the tables on MySQL and starts up successfully.
