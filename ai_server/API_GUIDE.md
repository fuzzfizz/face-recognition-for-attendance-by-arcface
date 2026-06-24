# Face Recognition API - Async Queue Postman Testing Guide

## Prerequisites

- Server running at `http://<YOUR-VM-IP>:8000`
- Postman installed on your local machine
- Set the base URL variable in Postman: `{{baseUrl}} = http://<YOUR-VM-IP>:8000`

---

## API 1: Health Check

**Purpose:** Verify the server is running

- **Method:** GET
- **URL:** `{{baseUrl}}/`
- **Headers:** None
- **Body:** None
- **Success Response (200):**

```json
{
  "status": "ok"
}
```

---

## API 2: Register (Async Queue) ⭐ **Recommended**

**Purpose:** Upload face images for registration. Non-blocking — saves images to disk, queues them for AI processing, and returns immediately.

- **Method:** POST
- **URL:** `{{baseUrl}}/register`
- **Headers:** None
- **Body:** `form-data`
  - Key: `student_id` (type: **Text**) — Student ID (e.g., "6600001")
  - Key: `files` (type: **File**) — Select 1-3 clear front-facing photos (hold Ctrl/Cmd for multiple)
- **Success Response (200):**

```json
{
  "message": "Images queued for processing successfully",
  "student_id": "6600001",
  "status": "pending"
}
```

**Note:** The response is instant. AI processing happens later via `/train-now` or a scheduled worker.

---

## API 3: Check Registration Status

**Purpose:** Check whether the AI has finished processing face embeddings for a student.

- **Method:** GET
- **URL:** `{{baseUrl}}/register/status/6600001`
- **Headers:** None
- **Body:** None

**Response — Pending:**

```json
{
  "student_id": "6600001",
  "status": "pending",
  "message": "Waiting for AI processing"
}
```

**Response — Completed:**

```json
{
  "student_id": "6600001",
  "status": "completed",
  "message": "Face extracted and saved successfully"
}
```

**Response — Failed:**

```json
{
  "student_id": "6600001",
  "status": "failed",
  "message": "No face detected, please upload a new clear image"
}
```

---

## API 4: Trigger Training (Process Queue)

**Purpose:** Manually trigger AI processing for all pending queue items. Extracts face embeddings and updates the .pkl file.

- **Method:** POST
- **URL:** `{{baseUrl}}/train-now`
- **Headers:** None
- **Body:** None
- **Success Response (200):**

```json
{
  "message": "Background training started",
  "pending_images_in_queue": 15
}
```

---

## API 5: Verify Face (File Upload)

**Purpose:** Real-time face verification. Matches the input photo against trained embeddings and logs attendance.

- **Method:** POST
- **URL:** `{{baseUrl}}/verify`
- **Headers:** None
- **Body:** `form-data`
  - Key: `file` (type: **File**) — Photo of the person to identify
  - Key: `device_id` (type: **Text**, optional) — Default: "ESP32-S3-01"

**Response — Match Found (200):**

```json
{
  "match": true,
  "student_id": "6600001",
  "similarity_score": 0.85,
  "timestamp": "2026-06-24T12:30:00"
}
```

**Response — Unknown (200):**

```json
{
  "match": false,
  "student_id": null,
  "similarity_score": 0.0,
  "timestamp": "2026-06-24T12:30:00"
}
```

---

## API 6: Verify Face (Base64)

**Purpose:** Alternative method to verify using a base64-encoded image string.

- **Method:** POST
- **URL:** `{{baseUrl}}/verify`
- **Body:** `form-data`
  - Key: `image_base64` (type: **Text**) — `data:image/jpeg;base64,...`
  - Key: `device_id` (type: **Text**, optional)

**How to convert image to base64:**

```bash
# macOS/Linux
base64 -i photo.jpg

# Windows PowerShell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("photo.jpg"))
```

---

## API 7: Get Attendance Logs

**Purpose:** View all check-in history.

- **Method:** GET
- **URL:** `{{baseUrl}}/logs`
- **Query Params (optional):** `?limit=50`
- **Success Response (200):**

```json
[
  {
    "id": 1,
    "student_id": "6600001",
    "similarity_score": 0.85,
    "device_id": "ESP32-S3-01",
    "timestamp": "2026-06-24T12:30:00"
  }
]
```

---

## Complete Testing Workflow (Async)

| Step | API              | Action                                      | Expected Result                      |
| ---- | ---------------- | ------------------------------------------- | ------------------------------------ |
| 1    | Health Check     | GET `/`                                     | `{"status":"ok"}`                    |
| 2    | Register         | POST `/register` with `student_id` + photos | `{"status":"pending"}`               |
| 3    | Trigger Training | POST `/train-now`                           | `{"pending_images_in_queue": N}`     |
| 4    | Check Status     | GET `/register/status/{id}`                 | `{"status":"completed"}`             |
| 5    | Verify Face      | POST `/verify` with test photo              | `match: true, student_id: "6600001"` |
| 6    | Verify Unknown   | POST `/verify` with stranger photo          | `match: false`                       |
| 7    | Get Logs         | GET `/logs`                                 | Shows all check-in records           |

---

## Legacy Endpoints (Still Supported)

| API                  | Method | Purpose                         |
| -------------------- | ------ | ------------------------------- |
| `/users`             | POST   | Create user profile             |
| `/users`             | GET    | List all users                  |
| `/users/{id}/images` | POST   | Upload image for existing user  |
| `/train`             | POST   | Full retrain from all DB images |

---

## Tips for Best Results

1. **Use 1-3 clear front-facing photos** — ArcFace is robust with minimal images
2. **Good lighting** — improves face detection and embedding quality
3. **Always call `/train-now` after `/register`** to trigger AI processing
4. **Check status** with `/register/status/{id}` before attempting verification
5. **Adjust threshold** in `app/config.py` (default: 0.60)

---

## Troubleshooting

| Issue                        | Solution                                |
| ---------------------------- | --------------------------------------- |
| "No face detected"           | Use clearer photo with visible face     |
| Low similarity score (< 0.6) | Re-register with better quality photos  |
| Status stuck on "pending"    | Call `/train-now` to trigger processing |
| Status shows "failed"        | Upload new clear photos and re-register |
| Timeout                      | Check VM firewall and server status     |

---

## View Database

```bash
sqlite3 ai_server/face_recognition.db
.tables
SELECT * FROM users;
SELECT * FROM registration_queue;
SELECT * FROM check_in_logs;
.quit
```

Database location: `ai_server/face_recognition.db`
Image storage: `ai_server/data/uploads/`
