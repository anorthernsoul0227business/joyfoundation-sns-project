"""WebSocket 通知配信 (WEB-027).

`/ws/notifications?token=<jwt>` で接続。JWT を検証して user_id を特定し、
Redis PubSub の `notifications:{user_id}` channel を subscribe して
サーバ発火の通知をクライアントに push する。

Redis 未設定時は接続を受け付けたうえで ping のみ返し、publish は no-op とする。
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.config import get_settings
from app.core.security import _get_jwks_client

logger = logging.getLogger(__name__)

router = APIRouter()

HEARTBEAT_INTERVAL_SECONDS = 30


async def _resolve_user_id(token: str) -> str | None:
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        logger.info("WebSocket JWT validation failed: %s", exc)
        return None
    subject = payload.get("sub")
    if isinstance(subject, str) and subject:
        return subject
    return None


def _notifications_channel(user_id: str) -> str:
    return f"notifications:{user_id}"


async def _subscribe_redis(user_id: str) -> Any:
    """Return an async-capable Redis PubSub or None when Redis is unavailable."""
    try:
        import redis.asyncio as redis_async  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover - redis is expected in prod
        return None

    settings = get_settings()
    broker_url = getattr(settings, "redis_url", None) or "redis://localhost:6379/0"
    try:
        client = redis_async.from_url(broker_url, decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.subscribe(_notifications_channel(user_id))
        return pubsub
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Redis subscribe failed for user=%s: %s", user_id, exc)
        return None


@router.websocket("/notifications")
async def notifications_ws(
    websocket: WebSocket,
    token: str = Query(..., description="Supabase JWT access token"),
) -> None:
    user_id = await _resolve_user_id(token)
    if user_id is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    await websocket.send_json({"type": "connected", "user_id": user_id})

    pubsub = await _subscribe_redis(user_id)

    async def forward_redis() -> None:
        if pubsub is None:
            return
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=HEARTBEAT_INTERVAL_SECONDS,
            )
            if message is None:
                await websocket.send_json({"type": "ping"})
                continue
            payload = message.get("data")
            if payload is None:
                continue
            try:
                parsed = json.loads(payload) if isinstance(payload, str) else payload
            except (TypeError, ValueError):
                parsed = {"type": "message", "raw": payload}
            await websocket.send_json({"type": "notification", "payload": parsed})

    async def heartbeat_only() -> None:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
            await websocket.send_json({"type": "ping"})

    forwarder = asyncio.create_task(
        forward_redis() if pubsub is not None else heartbeat_only()
    )

    try:
        while True:
            received = await websocket.receive_text()
            if received == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        forwarder.cancel()
        if pubsub is not None:
            try:
                await pubsub.unsubscribe(_notifications_channel(user_id))
                await pubsub.close()
            except Exception:  # pragma: no cover - defensive
                pass
