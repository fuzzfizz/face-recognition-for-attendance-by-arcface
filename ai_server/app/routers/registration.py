from fastapi import APIRouter, File, UploadFile, Form, status
from typing import List

from app.schemas import RegisterResponse, RegistrationStatusResponse
from app.services import registration_service

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
