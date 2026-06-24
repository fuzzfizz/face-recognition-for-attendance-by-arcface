# Deploy on VM — Face Recognition AI Server

คู่มือการติดตั้งโปรเจค Face Recognition AI Server บน Virtual Machine (VM)
รองรับ 2 รูปแบบ: **Docker** (แนะนำ) และ **Bare Metal** (ไม่มี Docker)

---

## 1. ข้อกำหนด VM (Minimum Requirements)

| Resource | Minimum              | Recommended                  |
| -------- | -------------------- | ---------------------------- |
| OS       | Ubuntu 22.04 LTS     | Ubuntu 22.04 LTS / Debian 12 |
| CPU      | 2 cores              | 4 cores                      |
| RAM      | 4 GB                 | 8 GB                         |
| Storage  | 20 GB                | 50 GB (SSD)                  |
| Network  | Public IP, port 8000 | Domain + SSL (port 443)      |
| Docker   | 24+ (ถ้าใช้ Docker)  | 24+                          |

> **หมายเหตุ**: ถ้าใช้ CPU เท่านั้น (ไม่ใช้ GPU) ต้องใช้ RAM พอสมควรเพราะ InsightFace ใช้ ONNX Runtime บน CPU

---

## 2. Architecture บน VM

```
┌─────────────────────────────────────────────┐
│                  VM Server                   │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │   Nginx (Reverse Proxy) [port 443]   │   │
│  │   • SSL Termination (Let's Encrypt)  │   │
│  │   • Rate Limiting                    │   │
│  └──────────────┬───────────────────────┘   │
│                 │                            │
│  ┌──────────────▼───────────────────────┐   │
│  │   Face Recognition AI Server         │   │
│  │   (Docker Container or systemd)      │   │
│  │   • FastAPI + Uvicorn [port 8000]    │   │
│  │   • InsightFace (ArcFace)            │   │
│  │   • Local .pkl embeddings            │   │
│  └──────────────┬───────────────────────┘   │
│                 │                            │
│  ┌──────────────▼───────────────────────┐   │
│  │   Data Volume (persistent)           │   │
│  │   • /opt/face-recognition/data/      │   │
│  │   • face_embeddings.pkl              │   │
│  │   • face_recognition.db (SQLite)     │   │
│  └──────────────────────────────────────┘   │
│                                              │
└──────────────────┬──────────────────────────┘
                   │
                   ▼ (Internet)
┌─────────────────────────────────────────────┐
│              Supabase (Cloud)               │
│  • PostgreSQL (users, logs, queue)          │
│  • Storage (face images)                    │
└─────────────────────────────────────────────┘
```

---

## 3. วิธีที่ 1: Docker (แนะนำ)

### 3.1 ติดตั้ง Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add current user to docker group (ไม่ต้อง sudo ทุกครั้ง)
sudo usermod -aG docker $USER

# Logout แล้ว login ใหม่ หรือใช้คำสั่ง:
newgrp docker

# Verify
docker --version
```

### 3.2 สร้าง Directory สำหรับ Data

```bash
sudo mkdir -p /opt/face-recognition/data
sudo chown -R $USER:$USER /opt/face-recognition
```

### 3.3 Pull & Run Container

#### แบบใช้ Supabase (Cloud DB + Storage)

```bash
docker run -d --name face-recognition \
  --restart unless-stopped \
  -p 8000:8000 \
  -e SUPABASE_URL="https://your-project.supabase.co" \
  -e SUPABASE_KEY="eyJhbGciOiJIUzI1NiIs..." \
  -e SUPABASE_STORAGE_BUCKET="face-images" \
  -e SIMILARITY_THRESHOLD="0.60" \
  -v /opt/face-recognition/data:/app/data \
  athit0900/face-recognition-ai-server:latest
```

#### แบบใช้ SQLite (Local DB, ไม่ต้องมี Supabase)

```bash
docker run -d --name face-recognition \
  --restart unless-stopped \
  -p 8000:8000 \
  -e SIMILARITY_THRESHOLD="0.60" \
  -v /opt/face-recognition/data:/app/data \
  athit0900/face-recognition-ai-server:latest
```

### 3.4 ตรวจสอบว่า Container ทำงาน

```bash
# ดู logs
docker logs -f face-recognition

# ตรวจสอบ health
curl http://localhost:8000/
# ควรได้: {"status":"ok","mode":"supabase"} หรือ {"status":"ok","mode":"sqlite"}
```

### 3.5 Docker Compose (Optional)

สร้างไฟล์ `/opt/face-recognition/docker-compose.yml`:

```yaml
version: "3.8"

