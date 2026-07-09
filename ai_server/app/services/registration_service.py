from fastapi import UploadFile, HTTPException, status
from typing import List

from app.database import (
    upsert_user,
    get_user_by_student_id,
    upload_image,
    get_all_embeddings,
    save_all_embeddings,
    delete_student_from_db,
    get_pending_queue_items,
    match_face_embedding,
)
from app.matcher import invalidate_cache

def delete_student(student_id: str) -> dict:
    """Delete a student's registration records, embeddings, and clear cache."""
    success = delete_student_from_db(student_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete student database/storage records"
        )

    existing = get_all_embeddings()
    updated = [e for e in existing if e.get("student_id") != student_id]
    if len(updated) < len(existing):
        save_all_embeddings(updated)
        invalidate_cache()

    return {
        "message": "Student registration data deleted successfully",
        "student_id": student_id
    }

async def register_images(student_id: str, name: str, files: List[UploadFile]) -> dict:
    """
    Upsert user in storage, upload images to storage, insert queue entries,
    and return the result.
    """
    # Self-healing: if not in test mode, check database existence and prune orphaned embeddings
    from app.config import is_local_or_test
    if not is_local_or_test:
        db_user = get_user_by_student_id(student_id)
        if not db_user:
            # User is not in DB, but embeddings exist in pickle -> prune
            existing_all = get_all_embeddings()
            updated = [e for e in existing_all if e.get("student_id") != student_id]
            if len(updated) < len(existing_all):
                save_all_embeddings(updated)
                invalidate_cache()

    # 1. Quota Check: count user images (already registered embeddings) + pending queue records.
    # Limit to 10 photos per student (including already registered embeddings and pending queue records).
    pending_items = get_pending_queue_items()
    pending_count = sum(1 for item in pending_items if item.get("student_id") == student_id)

    existing_embeddings = []
    for record in get_all_embeddings():
        if record.get("student_id") == student_id:
            existing_embeddings = record.get("embeddings", [])
            break
    existing_count = len(existing_embeddings)

    if existing_count + pending_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Already registered 10 photos (Quota full)",
                "results": []
            }
        )

    if existing_count + pending_count + len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": f"Cannot register {len(files)} photos. Already registered {existing_count + pending_count} photos. Remaining quota is {10 - (existing_count + pending_count)} photos.",
                "results": []
            }
        )

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
            results.append({
                "filename": file.filename,
                "passed": False,
                "error": "Empty upload file",
                "validation_checklist": {
                    "face_detected": False,
                    "single_face": False,
                    "database_match": None
                }
            })
            has_failure = True
            continue
        cv_img = processor.decode_image(file_bytes)
        if cv_img is None:
            results.append({
                "filename": file.filename,
                "passed": False,
                "error": "Cannot parse image file",
                "validation_checklist": {
                    "face_detected": False,
                    "single_face": False,
                    "database_match": None
                }
            })
            has_failure = True
            continue
        
        val_res = processor.validate_image_quality(cv_img)
        if not val_res["passed"]:
            err_msg = val_res["error_message"]
            if err_msg == "Please look at the camera":
                err_msg = "Face not found, please retake"
            elif err_msg == "One person at a time":
                err_msg = "Multiple faces in frame"
            results.append({
                "filename": file.filename,
                "passed": False,
                "error": err_msg,
                "validation_checklist": val_res["results"]
            })
            has_failure = True
        else:
            # 2. Duplicate Check: extract embedding and check against system
            face_data = processor.extract_face_embedding(cv_img, face=val_res.get("face"))
            if face_data and "embedding" in face_data:
                match = match_face_embedding(face_data["embedding"])
                if match and match.get("student_id") != student_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "message": "This face is already registered",
                            "results": []
                        }
                    )

            results.append({
                "filename": file.filename,
                "passed": True,
                "error": None,
                "validation_checklist": val_res["results"]
            })
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
        # Directly upload image to MySQL blob storage and queue it as "pending"
        queue_id = upload_image(file_bytes, student_id)
        if queue_id is None:
            continue

        queue_count += 1

    if queue_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid images were uploaded"
        )

    return {
        "message": "Images queued for processing successfully",
        "student_id": student_id,
        "status": "pending",
        "validation_checklist": results[0]["validation_checklist"] if results else None
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
