"""
Face embedding matcher with mtime-based in-memory cache.

Loads embeddings from a .pkl file and matches a query embedding against
all stored embeddings using cosine similarity (dot product of L2-normalised
vectors).
"""
import pickle

import numpy as np

from app.config import EMBEDDINGS_PATH, SIMILARITY_THRESHOLD

# ── In-memory cache ──────────────────────────────────────────────────
_cache: list | None = None
_cache_mtime: float = 0.0


def load_embeddings() -> list:
    """
    Load face embeddings from the .pkl file.

    Uses an mtime-based cache: the file is re-read only when the
    modification time has changed (or the cache has been invalidated).
    """
    global _cache, _cache_mtime

    if not EMBEDDINGS_PATH.exists():
        return []

    try:
        current_mtime = EMBEDDINGS_PATH.stat().st_mtime
    except OSError:
        return _cache if _cache is not None else []

    if _cache is not None and current_mtime == _cache_mtime:
        return _cache

    try:
        with open(EMBEDDINGS_PATH, "rb") as f:
            _cache = pickle.load(f)
        _cache_mtime = current_mtime
        return _cache
    except Exception as e:
        print(f"Error loading embeddings: {e}")
        return _cache if _cache is not None else []


def save_embeddings(embeddings_data: list) -> None:
    """Save face embeddings to the .pkl file."""
    EMBEDDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EMBEDDINGS_PATH, "wb") as f:
        pickle.dump(embeddings_data, f)


def invalidate_cache() -> None:
    """Clear the in-memory cache so the next load re-reads from disk."""
    global _cache, _cache_mtime
    _cache = None
    _cache_mtime = 0.0


def match_face(query_embedding: list) -> dict | None:
    """
    Compare *query_embedding* against all saved embeddings using cosine
    similarity (dot product of L2-normalised vectors).

    Returns a dict with ``user_id``, ``name``, ``student_id``, and
    ``similarity`` if a match is found above the threshold, else ``None``.
    """
    embeddings_list = load_embeddings()
    if not embeddings_list:
        return None

    query_vec = np.array(query_embedding)

    best_match = None
    max_sim = -1.0

    for user_data in embeddings_list:
        user_id = user_data["user_id"]
        name = user_data["name"]
        student_id = user_data.get("student_id") or user_data.get("name", "unknown")

        for stored_emb in user_data["embeddings"]:
            stored_vec = np.array(stored_emb)
            similarity = float(np.dot(query_vec, stored_vec))

            if similarity > max_sim:
                max_sim = similarity
                best_match = {
                    "user_id": user_id,
                    "name": name,
                    "student_id": student_id,
                    "similarity": similarity,
                }

    if best_match and max_sim >= SIMILARITY_THRESHOLD:
        return best_match

    return None
