from pydantic import BaseModel
from typing import List, Optional

class UserCreate(BaseModel):
    name: str

class ImageUploadBase64(BaseModel):
    image_base64: str

class RegisterResponse(BaseModel):
    message: str
    student_id: str
    status: str

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

class RegistrationStatusResponse(BaseModel):
    student_id: str
    status: str
    message: str
