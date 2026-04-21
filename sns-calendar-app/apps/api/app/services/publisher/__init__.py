from __future__ import annotations

from fastapi import HTTPException, status

from app.config import get_settings

from .base import Publisher, PublishResult
from .x_publisher import XPublisher


def get_publisher(platform: str) -> Publisher:
    normalized = platform.lower()
    if normalized == "x":
        settings = get_settings()
        if not settings.x_consumer_key or not settings.x_consumer_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="X consumer credentials not configured",
            )
        return XPublisher(
            consumer_key=settings.x_consumer_key,
            consumer_secret=settings.x_consumer_secret,
        )
    raise NotImplementedError(f"Publisher for platform '{platform}' is not implemented")


__all__ = ["PublishResult", "Publisher", "XPublisher", "get_publisher"]
