from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from config import settings
from database import engine, get_db
import models
from routers import schemes, profile

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="AI assistant for finding Indian government schemes",
)

# Create database tables on startup
models.Base.metadata.create_all(bind=engine)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint for monitoring."""
    schemes_count = db.query(models.Scheme).count()
    return {
        "status": "healthy",
        "api_version": settings.api_version,
        "schemes_count": schemes_count,
    }

# Router registration (to be added as routers are created)
# from routers import chat, profile, schemes, notifications, admin
# app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(profile.router, prefix="/api", tags=["profile"])
app.include_router(schemes.router, prefix="/api", tags=["schemes"])
# app.include_router(notifications.router, prefix="/api", tags=["notifications"])
# app.include_router(admin.router, prefix="/api", tags=["admin"])
