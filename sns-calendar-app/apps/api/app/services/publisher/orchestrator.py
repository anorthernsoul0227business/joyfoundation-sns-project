from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Protocol

from fastapi import HTTPException, status

from app.core.supabase import get_supabase_client

from . import get_publisher
from .base import PublishResult

logger = logging.getLogger(__name__)
MAX_ERROR_MESSAGE_LENGTH = 500


class PublishStore(Protocol):
    def get_target(self, target_id: str) -> dict[str, Any] | None: ...

    def get_post(self, post_id: str) -> dict[str, Any] | None: ...

    def list_media(self, post_id: str, limit: int = 4) -> list[dict[str, Any]]: ...

    def get_active_account(self, *, org_id: str, platform: str) -> dict[str, Any] | None: ...

    def update_target(self, target_id: str, updates: dict[str, Any]) -> None: ...

    def list_targets(self, post_id: str) -> list[dict[str, Any]]: ...

    def update_post(self, post_id: str, updates: dict[str, Any]) -> None: ...


class SupabasePublishStore:
    def __init__(self) -> None:
        self._client = get_supabase_client()

    def get_target(self, target_id: str) -> dict[str, Any] | None:
        rows = (
            self._client.table("post_targets")
            .select("*")
            .eq("id", target_id)
            .limit(1)
            .execute()
            .data
        )
        return rows[0] if rows else None

    def get_post(self, post_id: str) -> dict[str, Any] | None:
        rows = (
            self._client.table("posts")
            .select("*")
            .eq("id", post_id)
            .limit(1)
            .execute()
            .data
        )
        return rows[0] if rows else None

    def list_media(self, post_id: str, limit: int = 4) -> list[dict[str, Any]]:
        return (
            self._client.table("post_media")
            .select("*")
            .eq("post_id", post_id)
            .order("sort_order", desc=False)
            .limit(limit)
            .execute()
            .data
            or []
        )

    def get_active_account(self, *, org_id: str, platform: str) -> dict[str, Any] | None:
        rows = (
            self._client.table("sns_accounts")
            .select("*")
            .eq("org_id", org_id)
            .eq("platform", platform)
            .eq("is_active", True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        return rows[0] if rows else None

    def update_target(self, target_id: str, updates: dict[str, Any]) -> None:
        self._client.table("post_targets").update(updates).eq("id", target_id).execute()

    def list_targets(self, post_id: str) -> list[dict[str, Any]]:
        return (
            self._client.table("post_targets")
            .select("*")
            .eq("post_id", post_id)
            .execute()
            .data
            or []
        )

    def update_post(self, post_id: str, updates: dict[str, Any]) -> None:
        self._client.table("posts").update(updates).eq("id", post_id).execute()


def _truncate_error_message(message: str | None) -> str | None:
    if message is None:
        return None
    return message[:MAX_ERROR_MESSAGE_LENGTH]


def _current_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def publish_target(target_id: str, store: PublishStore | None = None) -> PublishResult:
    active_store = store or SupabasePublishStore()

    target = active_store.get_target(target_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post target not found",
        )

    target_status = target.get("status")
    if target_status in {"published", "skipped", "publishing"}:
        return PublishResult(
            success=True,
            platform_post_id=target.get("platform_post_id"),
            error_message=None,
            extra={"status": target_status},
        )

    post = active_store.get_post(str(target["post_id"]))
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent post not found",
        )

    image_urls: list[str] = []
    for media in active_store.list_media(str(post["id"]), limit=4):
        storage_path = media.get("storage_path")
        if isinstance(storage_path, str) and storage_path.startswith("http"):
            image_urls.append(storage_path)
        elif storage_path:
            logger.warning(
                "Skipping non-http media for target_id=%s storage_path=%s",
                target_id,
                storage_path,
            )

    account = active_store.get_active_account(
        org_id=str(post["org_id"]),
        platform=str(target["platform"]),
    )
    if account is None:
        result = PublishResult(
            success=False,
            platform_post_id=None,
            error_message="No active X account connected",
        )
        active_store.update_target(
            target_id,
            {
                "status": "failed",
                "error_message": _truncate_error_message(result.error_message),
            },
        )
        return result

    active_store.update_target(
        target_id,
        {
            "status": "publishing",
            "error_message": None,
        },
    )

    try:
        publisher = get_publisher(str(target["platform"]))
        result = publisher.publish(
            text=str(post["content_text"]),
            image_urls=image_urls,
            account=account,
            options={},
        )
    except Exception as exc:  # pragma: no cover - defensive wrapper around unexpected faults
        logger.exception("Unexpected publish failure for target_id=%s", target_id)
        result = PublishResult(
            success=False,
            platform_post_id=None,
            error_message=f"Unexpected publish failure: {exc}",
        )

    if result.success:
        active_store.update_target(
            target_id,
            {
                "status": "published",
                "published_at": _current_timestamp(),
                "platform_post_id": result.platform_post_id,
                "error_message": None,
            },
        )
        sibling_targets = active_store.list_targets(str(post["id"]))
        if sibling_targets and all(t.get("status") == "published" for t in sibling_targets):
            active_store.update_post(
                str(post["id"]),
                {
                    "status": "published",
                    "published_at": _current_timestamp(),
                },
            )
    else:
        active_store.update_target(
            target_id,
            {
                "status": "failed",
                "error_message": _truncate_error_message(result.error_message),
            },
        )

    return result
