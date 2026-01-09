"""
VoxDocs - Dental Speech-to-Text Documentation System
Main FastAPI Application
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys

from app.api import audio, transcription, classification, health, onboarding, export
from app.core.config import settings
from app.core.database import init_db
from app.services.queue_service import queue_service


# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/voxdocs.log",
    rotation="10 MB",
    retention="90 days",
    compression="gz",
    level="DEBUG"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting VoxDocs Dental Speech-to-Text System...")
    await init_db()
    await queue_service.start()
    logger.info("VoxDocs started successfully")

    yield

    # Shutdown
    logger.info("Shutting down VoxDocs...")
    await queue_service.stop()
    logger.info("VoxDocs shut down complete")


app = FastAPI(
    title="VoxDocs - Dental Speech-to-Text",
    description="GDPR-compliant speech recognition system for German dental practices",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration for PWA
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(audio.router, prefix="/api/audio", tags=["Audio"])
app.include_router(transcription.router, prefix="/api/transcription", tags=["Transcription"])
app.include_router(classification.router, prefix="/api/classification", tags=["Classification"])
app.include_router(onboarding.router, prefix="/api/onboarding", tags=["Onboarding"])
app.include_router(export.router, prefix="/api/export", tags=["Export"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "VoxDocs",
        "version": "1.0.0",
        "description": "Dental Speech-to-Text Documentation System"
    }
