"""
Health check endpoints.
"""

from fastapi import APIRouter
from datetime import datetime
from typing import Dict, Any

# from app.services.queue_service import queue_service # Removed for Platform MVP Pivot

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Platform API"
    }

# Detailed health check removed for now
