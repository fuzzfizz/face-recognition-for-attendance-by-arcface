from fastapi import HTTPException, status

from app.database import (
    get_pending_queue_items,
    update_queue_item_status,
    get_all_embeddings,
    save_all_embeddings,
)
from app.face_processor import get_face_processor
from app.matcher import invalidate_cache

def process_pending_queue() -> dict:
    """
    Process all pending registration queue items, extract face embeddings,
    update queue status, save to .pkl, and invalidate the matcher cache.
    """
    pending_items = get_pending_queue_items()

    if not pending_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending images in queue. Upload images via /register first."
        )

    processor = get_face_processor()
    embeddings_by_student = {}

    for item in pending_items:
        try:
            cv_img = processor.decode_image_path(item["image_path"])
            if cv_img is None:
                update_queue_item_status(item["id"], "failed", "Could not read image file")
                continue

            result = processor.extract_face_embedding(cv_img)
            if result and "embedding" in result:
                student_id = item["student_id"]
                if student_id not in embeddings_by_student:
                    embeddings_by_student[student_id] = []
                embeddings_by_student[student_id].append(result["embedding"])
                update_queue_item_status(item["id"], "completed")
            else:
                update_queue_item_status(item["id"], "failed", "No face detected")

        except Exception as e:
            update_queue_item_status(item["id"], "failed", str(e))

    # Update .pkl file with newly processed embeddings
    existing = get_all_embeddings()
    for student_id, emb_list in embeddings_by_student.items():
        if emb_list:
            # Remove old data for this student
            existing = [e for e in existing if e.get("student_id") != student_id]
            existing.append({
                "user_id": student_id,
                "name": student_id,
                "student_id": student_id,
                "embeddings": emb_list
            })

    save_all_embeddings(existing)
    invalidate_cache()

    return {
        "message": "Training completed",
        "processed_students": list(embeddings_by_student.keys()),
        "total_pending": len(pending_items)
    }
