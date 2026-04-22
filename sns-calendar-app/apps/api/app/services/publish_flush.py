"""ARCH-002: publish_queue から pending を取り出し、同期的に投稿実行するサービス.

Celery Worker (既存 apps/api/app/tasks/scheduled_posts.py) を置換するもの。
- 入口: FastAPI /internal/publish/flush エンドポイント (apps/api/app/api/internal.py)
- 呼び出し元: GitHub Actions Cron (publish_flush.yml, 5分毎)
- 処理対象: ARCH-001 の publish_queue テーブル（pg_cron で enqueue 済み）

排他制御はアプリ層で実装する（Supabase の RPC を介した SELECT ... FOR UPDATE
SKIP LOCKED は現状取り回しが複雑なので、compare-and-swap 風に locked_at UPDATE で
排他する）。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Callable

from app.core.supabase import get_supabase_client
from app.services.notifier import notify_post_result
from app.services.publisher.base import PublishResult
from app.services.publisher.orchestrator import publish_target

logger = logging.getLogger(__name__)

MAX_ERROR_MESSAGE_LENGTH = 500
MAX_ATTEMPTS = 3


def _truncate_error(message: str | None) -> str | None:
    if message is None:
        return None
    return message[:MAX_ERROR_MESSAGE_LENGTH]


def _lock_pending_queue(client: Any, limit: int, locked_by: str) -> list[dict[str, Any]]:
    """publish_queue から locked_at IS NULL かつ completed_at IS NULL の行を
    lock して返す。compare-and-swap 風 UPDATE で他プロセスとの競合を防ぐ."""
    candidates = (
        client.table("publish_queue")
        .select("id,post_id,org_id,scheduled_at,attempts")
        .is_("locked_at", "null")
        .is_("completed_at", "null")
        .order("scheduled_at")
        .limit(limit)
        .execute()
        .data
        or []
    )

    locked: list[dict[str, Any]] = []
    now_iso = datetime.now(UTC).isoformat()
    for row in candidates:
        updated = (
            client.table("publish_queue")
            .update({"locked_at": now_iso, "locked_by": locked_by})
            .eq("id", row["id"])
            .is_("locked_at", "null")
            .execute()
            .data
            or []
        )
        if updated:
            locked.append({**row, "locked_at": now_iso, "locked_by": locked_by})
    return locked


def _mark_completed(client: Any, queue_id: str) -> None:
    now_iso = datetime.now(UTC).isoformat()
    client.table("publish_queue").update(
        {"completed_at": now_iso}
    ).eq("id", queue_id).execute()


def _mark_failed_retry(
    client: Any, queue_id: str, attempts: int, error: str | None
) -> bool:
    """失敗時に attempts をインクリメント。上限超過なら completed 扱いで諦める。

    Returns True if the row is terminal (should not retry)."""
    next_attempts = attempts + 1
    now_iso = datetime.now(UTC).isoformat()
    if next_attempts >= MAX_ATTEMPTS:
        client.table("publish_queue").update(
            {
                "attempts": next_attempts,
                "last_error": _truncate_error(error),
                "locked_at": None,
                "locked_by": None,
                "completed_at": now_iso,
            }
        ).eq("id", queue_id).execute()
        return True
    client.table("publish_queue").update(
        {
            "attempts": next_attempts,
            "last_error": _truncate_error(error),
            "locked_at": None,
            "locked_by": None,
        }
    ).eq("id", queue_id).execute()
    return False


def _update_post_parent_status(client: Any, post_id: str) -> str:
    final_targets = (
        client.table("post_targets")
        .select("status")
        .eq("post_id", post_id)
        .execute()
        .data
        or []
    )
    statuses = {
        str(t["status"])
        for t in final_targets
        if t.get("status") is not None
    }
    now_iso = datetime.now(UTC).isoformat()

    parent_status = "publishing"
    update: dict[str, Any] | None = None
    if statuses == {"published"}:
        parent_status = "published"
        update = {"status": "published", "published_at": now_iso}
    elif "failed" in statuses:
        parent_status = "failed"
        update = {"status": "failed"}

    if update is not None:
        client.table("posts").update(update).eq("id", post_id).execute()
    return parent_status


def _dispatch_notification(
    client: Any,
    *,
    post_id: str,
    results: list[dict[str, Any]],
    notifier: Callable[..., None],
) -> None:
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
        summary = {
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
        logger.warning("notification dispatch failed for post_id=%s", post_id)


def _publish_one(
    client: Any,
    *,
    post_id: str,
    notifier: Callable[..., None],
) -> tuple[bool, list[dict[str, Any]]]:
    """指定 post の全 post_target を順次投稿する。

    Returns (all_success, results)."""
    targets = (
        client.table("post_targets")
        .select("id,platform,status")
        .eq("post_id", post_id)
        .execute()
        .data
        or []
    )

    # 親 posts を publishing にマーク（既存ロジック踏襲）
    client.table("posts").update({"status": "publishing"}).eq(
        "id", post_id
    ).eq("status", "scheduled").execute()

    results: list[dict[str, Any]] = []
    all_success = True
    for target in targets:
        target_id = str(target["id"])
        if target.get("status") in {"published", "skipped"}:
            continue
        try:
            result = publish_target(target_id)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception(
                "publish_target raised for target_id=%s", target_id
            )
            result = PublishResult(
                success=False,
                platform_post_id=None,
                error_message=f"unhandled: {exc}",
            )
            client.table("post_targets").update(
                {
                    "status": "failed",
                    "error_message": _truncate_error(str(exc)),
                }
            ).eq("id", target_id).execute()
        if not result.success:
            all_success = False
        results.append(
            {
                "target_id": target_id,
                "platform": target.get("platform"),
                "success": result.success,
                "platform_post_id": result.platform_post_id,
                "error": result.error_message,
            }
        )

    _update_post_parent_status(client, post_id)
    _dispatch_notification(
        client, post_id=post_id, results=results, notifier=notifier
    )
    return all_success, results


def flush_publish_queue(
    *,
    limit: int = 20,
    locked_by: str = "gh-actions",
    notifier: Callable[..., None] | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    """ARCH-002 entry point. publish_queue を処理して FlushResult を返す."""
    supabase_client = client or get_supabase_client()
    active_notifier = notifier or notify_post_result

    locked_rows = _lock_pending_queue(
        supabase_client, limit=limit, locked_by=locked_by
    )

    items: list[dict[str, Any]] = []
    for row in locked_rows:
        queue_id = str(row["id"])
        post_id = str(row["post_id"])
        attempts = int(row.get("attempts") or 0)
        try:
            success, per_target = _publish_one(
                supabase_client,
                post_id=post_id,
                notifier=active_notifier,
            )
            if success and per_target:
                _mark_completed(supabase_client, queue_id)
                items.append(
                    {
                        "queue_id": queue_id,
                        "post_id": post_id,
                        "status": "success",
                    }
                )
            elif success and not per_target:
                # 全 target が published/skipped で処理対象なし
                _mark_completed(supabase_client, queue_id)
                items.append(
                    {
                        "queue_id": queue_id,
                        "post_id": post_id,
                        "status": "skipped",
                    }
                )
            else:
                error = next(
                    (r.get("error") for r in per_target if not r.get("success")),
                    "partial failure",
                )
                terminal = _mark_failed_retry(
                    supabase_client, queue_id, attempts, error
                )
                items.append(
                    {
                        "queue_id": queue_id,
                        "post_id": post_id,
                        "status": "failed",
                        "error": error,
                        "terminal": terminal,
                    }
                )
        except Exception as exc:
            logger.exception("flush_publish_queue failed for queue_id=%s", queue_id)
            terminal = _mark_failed_retry(
                supabase_client, queue_id, attempts, str(exc)
            )
            items.append(
                {
                    "queue_id": queue_id,
                    "post_id": post_id,
                    "status": "failed",
                    "error": str(exc),
                    "terminal": terminal,
                }
            )

    return {
        "processed": len(items),
        "items": items,
    }
