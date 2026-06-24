# Real-World Workflow: Face Registration & Attendance (Optimized Version)

This guide shows the **optimized process** for registering new faces and taking attendance in a real deployment.

> **What changed?**
>
> - **One-step registration:** `POST /register` replaces the old 3-step (`/users` → `/users/{id}/images` → `/train`)
> - **Auto-embedding:** Face vectors are extracted immediately during upload — no separate training step
> - **Recommended photos:** Reduced from 5-10 to **1-2 clear front-facing photos** (ArcFace is robust enough)
> - **Backward compatible:** All old endpoints (`/users`, `/users/{id}/images`, `/train`) still work

---

## Part 1: Registering a New Face (One-Step)

### Overview

When a new person joins (employee, student, member), you need only **one API call**:

1. `POST /register` — Upload name + photos → System auto-creates user, stores images, and extracts face embeddings

---

### Step-by-Step Registration (Postman)

#### Step 1: Prepare Photos

| Do This                               | Avoid This                          |
| ------------------------------------- | ----------------------------------- |
| Front-facing, looking at camera       | Side profiles                       |
| Good lighting (natural light is best) | Dark or backlit photos              |
| Clear, not blurry                     | Blurry or pixelated images          |
| Neutral expression                    | Extreme expressions (yawning, etc.) |

**Recommended photo count:** 1-2 photos per person (front-facing, well-lit)

---

#### Step 2: Register User & Upload Photos (One Request)

**Method:** POST
**URL:** `http://<VM-IP>:8000/register`
**Headers:** None
**Body:** `form-data`

- Key: `name` (type: **Text**) — e.g., "6600001" or "Alice Johnson"
- Key: `file` (type: **File**) — Select one or more images (hold Ctrl/Cmd to select multiple files)

**Click Send**

**Response:**

```json
{
  "message": "User registered and face embedded successfully",
  "user_id": 1,
  "name": "6600001"
}
```

**What happened behind the scenes:**

1. Created user profile in database
2. Saved uploaded images as base64
3. Detected faces in each image
4. Aligned faces using ArcFace landmarks
5. Extracted 512-dimensional face embeddings
6. Saved embeddings to `data/face_embeddings.pkl`
7. **No separate `/train` call needed!**

---

#### Step 3: Verify Registration Works

**Method:** POST
**URL:** `http://<VM-IP>:8000/verify`
**Body:** `form-data`

- Key: `file` (type: **File**) — Upload a test photo

**Expected Response:**

```json
{
  "match": true,
  "user_id": 1,
  "name": "6600001",
  "similarity_score": 0.85,
  "timestamp": "2026-06-24T10:30:00"
}
```

**If `match: false` or low score (< 0.6):**

- Upload clearer, front-facing photos
- Ensure photos are well-lit (no shadows on face)
- Re-register with better photos

---

### Registration Checklist (Optimized)

- [ ] Prepared 1-2 clear front-facing photos
- [ ] Called `POST /register` with name + photos
- [ ] Verified with test photo via `/verify` → `match: true`
- [ ] Saved user ID for future reference

---

## Part 2: Taking Attendance (Face Verification)

### Overview

When a person arrives (at office, school, event), the system:

1. Captures their face (via ESP32-S3 or uploaded photo)
2. Compares against stored embeddings
3. Logs check-in if match found

---

### Step-by-Step Attendance

#### Method A: Using ESP32-S3 (Real-time)

**This is the automated method for actual deployment.**

1. **ESP32-S3 captures face** automatically when person stands in front
2. **ESP32 sends photo** to `POST /verify` via HTTP
3. **Server processes and returns result**
4. **ESP32 displays result** on TFT screen or LED indicator

**ESP32 sends:**

```http
POST http://<VM-IP>:8000/verify
Content-Type: multipart/form-data

[image data]
```

**Server responds (Match Found):**

```json
{
  "match": true,
  "user_id": 1,
  "name": "6600001",
  "similarity_score": 0.85,
  "timestamp": "2026-06-24T10:30:00"
}
```

**ESP32 actions:**

- If `match: true` → Show "Welcome 6600001!" + log attendance
- If `match: false` → Show "Unknown person" + alert admin

---

#### Method B: Using Postman (Manual Testing)

