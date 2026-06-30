# Deployment & Build Guide

This document contains step-by-step instructions for:
1. Installing and running the **Face Recognition AI Server** on a virtual machine (VM) using Docker.
2. Building the **Face Capture Mobile App** APK for Android devices.

---

## Part 1: AI Server Deployment on VM (Docker)

### 1. Prepare your VM
Before deploying, make sure your VM's firewall permits incoming traffic on port **8000** (or whichever port you choose to bind).
* **AWS/GCP/Azure**: Add an inbound security group rule allowing **TCP Port 8000** from your edge devices or anywhere (`0.0.0.0/0`).

### 2. Install Docker & Docker Compose
If not already installed on your VM, run the following commands (Ubuntu/Debian example):

```bash
# Update package database
sudo apt-get update

# Install Docker
sudo apt-get install -y docker.io

# Install Docker Compose
sudo apt-get install -y docker-compose-plugin

# Start and enable Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Allow your user to run docker commands without sudo (optional, requires relog)
sudo usermod -aG docker $USER
```

### 3. Clone / Transfer Code to VM
Transfer the `ai_server/` directory from your project to the VM. You can use `scp`, `rsync`, or clone your repository directly via git:

```bash
git clone <your-repo-url>
cd face-recognition-attendance/ai_server
```

### 4. Configure Environment Variables
Create a `.env` file in the same directory as `docker-compose.yml` to store your configuration:

```bash
cp .env.example .env
nano .env
```

Ensure your `.env` contains the required credentials:

```ini
# Supabase settings (For hybrid mode, leave blank to default to local SQLite mode)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key
SUPABASE_STORAGE_BUCKET=face-images

# Admin Authentication
ADMIN_API_KEY=your-secret-admin-key

# Machine learning parameters
SIMILARITY_THRESHOLD=0.60
MODEL_NAME=buffalo_l
```

### 5. Build and Start Container
Run the following command to build the image and start the server in the background:

```bash
docker compose up -d --build
```

### 6. Verify Server is Running
Check the status of the running container:

```bash
docker compose ps
```

You can view server logs in real time:

```bash
docker compose logs -f
```

* **Health Check**: The server runs an automatic python-based health check every 30 seconds.
* **Persistent Folders**:
  * `./data`: Holds the local SQLite DB file and `.pkl` embedding files.
  * `~/.insightface`: Holds the cached ArcFace ML model (~20MB) so it doesn't download it again on container restart.

---

## Part 2: Flutter APK Build Guide (Android)

To distribute the registration app (`app_face_capture`), you can build a release APK file that can be installed on Android smartphones.

### 1. Prerequisites
Ensure you have the following installed on your local computer:
* **Flutter SDK** (v3.12.1 or newer recommended)
* **Android SDK** (Android Studio)
* **Java Development Kit (JDK)**

### 2. Configure default server URL
If you want the app to connect to your VM automatically upon installation, open `app_face_capture/lib/core/constants/api_constants.dart` and change `baseUrl` to your VM's public IP address:

```dart
// Change 'http://10.0.2.2:8000' to your VM's public IP address:
static const String baseUrl = 'http://your-vm-ip-address:8000';
```

*(Note: Users can also manually update the Server URL inside the app settings at runtime.)*

### 3. Build using environment parameters (Alternative)
You can inject the configurations at build time without modifying Dart code by using `--dart-define` parameters:

```bash
cd app_face_capture

flutter build apk --release \
  --dart-define=SUPABASE_URL=https://your-project.supabase.co \
  --dart-define=SUPABASE_ANON_KEY=your-anon-key \
  --dart-define=ADMIN_PIN=1234 \
  --dart-define=ADMIN_API_KEY=your-secret-admin-key
```

### 4. Build a standard release APK
Run the standard build command inside the `app_face_capture` folder:

```bash
cd app_face_capture
flutter pub get
flutter build apk --release
```

If you want to build a split-per-ABI APK (reducing file size for specific CPU architectures):

```bash
flutter build apk --split-per-abi --release
```

### 5. Locate the APK
Once compilation completes, the APK file will be saved at:
📂 **`build/app/outputs/flutter-apk/app-release.apk`**

### 6. Installation
1. Transfer the `app-release.apk` to your Android device (via USB, email, Google Drive, or hosting it on a web page).
2. Open the file on the Android device.
3. Enable **"Install from Unknown Sources"** if prompted by the OS.
4. Follow the installer steps to complete installation.
