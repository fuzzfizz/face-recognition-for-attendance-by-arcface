from fastapi import HTTPException, status

import app.config
import app.database
import app.matcher
from app.database import (
    get_pending_queue_items,
    update_queue_item_status,
    get_all_embeddings,
    save_all_embeddings,
    get_user_by_student_id,
)
from app.face_processor import get_face_processor
from app.matcher import invalidate_cache

def process_pending_queue(limit: int = 50) -> dict:
    """
    Process all pending registration queue items, group by student, extract face embeddings,
    update queue status, save to .pkl per student, and invalidate the matcher cache.
    """
    pending_items = get_pending_queue_items(limit=limit)

    if not pending_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending images in queue. Upload images via /register first."
        )

    items_by_student = {}
    for item in pending_items:
        student_id = item["student_id"]
        if student_id not in items_by_student:
            items_by_student[student_id] = []
        items_by_student[student_id].append(item)

    processor = get_face_processor()
    processed_students = []
    all_item_statuses = []

    existing = get_all_embeddings()
    embeddings_changed = False

    for student_id, student_items in items_by_student.items():
        # Check if the student exists in the database (Self-healing Orphan Queue Check)
        if not app.config.is_local_or_test:
            db_user = app.database.get_user_by_student_id(student_id)
            if not db_user:
                # Student is orphaned! Skip processing and mark all queue items as failed
                for item in student_items:
                    all_item_statuses.append((item["id"], "failed", "Student record not found in database"))
                
                # Prune in-memory
                old_len = len(existing)
                existing = [e for e in existing if e.get("student_id") != student_id]
                if len(existing) < old_len:
                    embeddings_changed = True
                continue

        new_embeddings = []

        for item in student_items:
            try:
                # Decode image directly from database blob in memory
                cv_img = processor.decode_image(item["image_blob"])
                if cv_img is None:
                    all_item_statuses.append((item["id"], "failed", "Could not read image file"))
                    continue

                val_res = processor.validate_image_quality(cv_img)
                if not val_res["passed"]:
                    all_item_statuses.append((item["id"], "failed", val_res["error_message"]))
                    continue

                result = processor.extract_face_embedding(cv_img, face=val_res.get("face"))
                if result and "embedding" in result:
                    # Check for duplicate face matching a different student
                    match = app.matcher.match_face(result["embedding"])
                    if match and match.get("student_id") != student_id:
                        matched_student_id = match.get("student_id")
                        is_orphaned = False
                        if not app.config.is_local_or_test:
                            matched_user = app.database.get_user_by_student_id(matched_student_id)
                            if not matched_user:
                                is_orphaned = True
                                # Prune the orphaned student's embeddings in-memory
                                old_len = len(existing)
                                existing = [e for e in existing if e.get("student_id") != matched_student_id]
                                if len(existing) < old_len:
                                    embeddings_changed = True
                        
                        if not is_orphaned:
                            all_item_statuses.append((item["id"], "failed", "This face is already registered"))
                        else:
                            new_embeddings.append(result["embedding"])
                            all_item_statuses.append((item["id"], "completed", None))
                    else:
                        new_embeddings.append(result["embedding"])
                        all_item_statuses.append((item["id"], "completed", None))
                else:
                    all_item_statuses.append((item["id"], "failed", "No face detected"))

            except Exception as e:
                all_item_statuses.append((item["id"], "failed", str(e)))

        if new_embeddings:
            student_entry = next((e for e in existing if e.get("student_id") == student_id), None)
            if student_entry:
                student_entry["embeddings"].extend(new_embeddings)
                student_entry["embeddings"] = student_entry["embeddings"][-20:]
            else:
                existing.append({
                    "user_id": student_id,
                    "name": student_id,
                    "student_id": student_id,
                    "embeddings": new_embeddings[-20:]
                })
            embeddings_changed = True
            processed_students.append(student_id)

    # Save once at the end if any changes were made
    if embeddings_changed:
        save_all_embeddings(existing)
        invalidate_cache()

    for item_id, db_status, err_msg in all_item_statuses:
        update_queue_item_status(item_id, db_status, err_msg)

    return {
        "message": "Training completed for batch",
        "processed_students": processed_students,
        "total_pending": len(pending_items)
    }

