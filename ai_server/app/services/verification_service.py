import datetime
from fastapi import HTTPException, status
from typing import Optional

from app.database import (
    insert_log,
    match_face_embedding,
)
from app.face_processor import get_face_processor
from app.utils.image_utils import decode_image_bytes, decode_base64_image

def verify_face(
    image_data: Optional[bytes] = None,
    image_base64: Optional[str] = None,
    device_id: str = "ESP32-S3-01"
) -> dict:
    """
    Real-time face verification. Matches the input BGR image (from raw bytes
    or base64 string) against local face embeddings and logs the attendance check-in.
    """
    processor = get_face_processor()
    cv_img = None

    if image_data:
        cv_img = decode_image_bytes(image_data)
    elif image_base64:
        try:
            cv_img = decode_base64_image(image_base64)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to decode base64 image: {str(e)}"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image provided. Send an image file or base64 parameter."
        )

    if cv_img is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image content."
        )

    # Extract embedding
    face_data = processor.extract_face_embedding(cv_img)
    if not face_data:
        # No face detected — log with no match
        insert_log(student_id=None, similarity_score=0.0, device_id=device_id)
        return {
            "match": False,
            "student_id": None,
            "similarity_score": 0.0,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

    # Match against local .pkl embeddings
    match = match_face_embedding(face_data["embedding"])

    if match:
        student_id = match.get("student_id") or match.get("name", "Unknown")
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
