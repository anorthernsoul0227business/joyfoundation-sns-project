"""Post CRUD API (WEB-011).

Authenticated endpoints for creating, listing, retrieving, updating, and deleting
posts. All database operations go through a user-scoped Supabase client so that
RLS policies (WEB-010) are enforced consistently.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from postgrest.exceptions import APIError
from supabase import Client, create_client

from app.config import get_settings
from app.core.security import CurrentUser, get_current_user
from app.core.supabase import get_supabase_client
from app.schemas.post import (
    Platform,
    PostCreate,
    PostListResponse,
    PostResponse,
    PostStatus,
    PostUpdate,
    ScheduleRequest,
)

router = APIRouter()


def _get_user_client(user: CurrentUser) -> Client:
    """Return a Supabase client that carries the caller's JWT.

    RLS policies are evaluated against this token, so the client cannot see or
    modify rows outside the user's organizations.
    """
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase is not configured",
        )

    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(user.access_token)
    return client


def _resolve_default_org_id(user: CurrentUser) -> str:
    """Look up the user's profile (service_role) to obtain default_org_id."""
    service = get_supabase_client()
    rows = (
        service.table("users")
        .select("default_org_id")
        .eq("id", user.id)
        .limit(1)
        .execute()
        .data
    )
    if not rows or not rows[0].get("default_org_id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile does not have a default organization",
        )
    return rows[0]["default_org_id"]


def _map_api_error(error: APIError) -> HTTPException:
    message = getattr(error, "message", None) or str(error)
    code = getattr(error, "code", "") or ""
    if code == "23514" or "check constraint" in message.lower():
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)
    if code == "42501" or "permission denied" in message.lower():
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)
    if code == "PGRST116":
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


