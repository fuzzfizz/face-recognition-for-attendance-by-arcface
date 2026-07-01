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

    queue_count = 0
    for file in files:
        file_bytes = await file.read()
        if not file_bytes:
            continue

        ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"

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

    return {
        "student_id": student_id,
        "status": "pending",
        "message": "Waiting for AI processing (trigger /train-now)"
    }
