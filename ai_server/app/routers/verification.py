from fastapi import APIRouter, File, UploadFile, Form
from typing import Optional

from app.schemas import VerifyResponse
from app.services import verification_service

router = APIRouter(tags=["verification"])

@router.post("/verify", response_model=VerifyResponse)
async def verify(
    file: Optional[UploadFile] = File(None),
    image_base64: Optional[str] = Form(None),
    device_id: str = Form("ESP32-S3-01"),
):
    """
    Real-time face verification. Matches the input photo against local embeddings
    and logs attendance.
    """
    file_bytes = None
    if file:
        file_bytes = await file.read()
    return verification_service.verify_face(
        image_data=file_bytes,
        image_base64=image_base64,
        device_id=device_id
    )
