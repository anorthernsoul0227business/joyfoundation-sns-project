"""ARCH-001 / ARCH-002: 内部エンドポイント（GitHub Actions Cron 用）.

/internal/publish/flush は publish_queue から pending を取り出し、
FastAPI プロセス内で投稿を実行する。ARCH-001 では雛形のみ、
実際の投稿ロジックは ARCH-002 の Publisher service で接続する。

認証は X-Internal-Token ヘッダーで行う（GH Secrets `INTERNAL_API_TOKEN`）。
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.config import get_settings
from app.services.publish_flush import flush_publish_queue as run_flush

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])


class FlushItem(BaseModel):
    queue_id: str
    post_id: str
    status: str  # "success" | "failed" | "skipped"
    error: str | None = None
    terminal: bool | None = None


class FlushResult(BaseModel):
    processed: int
    items: list[FlushItem]


async def verify_internal_token(
    x_internal_token: Annotated[str | None, Header()] = None,
) -> None:
    settings = get_settings()
    if settings.internal_api_token is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="INTERNAL_API_TOKEN is not configured on server.",
        )
    expected = settings.internal_api_token.get_secret_value()
    if not x_internal_token or x_internal_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal token",
        )


@router.post(
    "/publish/flush",
    response_model=FlushResult,
    dependencies=[Depends(verify_internal_token)],
)
async def flush_publish_queue(limit: int = 20) -> FlushResult:
    """publish_queue の pending を順次処理する（ARCH-002）.

    GitHub Actions Cron (publish_flush.yml) から定期的に呼ばれ、
    pg_cron が enqueue した予約投稿を FastAPI プロセス内で同期実行する。
    """
    logger.info("internal/publish/flush called (limit=%s)", limit)
    result = run_flush(limit=limit, locked_by="gh-actions")
    items_payload: list[dict[str, Any]] = [
        {
            "queue_id": item.get("queue_id"),
            "post_id": item.get("post_id"),
            "status": item.get("status"),
            "error": item.get("error"),
            "terminal": item.get("terminal"),
        }
        for item in result.get("items", [])
    ]
    return FlushResult(processed=result.get("processed", 0), items=items_payload)
