"""
Modular API routing entry point for DS-Copilot.
"""
from fastapi import APIRouter
from app.config import settings
from app.models.schemas import HealthResponse
from app.api.routers import pipeline, files, settings as settings_router, chat, notebook, sessions

router = APIRouter(prefix="/api")

# Include sub-routers
router.include_router(pipeline.router)
router.include_router(files.router)
router.include_router(settings_router.router)
router.include_router(chat.router)
router.include_router(notebook.router)
router.include_router(sessions.router)

@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        debug=settings.DEBUG,
    )
