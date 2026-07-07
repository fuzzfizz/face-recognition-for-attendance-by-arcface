# Google Cloud VM Deployment Guide (MySQL Split VM Deployment)

This guide provides step-by-step instructions on how to deploy the MySQL BLOB database inside a Docker container on a dedicated database VM, and connect the FastAPI AI application server running on a separate application VM.

---

## 1. Database VM Deployment (MySQL)

### Create the Database VM
1. Go to GCP Console -> **Compute Engine** -> **VM instances** -> **Create Instance**.
2. **OS Image**: Select **Ubuntu 20.04 LTS** or **Ubuntu 22.04 LTS** (x86_64).
3. **Machine Type**: An `e2-small` or `e2-medium` machine is sufficient for MySQL database hosting.
4. **Firewall Settings**: Configure VPC firewall rules to allow incoming TCP traffic on port `3306` (MySQL port) from your **Application VM IP** (or restricted internal VPC network).

### Setup and Deploy MySQL Container
SSH into your **Database VM** and run:

```bash
# 1. Update system packages
sudo apt-get update

# 2. Install Docker and Docker Compose
sudo apt-get install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER # Log out and log back in for changes

# 3. Clone repository and navigate to the directory
git clone <your-repository-url> face-recognition
cd face-recognition/database_mysql

# 4. Start the MySQL database container
docker-compose up --build -d

# 5. Verify the database is running
docker-compose ps
```

The database container will build, expose port `3306`, mount the `mysql_data` volume for persistence, and automatically initialize the schema and tables defined in `init_schema.sql`.

---

## 2. Application VM Deployment (FastAPI AI Server)

### Create the Application VM
1. Go to GCP Console -> **Compute Engine** -> **VM instances** -> **Create Instance**.
2. **Machine Type**: At least `e2-medium` (2 vCPUs, 4 GB RAM) is recommended to support deep learning inference (InsightFace/ONNXRuntime).
3. **Firewall Settings**: Configure firewall rules to allow incoming TCP traffic on port `8000` (FastAPI backend port).

### Setup and Run FastAPI App Server
SSH into your **Application VM** and run:

```bash
# 1. Clone repository
git clone <your-repository-url> face-recognition
cd face-recognition/ai_server

# 2. Install system libraries for OpenCV and dependencies
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv libgl1-mesa-glx libglib2.0-0

# 3. Setup Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configure Environment Variables
Create the server's `.env` configuration file inside `ai_server/`:
```bash
cp .env.example .env
```
Edit `.env` to connect to your **Database VM IP**:
```ini
# Database Mode Configuration
DB_MODE=mysql

# Point to your Database VM external/internal IP address
MYSQL_URL=mysql+pymysql://face_admin:SecurePassword123!@<DB_VM_IP>:3306/face_attendance

# Admin API Key (used for admin-guarded API endpoints like /train-now)
ADMIN_API_KEY=my-secure-admin-token-12345

# Server binding configurations
HOST=0.0.0.0
PORT=8000
```

### Start the FastAPI Server
```bash
# Run using uvicorn in production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 3. Verification & Web Dashboard Integration

### Verification
1. Access the health check from a client machine:
   ```bash
   curl http://<APP_VM_IP>:8000/
   ```
   **Expected Response:** `{"status": "ok", "mode": "mysql"}`
2. Import the Postman collection and test endpoints via your API client.

### Web Dashboard Integration (MySQL Mode)
Update **`web_dashboard/config.php`** to connect directly to the **Database VM IP**:
```php
<?php
define('MYSQL_HOST', '<DB_VM_IP>'); // Database VM IP
define('MYSQL_DB', 'face_attendance');
define('MYSQL_USER', 'face_admin');
define('MYSQL_PASS', 'SecurePassword123!');

define('AI_SERVER_URL', 'http://<APP_VM_IP>:8000'); // Application VM IP
define('ADMIN_API_KEY', 'my-secure-admin-token-12345');
```
*(The MySQL helper methods in config.php will execute queries via PDO directly to the database container on the database VM).*
