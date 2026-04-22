from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, HttpUrl

Platform = Literal["x", "ig"]


class ConnectResponse(BaseModel):
    authorization_url: HttpUrl
    state: str


class SnsAccountSafe(BaseModel):
    id: UUID
    org_id: UUID
    platform: Platform
    handle: str
    display_name: str | None = None
    expires_at: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SnsAccountListResponse(BaseModel):
    accounts: list[SnsAccountSafe]
