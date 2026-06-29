from fastapi import APIRouter
from typing import List

from app.database import get_logs

router = APIRouter(tags=["logs"])

@router.get("/logs")
def get_check_in_logs(limit: int = 50):
    """Retrieve the recent check-in logs."""
    return get_logs(limit)
