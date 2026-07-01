"""
Supabase client wrapper.
Handles all interactions with Supabase PostgreSQL + Storage.
If SUPABASE_URL is empty, falls back to a no-op mode (for offline dev).
"""
import io
import uuid
import base64
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_STORAGE_BUCKET

# Lazy-init supabase client
_supabase = None


def get_supabase():
    global _supabase
    if _supabase is None and SUPABASE_URL and SUPABASE_KEY:
        from supabase import create_client
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase


def is_available() -> bool:
    """Check if Supabase is configured and reachable."""
    return bool(SUPABASE_URL and SUPABASE_KEY)


# ──────────────────────────────────────────────
# USERS
# ──────────────────────────────────────────────
def upsert_user(student_id: str, name: str = None) -> Optional[Dict[str, Any]]:
    """
    Create or retrieve a user in Supabase using an atomic upsert.
    Returns the user record dict or None if Supabase is unavailable.
    """
    if not is_available():
        return None
    try:
        sb = get_supabase()
        payload = {"student_id": student_id}
        if name:
            payload["name"] = name
        response = sb.table("users").upsert(
            payload, on_conflict="student_id"
        ).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"[Supabase] upsert_user error: {e}")
        return None


def get_user(student_id: str) -> Optional[Dict[str, Any]]:
    """Get user by student_id from Supabase."""
    if not is_available():
        return None
    try:
        sb = get_supabase()
        result = sb.table("users").select("*").eq("student_id", student_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"[Supabase] get_user error: {e}")
        return None


# ──────────────────────────────────────────────
# CHECK-IN LOGS
# ──────────────────────────────────────────────
def insert_log(
    student_id: Optional[str],
    similarity_score: float,
    device_id: Optional[str],
    supabase_user_id: Optional[Any] = None
) -> bool:
    """Insert a check-in log into Supabase."""
    if not is_available():
        return False
    try:
        sb = get_supabase()
        
        actual_user_id = None
        if supabase_user_id is not None:
            try:
                actual_user_id = int(supabase_user_id)
            except ValueError:
                pass
                
        if actual_user_id is None and student_id:
            user_record = get_user(student_id)
            if user_record:
                actual_user_id = user_record.get("id")

        sb.table("check_in_logs").insert({
            "user_id": actual_user_id,
            "student_id": student_id,
            "similarity_score": similarity_score,
            "device_id": device_id,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()
        return True
    except Exception as e:
        print(f"[Supabase] insert_log error: {e}")
        return False


def get_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent check-in logs from Supabase."""
    if not is_available():
        return []
    try:
        sb = get_supabase()
        result = sb.table("check_in_logs") \
            .select("*") \
            .order("timestamp", desc=True) \
            .limit(limit) \
            .execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"[Supabase] get_logs error: {e}")
        return []


# ──────────────────────────────────────────────
# REGISTRATION QUEUE
# ──────────────────────────────────────────────
def insert_queue_item(student_id: str, image_path: str) -> bool:
    """Insert a registration queue item into Supabase."""
    if not is_available():
        return False
    try:
        sb = get_supabase()
        sb.table("registration_queue").insert({
            "student_id": student_id,
            "image_path": image_path,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        return True
    except Exception as e:
        print(f"[Supabase] insert_queue_item error: {e}")
        return False


def update_queue_item(queue_id: int, status: str, error_message: Optional[str] = None) -> bool:
    """Update a queue item status in Supabase."""
    if not is_available():
        return False
    try:
        sb = get_supabase()
        update_data = {
            "status": status,
            "processed_at": datetime.utcnow().isoformat()
        }
        if error_message:
            update_data["error_message"] = error_message
        sb.table("registration_queue").update(update_data).eq("id", queue_id).execute()
        return True
    except Exception as e:
        print(f"[Supabase] update_queue_item error: {e}")
        return False


def get_pending_queue_items() -> List[Dict[str, Any]]:
    """Get all pending registration queue items from Supabase."""
    if not is_available():
        return []
    try:
        response = get_supabase().table("registration_queue").select("*").eq("status", "pending").execute()
        return response.data or []
    except Exception as e:
        print(f"[Supabase] get_pending_queue_items error: {e}")
        return []


# ──────────────────────────────────────────────
# STORAGE (Images)
# ──────────────────────────────────────────────
def upload_image(file_bytes: bytes, student_id: str, ext: str = "jpg") -> Optional[str]:
    """
    Upload an image to Supabase Storage.
    Returns the public URL of the uploaded image, or None on failure.
    """
    if not is_available():
        return None
    try:
        sb = get_supabase()
        filename = f"{student_id}_{uuid.uuid4().hex[:8]}.{ext}"
        # Upload to storage bucket
        sb.storage.from_(SUPABASE_STORAGE_BUCKET).upload(
            filename,
            file_bytes,
            {"content-type": f"image/{ext}"}
        )
        # Get public URL
        public_url = sb.storage.from_(SUPABASE_STORAGE_BUCKET).get_public_url(filename)
        return public_url
    except Exception as e:
        print(f"[Supabase] upload_image error: {e}")
        return None


def get_image_url(filename: str) -> Optional[str]:
    """Get public URL of an image in Supabase Storage."""
    if not is_available():
        return None
    try:
        sb = get_supabase()
        return sb.storage.from_(SUPABASE_STORAGE_BUCKET).get_public_url(filename)
    except Exception as e:
        print(f"[Supabase] get_image_url error: {e}")
        return None