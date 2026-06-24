import datetime
import base64
from fastapi import FastAPI, Depends, File, UploadFile, Form, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
import pydantic

from app.config import HOST, PORT
from app.database import init_db, get_db, User, UserImage, CheckInLog
from app.face_processor import get_face_processor
from app.matcher import match_face, save_embeddings
from app.trainer import train_system, decode_base64_image

# Initialize Database
init_db()

# Initialize FastAPI App
app = FastAPI(
    title="Face Recognition AI Server (Optimized)",
    description="Optimized API for Face Registration, Real-Time Verification, and Attendance Logging",
    version="2.0.0"
)

# Pydantic Schemas for API Requests/Responses
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
# REGISTER: One-step user creation + image upload + face embedding extraction
# ──────────────────────────────────────────────
@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    name: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Register a new user and extract face embeddings in a single request.
    
    - Accepts `name` (text) and one or more `file` (image) fields via form-data.
    - Creates the user profile in the database.
    - Stores the uploaded images as base64 in the database.
    - Automatically extracts face embeddings and saves them to .pkl — no separate `/train` call needed.
    """
    # 1. Create user
    user = User(name=name)
    db.add(user)
    db.commit()
    db.refresh(user)

    # 2. Store images and collect embeddings
    processor = get_face_processor()
    user_embeddings = []
    images_saved = 0

    for file in files:
        file_bytes = await file.read()
        if not file_bytes:
            continue

        # Encode to base64 for DB storage
        img_b64 = base64.b64encode(file_bytes).decode('utf-8')

        # Save image record to DB
        img_record = UserImage(user_id=user.id, image_base64=img_b64)
        db.add(img_record)
        db.commit()
        db.refresh(img_record)
        images_saved += 1

        # Extract face embedding immediately (no separate /train needed)
        cv_img = processor.decode_image(file_bytes)
        if cv_img is not None:
            result = processor.extract_face_embedding(cv_img)
            if result and "embedding" in result:
                user_embeddings.append(result["embedding"])

    # 3. If we got valid embeddings, merge them into the .pkl file
    if user_embeddings:
        existing = _load_existing_embeddings()
        # Remove any previous data for this user (in case of re-registration)
        existing = [e for e in existing if e["user_id"] != user.id]
        existing.append({
            "user_id": user.id,
            "name": user.name,
            "embeddings": user_embeddings
        })
        save_embeddings(existing)

    return {
        "message": "User registered and face embedded successfully",
        "user_id": user.id,
        "name": user.name
    }


def _load_existing_embeddings():
    """Load the current .pkl embeddings list."""
    from app.matcher import load_embeddings
    return load_embeddings()


# ──────────────────────────────────────────────
# LEGACY: Create User (kept for backward compatibility)
# ──────────────────────────────────────────────
@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Creates a new user profile in the database.
    (Legacy — use `/register` for new enrollments.)
    """
    user = User(name=user_in.name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"status": "success", "user_id": user.id, "name": user.name}


@app.get("/users")
def list_users(db: Session = Depends(get_db)):
    """
    Lists all registered users in the database.
    """
    users = db.query(User).all()
    return [{"user_id": u.id, "name": u.name, "created_at": u.created_at} for u in users]


@app.post("/users/{user_id}/images", status_code=status.HTTP_201_CREATED)
async def upload_user_image(
    user_id: int,
    file: Optional[UploadFile] = File(None),
    payload: Optional[ImageUploadBase64] = None,
    db: Session = Depends(get_db)
):
    """
    Registers an image for a user. Accepts either a multipart/form-data upload file or a JSON base64 string.
    (Legacy — use `/register` for new enrollments.)
    """
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


# ──────────────────────────────────────────────
# LEGACY: Train (kept for backward compatibility; new users go through /register)
# ──────────────────────────────────────────────
@app.post("/train")
def train_model(db: Session = Depends(get_db)):
    """
    Triggers the face training process:
    Pulls all user images, aligns them, extracts embedding vectors, 
    and saves them in the memory .pkl file for real-time verification.
    (Legacy — the new `/register` endpoint handles this automatically.)
    """
    try:
        result = train_system(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


# ──────────────────────────────────────────────
# VERIFY: Face recognition + attendance logging
# ──────────────────────────────────────────────
@app.post("/verify")
async def verify_identity(
    file: Optional[UploadFile] = File(None),
    image_base64: Optional[str] = Form(None),
    device_id: Optional[str] = Form("ESP32-S3-01"),
    db: Session = Depends(get_db)
):
    """
    Receives an image (from ESP32-S3 camera via file upload or base64),
    performs face detection/alignment/feature extraction, matches against trained .pkl embeddings,
    logs the event in the database, and returns the identification result.
    """
    processor = get_face_processor()
    cv_img = None

    if file:
        file_bytes = await file.read()
        cv_img = processor.decode_image(file_bytes)
    elif image_base64:
        try:
            cv_img = decode_base64_image(image_base64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to decode base64 image: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="No image provided. Send an image file or base64 parameter.")

    if cv_img is None:
        raise HTTPException(status_code=400, detail="Invalid image content.")

    # 1. Align and Extract Embedding
    face_data = processor.extract_face_embedding(cv_img)
    if not face_data:
        log = CheckInLog(user_id=None, similarity_score=0.0, device_id=device_id)
        db.add(log)
        db.commit()
        return {"status": "no_face_detected", "message": "No face found in the image"}

    # 2. Compare embeddings with trained pkl
    match = match_face(face_data["embedding"])
    
    if match:
        log = CheckInLog(
            user_id=match["user_id"], 
            similarity_score=match["similarity"], 
            device_id=device_id
        )
        db.add(log)
        db.commit()
        
        return {
            "match": True,
            "user_id": match["user_id"],
            "name": match["name"],
            "similarity_score": match["similarity"],
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    else:
        log = CheckInLog(user_id=None, similarity_score=0.0, device_id=device_id)
        db.add(log)
        db.commit()
        
        return {
            "match": False,
            "user_id": None,
            "name": "Unknown",
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
            "user_id": log.user_id,
            "name": log.user.name if log.user else "Unknown",
            "similarity_score": log.similarity_score,
            "device_id": log.device_id,
            "timestamp": log.timestamp
        })
    return results


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
