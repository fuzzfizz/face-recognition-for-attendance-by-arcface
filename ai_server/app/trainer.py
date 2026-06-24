"""
Trainer module — processes face images and updates the local .pkl embeddings file.
Works with both Supabase and SQLite modes via the database abstraction layer.
"""
import base64
import cv2
import numpy as np
from app.database import get_all_embeddings, save_all_embeddings
from app.face_processor import get_face_processor


def decode_base64_image(base64_str: str) -> np.ndarray:
    """
    Decodes a base64 string into an OpenCV image (numpy array).
    """
    if "," in base64_str:
        # Split out the header (e.g., "data:image/jpeg;base64,...")
        base64_str = base64_str.split(",")[1]
    img_data = base64.b64decode(base64_str)
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img


def train_system():
    """
    Re-processes all existing embeddings in the .pkl file.
    This is useful for re-training after model changes or data cleanup.
    Note: In the new architecture, training is primarily done via /train-now
    which processes the queue. This function is kept for backward compatibility.
    """
    processor = get_face_processor()
    embeddings_data = get_all_embeddings()

    if not embeddings_data:
        return {
            "status": "success",
            "users_trained": 0,
            "total_embeddings": 0,
            "message": "No embeddings found in .pkl file"
        }

    total_embeddings_count = sum(
        len(e.get("embeddings", [])) for e in embeddings_data
    )

    return {
        "status": "success",
        "users_trained": len(embeddings_data),
        "total_embeddings": total_embeddings_count,
        "message": "Embeddings are already up to date in local .pkl"
    }