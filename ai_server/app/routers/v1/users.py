import base64
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status
from typing import Optional

from app.database import (
    upsert_user,
    get_all_embeddings,
    upload_image,
)
from app.dependencies import require_admin
from app.schemas import UserCreate, ImageUploadBase64
from app.services import training_service

router = APIRouter()

@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserCreate):
    """Creates a new user profile."""
    user = upsert_user(user_in.name)
    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user")
    return {
        "status": "success",
        "user_id": user.get("id") or user.get("student_id"),
        "name": user_in.name
    }

@router.get("/users")
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

@router.post("/users/{user_id}/images", status_code=status.HTTP_201_CREATED)
async def upload_user_image(
    user_id: int,
    file: Optional[UploadFile] = File(None),
    payload: Optional[ImageUploadBase64] = None,
):
    """Upload an image for an existing user."""
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

    # Directly upload image to MySQL blob storage and queue it as "pending"
    queue_id = upload_image(file_bytes, student_id)
    if queue_id is None:
        raise HTTPException(status_code=500, detail="Failed to upload image")

    return {
        "status": "success",
        "user_id": user_id,
        "message": "Image uploaded and queued for processing successfully"
    }

@router.post("/train")
def train_model(limit: int = 50, admin=Depends(require_admin)):
    """Legacy train endpoint. Calls new training service."""
    try:
        return training_service.process_pending_queue(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")
