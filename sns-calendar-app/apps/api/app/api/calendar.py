"""Calendar API (WEB-013).

Single GET endpoint that returns post events optimised for calendar rendering
(FullCalendar on the frontend). Uses the user-scoped Supabase client so RLS
policies gate access.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from postgrest.exceptions import APIError

from app.api.posts import _get_user_client, _map_api_error
from app.core.security import CurrentUser, get_current_user
from app.schemas.calendar import CalendarEvent, CalendarRange, CalendarResponse
from app.schemas.post import Platform

router = APIRouter()

# Any post with an actionable slot on the calendar: already scheduled /
# publishing in flight / published / failed so the user can retry.
CALENDAR_STATUSES = ("scheduled", "publishing", "published", "failed")


@router.get("", response_model=CalendarResponse)
def get_calendar(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    from_date: Annotated[datetime, Query(alias="from")],
    to_date: Annotated[datetime, Query(alias="to")],
    platforms: Annotated[list[Platform] | None, Query()] = None,
) -> CalendarResponse:
    if to_date <= from_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'to' must be greater than 'from'",
        )

    client = _get_user_client(current_user)
    try:
        query = (
            client.table("posts")
            .select("id,content_text,status,scheduled_at,published_at,post_targets(platform),post_media(id)")
            .in_("status", list(CALENDAR_STATUSES))
            .or_(
                f"and(scheduled_at.gte.{from_date.isoformat()},scheduled_at.lte.{to_date.isoformat()}),"
                f"and(published_at.gte.{from_date.isoformat()},published_at.lte.{to_date.isoformat()})"
            )
            .order("scheduled_at", desc=False)
        )
        rows = query.execute().data or []
    except APIError as exc:
        raise _map_api_error(exc) from exc

    events: list[CalendarEvent] = []
    platform_filter = set(platforms) if platforms else None
    for row in rows:
        row_platforms: list[Platform] = [
            t["platform"] for t in (row.get("post_targets") or [])
        ]
        if platform_filter and not platform_filter.intersection(row_platforms):
            continue

        slot = row.get("scheduled_at") or row.get("published_at")
        if slot is None:
            continue

        content = row.get("content_text") or ""
        title = content.strip().splitlines()[0] if content else ""
        if len(title) > 50:
            title = title[:47] + "..."

        events.append(
            CalendarEvent(
                id=row["id"],
                title=title or "(空の投稿)",
                start=slot,
                status=row["status"],
                platforms=sorted(set(row_platforms)),
                has_media=bool(row.get("post_media")),
            )
        )

    return CalendarResponse(
        events=events,
        range=CalendarRange.model_validate({"from": from_date, "to": to_date}),
    )
