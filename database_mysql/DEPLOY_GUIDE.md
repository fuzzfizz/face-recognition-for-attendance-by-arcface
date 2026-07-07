# Google Cloud VM Deployment Guide (MySQL + Docker)

This guide provides step-by-step instructions on how to deploy the Face Recognition AI Server and MySQL BLOB database stack to a Google Cloud Platform (GCP) Compute Engine VM instance.

---

## 1. VM Prerequisites & GCP Configuration

### Create VM Instance
1. Go to GCP Console -> **Compute Engine** -> **VM instances** -> **Create Instance**.
2. **OS Image**: Select **Ubuntu 20.04 LTS** or **Ubuntu 22.04 LTS** (x86_64).
3. **Machine Type**: At least `e2-medium` (2 vCPUs, 4 GB RAM) is recommended to support deep learning inference (InsightFace/ONNXRuntime) and MySQL concurrently.
4. **Firewall Settings**:
   - Check **Allow HTTP traffic**.
   - Check **Allow HTTPS traffic**.

### Configure GCP Firewall Rules
The FastAPI app server runs on port `8000` by default. You must configure GCP to allow traffic on this port:
1. Go to GCP Console -> **VPC network** -> **Firewall**.
2. Click **Create Firewall Rule**:
   - **Name**: `allow-face-recognition-api`
   - **Targets**: `All instances in the network` (or specify VM target tag)
   - **Source IPv4 ranges**: `0.0.0.0/0` (or your client IPs for restricted access)
   - **Protocols and ports**: Under TCP, check port `8000`.
3. Click **Create**.

---

## 2. Docker & Environment Setup

Connect to your GCP VM via SSH and execute the following commands:

### Install Docker and Docker Compose
```bash
# Update repositories
sudo apt-get update

# Install Docker
sudo apt-get install -y docker.io docker-compose

# Start and enable Docker daemon
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to the docker group (avoids needing sudo for docker commands)
sudo usermod -aG docker $USER
# Log out and log back in to apply group changes
```

### Clone the Repository
Clone the repository containing the codebase to your VM:
```bash
git clone <your-repository-url> face-recognition
cd face-recognition/database_mysql
```

### Configure Environment Variables
Create the server's `.env` configuration inside the `ai_server/` directory:
```bash
cp ../ai_server/.env.example ../ai_server/.env
```
Edit `../ai_server/.env` to configure credentials:
```ini
# Database Mode Configuration
DB_MODE=mysql
MYSQL_URL=mysql+pymysql://face_admin:SecurePassword123!@db/face_attendance

# Admin API Key (used for admin-guarded API endpoints like /train-now)
ADMIN_API_KEY=my-secure-admin-token-12345

# Server binding configurations
HOST=0.0.0.0
PORT=8000
```
> [!IMPORTANT]
> Change the passwords (`SecurePassword123!`) to strong values before running in production.

---

## 3. Deploy using Docker Compose

Deploy the database and FastAPI server using Docker Compose from the `database_mysql/` directory. The database container will automatically run the schema migrations on startup.

```bash
# Build and run the containers in detached mode (background)
docker-compose up --build -d

# Verify that the containers are running
docker-compose ps
```

### Checking Deployment Logs
You can view active logs of the application or database using:
```bash
# View FastAPI server logs
docker-compose logs -f app

# View MySQL database logs
docker-compose logs -f db
```

---

## 4. Verification & Testing

### Health Check Endpoint
Once the containers are running, query the health check endpoint from your local machine:
```bash
curl http://<VM_EXTERNAL_IP>:8000/
```
**Expected Response:**
```json
{"status": "ok", "mode": "mysql"}
```

### Test API Functionality
Import the Postman collection and environment files in `ai_server/` (configured with `base_url = http://<VM_EXTERNAL_IP>:8000`) to test verification, registration, and logs.

---

## 5. Web Dashboard Integration (MySQL Mode)

Since the database has been migrated from Supabase to MySQL, you will need to update the PHP Web Dashboard to query the local MySQL database directly instead of Supabase's REST endpoints.

