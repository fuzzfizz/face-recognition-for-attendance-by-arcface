from fastapi import APIRouter, File, UploadFile, Form, status, Depends
from typing import List

from app.schemas import RegisterResponse, RegistrationStatusResponse
from app.services import registration_service
from app.dependencies import require_admin

router = APIRouter(tags=["registration"])

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
    return await registration_service.register_images(student_id, name, files)

@router.get("/register/status/{student_id}", response_model=RegistrationStatusResponse)
def get_status(student_id: str):
    """Check processing status for a student."""
    return registration_service.get_registration_status(student_id)

@router.delete("/register/student/{student_id}", status_code=status.HTTP_200_OK)
def delete_student_endpoint(student_id: str, _ = Depends(require_admin)):
    """Delete a student, their images, queue records, and embeddings."""
    return registration_service.delete_student(student_id)

