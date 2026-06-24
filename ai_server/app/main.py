import datetime
import base64
import uuid
from fastapi import FastAPI, Depends, File, UploadFile, Form, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from typing import Optional, List
import pydantic

from app.config import HOST, PORT
from app.database import init_db, get_db, User, UserImage, RegistrationQueue, CheckInLog, IMAGES_DIR
from app.face_processor import get_face_processor
from app.matcher import match_face, save_embeddings, load_embeddings

# Initialize Database
init_db()

# Initialize FastAPI App
app = FastAPI(
    title="Face Recognition AI Server (Async Queue)",
    description="Asynchronous API with queue-based registration — non-blocking /register, background AI processing",
    version="3.0.0"
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
    return {"status": "ok"}


# ──────────────────────────────────────────────
# REGISTER: Non-blocking — save images to disk + queue, return immediately
# ──────────────────────────────────────────────
@app.post("/register", status_code=status.HTTP_200_OK)
async def register_user(
    student_id: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload face images for registration. Non-blocking — saves images to disk,
    creates queue entries (status='pending'), and returns immediately.
    AI processing happens later via background worker or /train-now trigger.
    
    - Key `student_id` (Text): Student ID (e.g. "6600001")
    - Key `files` (File): 1-3 clear front-facing photos
    """
    # 1. Upsert user by student_id
    user = db.query(User).filter(User.student_id == student_id).first()
    if not user:
        user = User(student_id=student_id)
        db.add(user)
        db.commit()
        db.refresh(user)

    # 2. Save images to disk and create queue entries
    queue_count = 0
    for file in files:
        file_bytes = await file.read()
        if not file_bytes:
            continue

        # Generate unique filename: student_id_uuid.ext
        ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
        filename = f"{student_id}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = IMAGES_DIR / filename

        # Write to disk
        with open(filepath, "wb") as f:
            f.write(file_bytes)

        # Also store base64 in user_images for DB portability
        img_b64 = base64.b64encode(file_bytes).decode('utf-8')
        img_record = UserImage(user_id=user.id, image_path=str(filepath), image_base64=img_b64)
        db.add(img_record)
        db.commit()
        db.refresh(img_record)

        # Create queue entry
        queue_item = RegistrationQueue(
            student_id=student_id,
            image_path=str(filepath),
            status="pending"
        )
        db.add(queue_item)
        db.commit()
        queue_count += 1

    return {
        "message": "Images queued for processing successfully",
        "student_id": student_id,
        "status": "pending"
    }


# ──────────────────────────────────────────────
# REGISTER STATUS: Check processing status for a student
# ──────────────────────────────────────────────
@app.get("/register/status/{student_id}")
def get_registration_status(student_id: str, db: Session = Depends(get_db)):
    """
    Check whether the face registration for a student has been processed.
    - pending: Waiting for AI processing
    - completed: Face extracted and saved successfully
    - failed: No face detected or processing error
    """
    queue_items = db.query(RegistrationQueue).filter(
        RegistrationQueue.student_id == student_id
    ).order_by(RegistrationQueue.created_at.desc()).all()

    if not queue_items:
        raise HTTPException(status_code=404, detail=f"No registration found for student_id: {student_id}")

    # Determine overall status
    all_statuses = [item.status for item in queue_items]
    if all(s == "completed" for s in all_statuses):
        overall = "completed"
        message = "Face extracted and saved successfully"
    elif "failed" in all_statuses:
        overall = "failed"
        message = "No face detected, please upload a new clear image"
    else:
        overall = "pending"
        message = "Waiting for AI processing"

    return {
        "student_id": student_id,
        "status": overall,
        "message": message
    }


# ──────────────────────────────────────────────
# TRAIN NOW: Process all pending queue items immediately
# ──────────────────────────────────────────────
@app.post("/train-now")
def trigger_training(db: Session = Depends(get_db)):
    """
    Manually trigger processing of all pending queue items.
    Extracts face embeddings for each queued image and updates .pkl file.
    """
    pending_items = db.query(RegistrationQueue).filter(
        RegistrationQueue.status == "pending"
    ).all()

    if not pending_items:
        raise HTTPException(status_code=400, detail="No pending images in queue")

    processor = get_face_processor()
    # Group embeddings by student_id
    embeddings_by_student = {}

    for item in pending_items:
        try:
            # Read image from disk
            cv_img = processor.decode_image_path(item.image_path)
            if cv_img is None:
                item.status = "failed"
                item.error_message = "Could not read image file"
                item.processed_at = datetime.datetime.utcnow()
                db.commit()
                continue

            # Extract face embedding
            result = processor.extract_face_embedding(cv_img)
            if result and "embedding" in result:
                if item.student_id not in embeddings_by_student:
                    embeddings_by_student[item.student_id] = []
                embeddings_by_student[item.student_id].append(result["embedding"])
                item.status = "completed"
                item.processed_at = datetime.datetime.utcnow()
            else:
                item.status = "failed"
                item.error_message = "No face detected"
                item.processed_at = datetime.datetime.utcnow()

        except Exception as e:
            item.status = "failed"
            item.error_message = str(e)
            item.processed_at = datetime.datetime.utcnow()

        db.commit()

    # Update .pkl file with newly processed embeddings
    existing = load_embeddings()
    for student_id, emb_list in embeddings_by_student.items():
        user = db.query(User).filter(User.student_id == student_id).first()
        if user and emb_list:
            # Remove old data for this user
            existing = [e for e in existing if e.get("user_id") != user.id]
            existing.append({
                "user_id": user.id,
                "name": student_id,
                "student_id": student_id,
                "embeddings": emb_list
            })

    save_embeddings(existing)

    return {
        "message": "Background training started",
        "pending_images_in_queue": len(pending_items)
    }


# ──────────────────────────────────────────────
# LEGACY ENDPOINTS (backward compatible)
# ──────────────────────────────────────────────
@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """Legacy: Creates a new user profile. New users should use /register."""
    user = User(student_id=user_in.name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"status": "success", "user_id": user.id, "name": user.student_id}


@app.get("/users")
def list_users(db: Session = Depends(get_db)):
    """Lists all registered users."""
    users = db.query(User).all()
    return [{"user_id": u.id, "student_id": u.student_id, "created_at": u.created_at} for u in users]


@app.post("/users/{user_id}/images", status_code=status.HTTP_201_CREATED)
async def upload_user_image(
    user_id: int,
    file: Optional[UploadFile] = File(None),
    payload: Optional[ImageUploadBase64] = None,
    db: Session = Depends(get_db)
):
    """Legacy: Upload an image for an existing user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    image_base64 = None
    if file:
        file_bytes = await file.read()
        image_base64 = base64.b64encode(file_bytes).decode('utf-8')
    elif payload and payload.image_base64:
        image_base64 = payload.image_base64
    else:
        raise HTTPException(status_code=400, detail="Must provide an image file or a base64 string")

    img_record = UserImage(user_id=user_id, image_base64=image_base64)
    db.add(img_record)
    db.commit()
    db.refresh(img_record)

    return {
        "status": "success",
        "image_id": img_record.id,
        "user_id": user_id,
        "message": "Image uploaded successfully"
    }


@app.post("/train")
def train_model(db: Session = Depends(get_db)):
    """Legacy: Full retrain from all user images in DB."""
    try:
        # Reuse the existing training logic
        from app.trainer import train_system
        result = train_system(db)
        return result
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
    db: Session = Depends(get_db)
):
    """
    Real-time face verification. Matches the input photo against trained embeddings
    and logs the attendance record.
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
        log = CheckInLog(user_id=None, student_id=None, similarity_score=0.0, device_id=device_id)
        db.add(log)
        db.commit()
        return {"match": False, "student_id": None, "similarity_score": 0.0, "timestamp": datetime.datetime.utcnow().isoformat()}

    # Match against trained embeddings
    match = match_face(face_data["embedding"])
    
    if match:
        student_id = match.get("student_id", match.get("name", "Unknown"))
        log = CheckInLog(
            user_id=match["user_id"],
            student_id=student_id,
            similarity_score=match["similarity"],
            device_id=device_id
        )
        db.add(log)
        db.commit()
        
        return {
            "match": True,
            "student_id": student_id,
            "similarity_score": match["similarity"],
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    else:
        log = CheckInLog(user_id=None, student_id=None, similarity_score=0.0, device_id=device_id)
        db.add(log)
        db.commit()
        
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
def view_logs(limit: int = 50, db: Session = Depends(get_db)):
    """
    Retrieves the recent check-in logs.
    """
    logs = db.query(CheckInLog).order_by(CheckInLog.timestamp.desc()).limit(limit).all()
    results = []
    for log in logs:
        results.append({
            "id": log.id,
            "student_id": log.student_id if log.student_id else "Unknown",
            "similarity_score": log.similarity_score,
            "device_id": log.device_id,
            "timestamp": log.timestamp
        })
    return results


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)