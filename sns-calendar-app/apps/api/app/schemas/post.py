"""Pydantic schemas for WEB-011 post CRUD API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

PostStatus = Literal[
    "draft", "scheduled", "publishing", "published", "failed", "archived"
]
Platform = Literal["x", "ig", "note", "youtube", "line"]


class PostMediaInput(BaseModel):
    storage_path: str
    mime_type: str
    width: int | None = None
    height: int | None = None
    sort_order: int = 0


class PostMediaOut(BaseModel):
    id: str
    storage_path: str
    mime_type: str
    width: int | None = None
    height: int | None = None
    sort_order: int = 0


class PostTargetOut(BaseModel):
    id: str
    platform: Platform
    status: str
    published_at: datetime | None = None
    platform_post_id: str | None = None
    error_message: str | None = None


class PostCreate(BaseModel):
    content_text: str = Field(min_length=1, max_length=10000)
    status: Literal["draft", "scheduled"] = "draft"
    scheduled_at: datetime | None = None
    ai_generated: bool = False
    platforms: list[Platform] = Field(default_factory=list)
    media: list[PostMediaInput] = Field(default_factory=list)

    @field_validator("scheduled_at")
    @classmethod
    def _require_scheduled_at_when_scheduled(
        cls, value: datetime | None, info: object
    ) -> datetime | None:
        return value


class PostUpdate(BaseModel):
    content_text: str | None = Field(default=None, min_length=1, max_length=10000)
    status: Literal["draft", "scheduled", "archived"] | None = None
    scheduled_at: datetime | None = None
    ai_generated: bool | None = None


class PostResponse(BaseModel):
    id: str
    org_id: str
    user_id: str
    status: PostStatus
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    content_text: str
    ai_generated: bool
    created_at: datetime
    updated_at: datetime
    targets: list[PostTargetOut] = Field(default_factory=list)
    media: list[PostMediaOut] = Field(default_factory=list)


class PostListResponse(BaseModel):
    items: list[PostResponse]
    total: int


class ScheduleRequest(BaseModel):
    scheduled_at: datetime
