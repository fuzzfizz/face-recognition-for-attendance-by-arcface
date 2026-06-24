import datetime
import base64
import uuid
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from typing import Optional, List
import pydantic

from app.config import HOST, PORT, DATA_DIR
from app.database import (
    init_db, using_supabase,
    upsert_user, get_user_by_student_id,
    insert_log, get_logs,
    insert_queue_item, get_pending_queue_items, update_queue_item_status,
    upload_image,
    get_all_embeddings, save_all_embeddings, match_face_embedding,
)
from app.face_processor import get_face_processor

# Initialize Database (SQLite only if Supabase not available)
init_db()

# Initialize FastAPI App
app = FastAPI(
    title="Face Recognition AI Server (Supabase + Local .pkl)",
    description="Hybrid architecture: face matching via local .pkl, data via Supabase (or SQLite fallback)",
    version="4.0.0"
)

# Pydantic Schemas
class UserCreate(pydantic.BaseModel):
    name: str

class ImageUploadBase64(pydantic.BaseModel):
    image_base64: str


# ──────────────────────────────────────────────
# Health Check
# ──────────────────────────────────────────────
@app.get("/")
def read_root():
    return {
        "status": "ok",
        "mode": "supabase" if using_supabase() else "sqlite"
    }


# ──────────────────────────────────────────────
# REGISTER: Non-blocking — upload image + queue
# ──────────────────────────────────────────────
@app.post("/register", status_code=status.HTTP_200_OK)
async def register_user(
    student_id: str = Form(...),
    files: List[UploadFile] = File(...),
):
    """
    Upload face images for registration. Non-blocking — saves image to storage,
    creates queue entry (status='pending'), and returns immediately.
    """
    # 1. Upsert user in storage (Supabase or SQLite)
    user = upsert_user(student_id)
    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user record")

    # 2. Save image + create queue entry
    queue_count = 0
    for file in files:
        file_bytes = await file.read()
        if not file_bytes:
            continue

        ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"

        # Upload image (to Supabase Storage or local disk)
        image_path = upload_image(file_bytes, student_id, ext)
        if not image_path:
            continue

        # Create queue entry
        insert_queue_item(student_id, image_path)
        queue_count += 1

    if queue_count == 0:
        raise HTTPException(status_code=400, detail="No valid images were uploaded")

    return {
        "message": "Images queued for processing successfully",
        "student_id": student_id,
        "status": "pending"
    }


# ──────────────────────────────────────────────
# REGISTER STATUS: Check processing status for a student
# ──────────────────────────────────────────────
@app.get("/register/status/{student_id}")
def get_registration_status(student_id: str):
    """
    Check whether the face registration for a student has been processed.
    Note: In Supabase mode, this is simplified to always return status from local .pkl.
    """
    user = get_user_by_student_id(student_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"No registration found for student_id: {student_id}")

    # Check if embeddings exist in local .pkl for this student
    embeddings = get_all_embeddings()
    for e in embeddings:
        if e.get("student_id") == student_id:
            return {
                "student_id": student_id,
                "status": "completed",
                "message": "Face extracted and saved successfully"
            }

    return {
        "student_id": student_id,
        "status": "pending",
        "message": "Waiting for AI processing (trigger /train-now)"
    }


# ──────────────────────────────────────────────
# TRAIN NOW: Process all pending queue items immediately
# ──────────────────────────────────────────────
@app.post("/train-now")
def trigger_training():
    """
    Process pending queue items. Extracts face embeddings for each queued image
    and updates .pkl file. Works with both Supabase and SQLite queue data.
    """
    pending_items = get_pending_queue_items()

    if not pending_items:
        raise HTTPException(status_code=400, detail="No pending images in queue. Upload images via /register first.")

    processor = get_face_processor()
    embeddings_by_student = {}

    for item in pending_items:
        try:
            # Read image from path
            cv_img = processor.decode_image_path(item["image_path"])
            if cv_img is None:
                update_queue_item_status(item["id"], "failed", "Could not read image file")
                continue

            # Extract face embedding
            result = processor.extract_face_embedding(cv_img)
            if result and "embedding" in result:
                student_id = item["student_id"]
                if student_id not in embeddings_by_student:
                    embeddings_by_student[student_id] = []
                embeddings_by_student[student_id].append(result["embedding"])
                update_queue_item_status(item["id"], "completed")
            else:
                update_queue_item_status(item["id"], "failed", "No face detected")

        except Exception as e:
            update_queue_item_status(item["id"], "failed", str(e))

    # Update .pkl file with newly processed embeddings
    existing = get_all_embeddings()
    for student_id, emb_list in embeddings_by_student.items():
        if emb_list:
            # Remove old data for this student
            existing = [e for e in existing if e.get("student_id") != student_id]
            existing.append({
                "user_id": student_id,
                "name": student_id,
                "student_id": student_id,
                "embeddings": emb_list
            })

    save_all_embeddings(existing)

    return {
        "message": "Training completed",
        "processed_students": list(embeddings_by_student.keys()),
        "total_pending": len(pending_items)
    }


