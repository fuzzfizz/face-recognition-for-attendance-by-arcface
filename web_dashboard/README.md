# FaceAttend Web Dashboard

A **PHP + MySQL** web dashboard for the face recognition attendance system. Provides live attendance monitoring, student management, registration queue oversight, and admin controls — all from a modern, responsive UI with light/dark theme support.

---

## Features

### Dashboard Stats
- **Total Students** — Number of registered users in the database.
- **Today's Check-ins** — Real-time count of check-ins for the current day (UTC).
- **Pending Queue** — Number of registration queue items awaiting processing.
- **Last Check-in** — Name and relative time of the most recent attendance event.

### Attendance Logs
- **Live auto-refresh** — Polls every 5 seconds (pauses when the browser tab is hidden).
- **Date filter** — Pick any date to view check-in logs.
- **Device filter** — Dynamically populated from all devices seen in logs.
- **Pagination** — 20 records per page with page navigation.
- **Similarity score badges** — Color-coded confidence levels: Green >= 0.75 high, Yellow 0.60-0.74 medium, Red < 0.60 low.
- **New-row highlighting** — Fresh check-ins (since the last poll) are visually emphasized.

### Student Management
- View all registered students with name, registration date, and latest queue status.
- **Delete students** (admin-protected) — Removes the student record and their photos from the AI server; check-in history is preserved.

### Registration Queue
- **Status filter** — Filter by pending, completed, or failed.
- **Expandable detail rows** — Click any student to reveal per-photo failure checklists.
- **Failure Checklist tab** — Visual step-by-step breakdown (face detection, single face, duplicate check, quota check) with pass/fail/skip indicators.
- **Raw Data tab** — Full JSON response for debugging.
- **Photo viewer** — Dropdown per student to open any uploaded registration photo in a new tab.
- **Force Training** — Admin-protected button to immediately process all pending registrations.

### Theme Toggle
- Dark theme (default) and light theme.
- Persisted in localStorage.
- Smooth CSS transitions on all themed elements.

### Admin API Key Management
- Inline input in the top bar; saved to localStorage.
- Used to authorize Force Training and Delete Student actions.
- Automatically prompts if the key is missing when an admin action is triggered.

### Automated Setup Detection
- If config.php is missing, the dashboard displays a setup page with instructions instead of a blank error.

## Requirements

- **PHP 8.0+** with pdo_mysql extension and curl extension
- **MySQL 8.0+** database (face_attendance schema with tables: users, check_in_logs, registration_queue)
- **AI Server** (Face Recognition API) — reachable HTTP endpoint for training and registration operations
- **Web Server** — Apache (with mod_rewrite) or Nginx (for production)
- **Docker** (optional) — Docker Engine 20.10+ and Docker Compose v2+

---

## Directory Structure

```
web_dashboard/
├── api/
│   ├── attendance.php       # Fetch attendance logs (paginated, filtered by date/device)
│   ├── delete_student.php   # Delete student (proxies to AI server, admin-protected)
│   ├── queue.php            # Fetch registration queue (filtered by status)
│   ├── queue_image.php      # Serve registration photo blobs from database
│   ├── stats.php            # Dashboard statistics (counts, last check-in)
│   ├── students.php         # List all registered students
│   └── train.php            # Trigger AI model training (admin-protected)
├── assets/
│   ├── style.css            # Complete stylesheet (dark/light themes, responsive)
│   ├── dashboard-utils.js   # Formatting, DOM helpers, theme toggle, admin key
│   ├── dashboard-api.js     # Data fetching, tab switching, pagination, polling
│   └── dashboard-queue.js   # Queue expand/collapse, checklists, force training, delete
├── config.php               # Database credentials and environment config (gitignored)
├── config.example.php       # Template for config.php
├── index.php                # Main dashboard entry point
├── .htaccess                # Apache: blocks direct HTTP access to config.php
├── Dockerfile               # php:8.2-apache Docker image
├── docker-compose.yml       # Docker Compose service definition
├── .dockerignore            # Docker build exclusions
├── .gitignore               # Excludes config.php and DEPLOY.md
├── DEPLOY.md                # VM deployment instructions (Docker)
└── README.md                # This file
```

---

## Quick Start (Native PHP)

### 1. Clone and Configure

```bash
cd web_dashboard
cp config.example.php config.php
```

### 2. Edit config.php

Set your MySQL connection details and AI server URL:

```php
define('DB_HOST', '127.0.0.1');
define('DB_PORT', '3306');
define('DB_USER', 'face_admin');
define('DB_PASS', 'your-secure-password');
define('DB_NAME', 'face_attendance');
define('AI_SERVER_URL', 'http://your-ai-server:8000');
define('ADMIN_API_KEY', 'your-secret-admin-key');
```

> **Security:** config.php is listed in .gitignore and must never be committed. It contains database passwords and API secrets.

### 3. Run Development Server

```bash
php -S localhost:8080
```

Open http://localhost:8080 in your browser.

---

## Docker Deployment

### Environment Variables

The Docker image reads configuration from environment variables. These can be set in docker-compose.yml or passed via docker run -e.