def _serialize_post(row: dict[str, Any]) -> PostResponse:
    targets = row.get("post_targets") or []
    media = row.get("post_media") or []
    return PostResponse(
        id=row["id"],
        org_id=row["org_id"],
        user_id=row["user_id"],
        status=row["status"],
        scheduled_at=row.get("scheduled_at"),
        published_at=row.get("published_at"),
        content_text=row["content_text"],
        ai_generated=row["ai_generated"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        targets=targets,
        media=media,
    )


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_post(
    payload: PostCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> PostResponse:
    if payload.status == "scheduled" and payload.scheduled_at is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="scheduled_at is required when status is 'scheduled'",
        )

    org_id = _resolve_default_org_id(current_user)
    client = _get_user_client(current_user)

    insert_body = {
        "org_id": org_id,
        "user_id": current_user.id,
        "status": payload.status,
        "content_text": payload.content_text,
        "ai_generated": payload.ai_generated,
    }
    if payload.scheduled_at is not None:
        insert_body["scheduled_at"] = payload.scheduled_at.isoformat()

    try:
        created = client.table("posts").insert(insert_body).execute().data[0]
        post_id = created["id"]

        if payload.platforms:
            client.table("post_targets").insert(
                [{"post_id": post_id, "platform": p} for p in payload.platforms]
            ).execute()

        if payload.media:
            client.table("post_media").insert(
                [
                    {
                        "post_id": post_id,
                        "storage_path": m.storage_path,
                        "mime_type": m.mime_type,
                        "width": m.width,
                        "height": m.height,
                        "sort_order": m.sort_order,
                    }
                    for m in payload.media
                ]
            ).execute()

        row = (
            client.table("posts")
            .select("*,post_targets(*),post_media(*)")
            .eq("id", post_id)
            .single()
            .execute()
            .data
        )
    except APIError as exc:
        raise _map_api_error(exc) from exc

    return _serialize_post(row)


@router.get(
    "",
    response_model=PostListResponse,
)
def list_posts(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    status_filter: Annotated[PostStatus | None, Query(alias="status")] = None,
    platform: Annotated[Platform | None, Query()] = None,
    from_date: Annotated[datetime | None, Query(alias="from")] = None,
    to_date: Annotated[datetime | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PostListResponse:
    client = _get_user_client(current_user)
    query = client.table("posts").select(
        "*,post_targets(*),post_media(*)",
        count="exact",
    )
    if status_filter:
        query = query.eq("status", status_filter)
    if from_date:
        query = query.gte("scheduled_at", from_date.isoformat())
    if to_date:
        query = query.lte("scheduled_at", to_date.isoformat())

    try:
        result = (
            query.order("scheduled_at", desc=False)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
    except APIError as exc:
        raise _map_api_error(exc) from exc

    rows = result.data or []
    if platform:
        rows = [
            row
            for row in rows
            if any(t.get("platform") == platform for t in (row.get("post_targets") or []))
        ]

    return PostListResponse(
        items=[_serialize_post(r) for r in rows],
        total=result.count or len(rows),
    )


@router.get(
    "/{post_id}",
    response_model=PostResponse,
)
def get_post(
    post_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> PostResponse:
    client = _get_user_client(current_user)
    try:
        row = (
            client.table("posts")
            .select("*,post_targets(*),post_media(*)")
            .eq("id", post_id)
            .single()
            .execute()
            .data
        )
    except APIError as exc:
        raise _map_api_error(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return _serialize_post(row)


@router.patch(
    "/{post_id}",
    response_model=PostResponse,
)
def update_post(
    post_id: str,
    payload: PostUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> PostResponse:
    updates = payload.model_dump(exclude_unset=True, exclude_none=False)
    if "scheduled_at" in updates and updates["scheduled_at"] is not None:
        updates["scheduled_at"] = updates["scheduled_at"].isoformat()
    if updates.get("status") == "scheduled" and updates.get("scheduled_at") is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="scheduled_at is required when status is 'scheduled'",
        )
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields to update",
        )

    client = _get_user_client(current_user)
    try:
        updated = (
            client.table("posts")
            .update(updates)
            .eq("id", post_id)
            .execute()
            .data
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found or not editable",
            )

        row = (
            client.table("posts")
            .select("*,post_targets(*),post_media(*)")
            .eq("id", post_id)
            .single()
            .execute()
            .data
        )
    except APIError as exc:
        raise _map_api_error(exc) from exc

    return _serialize_post(row)


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_post(
    post_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> Response:
    client = _get_user_client(current_user)
    try:
        deleted = client.table("posts").delete().eq("id", post_id).execute().data
    except APIError as exc:
        raise _map_api_error(exc) from exc
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found or not deletable (published posts cannot be deleted)",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =============================================================================
# WEB-012: schedule / reschedule / unschedule / publish-now
# =============================================================================

def _apply_status_update(
    client: Client, post_id: str, updates: dict[str, Any]
) -> dict[str, Any]:
    try:
        updated = (
            client.table("posts")
            .update(updates)
            .eq("id", post_id)
            .execute()
            .data
        )
    except APIError as exc:
        raise _map_api_error(exc) from exc

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found or not editable in current state",
        )

    try:
        row = (
            client.table("posts")
            .select("*,post_targets(*),post_media(*)")
            .eq("id", post_id)
            .single()
            .execute()
            .data
        )
    except APIError as exc:
        raise _map_api_error(exc) from exc
    return row


@router.post(
    "/{post_id}/schedule",
    response_model=PostResponse,
)
def schedule_post(
    post_id: str,
    payload: ScheduleRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> PostResponse:
    client = _get_user_client(current_user)
    existing = (
        client.table("posts").select("status").eq("id", post_id).limit(1).execute().data
    )
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if existing[0]["status"] not in ("draft", "scheduled"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot schedule a post in status '{existing[0]['status']}'",
        )

    row = _apply_status_update(
        client,
        post_id,
        {
            "status": "scheduled",
            "scheduled_at": payload.scheduled_at.isoformat(),
        },
    )
    return _serialize_post(row)


@router.post(
    "/{post_id}/reschedule",
    response_model=PostResponse,
)
def reschedule_post(
    post_id: str,
    payload: ScheduleRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> PostResponse:
    client = _get_user_client(current_user)
    existing = (
        client.table("posts").select("status").eq("id", post_id).limit(1).execute().data
    )
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if existing[0]["status"] != "scheduled":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only scheduled posts can be rescheduled",
        )

    row = _apply_status_update(
        client,
        post_id,
        {"scheduled_at": payload.scheduled_at.isoformat()},
    )
    return _serialize_post(row)


@router.post(
    "/{post_id}/unschedule",
    response_model=PostResponse,
)
def unschedule_post(
    post_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> PostResponse:
    client = _get_user_client(current_user)
    existing = (
        client.table("posts").select("status").eq("id", post_id).limit(1).execute().data
    )
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if existing[0]["status"] != "scheduled":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only scheduled posts can be unscheduled",
        )

    row = _apply_status_update(
        client,
        post_id,
        {"status": "draft", "scheduled_at": None},
    )
    return _serialize_post(row)


@router.post(
    "/{post_id}/publish-now",
    response_model=PostResponse,
)
def publish_now(
    post_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> PostResponse:
    client = _get_user_client(current_user)
    existing = (
        client.table("posts").select("status").eq("id", post_id).limit(1).execute().data
    )
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if existing[0]["status"] not in ("draft", "scheduled", "failed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot publish a post in status '{existing[0]['status']}'",
        )

    # Celery scheduler picks up status='scheduled' with scheduled_at <= now().
    # Setting scheduled_at to the current time triggers immediate publication.
    now = datetime.now(UTC)
    row = _apply_status_update(
        client,
        post_id,
        {
            "status": "scheduled",
            "scheduled_at": now.isoformat(),
        },
    )
    return _serialize_post(row)