# ──────────────────────────────────────────────
# LEGACY ENDPOINTS (backward compatible)
# ──────────────────────────────────────────────
@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserCreate):
    """Creates a new user profile."""
    user = upsert_user(user_in.name)
    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user")
    return {"status": "success", "user_id": user.get("id") or user.get("student_id"), "name": user_in.name}


@app.get("/users")
def list_users():
    """Lists all registered users from the .pkl embeddings."""
    embeddings = get_all_embeddings()
    return [
        {
            "user_id": e.get("user_id"),
            "student_id": e.get("student_id"),
            "embeddings_count": len(e.get("embeddings", []))
        }
        for e in embeddings
    ]


@app.post("/users/{user_id}/images", status_code=status.HTTP_201_CREATED)
async def upload_user_image(
    user_id: int,
    file: Optional[UploadFile] = File(None),
    payload: Optional[ImageUploadBase64] = None,
):
    """Upload an image for an existing user."""
    # In the new architecture, users are identified by student_id, not numeric user_id
    # This legacy endpoint is maintained for compatibility
    student_id = str(user_id)

    file_bytes = None
    if file:
        file_bytes = await file.read()
    elif payload and payload.image_base64:
        try:
            file_bytes = base64.b64decode(payload.image_base64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64: {e}")
    else:
        raise HTTPException(status_code=400, detail="Must provide an image file or a base64 string")

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty image data")

    ext = "jpg"
    image_path = upload_image(file_bytes, student_id, ext)
    if not image_path:
        raise HTTPException(status_code=500, detail="Failed to upload image")

    # Create queue entry
    insert_queue_item(student_id, image_path)

    return {
        "status": "success",
        "user_id": user_id,
        "message": "Image uploaded and queued for processing successfully"
    }


@app.post("/train")
def train_model():
    """Full retrain from the .pkl embeddings (intended for re-processing existing data)."""
    try:
        from app.trainer import train_system
        return train_system()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


# ──────────────────────────────────────────────
# VERIFY: Real-time face recognition + attendance logging
# ──────────────────────────────────────────────
@app.post("/verify")
async def verify_identity(
    file: Optional[UploadFile] = File(None),
    image_base64: Optional[str] = Form(None),
    device_id: Optional[str] = Form("ESP32-S3-01"),
):
    """
    Real-time face verification. Matches the input photo against local .pkl embeddings
    and logs the attendance record to Supabase (or SQLite).
    """
    processor = get_face_processor()
    cv_img = None

    if file:
        file_bytes = await file.read()
        cv_img = processor.decode_image(file_bytes)
    elif image_base64:
        try:
            from app.trainer import decode_base64_image
            cv_img = decode_base64_image(image_base64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to decode base64 image: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="No image provided. Send an image file or base64 parameter.")

    if cv_img is None:
        raise HTTPException(status_code=400, detail="Invalid image content.")

    # Extract embedding
    face_data = processor.extract_face_embedding(cv_img)
    if not face_data:
        # No face detected — log with no match
        insert_log(student_id=None, similarity_score=0.0, device_id=device_id)
        return {"match": False, "student_id": None, "similarity_score": 0.0, "timestamp": datetime.datetime.utcnow().isoformat()}

    # Match against local .pkl embeddings (fast, no network)
    match = match_face_embedding(face_data["embedding"])

    if match:
        student_id = match.get("student_id", match.get("name", "Unknown"))
        insert_log(
            student_id=student_id,
            similarity_score=match["similarity"],
            device_id=device_id,
            user_id=match.get("user_id"),
        )

        return {
            "match": True,
            "student_id": student_id,
            "similarity_score": match["similarity"],
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    else:
        insert_log(student_id=None, similarity_score=0.0, device_id=device_id)
        return {
            "match": False,
            "student_id": None,
            "similarity_score": 0.0,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }


# ──────────────────────────────────────────────
# LOGS: Attendance history
# ──────────────────────────────────────────────
@app.get("/logs")
def view_logs(limit: int = 50):
    """
    Retrieves the recent check-in logs from Supabase (or SQLite).
    """
    logs = get_logs(limit)
    return logs


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)