from fastapi import HTTPException, status

from app.database import (
    get_pending_queue_items,
    update_queue_item_status,
    get_all_embeddings,
    save_all_embeddings,
    get_image_blob_by_ref,
    add_user_image,
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

    for student_id, student_items in items_by_student.items():
        new_embeddings = []

        for item in student_items:
            try:
                cv_img = processor.decode_image_path(item["image_path"])
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
                    from app.matcher import match_face
                    match = match_face(result["embedding"])
                    if match and match["student_id"] != student_id:
                        all_item_statuses.append((item["id"], "failed", "This face is already registered"))
                    else:
                        new_embeddings.append(result["embedding"])
                        all_item_statuses.append((item["id"], "completed", None))
                        
                        # Get the raw image_blob and save it to user_images
                        image_blob = None
                        if item.get("image_path"):
                            if item["image_path"].startswith("db://"):
                                image_blob = get_image_blob_by_ref(item["image_path"])
                            else:
                                import os
                                if os.path.exists(item["image_path"]):
                                    try:
                                        with open(item["image_path"], "rb") as f:
                                            image_blob = f.read()
                                    except Exception as e:
                                        print(f"Error reading local file: {e}")
                        
                        if image_blob:
                            add_user_image(student_id, image_blob)
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
            save_all_embeddings(existing)
            invalidate_cache()
            processed_students.append(student_id)

    for item_id, db_status, err_msg in all_item_statuses:
        update_queue_item_status(item_id, db_status, err_msg)

    return {
        "message": "Training completed for batch",
        "processed_students": processed_students,
        "total_pending": len(pending_items)
    }

