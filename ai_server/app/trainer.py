import base64
import cv2
import numpy as np
from sqlalchemy.orm import Session
from app.database import User, UserImage
from app.face_processor import get_face_processor
from app.matcher import save_embeddings

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

def train_system(db: Session):
    """
    Retrieves all users and their registered images from the database,
    processes them to extract face embeddings, and saves them to the .pkl file.
    """
    processor = get_face_processor()
    users = db.query(User).all()
    
    embeddings_data = []
    total_embeddings_count = 0
    users_trained_count = 0

    for user in users:
        user_embeddings = []
        
        # Pull all images for this user
        images = db.query(UserImage).filter(UserImage.user_id == user.id).all()
        
        for img_record in images:
            cv_img = None
            
            # 1. Try decoding from Base64
            if img_record.image_base64:
                try:
                    cv_img = decode_base64_image(img_record.image_base64)
                except Exception as e:
                    print(f"Error decoding base64 image ID {img_record.id} for user {user.student_id}: {e}")
            
            # 2. Try loading from Path if Base64 wasn't available or failed
            if cv_img is None and img_record.image_path:
                try:
                    cv_img = cv2.imread(img_record.image_path)
                except Exception as e:
                    print(f"Error reading image path {img_record.image_path} for user {user.student_id}: {e}")

            if cv_img is None:
                continue

            # Process and extract embedding
            try:
                result = processor.extract_face_embedding(cv_img)
                if result and "embedding" in result:
                    user_embeddings.append(result["embedding"])
                    total_embeddings_count += 1
            except Exception as e:
                print(f"Error processing face for user {user.student_id}, image ID {img_record.id}: {e}")

        # Only register user if we have at least one valid face embedding
        if user_embeddings:
            embeddings_data.append({
                "user_id": user.id,
                "name": user.student_id,
                "student_id": user.student_id,
                "embeddings": user_embeddings
            })
            users_trained_count += 1

    # Save to .pkl file
    save_embeddings(embeddings_data)

    return {
        "status": "success",
        "users_trained": users_trained_count,
        "total_embeddings": total_embeddings_count
    }
