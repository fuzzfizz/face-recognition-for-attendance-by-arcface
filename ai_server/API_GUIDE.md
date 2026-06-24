# Face Recognition API - Optimized Postman Testing Guide

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
- **Action:** Click **Send**
- **Success Response (200):**

```json
{
  "status": "ok"
}
```

---

## API 2: Register & Train (One-Step Registration) ⭐ **Recommended**

**Purpose:** Register a new user and extract face embeddings in a single request. No separate `/train` call needed.

- **Method:** POST
- **URL:** `{{baseUrl}}/register`
- **Headers:** None
- **Body:** `form-data`
  - Key: `name` (type: **Text**) — Student ID or name (e.g., "6600001")
  - Key: `file` (type: **File**) — Select 1-2 clear front-facing photos (hold Ctrl/Cmd for multiple)
- **Action:** Click **Send**
- **Success Response (201):**

```json
{
  "message": "User registered and face embedded successfully",
  "user_id": 1,
  "name": "6600001"
}
```

**What happens automatically:**

1. Creates user profile in database
2. Saves uploaded images as base64
3. Detects faces, aligns, and extracts 512-dimension ArcFace embeddings
4. Saves embeddings to `data/face_embeddings.pkl`
5. **Ready for verification immediately — no `/train` needed!**

---

## API 3: Verify Face (File Upload)

**Purpose:** Identify a person from a photo (for ESP32-S3 or manual testing)

- **Method:** POST
- **URL:** `{{baseUrl}}/verify`
- **Headers:** None
- **Body:** `form-data`
  - Key: `file` (type: **File**) — Upload a photo of the person to identify
  - Key: `device_id` (type: **Text**, optional) — Default: "ESP32-S3-01"
- **Action:** Click **Send**
- **Success Response - Match Found (200):**

```json
{
  "match": true,
  "user_id": 1,
  "name": "6600001",
  "similarity_score": 0.85,
  "timestamp": "2026-06-24T10:30:00"
}
```

- **Success Response - Unknown (200):**

```json
{
  "match": false,
  "user_id": null,
  "name": "Unknown",
  "similarity_score": 0.0,
  "timestamp": "2026-06-24T10:30:00"
}
```

- **Note:** `similarity_score` ranges from 0-1. Default threshold is 0.60 (configured in `app/config.py`)

---

## API 4: Verify Face (Base64)

**Purpose:** Alternative method to verify using base64-encoded image (for mobile apps / web)

- **Method:** POST
- **URL:** `{{baseUrl}}/verify`
- **Headers:** None
- **Body:** `form-data`
  - Key: `image_base64` (type: **Text**)
  - Value: `data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ...` (full base64 string)
  - Key: `device_id` (type: **Text**, optional)
- **Action:** Click **Send**
- **Response:** Same as API 3

**How to convert image to base64:**

```bash
# macOS/Linux
base64 -i photo.jpg

# Windows PowerShell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("photo.jpg"))
```

---

## API 5: Get Attendance Logs

**Purpose:** View all check-in history

- **Method:** GET
- **URL:** `{{baseUrl}}/logs`
- **Headers:** None
- **Body:** None
- **Query Params (optional):** `?limit=50` (default: 50)
- **Action:** Click **Send**
- **Success Response (200):**

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

---

## Complete Testing Workflow (Optimized)

Follow this sequence to test the entire system:

| Step | API            | Action                                  | Expected Result                                                              |
| ---- | -------------- | --------------------------------------- | ---------------------------------------------------------------------------- |
| 1    | Health Check   | Send GET request                        | `{"status":"ok"}`                                                            |
| 2    | Register       | POST `name` + 1-2 photos to `/register` | `{"message":"User registered and face embedded successfully", "user_id": 1}` |
| 3    | Verify Face    | POST photo of same person to `/verify`  | `match: true, name: "6600001"`                                               |
| 4    | Verify Unknown | POST photo of stranger to `/verify`     | `match: false, name: "Unknown"`                                              |
| 5    | Get Logs       | GET `/logs`                             | Shows all check-in records                                                   |

**That's it!** No separate `/users`, `/users/{id}/images`, or `/train` calls needed.

---

## Legacy Endpoints (Still Supported)

These endpoints from the original system are still available for backward compatibility:

### Create User (Legacy)

- **Method:** POST
- **URL:** `{{baseUrl}}/users`
- **Headers:** `Content-Type: application/json`
- **Body:** `raw` → `JSON`

```json
{
  "name": "John Doe"
}
```

### List All Users (Legacy)

- **Method:** GET
- **URL:** `{{baseUrl}}/users`

### Upload Face Image (Legacy)

- **Method:** POST
- **URL:** `{{baseUrl}}/users/1/images`
- **Body:** `form-data`
  - Key: `file` (type: **File**)

### Train Model (Legacy)

- **Method:** POST
- **URL:** `{{baseUrl}}/train`
- **Note:** Only needed if you used legacy endpoints to add users/images

---

## Tips for Best Results

1. **Use 1-2 clear front-facing photos** — ArcFace is robust enough with minimal images
2. **Good lighting** — improves face detection and embedding quality
3. **Consistent camera** — use similar camera for registration and verification
4. **Adjust threshold if needed** — edit `SIMILARITY_THRESHOLD` in `app/config.py` (default: 0.60)

---

## Troubleshooting

| Issue                        | Solution                                         |
| ---------------------------- | ------------------------------------------------ |
| "No face detected"           | Use clearer photo with visible face              |
| Low similarity score (< 0.6) | Re-register with better quality photos           |
| Timeout                      | Check VM firewall and server status              |
| 404 error                    | Verify URL is correct (use VM IP, not localhost) |

---

## View Database

To view the SQLite database on the VM:

```bash
# Install SQLite
sudo apt install sqlite3 -y

# Open database
sqlite3 ai_server/face_recognition.db

# View tables
.tables

# View all users
SELECT * FROM users;

# View all check-in logs
SELECT * FROM check_in_logs;

# Exit
.quit
```

Database location: `ai_server/face_recognition.db`
