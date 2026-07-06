import datetime
from fastapi import HTTPException, status
from typing import Optional

from app.database import (
    insert_log,
    match_face_embedding,
    get_latest_check_in_log,
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

    # Run image quality validation first
    val_res = processor.validate_image_quality(cv_img)
    if not val_res["passed"]:
        insert_log(student_id=None, similarity_score=0.0, device_id=device_id, error_message=val_res["error_message"])
        checklist = val_res["results"].copy()
        checklist["database_match"] = False
        return {
            "match": False,
            "student_id": None,
            "similarity_score": 0.0,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "message": val_res["error_message"],
            "validation_checklist": checklist
        }

    # Extract embedding
    face_data = processor.extract_face_embedding(cv_img, face=val_res.get("face"))
    if not face_data:
        # No face detected — log with no match
        insert_log(student_id=None, similarity_score=0.0, device_id=device_id, error_message="Please look at the camera")
        checklist = val_res["results"].copy()
        checklist["database_match"] = False
        return {
            "match": False,
            "student_id": None,
            "similarity_score": 0.0,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "message": "Please look at the camera",
            "validation_checklist": checklist
        }

    # Match against local .pkl embeddings
    match = match_face_embedding(face_data["embedding"])

    if match:
        student_id = match.get("student_id") or match.get("name", "Unknown")
        user_id = match.get("user_id")

        latest_log = get_latest_check_in_log(student_id)
        if latest_log:
            latest_time = latest_log["timestamp"]
            if isinstance(latest_time, str):
                if latest_time.endswith('Z'):
                    latest_time = latest_time[:-1] + '+00:00'
                try:
                    latest_dt = datetime.datetime.fromisoformat(latest_time)
                except ValueError:
                    try:
                        latest_dt = datetime.datetime.strptime(latest_time, "%Y-%m-%d %H:%M:%S.%f")
                    except ValueError:
                        latest_dt = datetime.datetime.strptime(latest_time[:19], "%Y-%m-%dT%H:%M:%S")
            else:
                latest_dt = latest_time

            if latest_dt.tzinfo is not None:
                latest_dt = latest_dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)

            elapsed = (datetime.datetime.utcnow() - latest_dt).total_seconds()
            if elapsed < 300:
                checklist = val_res["results"].copy()
                checklist["database_match"] = True
                return {
                    "match": True,
                    "student_id": student_id,
                    "similarity_score": match["similarity"],
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "message": "Student has already checked in within the last 5 minutes.",
                    "validation_checklist": checklist
                }

        insert_log(
            student_id=student_id,
            similarity_score=match["similarity"],
            device_id=device_id,
            user_id=user_id,
        )

        checklist = val_res["results"].copy()
        checklist["database_match"] = True
        return {
            "match": True,
            "student_id": student_id,
            "similarity_score": match["similarity"],
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "message": None,
            "validation_checklist": checklist
        }
    else:
        insert_log(student_id=None, similarity_score=0.0, device_id=device_id, error_message="Employee data not found")
        checklist = val_res["results"].copy()
        checklist["database_match"] = False
        return {
            "match": False,
            "student_id": None,
            "similarity_score": 0.0,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "message": "Employee data not found",
            "validation_checklist": checklist
        }
