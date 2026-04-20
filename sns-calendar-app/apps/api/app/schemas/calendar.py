"""Pydantic schemas for WEB-013 calendar API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.post import Platform, PostStatus


class CalendarEvent(BaseModel):
    id: str
    title: str
    start: datetime
    status: PostStatus
    platforms: list[Platform] = Field(default_factory=list)
    has_media: bool = False


class CalendarRange(BaseModel):
    from_: datetime = Field(alias="from")
    to: datetime


class CalendarResponse(BaseModel):
    events: list[CalendarEvent]
    range: CalendarRange
