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

    def extract_face_embedding(self, cv_img: np.ndarray):
        """
        Detects faces in an image, aligns them, and extracts the 512-dimension embedding.
        Returns the embedding of the primary face detected, or None if no face is found.
        """
        if cv_img is None:
            return None
            
        # Get face predictions
        faces = self.app.get(cv_img)
        
        if not faces:
            return None
            
        # If multiple faces are detected, we take the largest one (usually the main subject)
        # faces can be sorted by bounding box area: (x2-x1) * (y2-y1)
        faces = sorted(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]), reverse=True)
        
        # InsightFace's `faces[0].normed_embedding` is the L2-normalized 512-d ArcFace feature vector,
        # which is perfect for direct Cosine Similarity calculation.
        primary_face = faces[0]
        
        # Return both the embedding and some metadata (like bbox and kps)
        return {
            "embedding": primary_face.normed_embedding.tolist() if hasattr(primary_face, "normed_embedding") else primary_face.embedding.tolist(),
            "bbox": primary_face.bbox.tolist(),
            "kps": primary_face.kps.tolist() if hasattr(primary_face, "kps") else None
        }

    def validate_image_quality(self, cv_img: np.ndarray) -> dict:
        results = {
            "face_detected": False,
            "single_face": False,
            "blur_passed": False,
            "distance_passed": False,
            "orientation_passed": False,
            "obstruction_passed": False
        }
        
        if cv_img is None or cv_img.size == 0:
            return {"passed": False, "failed_step": 1, "error_message": "Invalid image data", "results": results}
            
        faces = self.app.get(cv_img)
        if not faces:
            return {"passed": False, "failed_step": 1, "error_message": "No face detected in the image", "results": results}
        results["face_detected"] = True

        if len(faces) > 1:
            return {"passed": False, "failed_step": 2, "error_message": "Multiple faces detected in the frame", "results": results}
        results["single_face"] = True

        # 3. Blur Check
        variance = calculate_blur_variance(cv_img)
        if variance < 100:
            return {"passed": False, "failed_step": 3, "error_message": f"Image is blurry / motion detected (variance: {variance:.1f} < 100)", "results": results}
        results["blur_passed"] = True

        primary = faces[0]
        bbox = primary.bbox # [x1, y1, x2, y2]
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

        # 4. Distance (Size) Check
        if w < 120 or h < 120:
            return {"passed": False, "failed_step": 4, "error_message": f"Face is too far or too small (size: {int(w)}x{int(h)} px < 120x120 px)", "results": results}
        results["distance_passed"] = True

        # 5. Orientation (Pose) Check using 5 keypoints
        if hasattr(primary, "kps") and primary.kps is not None and len(primary.kps) >= 5:
            kps = primary.kps
            left_eye, right_eye, nose, left_mouth, right_mouth = kps[0], kps[1], kps[2], kps[3], kps[4]
            
            # Roll (tilt) calculation
            dy = right_eye[1] - left_eye[1]
            dx = right_eye[0] - left_eye[0]
            roll_angle = abs(math.atan2(dy, dx)) * 180 / math.pi
            if roll_angle > 20:
                return {"passed": False, "failed_step": 5, "error_message": f"Face is not straight (tilted: {roll_angle:.1f}° > 20°)", "results": results}
                
            # Yaw (turn left/right) calculation in degrees
            left_dist = abs(nose[0] - left_eye[0])
            right_dist = abs(right_eye[0] - nose[0])
            total_width = left_dist + right_dist
            if total_width == 0:
                return {"passed": False, "failed_step": 5, "error_message": "Face is not straight (profile view detected)", "results": results}
            yaw_offset = abs(left_dist - right_dist) / total_width
            yaw_angle = yaw_offset * 90.0
            if yaw_angle > 20:
                return {"passed": False, "failed_step": 5, "error_message": f"Face is not straight (turned sideways: yaw {yaw_angle:.1f}° > 20°)", "results": results}
                
            # Pitch (tilt up/down) calculation in degrees
            eye_y = (left_eye[1] + right_eye[1]) / 2.0
            mouth_y = (left_mouth[1] + right_mouth[1]) / 2.0
            eye_to_mouth_y = mouth_y - eye_y
            if eye_to_mouth_y <= 0:
                return {"passed": False, "failed_step": 5, "error_message": "Face is not straight (invalid vertical features)", "results": results}
            eye_to_nose_y = nose[1] - eye_y
            pitch_ratio = eye_to_nose_y / eye_to_mouth_y
            # For a normal straight face, pitch_ratio is around 0.42. 
            pitch_offset = pitch_ratio - 0.42
            pitch_angle = abs(pitch_offset) * 150.0
            if pitch_angle > 20:
                return {"passed": False, "failed_step": 5, "error_message": f"Face is not straight (tilted up/down: pitch {pitch_angle:.1f}° > 20°)", "results": results}
        results["orientation_passed"] = True

        # 6. Obstruction Check (Det score)
        if hasattr(primary, "det_score") and primary.det_score < 0.6:
            return {"passed": False, "failed_step": 6, "error_message": f"Obstructions detected (confidence: {primary.det_score:.2f} < 0.6)", "results": results}
        results["obstruction_passed"] = True

        return {"passed": True, "failed_step": None, "error_message": None, "results": results}


# Singleton instance
_processor_instance = None

def get_face_processor() -> FaceProcessor:
    global _processor_instance
    if _processor_instance is None:
        # Default to CPU (-1). If CUDA is available, you can change to 0
        _processor_instance = FaceProcessor(ctx_id=-1)
    return _processor_instance