services:
  face-recognition:
    image: athit0900/face-recognition-ai-server:latest
    container_name: face-recognition
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - SUPABASE_URL=https://your-project.supabase.co
      - SUPABASE_KEY=eyJhbGciOiJIUzI1NiIs...
      - SUPABASE_STORAGE_BUCKET=face-images
      - SIMILARITY_THRESHOLD=0.60
    volumes:
      - /opt/face-recognition/data:/app/data
```

รันด้วย:

```bash
cd /opt/face-recognition
docker compose up -d
```

---

## 4. วิธีที่ 2: Bare Metal (ไม่มี Docker)

### 4.1 ติดตั้ง System Dependencies

```bash
sudo apt update && sudo apt install -y \
  python3 \
  python3-pip \
  python3-venv \
  git \
  build-essential \
  libglib2.0-0 \
  libsm6 \
  libxext6 \
  libxrender-dev \
  libgomp1 \
  libgl1 \
  cmake \
  && sudo apt autoremove -y
```

### 4.2 Clone โปรเจค

```bash
sudo mkdir -p /opt/face-recognition
sudo chown -R $USER:$USER /opt/face-recognition
git clone <repository-url> /opt/face-recognition
cd /opt/face-recognition/ai_server
```

### 4.3 สร้าง Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4.4 ติดตั้ง Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **หมายเหตุ**: ถ้า `insightface` ไม่สามารถ build ได้ (ต้องใช้ C++ compiler) ให้ลอง:
>
> ```bash
> # ติดตั้ง Cython ก่อน
> pip install cython
> # แล้วค่อยติดตั้ง insightface
> pip install insightface==0.7.3
> ```

### 4.5 สร้าง Environment File

สร้างไฟล์ `/opt/face-recognition/ai_server/.env`:

```bash
cat > /opt/face-recognition/ai_server/.env << 'EOF'
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIs...
SUPABASE_STORAGE_BUCKET=face-images
SIMILARITY_THRESHOLD=0.60
HOST=0.0.0.0
PORT=8000
EOF
```

### 4.6 ทดสอบรัน

```bash
cd /opt/face-recognition/ai_server
source venv/bin/activate
export $(cat .env | xargs)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

เปิด browser ไปที่ `http://<VM-IP>:8000` ควรเห็น `{"status":"ok","mode":"supabase"}`

### 4.7 ตั้งค่า systemd (Auto-start เมื่อ VM reboot)

สร้างไฟล์ `/etc/systemd/system/face-recognition.service`:

```bash
sudo tee /etc/systemd/system/face-recognition.service > /dev/null << 'EOF'
[Unit]
Description=Face Recognition AI Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/face-recognition/ai_server
EnvironmentFile=/opt/face-recognition/ai_server/.env
ExecStart=/opt/face-recognition/ai_server/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

เปิดใช้งาน service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable face-recognition
sudo systemctl start face-recognition

# ตรวจสอบสถานะ
sudo systemctl status face-recognition

# ดู logs
sudo journalctl -u face-recognition -f
```

---

## 5. ตั้งค่า Nginx Reverse Proxy + SSL (Optional)

ถ้าต้องการเข้าผ่าน domain name ด้วย HTTPS:

### 5.1 ติดตั้ง Nginx

```bash
sudo apt install -y nginx
```

### 5.2 สร้าง Nginx Config

```bash
sudo tee /etc/nginx/sites-available/face-recognition > /dev/null << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        client_max_body_size 50M;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/face-recognition /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5.3 ติดตั้ง SSL ด้วย Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 6. Firewall & Security

### 6.1 เปิด Port ที่จำเป็น

```bash
# ถ้าใช้ ufw (Ubuntu)
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP (สำหรับ Let's Encrypt)
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 8000/tcp    # API (ถ้าไม่ใช้ Nginx)
sudo ufw enable
```

### 6.2 จำกัดการเข้าถึง API (Optional)

ถ้าต้องการให้เฉพาะ ESP32 หรือ client ที่รู้จักเข้าถึงได้:

```bash
# ใช้ Nginx จำกัด IP
sudo tee /etc/nginx/sites-available/face-recognition > /dev/null << 'EOF'
server {
    listen 443 ssl;
    server_name your-domain.com;

    # SSL config (จาก certbot)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # จำกัดเฉพาะ IP ที่อนุญาต (เปลี่ยนเป็น IP จริง)
    allow 203.0.113.0/24;
    allow 198.51.100.0/24;
    deny all;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 50M;
    }
}
EOF
```

---

## 7. การ Update

### 7.1 Docker

```bash
# Pull image ใหม่
docker pull athit0900/face-recognition-ai-server:latest

