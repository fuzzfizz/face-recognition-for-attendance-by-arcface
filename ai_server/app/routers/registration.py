from fastapi import APIRouter, File, UploadFile, Form, status, Depends, HTTPException
from typing import List
import re

from app.schemas import RegisterResponse, RegistrationStatusResponse
from app.services import registration_service
from app.dependencies import require_admin

router = APIRouter(tags=["registration"])

def validate_student_id(student_id: str):
    if not re.match(r"^[a-zA-Z0-9_-]+$", student_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid student_id format. Only alphanumeric characters, dashes, and underscores are allowed."
        )

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_200_OK)
async def register(
    student_id: str = Form(...),
    name: str = Form(None),
    files: List[UploadFile] = File(...),
):
    """
    Upload face images for registration. Non-blocking — saves image to storage,
    creates queue entry, and returns immediately.
    """
    validate_student_id(student_id)
    return await registration_service.register_images(student_id, name, files)

@router.get("/register/status/{student_id}", response_model=RegistrationStatusResponse)
def get_status(student_id: str):
    """Check processing status for a student."""
    validate_student_id(student_id)
    return registration_service.get_registration_status(student_id)

@router.delete("/register/student/{student_id}", status_code=status.HTTP_200_OK)
def delete_student_endpoint(student_id: str, _ = Depends(require_admin)):
    """Delete a student, their images, queue records, and embeddings."""
    validate_student_id(student_id)
    return registration_service.delete_student(student_id)


