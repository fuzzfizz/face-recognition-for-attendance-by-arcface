# Deploying FaceAttend Web Dashboard on a VM

This guide details how to build, run, and manage the PHP Web Dashboard inside a Docker container on a Virtual Machine (VM).

---

## 1. Prerequisites

Ensure your target VM has the following installed:
* **Docker**: [Docker Install Guide](https://docs.docker.com/engine/install/)
* **Docker Compose**: Included with Docker Desktop/Compose plugin.

Verify installation by running:
```bash
docker --version
docker compose version
```

---

## 2. Configuration (`docker-compose.yml`)

The web dashboard is fully configured via environment variables inside [docker-compose.yml](file:///D:/AIproject/web_dashboard/docker-compose.yml). Open this file on your VM and customize the following environment variables:

| Variable | Description | Default Value |
| --- | --- | --- |
| `DB_HOST` | MySQL Server Host Address | `136.110.6.161` |
| `DB_PORT` | MySQL Server Port | `3306` |
| `DB_USER` | MySQL Username | `face_admin` |
| `DB_PASS` | MySQL Password | `SecurePassword123!` |
| `DB_NAME` | MySQL Database Name | `face_attendance` |
| `AI_SERVER_URL` | AI Server Endpoint URL | `http://34.124.240.7:8000` |
| `ADMIN_API_KEY` | Secret admin api key for administrative actions | `my-secure-admin-token-12345` |

---

## 3. Build & Deploy

Navigate to the directory containing `docker-compose.yml` and execute:

### Step 3.1: Build and start the container
```bash
docker compose up -d --build
```
* `-d` runs the container in background (detached) mode.
* `--build` forces a rebuild of the Docker image to ensure the latest changes are deployed.

### Step 3.2: Verify container status
Check that the container is up and running:
```bash
docker compose ps
```
The output should list the `faceattend_web_dashboard` container as `Up` and listening on port `8080` (or whichever host port you mapped to `80`).

---

## 4. Monitoring & Troubleshooting

### View logs in real-time
```bash
docker compose logs -f
```

### Access Apache server bash inside the container
```bash
docker compose exec web_dashboard bash
```

### Restarting the service
```bash
docker compose restart
```

### Tear down the deployment
```bash
docker compose down
```

---

## 5. Security Recommendations

1. **Firewall Rules**: Ensure port `8080` (or target host port) is open in your VM's security group/firewall for incoming HTTP traffic.
2. **Access Control**: Do NOT expose `config.php` publicly. The included `.htaccess` file prevents public HTTP access to it inside the container.
3. **Secrets Management**: For production environments, consider moving DB and API passwords out of `docker-compose.yml` into a secure `.env` file or environment secret store.