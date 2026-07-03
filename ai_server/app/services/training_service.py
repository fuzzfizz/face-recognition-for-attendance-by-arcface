from fastapi import HTTPException, status

from app.database import (
    get_pending_queue_items,
    update_queue_item_status,
    get_all_embeddings,
    save_all_embeddings,
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
    any_new_saved = False

    existing = get_all_embeddings()

    for student_id, student_items in items_by_student.items():
        new_embeddings = []

        for item in student_items:
            try:
                cv_img = processor.decode_image_path(item["image_path"])
                if cv_img is None:
                    all_item_statuses.append((item["id"], "failed", "Could not read image file"))
                    continue

                result = processor.extract_face_embedding(cv_img)
                if result and "embedding" in result:
                    new_embeddings.append(result["embedding"])
                    all_item_statuses.append((item["id"], "completed", None))
                else:
                    all_item_statuses.append((item["id"], "failed", "No face detected"))

            except Exception as e:
                all_item_statuses.append((item["id"], "failed", str(e)))

        if new_embeddings:
            any_new_saved = True
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
            processed_students.append(student_id)

    if any_new_saved:
        save_all_embeddings(existing)
        invalidate_cache()

    for item_id, db_status, err_msg in all_item_statuses:
        update_queue_item_status(item_id, db_status, err_msg)

    return {
        "message": "Training completed for batch",
        "processed_students": processed_students,
        "total_pending": len(pending_items)
    }