# Stop & remove container เก่า
docker stop face-recognition
docker rm face-recognition

# Run container ใหม่ (ใช้คำสั่งเดิมจากข้อ 3.3)
docker run -d --name face-recognition \
  --restart unless-stopped \
  -p 8000:8000 \
  -e SUPABASE_URL="https://your-project.supabase.co" \
  -e SUPABASE_KEY="eyJhbGciOiJIUzI1NiIs..." \
  -v /opt/face-recognition/data:/app/data \
  athit0900/face-recognition-ai-server:latest
```

### 7.2 Bare Metal

```bash
cd /opt/face-recognition
git pull origin main
cd ai_server
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart face-recognition
```

---

## 8. Monitoring & Troubleshooting

### 8.1 ตรวจสอบ Health

```bash
# Health check
curl http://localhost:8000/
# Response: {"status":"ok","mode":"supabase"}

# ดู logs (Docker)
docker logs -f face-recognition

# ดู logs (systemd)
sudo journalctl -u face-recognition -f
```

### 8.2 ปัญหาที่พบบ่อย

| ปัญหา                      | สาเหตุ                                 | วิธีแก้                                         |
| -------------------------- | -------------------------------------- | ----------------------------------------------- |
| Container crash ทันที      | ไม่มี `build-essential` หรือ `libgl1`  | ตรวจสอบ Dockerfile dependencies                 |
| `insightface` import error | ONNX Runtime ไม่ compatible            | ใช้ Python 3.11, ติดตั้ง `onnxruntime` ก่อน     |
| หน่วยความจำเต็ม            | InsightFace ใช้ RAM สูง                | เพิ่ม RAM VM หรือใช้ `--memory` limit ใน Docker |
| Supabase connection failed | `SUPABASE_URL` หรือ `SUPABASE_KEY` ผิด | ตรวจสอบค่าใน `.env` หรือ environment variables  |
| รูป upload ไม่ได้          | Storage bucket ไม่ได้ตั้ง public       | ตั้ง RLS policy ใน Supabase dashboard           |
| ไฟล์ .pkl ไม่ถูกสร้าง      | ยังไม่เคยรัน `/train-now`              | POST ไปที่ `/train-now` หลังจาก register        |

### 8.3 Backup

```bash
# Backup data (Docker)
docker cp face-recognition:/app/data /opt/face-recognition/backup-$(date +%Y%m%d)

# Backup data (Bare metal)
cp -r /opt/face-recognition/data /opt/face-recognition/backup-$(date +%Y%m%d)

# ถ้าใช้ Supabase → ข้อมูล users/logs อยู่ใน cloud อยู่แล้ว (backup อัตโนมัติ)
# แค่ backup .pkl ก็พอ
```

---

## 9. ตัวอย่างการ Setup ฉบับย่อ (Quick Start)

สำหรับคนที่ต้องการติดตั้งให้เร็วที่สุด (Docker + Supabase):

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com | sudo sh

# 2. Run
docker run -d --name face-recognition \
  --restart unless-stopped \
  -p 8000:8000 \
  -e SUPABASE_URL="https://your-project.supabase.co" \
  -e SUPABASE_KEY="eyJhbGciOiJIUzI1NiIs..." \
  -v /opt/face-recognition/data:/app/data \
  athit0900/face-recognition-ai-server:latest

# 3. Test
curl http://localhost:8000/
```

ใช้เวลาไม่เกิน **5 นาที** ก็พร้อมใช้งาน 🚀

---

## 10. Environment Variables Reference

| Variable                  | Required | Default                             | Description                                       |
| ------------------------- | -------- | ----------------------------------- | ------------------------------------------------- |
| `SUPABASE_URL`            | No       | `""`                                | Supabase project URL (ถ้าไม่ใส่ → ใช้ SQLite)     |
| `SUPABASE_KEY`            | No       | `""`                                | Supabase anon/public key                          |
| `SUPABASE_STORAGE_BUCKET` | No       | `"face-images"`                     | ชื่อ bucket ใน Supabase Storage                   |
| `DATABASE_URL`            | No       | `"sqlite:///./face_recognition.db"` | Database connection string (ใช้ตอนไม่มี Supabase) |
| `SIMILARITY_THRESHOLD`    | No       | `"0.60"`                            | ค่า threshold สำหรับ face matching (0.0–1.0)      |
| `MODEL_NAME`              | No       | `"buffalo_l"`                       | InsightFace model name                            |
| `HOST`                    | No       | `"0.0.0.0"`                         | Server bind address                               |
| `PORT`                    | No       | `"8000"`                            | Server port                                       |
