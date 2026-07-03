from pydantic import BaseModel
from typing import List, Optional

class UserCreate(BaseModel):
    name: str

class ImageUploadBase64(BaseModel):
    image_base64: str

class ValidationChecklist(BaseModel):
    face_detected: bool
    single_face: bool
    blur_passed: bool
    distance_passed: bool
    orientation_passed: bool
    obstruction_passed: bool
    database_match: Optional[bool] = None

class RegisterResponse(BaseModel):
    message: str
    student_id: str
    status: str
    validation_checklist: Optional[ValidationChecklist] = None

class TrainResponse(BaseModel):
    message: str
    processed_students: List[str]
    total_pending: int

class VerifyResponse(BaseModel):
    match: bool
    student_id: Optional[str]
    similarity_score: float
    timestamp: str
    message: Optional[str] = None
    validation_checklist: Optional[ValidationChecklist] = None

class RegistrationStatusResponse(BaseModel):
    student_id: str
    status: str
    message: str

