from fastapi import APIRouter, File, UploadFile, Form, Path, Query
from typing import Optional

from app.schemas import VerifyResponse
from app.services import verification_service

router = APIRouter(tags=["verification"])

@router.post("/verify/face_recognition/{device_id}", response_model=VerifyResponse)
async def verify(
    device_id: str = Path(..., max_length=50, pattern="^[a-zA-Z0-9_-]+$"),
    file: Optional[UploadFile] = File(None),
    image_base64: Optional[str] = Form(None),
    timestamp: Optional[str] = Form(None),
    timestamp_query: Optional[str] = Query(None, alias="timestamp"),
):
    """
    Real-time face verification. Matches the input photo against local embeddings
    and logs attendance.
    """
    file_bytes = None
    if file:
        file_bytes = await file.read()
    
    effective_timestamp = timestamp or timestamp_query
    return verification_service.verify_face(
        image_data=file_bytes,
        image_base64=image_base64,
        device_id=device_id,
        timestamp=effective_timestamp
    )

@router.post("/verify", response_model=VerifyResponse, deprecated=True)
async def verify_legacy(
    device_id: Optional[str] = Form(None),
    device_id_query: Optional[str] = Query(None, alias="device_id"),
    file: Optional[UploadFile] = File(None),
    image_base64: Optional[str] = Form(None),
    timestamp: Optional[str] = Form(None),
    timestamp_query: Optional[str] = Query(None, alias="timestamp"),
):
    """
    Legacy face verification endpoint. Deprecated fallback for old ESP32-CAM clients.
    """
    effective_device_id = device_id or device_id_query or "ESP32-S3-01"
    print(f"[Warning] Deprecated endpoint /verify called by device: {effective_device_id}")

    file_bytes = None
    if file:
        file_bytes = await file.read()
        
    effective_timestamp = timestamp or timestamp_query
    return verification_service.verify_face(
        image_data=file_bytes,
        image_base64=image_base64,
        device_id=effective_device_id,
        timestamp=effective_timestamp
    )
