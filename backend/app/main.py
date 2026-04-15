# backend/app/main.py
"""
FastAPI application entry point for DS-Copilot.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import os

from app.config import settings
from app.api.routes import router as api_router
from app.api.websocket import websocket_endpoint
from app.core.startup import run_startup_checks
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.rate_limiter import RateLimitMiddleware

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# Lifespan
# ══════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown hooks."""
    # Startup
    startup_results = await run_startup_checks()
    logger.info(f"Startup results: {startup_results}")
    yield
    # Shutdown
    logger.info("🛑 DS-Copilot shutting down...")


# ══════════════════════════════════════════════════════════════
# App
# ══════════════════════════════════════════════════════════════

app = FastAPI(
    title=settings.APP_NAME,
    description="🤖 AI-Powered Data Science Pipeline Assistant",
    version="1.0.0",
    lifespan=lifespan,
)


# ══════════════════════════════════════════════════════════════
# CORS
# ══════════════════════════════════════════════════════════════

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handler
app.add_middleware(ErrorHandlerMiddleware)

# Rate limiter
app.add_middleware(RateLimitMiddleware)


# ══════════════════════════════════════════════════════════════
# Routes
# ══════════════════════════════════════════════════════════════

app.include_router(api_router)


# WebSocket route
@app.websocket("/ws/{session_id}")
async def ws_route(websocket, session_id: str):
    await websocket_endpoint(websocket, session_id)


# ══════════════════════════════════════════════════════════════
# Static Files (for output/figures)
# ══════════════════════════════════════════════════════════════

output_dir = os.path.abspath(settings.OUTPUT_DIR)
os.makedirs(output_dir, exist_ok=True)
app.mount("/output", StaticFiles(directory=output_dir), name="output")


# ══════════════════════════════════════════════════════════════
# Root
# ══════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }
