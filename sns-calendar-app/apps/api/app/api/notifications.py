"""通知 REST API (WEB-027).

`notifications` テーブルに対する一覧取得・既読マーク・全既読を提供する。
すべて user_id スコープで、service_role クライアント + 明示フィルタで保護する。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.security import CurrentUser, get_current_user
from app.core.supabase import get_supabase_client

router = APIRouter()

MAX_LIMIT = 100
DEFAULT_LIMIT = 30


class NotificationItem(BaseModel):
    id: str
    kind: str
    title: str
    body: str | None = None
    related_post_id: str | None = None
    read_at: str | None = None
    created_at: str


class NotificationListResponse(BaseModel):
    items: list[NotificationItem]
    unread_count: int
    total: int


class NotificationReadResponse(BaseModel):
    id: str
    read_at: str


class NotificationReadAllResponse(BaseModel):
    updated_count: int


def _row_to_item(row: dict[str, Any]) -> NotificationItem:
    return NotificationItem(
        id=str(row["id"]),
        kind=str(row["kind"]),
        title=str(row["title"]),
        body=row.get("body"),
        related_post_id=str(row["related_post_id"]) if row.get("related_post_id") else None,
        read_at=row.get("read_at"),
        created_at=row["created_at"],
    )


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
    unread_only: Annotated[bool, Query()] = False,
) -> NotificationListResponse:
    client = get_supabase_client()
    query = client.table("notifications").select("*").eq("user_id", current_user.id)
    if unread_only:
        query = query.is_("read_at", "null")
    rows = (
        query.order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
        .data
        or []
    )

    unread_rows = (
        client.table("notifications")
        .select("id")
        .eq("user_id", current_user.id)
        .is_("read_at", "null")
        .execute()
        .data
        or []
    )
    total_rows = (
        client.table("notifications")
        .select("id")
        .eq("user_id", current_user.id)
        .execute()
        .data
        or []
    )

    return NotificationListResponse(
        items=[_row_to_item(row) for row in rows],
        unread_count=len(unread_rows),
        total=len(total_rows),
    )


@router.post(
    "/{notification_id}/read",
    response_model=NotificationReadResponse,
)
def mark_notification_read(
    notification_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> NotificationReadResponse:
    client = get_supabase_client()
    now_iso = datetime.now(UTC).isoformat()
    updated = (
        client.table("notifications")
        .update({"read_at": now_iso})
        .eq("id", notification_id)
        .eq("user_id", current_user.id)
        .is_("read_at", "null")
        .execute()
        .data
        or []
    )
    if not updated:
        existing = (
            client.table("notifications")
            .select("id,read_at")
            .eq("id", notification_id)
            .eq("user_id", current_user.id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )
        row = existing[0]
        return NotificationReadResponse(
            id=str(row["id"]),
            read_at=row.get("read_at") or now_iso,
        )
    row = updated[0]
    return NotificationReadResponse(
        id=str(row["id"]),
        read_at=str(row["read_at"]),
    )


@router.post("/read-all", response_model=NotificationReadAllResponse)
def mark_all_notifications_read(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> NotificationReadAllResponse:
    client = get_supabase_client()
    now_iso = datetime.now(UTC).isoformat()
    updated = (
        client.table("notifications")
        .update({"read_at": now_iso})
        .eq("user_id", current_user.id)
        .is_("read_at", "null")
        .execute()
        .data
        or []
    )
    return NotificationReadAllResponse(updated_count=len(updated))