**Method:** POST
**URL:** `http://<VM-IP>:8000/verify`
**Body:** `form-data`

- Key: `file` (type: **File**) — Upload a photo of the person

**Response (Match Found):**

```json
{
  "match": true,
  "user_id": 1,
  "name": "6600001",
  "similarity_score": 0.85,
  "timestamp": "2026-06-24T10:30:00"
}
```

**Response (Unknown Person):**

```json
{
  "match": false,
  "user_id": null,
  "name": "Unknown",
  "similarity_score": 0.0,
  "timestamp": "2026-06-24T10:30:00"
}
```

---

#### Method C: Using Base64 (Mobile App / Web)

**For integration with mobile apps or web interfaces:**

1. **Convert photo to base64:**

```bash
# macOS/Linux
base64 -i photo.jpg

# Windows PowerShell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("photo.jpg"))
```

2. **Send to verify:**

- Key: `image_base64` (type: **Text**)
- Value: `data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ...`

---

### View Attendance Logs

**To see all check-in records:**

**Method:** GET
**URL:** `http://<VM-IP>:8000/logs`

**Response:**

```json
[
  {
    "id": 1,
    "user_id": 1,
    "name": "6600001",
    "similarity_score": 0.85,
    "device_id": "ESP32-S3-01",
    "timestamp": "2026-06-24T10:30:00"
  }
]
```

**Database location:** `ai_server/face_recognition.db`

---

## Part 3: Real-World Scenarios

### Scenario 1: New Employee Onboarding

**Situation:** A new employee "6600020" joins the company

**Process:**

1. HR takes **2 photos** of the employee (front-facing, well-lit)
2. HR calls one API: `POST /register` with `name="6600020"` + 2 photos
3. System auto-creates user, saves images, and extracts face embeddings
4. HR tests: `POST /verify` with one of the photos
5. **Result:** `match: true, name: "6600020"`
6. Employee can now use the attendance system **immediately**

**Time saved vs old system:** ~5 minutes → ~10 seconds

---

### Scenario 2: Daily Attendance (Office)

**Situation:** Employees arrive at office and check in via ESP32-S3 at entrance

1. Employee walks to ESP32-S3 kiosk
2. ESP32-S3 automatically captures face
3. ESP32 sends photo to `POST /verify`
4. Server identifies employee (if registered)
5. Server logs check-in with timestamp
6. ESP32 displays: "Welcome, 6600001! Check-in at 09:05 AM"
7. If unknown: "Access denied. Please contact HR."

**Result:** Attendance automatically recorded in database

---

### Scenario 3: Student Attendance (Classroom)

**Situation:** Teacher takes attendance using a tablet with camera

1. Teacher opens attendance app (connected to API)
2. App captures student face one by one
3. App sends photo to `POST /verify`
4. Server returns student name/ID
5. App marks student as "Present"
6. If unknown: "Unknown — mark as absent"
7. Teacher reviews and confirms

**Result:** Attendance sheet auto-filled

---

### Scenario 4: Event Check-in

**Situation:** Conference attendees check in at registration desk

1. Attendee stands in front of camera
2. System captures face and verifies against pre-registered list
3. If match: "Welcome, John! You are checked in."
4. If no match: "Please register at the help desk."
5. System logs check-in time

**Result:** Fast, contactless check-in

---

## Part 4: API Endpoint Reference

| API         | Method | Purpose               | Request Body                          | Notes                           |
| ----------- | ------ | --------------------- | ------------------------------------- | ------------------------------- |
| `/`         | GET    | Health check          | None                                  | Returns `{"status": "ok"}`      |
| `/register` | POST   | One-step registration | `form-data`: `name` + `file`(s)       | **Recommended** — auto-embeds   |
| `/verify`   | POST   | Face verification     | `form-data`: `file` or `image_base64` | Returns match + logs attendance |
| `/logs`     | GET    | Attendance history    | Query param: `?limit=50`              | Shows recent check-in records   |

### Legacy Endpoints (Still Supported)

| API                  | Method | Purpose                         |
| -------------------- | ------ | ------------------------------- |
| `/users`             | POST   | Create user only                |
| `/users`             | GET    | List all users                  |
| `/users/{id}/images` | POST   | Upload images for existing user |
| `/train`             | POST   | Manual training (retrain all)   |

---

## Part 5: Best Practices

