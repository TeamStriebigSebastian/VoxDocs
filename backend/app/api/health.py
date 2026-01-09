"""
Health check endpoints.
"""

from fastapi import APIRouter
from datetime import datetime
from typing import Dict, Any

from app.services.queue_service import queue_service

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "VoxDocs API"
    }


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check with queue status."""
    queue_stats = queue_service.get_queue_stats()

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "VoxDocs API",
        "components": {
            "api": "healthy",
            "queue": {
                "status": "healthy",
                "stats": queue_stats
            }
        }
    }
