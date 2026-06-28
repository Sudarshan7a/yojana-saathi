from fastapi import APIRouter, Depends, Header, HTTPException, status

from config import settings

router = APIRouter()


def verify_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    if x_admin_token != settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token",
        )


@router.post("/admin/sync")
def trigger_scheme_sync(_: None = Depends(verify_admin_token)) -> dict:
    return {
        "triggered": True,
        "message": "Sync started",
    }
