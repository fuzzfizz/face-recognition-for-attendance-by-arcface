import os
from fastapi import Header, HTTPException

from typing import Optional

ADMIN_KEY = os.getenv("ADMIN_API_KEY", "")

def require_admin(x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")):
    if not ADMIN_KEY or not x_admin_key or x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
