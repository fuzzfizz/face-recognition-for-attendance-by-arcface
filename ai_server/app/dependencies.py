import os
from fastapi import Header, HTTPException

ADMIN_KEY = os.getenv("ADMIN_API_KEY", "")

def require_admin(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    if not ADMIN_KEY or x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
