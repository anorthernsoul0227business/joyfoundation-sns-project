from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.core.supabase import get_supabase_client
from app.services.notifier import notify_post_result
from app.services.publisher.base import PublishResult
from app.services.publisher.orchestrator import publish_target
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)
MAX_POSTS_PER_CHECK = 50
MAX_ERROR_MESSAGE_LENGTH = 500


def _truncate_error_message(message: str | None) -> str | None:
    if message is None:
        return None
    return message[:MAX_ERROR_MESSAGE_LENGTH]


@celery_app.task(name="app.tasks.scheduled_posts.check_scheduled_posts")
def check_scheduled_posts() -> dict[str, Any]:
    client = get_supabase_client()
    now_iso = datetime.now(UTC).isoformat()
    due_posts = (
        client.table("posts")
        .select("id,org_id")
        .eq("status", "scheduled")
        .lte("scheduled_at", now_iso)
        .limit(MAX_POSTS_PER_CHECK)
        .execute()
        .data
        or []
    )

    enqueued: list[str] = []
    for row in due_posts:
        post_id = str(row["id"])
        updated = (
            client.table("posts")
            .update({"status": "publishing"})
            .eq("id", post_id)
            .eq("status", "scheduled")
            .execute()
            .data
            or []
        )
        if not updated:
            continue
        logger.info("Enqueuing publish_post for post_id=%s", post_id)
        publish_post.delay(post_id)
        enqueued.append(post_id)

    return {
        "checked_at": now_iso,
        "enqueued_count": len(enqueued),
    }


@celery_app.task(
    name="app.tasks.scheduled_posts.publish_post",
    bind=True,
    max_retries=0,
)
def publish_post(self: Any, post_id: str, *, notifier: Any = None) -> dict[str, Any]:
    del self
    notify = notifier or notify_post_result

    client = get_supabase_client()
    targets = (
        client.table("post_targets")
        .select("id,platform,status")
        .eq("post_id", post_id)
        .execute()
        .data
        or []
    )

    results: list[dict[str, Any]] = []
    for target in targets:
        target_id = str(target["id"])
        target_status = target.get("status")
        if target_status in {"published", "skipped"}:
            continue

        try:
            result = publish_target(target_id)
        except Exception as exc:  # pragma: no cover - defensive wrapper
            logger.exception("Unhandled publish_post failure for target_id=%s", target_id)
            result = PublishResult(
                success=False,
                platform_post_id=None,
                error_message=f"unhandled: {exc}",
            )
            client.table("post_targets").update(
                {
                    "status": "failed",
                    "error_message": _truncate_error_message(str(exc)),
                }
            ).eq("id", target_id).execute()

        results.append(
            {
                "target_id": target_id,
                "platform": target.get("platform"),
                "success": result.success,
                "platform_post_id": result.platform_post_id,
                "error": result.error_message,
            }
        )

    final_targets = (
        client.table("post_targets")
        .select("status")
        .eq("post_id", post_id)
        .execute()
        .data
        or []
    )
    statuses = {str(target["status"]) for target in final_targets if target.get("status") is not None}
    now_iso = datetime.now(UTC).isoformat()

    parent_status = "publishing"
    parent_update: dict[str, Any] | None = None
    if statuses == {"published"}:
        parent_status = "published"
        parent_update = {
            "status": "published",
            "published_at": now_iso,
        }
    elif "failed" in statuses:
        parent_status = "failed"
        parent_update = {
            "status": "failed",
        }

    if parent_update is not None:
        client.table("posts").update(parent_update).eq("id", post_id).execute()

    _dispatch_notification(client, post_id=post_id, results=results, notifier=notify)

    return {
        "post_id": post_id,
        "parent_status": parent_status,
        "results": results,
    }


def _dispatch_notification(
    client: Any,
    *,
    post_id: str,
    results: list[dict[str, Any]],
    notifier: Any,
) -> None:
    """publish_post 終了時に owner メールへ結果通知を送る。失敗は握り潰す."""
    if not results:
        return
    try:
        post_rows = (
            client.table("posts")
            .select("user_id")
            .eq("id", post_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        user_id = post_rows[0].get("user_id") if post_rows else None
        if not user_id:
            return

        user_rows = (
            client.table("users")
            .select("email")
            .eq("id", user_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        owner_email = user_rows[0].get("email") if user_rows else None
        if not owner_email:
            return

        summary: dict[str, list[dict[str, Any]]] = {
            "success": [r for r in results if r.get("success")],
            "failed": [r for r in results if not r.get("success")],
        }
        notifier(
            post_id=post_id,
            owner_email=owner_email,
            summary=summary,
            user_id=user_id,
        )
    except Exception:  # pragma: no cover - defensive
        logger.warning(
            "Failed to dispatch post result notification for post_id=%s",
            post_id,
            exc_info=True,
        )
