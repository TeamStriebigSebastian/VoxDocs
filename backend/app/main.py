"""
Platform - Generic Documentation Engine
Main FastAPI Application
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys

from app.core.config import settings, ensure_directories

# Ensure directories exist
ensure_directories()

# Import all models for SQLAlchemy
from app.models import *
# Explicitly import appointments api if we wanted to keep the demo alive, 
# but per User Request we focusing on 'Cases' and 'Entries'.
# However, we must ensure all models are imported in app/models/__init__.py

from app.api import cases, entries, tasks, categories, health, users, groups, webhooks, auth, settings as settings_router, translation
from app.core.database import init_db, get_db_session
from app.utils.seeding import seed_default_platform_data

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

from app.workers.audio_worker import start_worker

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting Platform Documentation Engine...")
    
    # Initialize Database (Create tables)
    await init_db()
    
    # Seed Default Data
    async with get_db_session() as db:
        await seed_default_platform_data(db)
        
    # Start Background Workers
    await start_worker()
    
    logger.info("Platform started successfully")
    yield
    logger.info("Shutting down Platform...")


app = FastAPI(
    title="Platform Documentation Engine",
    description="Generic, self-hosted documentation platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS, # Use settings!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(cases.router, prefix="/api") # tags are in router
app.include_router(entries.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(groups.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api") # Added Webhooks
app.include_router(auth.router, prefix="/api") # Authentication
app.include_router(settings_router.router, prefix="/api")
app.include_router(translation.router, prefix="/api")

# Keeping appointments router for reference but we are shifting to generic platform
# app.include_router(appointments.router) 

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Platform",
        "version": "0.1.0",
        "description": "Generic Documentation Engine"
    }
