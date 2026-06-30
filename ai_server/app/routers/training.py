from fastapi import APIRouter, Depends

from app.schemas import TrainResponse
from app.dependencies import require_admin
from app.services import training_service

router = APIRouter(tags=["training"])

@router.post("/train-now", response_model=TrainResponse)
def train(admin=Depends(require_admin)):
    """Process pending queue items immediately."""
    return training_service.process_pending_queue()
