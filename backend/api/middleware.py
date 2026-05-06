import os
from fastapi import Header, HTTPException, status


def require_admin(admin_token: str = Header(None, alias="admin-token")) -> None:
    expected = os.getenv("ADMIN_TOKEN", "")
    if not expected or admin_token != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