### Photo Guidelines

| Aspect     | Good                       | Bad                            |
| ---------- | -------------------------- | ------------------------------ |
| Lighting   | Bright, even lighting      | Dark, backlit, shadows on face |
| Angle      | Front-facing (±15 degrees) | Profile, extreme angles        |
| Distance   | Face fills 60-70% of frame | Too far or too close           |
| Focus      | Sharp, clear               | Blurry, out of focus           |
| Background | Plain, neutral             | Busy, distracting              |
| Expression | Neutral to slight smile    | Extreme expressions            |
| **Count**  | **1-2 photos is enough**   | 5-10 photos (old system)       |

### Similarity Threshold

- **Default:** 0.60 (configurable in `app/config.py`)
- Too many false positives (wrong person matched) → **Increase** to 0.65-0.70
- Too many false negatives (correct person not matched) → **Decrease** to 0.55-0.50

### Security Guidelines

1. **Restrict API access:** Use firewall rules to allow only trusted IPs
2. **Use HTTPS:** In production, use reverse proxy (Nginx) with SSL
3. **Database backup:** Regular backups of `face_recognition.db`
4. **Backup embeddings:** Backup `data/face_embeddings.pkl` regularly

---

## Part 6: Troubleshooting

### Issue: "No face detected" Error

**Causes:**

- Photo is blurry or dark
- Face is at extreme angle
- Face is too small in frame

**Solutions:**

- Use clearer, better-lit photos
- Ensure face is front-facing
- Move closer to camera

### Issue: Low Similarity Score (< 0.6)

**Causes:**

- Photo quality is poor
- Different camera/lighting for registration vs verification
- Person looks very different (hairstyle, glasses, etc.)

**Solutions:**

- Re-register with better quality photos
- Use same camera type for registration and verification
- Ensure consistent lighting

### Issue: Wrong Person Matched (False Positive)

**Causes:**

- Similarity threshold too low
- Two people look similar
- Poor quality registration photos

**Solutions:**

- Increase `SIMILARITY_THRESHOLD` to 0.65 or 0.70
- Re-register with clearer, more distinct photos

---

## Part 7: Complete Real-World Example

### Registering 10 Employees (Optimized)

```bash
# Register Alice (1 API call, done in seconds)
POST /register
Body: form-data { name: "6600001", file: [alice1.jpg, alice2.jpg] }
Response: {"message": "User registered and face embedded successfully", "user_id": 1}

# Register Bob (1 API call)
POST /register
Body: form-data { name: "6600002", file: [bob1.jpg, bob2.jpg] }
Response: {"message": "User registered and face embedded successfully", "user_id": 2}

# ... repeat for 10 employees (10 API calls total)
# NO separate /train needed — each registration auto-embeds!
```

### Daily Attendance

```bash
# 9:00 AM - Alice arrives (ESP32-S3 auto-captures)
POST /verify (from ESP32)
Response: {"match": true, "user_id": 1, "name": "6600001", "similarity_score": 0.87}

# 9:05 AM - Bob arrives
POST /verify (from ESP32)
Response: {"match": true, "user_id": 2, "name": "6600002", "similarity_score": 0.82}

# 9:15 AM - Unknown person
POST /verify (from ESP32)
Response: {"match": false, "user_id": null, "name": "Unknown", "similarity_score": 0.0}

# End of day - View all logs
GET /logs
Response: [{"id": 1, "user_id": 1, "name": "6600001", ...}, ...]
```

---

## Summary

| Phase            | Action       | API Endpoint     | Frequency       |
| ---------------- | ------------ | ---------------- | --------------- |
| **Registration** | One-step reg | `POST /register` | Once per person |
| **Attendance**   | Verify face  | `POST /verify`   | Every check-in  |
| **Monitoring**   | View logs    | `GET /logs`      | As needed       |

---

## Quick Reference Card

```
NEW USER REGISTRATION (Optimized):
1. POST /register    → Upload name + 1-2 photos → Auto-registered & embedded ✓
   (No separate /users, /users/{id}/images, or /train needed!)

DAILY ATTENDANCE:
1. POST /verify      → Send photo, get result
2. GET /logs         → View attendance records

DATABASE:
Location: ai_server/face_recognition.db
View: sqlite3 face_recognition.db
```