Modify **`web_dashboard/config.php`** to connect to MySQL via PDO:

```php
<?php
// Define MySQL Database Credentials
define('MYSQL_HOST', 'localhost'); // Change to MySQL server IP if hosted separately
define('MYSQL_DB', 'face_attendance');
define('MYSQL_USER', 'face_admin');
define('MYSQL_PASS', 'SecurePassword123!');

define('AI_SERVER_URL', 'http://localhost:8000'); // FastAPI server address
define('ADMIN_API_KEY', 'my-secure-admin-token-12345');

// MySQL connection singleton helper
function get_mysql_connection() {
    static $pdo = null;
    if ($pdo === null) {
        try {
            $dsn = "mysql:host=" . MYSQL_HOST . ";dbname=" . MYSQL_DB . ";charset=utf8mb4";
            $pdo = new PDO($dsn, MYSQL_USER, MYSQL_PASS, [
                PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES   => false,
            ]);
        } catch (PDOException $e) {
            die("Database connection failed: " . $e->getMessage());
        }
    }
    return $pdo;
}

// Override supabase_get with direct PDO MySQL queries
function supabase_get(string $table, array $params = []): array {
    $db = get_mysql_connection();
    
    // Convert Supabase parameters (like order, select, limit) to SQL query parts
    $sql = "SELECT * FROM " . preg_replace('/[^a-zA-Z0-9_]/', '', $table);
    $conditions = [];
    $sqlParams = [];
    
    // Example: parse simple filters (like student_id => not.is.null)
    if (isset($params['student_id']) && $params['student_id'] === 'not.is.null') {
        $conditions[] = "student_id IS NOT NULL";
    }
    
    if (!empty($conditions)) {
        $sql .= " WHERE " . implode(" AND ", $conditions);
    }
    
    // Sort
    if (isset($params['order'])) {
        // e.g. "timestamp.desc" -> "ORDER BY timestamp DESC"
        $parts = explode('.', $params['order']);
        $col = preg_replace('/[^a-zA-Z0-9_]/', '', $parts[0]);
        $dir = (isset($parts[1]) && strtolower($parts[1]) === 'desc') ? 'DESC' : 'ASC';
        $sql .= " ORDER BY $col $dir";
    }
    
    // Limit & Offset
    if (isset($params['limit'])) {
        $sql .= " LIMIT " . (int)$params['limit'];
    }
    if (isset($params['offset'])) {
        $sql .= " OFFSET " . (int)$params['offset'];
    }
    
    try {
        $stmt = $db->prepare($sql);
        $stmt->execute($sqlParams);
        return [
            'data' => $stmt->fetchAll(),
            'error' => null,
            'status' => 200
        ];
    } catch (Exception $e) {
        return [
            'data' => [],
            'error' => $e->getMessage(),
            'status' => 500
        ];
    }
}

// Override supabase_count with direct PDO MySQL queries
function supabase_count(string $table, array $params = []): int {
    $db = get_mysql_connection();
    $sql = "SELECT COUNT(*) FROM " . preg_replace('/[^a-zA-Z0-9_]/', '', $table);
    $conditions = [];
    $sqlParams = [];
    
    if (isset($params['student_id']) && $params['student_id'] === 'not.is.null') {
        $conditions[] = "student_id IS NOT NULL";
    }
    // Parse timestamp filter if present
    if (isset($params['timestamp'])) {
        // Simple example parser: "gte.2026-07-07..."
        $parts = explode('.', $params['timestamp']);
        if ($parts[0] === 'gte') {
            $conditions[] = "timestamp >= :t_gte";
            $sqlParams['t_gte'] = $parts[1];
        }
    }
    
    if (!empty($conditions)) {
        $sql .= " WHERE " . implode(" AND ", $conditions);
    }
    
    try {
        $stmt = $db->prepare($sql);
        $stmt->execute($sqlParams);
        return (int)$stmt->fetchColumn();
    } catch (Exception $e) {
        return 0;
    }
}
```
Using this config override, the entire Web Dashboard will immediately transition to using your local MySQL database with zero changes needed to the actual application layout page files!
