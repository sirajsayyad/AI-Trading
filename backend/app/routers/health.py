"""
Health check router.
"""

from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "ai-trading-backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
