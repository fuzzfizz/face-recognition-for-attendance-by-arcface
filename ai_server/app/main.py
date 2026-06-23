import datetime
from fastapi import FastAPI, Depends, File, UploadFile, Form, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import pydantic

from app.config import HOST, PORT
from app.database import init_db, get_db, User, UserImage, CheckInLog
from app.face_processor import get_face_processor
from app.matcher import match_face
from app.trainer import train_system, decode_base64_image

# Initialize Database
init_db()

# Initialize FastAPI App
app = FastAPI(
    title="Face Recognition AI Server",
    description="Backend API for Face Alignment, Feature Extraction, .pkl training, and ESP32 Verification",
    version="1.0.0"
)

# Pydantic Schemas for API Requests/Responses
class UserCreate(pydantic.BaseModel):
    name: str

class ImageUploadBase64(pydantic.BaseModel):
    image_base64: str

# Endpoints
@app.get("/")
def read_root():
    return {"message": "Face Recognition AI Server is running!"}

@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Creates a new user profile in the database.
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
    This supports up to 10 photos per user for the learning database.
    """
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    image_base64 = None
    
    # Process from uploaded file
    if file:
        file_bytes = await file.read()
        import base64
        image_base64 = base64.b64encode(file_bytes).decode('utf-8')
    # Process from base64 JSON payload
    elif payload and payload.image_base64:
        image_base64 = payload.image_base64
    else:
        raise HTTPException(status_code=400, detail="Must provide an image file or a base64 string")

    # Add to database
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
    """
    Triggers the face training process:
    Pulls all user images, aligns them, extracts embedding vectors, 
    and saves them in the memory .pkl file for real-time verification.
    """
    try:
        result = train_system(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

@app.post("/verify")
async def verify_identity(
    file: Optional[UploadFile] = File(None),
    image_base64: Optional[str] = Form(None),
    device_id: Optional[str] = Form("esp32_cam"),
    db: Session = Depends(get_db)
):
    """
    Receives an image (e.g. from ESP32 camera via file upload or base64 form parameter),
    performs face detection/alignment/feature extraction, matches it against trained .pkl embeddings,
    logs the event in the database, and returns the identification result.
    """
    processor = get_face_processor()
    cv_img = None

    # Decode image from Uploaded File
    if file:
        file_bytes = await file.read()
        cv_img = processor.decode_image(file_bytes)
    # Decode image from Base64 Form
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
        # No face detected: Log unknown event with no user
        log = CheckInLog(user_id=None, similarity_score=0.0, device_id=device_id)
        db.add(log)
        db.commit()
        return {"status": "no_face_detected", "message": "No face found in the image"}

    # 2. Compare embeddings with trained pkl
    match = match_face(face_data["embedding"])
    
    if match:
        # Match found: Log the successful check-in
        log = CheckInLog(
            user_id=match["user_id"], 
            similarity_score=match["similarity"], 
            device_id=device_id
        )
        db.add(log)
        db.commit()
        
        return {
            "status": "matched",
            "user_id": match["user_id"],
            "name": match["name"],
            "similarity": match["similarity"]
        }
    else:
        # No match above threshold: Log unknown face check-in
        log = CheckInLog(user_id=None, similarity_score=0.0, device_id=device_id)
        db.add(log)
        db.commit()
        
        return {
            "status": "unknown",
            "message": "Face detected, but does not match any registered user"
        }

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
