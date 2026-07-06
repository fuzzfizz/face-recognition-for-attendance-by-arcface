import cv2
import math
import numpy as np
from insightface.app import FaceAnalysis
from app.config import MODEL_NAME
from app.utils.image_utils import decode_image_from_source, decode_image_bytes, calculate_blur_variance

class FaceProcessor:
    def __init__(self, ctx_id: int = -1):
        """
        Initialize InsightFace FaceAnalysis.
        ctx_id: -1 for CPU, >=0 for GPU (e.g. 0)
        """
        self.app = FaceAnalysis(name=MODEL_NAME)
        # Use CPU by default for portability, but can be configured for CUDA
        self.app.prepare(ctx_id=ctx_id, det_size=(640, 640))

    def decode_image(self, img_bytes: bytes) -> np.ndarray:
        """
        Decode raw image bytes (e.g., from network request) into OpenCV BGR image.
        """
        return decode_image_bytes(img_bytes)

    def decode_image_path(self, image_path: str) -> np.ndarray:
        """
        Read and decode an image from a file path on disk.
        Returns OpenCV BGR image or None if the file cannot be read.
        """
        return decode_image_from_source(image_path)

    def extract_face_embedding(self, cv_img: np.ndarray, face=None):
        """
        Detects faces in an image, aligns them, and extracts the 512-dimension embedding.
        If `face` is provided, skips calling `self.app.get(cv_img)` and extracts directly from it.
        Returns the embedding of the primary face detected, or None if no face is found.
        """
        if face is not None:
            primary_face = face
        else:
            if cv_img is None:
                return None
                
            # Get face predictions
            faces = self.app.get(cv_img)
            
            if not faces:
                return None
                
            # If multiple faces are detected, we take the largest one (usually the main subject)
            # faces can be sorted by bounding box area: (x2-x1) * (y2-y1)
            faces = sorted(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]), reverse=True)
            primary_face = faces[0]
        
        # InsightFace's `faces[0].normed_embedding` is the L2-normalized 512-d ArcFace feature vector,
        # which is perfect for direct Cosine Similarity calculation.
        
        # Return both the embedding and some metadata (like bbox and kps)
        return {
            "embedding": primary_face.normed_embedding.tolist() if hasattr(primary_face, "normed_embedding") else primary_face.embedding.tolist(),
            "bbox": primary_face.bbox.tolist(),
            "kps": primary_face.kps.tolist() if hasattr(primary_face, "kps") else None
        }

    def validate_image_quality(self, cv_img: np.ndarray) -> dict:
        results = {
            "face_detected": False,
            "single_face": False
        }
        
        if cv_img is None or cv_img.size == 0:
            return {"passed": False, "failed_step": 1, "error_message": "Please look at the camera", "results": results}
            
        faces = self.app.get(cv_img)
        if not faces:
            return {"passed": False, "failed_step": 1, "error_message": "Please look at the camera", "results": results}
        results["face_detected"] = True

        if len(faces) > 1:
            return {"passed": False, "failed_step": 2, "error_message": "One person at a time", "results": results}
        results["single_face"] = True

        return {"passed": True, "failed_step": None, "error_message": None, "results": results, "face": faces[0]}


# Singleton instance
_processor_instance = None

def get_face_processor() -> FaceProcessor:
    global _processor_instance
    if _processor_instance is None:
        # Default to CPU (-1). If CUDA is available, you can change to 0
        _processor_instance = FaceProcessor(ctx_id=-1)
    return _processor_instance
