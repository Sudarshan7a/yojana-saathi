from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from clerk_backend_api import Clerk

from config import settings

# Initialize Clerk client
clerk = Clerk(bearer_auth=settings.clerk_secret_key)

# HTTP Bearer scheme for extracting Authorization header
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Verify Clerk JWT token and return user_id.
    
    Usage in FastAPI routes:
        @app.get("/api/profile")
        def get_profile(user_id: str = Depends(get_current_user)):
            return {"user_id": user_id}
    
    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    try:
        # Extract JWT token from Authorization header
        token = credentials.credentials
        
        # Verify token with Clerk
        verified_token = clerk.verify_token(token)
        
        # Extract user_id from verified token
        user_id = verified_token.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id",
            )
        
        return user_id
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(optional_security),
) -> Optional[str]:
    """
    Optional version of get_current_user that returns None if no token provided.
    
    Usage in FastAPI routes where auth is optional:
        @app.get("/api/public-data")
        def get_public_data(user_id: str | None = Depends(get_current_user_optional)):
            if user_id:
                return {"user_id": user_id, "data": "personalized"}
            return {"data": "public"}
    """
    try:
        if not credentials:
            return None
            
        token = credentials.credentials
        verified_token = clerk.verify_token(token)
        user_id = verified_token.get("sub")
        
        return user_id if user_id else None
        
    except Exception:
        return None
