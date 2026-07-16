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
    device_id: str = "ESP32-S3-01",
    timestamp: Optional[str] = None
) -> dict:
    """
    Real-time face verification. Matches the input BGR image (from raw bytes
    or base64 string) against local face embeddings and logs the attendance check-in.
    """
    dt_obj = None
    if timestamp:
        clean_ts = timestamp.strip()
        if clean_ts.endswith("Z"):
            clean_ts = clean_ts[:-1] + "+00:00"
        try:
            dt_obj = datetime.datetime.fromisoformat(clean_ts)
        except ValueError as e:
            # Fall back to other common formats (especially 2-digit years like YY-MM-DDTHH:MM:SS.ffffff)
            formats_to_try = [
                "%y-%m-%dT%H:%M:%S.%f",
                "%y-%m-%d %H:%M:%S.%f",
                "%y-%m-%dT%H:%M:%S",
                "%y-%m-%d %H:%M:%S",
                "%y/%m/%d %H:%M:%S.%f",
                "%y/%m/%d %H:%M:%S",
                "%d-%m-%Y %H:%M:%S.%f",
                "%d-%m-%Y %H:%M:%S",
                "%d/%m/%Y %H:%M:%S.%f",
                "%d/%m/%Y %H:%M:%S",
            ]
            for fmt in formats_to_try:
                try:
                    dt_obj = datetime.datetime.strptime(clean_ts, fmt)
                    break
                except ValueError:
                    continue
            
            if dt_obj is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid timestamp format: {str(e)}"
                )
        if dt_obj.tzinfo is not None:
            dt_obj = dt_obj.astimezone(datetime.timezone.utc).replace(tzinfo=None)

    response_dt = dt_obj if dt_obj is not None else datetime.datetime.utcnow()

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
        log_kwargs = {
            "student_id": None,
            "similarity_score": 0.0,
            "device_id": device_id,
            "error_message": val_res["error_message"],
        }
        if dt_obj is not None:
            log_kwargs["timestamp"] = dt_obj
        insert_log(**log_kwargs)

        checklist = val_res["results"].copy()
        checklist["database_match"] = False
        return {
            "match": False,
            "student_id": None,
            "similarity_score": 0.0,
            "timestamp": response_dt.isoformat(),
            "message": val_res["error_message"],
            "validation_checklist": checklist
        }

    # Extract embedding
    face_data = processor.extract_face_embedding(cv_img, face=val_res.get("face"))
    if not face_data:
        # No face detected — log with no match
        log_kwargs = {
            "student_id": None,
            "similarity_score": 0.0,
            "device_id": device_id,
            "error_message": "Please look at the camera",
        }
        if dt_obj is not None:
            log_kwargs["timestamp"] = dt_obj
        insert_log(**log_kwargs)

        checklist = val_res["results"].copy()
        checklist["database_match"] = False
        return {
            "match": False,
            "student_id": None,
            "similarity_score": 0.0,
            "timestamp": response_dt.isoformat(),
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

            elapsed = (response_dt - latest_dt).total_seconds()
            if elapsed < 300:
                checklist = val_res["results"].copy()
                checklist["database_match"] = True
                return {
                    "match": True,
                    "student_id": student_id,
                    "similarity_score": match["similarity"],
                    "timestamp": response_dt.isoformat(),
                    "message": "Student has already checked in within the last 5 minutes.",
                    "validation_checklist": checklist
                }

        log_kwargs = {
            "student_id": student_id,
            "similarity_score": match["similarity"],
            "device_id": device_id,
            "user_id": user_id,
        }
        if dt_obj is not None:
            log_kwargs["timestamp"] = dt_obj
        insert_log(**log_kwargs)

        checklist = val_res["results"].copy()
        checklist["database_match"] = True
        return {
            "match": True,
            "student_id": student_id,
            "similarity_score": match["similarity"],
            "timestamp": response_dt.isoformat(),
            "message": None,
            "validation_checklist": checklist
        }
    else:
        log_kwargs = {
            "student_id": None,
            "similarity_score": 0.0,
            "device_id": device_id,
            "error_message": "Employee data not found",
        }
        if dt_obj is not None:
            log_kwargs["timestamp"] = dt_obj
        insert_log(**log_kwargs)

        checklist = val_res["results"].copy()
        checklist["database_match"] = False
        return {
            "match": False,
            "student_id": None,
            "similarity_score": 0.0,
            "timestamp": response_dt.isoformat(),
            "message": "Employee data not found",
            "validation_checklist": checklist
        }
