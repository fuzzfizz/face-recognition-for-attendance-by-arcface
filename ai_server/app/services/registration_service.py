from fastapi import UploadFile, HTTPException, status
from typing import List

from app.database import (
    upsert_user,
    get_user_by_student_id,
    upload_image,
    insert_queue_item,
    get_all_embeddings,
)

async def register_images(student_id: str, name: str, files: List[UploadFile]) -> dict:
    """
    Upsert user in storage, upload images to storage, insert queue entries,
    and return the result.
    """

    user = upsert_user(student_id, name)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user record"
        )

    from app.face_processor import get_face_processor
    processor = get_face_processor()

    # Pre-read and check faces first:
    decoded_images = []
    results = []
    has_failure = False
    for file in files:
        file_bytes = await file.read()
        if not file_bytes:
            continue
        cv_img = processor.decode_image(file_bytes)
        if cv_img is None:
            results.append({"filename": file.filename, "passed": False, "error": "Cannot parse image file"})
            has_failure = True
            continue
        faces = processor.app.get(cv_img)
        if not faces:
            results.append({"filename": file.filename, "passed": False, "error": "No face detected"})
            has_failure = True
        else:
            results.append({"filename": file.filename, "passed": True, "error": None})
            decoded_images.append((file.filename, file_bytes))

    if has_failure:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Some photos failed face verification.",
                "results": results
            }
        )

    queue_count = 0
    for filename, file_bytes in decoded_images:
        ext = filename.split(".")[-1] if filename and "." in filename else "jpg"

        image_path = upload_image(file_bytes, student_id, ext)
        if not image_path:
            continue

        insert_queue_item(student_id, image_path)
        queue_count += 1

    if queue_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid images were uploaded"
        )

    return {
        "message": "Images queued for processing successfully",
        "student_id": student_id,
        "status": "pending"
    }

def get_registration_status(student_id: str) -> dict:
    """Check user registration status."""
    user = get_user_by_student_id(student_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No registration found for student_id: {student_id}"
        )

    embeddings = get_all_embeddings()
    for e in embeddings:
        if e.get("student_id") == student_id:
            return {
                "student_id": student_id,
                "status": "completed",
                "message": "Face extracted and saved successfully"
            }

    from app.config import TRAINING_SCHEDULE_INFO
    return {
        "student_id": student_id,
        "status": "pending",
        "message": f"Waiting for AI processing. Scheduled updates run {TRAINING_SCHEDULE_INFO}."
    }
