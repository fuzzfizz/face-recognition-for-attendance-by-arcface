import pickle
import numpy as np
from app.config import EMBEDDINGS_PATH, SIMILARITY_THRESHOLD

def load_embeddings():
    """
    Loads face embeddings from the pkl file.
    Returns:
        List of dicts: [ {"user_id": int, "name": str, "embeddings": [[512-d list], ...]} ]
    """
    if not EMBEDDINGS_PATH.exists():
        return []
    try:
        with open(EMBEDDINGS_PATH, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        print(f"Error loading embeddings: {e}")
        return []

def save_embeddings(embeddings_data):
    """
    Saves face embeddings to the pkl file.
    """
    # Ensure parent directory exists
    EMBEDDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EMBEDDINGS_PATH, 'wb') as f:
        pickle.dump(embeddings_data, f)

def match_face(query_embedding: list):
    """
    Compares the query embedding against all saved embeddings in the .pkl file using Cosine Similarity.
    
    Since the embeddings returned by FaceProcessor are L2-normalized, 
    Cosine Similarity is simply the dot product between the query vector and target vector.
    
    Returns:
        Dict with "user_id", "name", and "similarity" if a match is found above threshold, 
        else None.
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
        
        # A user might have multiple registered face embeddings (e.g., 10 captures)
        for stored_emb in user_data["embeddings"]:
            stored_vec = np.array(stored_emb)
            
            # Compute cosine similarity (dot product of normalized vectors)
            similarity = np.dot(query_vec, stored_vec)
            
            if similarity > max_sim:
                max_sim = similarity
                best_match = {
                    "user_id": user_id,
                    "name": name,
                    "similarity": float(similarity)
                }

    # Check if the highest similarity exceeds the predefined threshold
    if best_match and max_sim >= SIMILARITY_THRESHOLD:
        return best_match
        
    return None