| Variable | Description |
|---|---|
| DB_HOST | MySQL server hostname |
| DB_PORT | MySQL server port |
| DB_USER | MySQL username |
| DB_PASS | MySQL password |
| DB_NAME | MySQL database name |
| AI_SERVER_URL | Face recognition AI server URL |
| ADMIN_API_KEY | Secret key for admin actions |

### Using Docker Compose (Recommended)

Edit docker-compose.yml with your environment values:

```yaml
version: "3.8"

services:
  web_dashboard:
    image: athit0900/face-recognition-ai-web-dashboard:1.0.0
    container_name: face-recognition-ai-web-dashboard
    restart: unless-stopped
    ports:
      - "8080:80"
    environment:
      - DB_HOST=your-mysql-host
      - DB_PORT=3306
      - DB_USER=face_admin
      - DB_PASS=your-secure-password
      - DB_NAME=face_attendance
      - AI_SERVER_URL=http://your-ai-server:8000
      - ADMIN_API_KEY=your-secret-admin-key
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Then run:

```bash
docker compose up -d --build
```

### Building and Running Manually

```bash
# Build the image
docker build -t face-attend-dashboard .

# Run the container
docker run -d   --name face-recognition-ai-web-dashboard   -p 8080:80   -e DB_HOST=your-mysql-host   -e DB_PORT=3306   -e DB_USER=face_admin   -e DB_PASS=your-secure-password   -e DB_NAME=face_attendance   -e AI_SERVER_URL=http://your-ai-server:8000   -e ADMIN_API_KEY=your-secret-admin-key   face-attend-dashboard
```

### Management Commands

| Command | Description |
|---|---|
| docker compose ps | Check container status |
| docker compose logs -f | Follow live logs |
| docker compose exec web_dashboard bash | Shell into the container |
| docker compose restart | Restart the service |
| docker compose down | Stop and remove the container |

---

## Web Server Configuration

### Apache (with .htaccess)

The included .htaccess file blocks direct HTTP access to config.php:

```apache
<Files "config.php">
    <IfModule authz_core_module>
        Require all denied
    </IfModule>
    <IfModule !authz_core_module>
        Order deny,allow
        Deny from all
    </IfModule>
</Files>
```

> Ensure AllowOverride All or AllowOverride Limit is enabled in your Apache virtual host configuration and mod_rewrite is loaded.

### Nginx

Add this location block to your server configuration to block config.php:

```nginx
location ~ /config\.php$ {
    deny all;
    return 404;
}
```

### Pointing the Document Root

Configure your web server to serve from the web_dashboard/ directory:

```apache
# Apache VirtualHost
DocumentRoot /var/www/web_dashboard
```

```nginx
# Nginx server block
root /var/www/web_dashboard;
```

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| api/stats.php | GET | Returns total students, today's check-ins, pending queue count, and last check-in info |
| api/attendance.php | GET | Paginated attendance logs for a given date, optionally filtered by device |
| api/students.php | GET | List all registered students with their latest queue status |
| api/queue.php | GET | Registration queue items, optionally filtered by status |
| api/queue_image.php | GET | Serve a registration photo blob from the database by queue item ID |
| api/train.php | POST | Trigger force training — requires X-Admin-Key header |
| api/delete_student.php | POST | Delete a student — requires X-Admin-Key header |

---

## Security Notes

1. **config.php is sensitive.** It contains database credentials and the admin API key. It is:
   - Blocked from public HTTP access via .htaccess (Apache) or Nginx rule.
   - Excluded from Git by .gitignore.
   - Excluded from Docker images by .dockerignore.

2. **Admin API Key.** The ADMIN_API_KEY constant (or environment variable) protects destructive actions (Force Training, Delete Student). The frontend sends it via the X-Admin-Key HTTP header. It is validated server-side using hash_equals() to prevent timing attacks.

3. **Database credentials** are passed via environment variables in Docker, keeping secrets out of the image layer.

4. **Input validation** is enforced on all API endpoints:
   - Date format is validated with regex.
   - Pagination parameters are clamped (per_page max 100).
   - Queue status filter is whitelisted against allowed values.
   - SQL uses prepared statements everywhere (no raw string concatenation).

5. **CORS and caching:** API responses disable browser caching (Cache-Control: no-store) for stats and logs to ensure fresh data.

6. **Firewall.** In production, restrict port 8080 (or your host port) to trusted IP ranges.

7. **TLS/HTTPS.** Always deploy behind a reverse proxy with HTTPS enabled to protect credentials and API keys in transit.

---

## Troubleshooting

| Problem | Likely Cause | Solution |
|---|---|---|
| Setup Required page shown | config.php does not exist | Copy config.example.php to config.php and fill in credentials |
| Database connection failed | MySQL credentials or host incorrect | Verify DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME in config.php |
| 500 Internal Server Error on Docker | Environment variables not set | Pass all required DB_* env vars to the container |
| Stats show dash | Database tables empty or unreachable | Check that users, check_in_logs, registration_queue tables exist |
| Unauthorized: Invalid Admin Key | Wrong or missing admin key | Set the correct key via the top-bar input or clear localStorage and re-enter |
| Force Training fails | AI server unreachable | Verify AI_SERVER_URL and that the AI server is running |
| .htaccess not working | Apache AllowOverride is off | Enable AllowOverride All in your Apache virtual host config |

---

## License

Part of the face-recognition-for-attendance-by-arcface project.
