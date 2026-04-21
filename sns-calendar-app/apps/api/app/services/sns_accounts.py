from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from postgrest.exceptions import APIError

from app.core.supabase import get_supabase_client
from app.schemas.sns_account import Platform, SnsAccountSafe


def _normalize_api_error(error: APIError, default_message: str) -> HTTPException:
    message = getattr(error, "message", None) or str(error)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message or default_message)


def _get_user_profile(user_id: str) -> dict[str, Any]:
    client = get_supabase_client()
    rows = (
        client.table("users")
        .select("id,default_org_id")
        .eq("id", user_id)
        .limit(1)
        .execute()
        .data
    )
    if not rows or not rows[0].get("default_org_id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile does not have a default organization",
        )
    return rows[0]


def get_default_org_id_for_user(user_id: str) -> str:
    return _get_user_profile(user_id)["default_org_id"]


def create_oauth_state(
    *,
    state: str,
    user_id: str,
    org_id: str,
    platform: Platform,
    redirect_uri: str,
    request_token: str | None = None,
    request_token_secret: str | None = None,
) -> None:
    client = get_supabase_client()
    payload = {
        "state": state,
        "user_id": user_id,
        "org_id": org_id,
        "platform": platform,
        "request_token": request_token,
        "request_token_secret": request_token_secret,
        "redirect_uri": redirect_uri,
    }
    try:
        client.table("oauth_states").insert(payload).execute()
    except APIError as exc:
        raise _normalize_api_error(exc, "Failed to create OAuth state") from exc


def consume_oauth_state(state: str, platform: Platform) -> dict[str, Any]:
    client = get_supabase_client()
    client.table("oauth_states").delete().lt("expires_at", datetime.now(UTC).isoformat()).execute()

    try:
        result = (
            client.table("oauth_states")
            .select("*")
            .eq("state", state)
            .limit(1)
            .execute()
            .data
        )
    except APIError as exc:
        raise _normalize_api_error(exc, "Failed to read OAuth state") from exc

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        )

    row = result[0]
    expires_at_raw = row.get("expires_at")
    if row.get("platform") != platform:
        client.table("oauth_states").delete().eq("state", state).execute()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state does not match platform",
        )

    if isinstance(expires_at_raw, str):
        expires_at = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
        if expires_at <= datetime.now(UTC):
            client.table("oauth_states").delete().eq("state", state).execute()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth state has expired",
            )

    client.table("oauth_states").delete().eq("state", state).execute()
    return row


def upsert_sns_account(
    *,
    org_id: str,
    platform: Platform,
    handle: str,
    display_name: str | None,
    access_token: str,
    refresh_token: str | None = None,
    expires_at: datetime | None = None,
) -> SnsAccountSafe:
    client = get_supabase_client()
    payload = {
        "org_id": org_id,
        "platform": platform,
        "handle": handle,
        "display_name": display_name,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "is_active": True,
    }

    try:
        client.table("sns_accounts").upsert(
            payload,
            on_conflict="org_id,platform,handle",
        ).execute()
        rows = (
            client.table("sns_accounts_safe")
            .select("*")
            .eq("org_id", org_id)
            .eq("platform", platform)
            .eq("handle", handle)
            .limit(1)
            .execute()
            .data
        )
    except APIError as exc:
        raise _normalize_api_error(exc, "Failed to save SNS account") from exc

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="SNS account was saved but could not be reloaded",
        )
    return SnsAccountSafe.model_validate(rows[0])


def list_sns_accounts_for_user(user_id: str) -> list[SnsAccountSafe]:
    org_id = get_default_org_id_for_user(user_id)
    client = get_supabase_client()
    try:
        rows = (
            client.table("sns_accounts_safe")
            .select("*")
            .eq("org_id", org_id)
            .eq("is_active", True)
            .order("created_at", desc=True)
            .execute()
            .data
        )
    except APIError as exc:
        raise _normalize_api_error(exc, "Failed to list SNS accounts") from exc

    return [SnsAccountSafe.model_validate(row) for row in rows or []]


def deactivate_sns_account_for_user(user_id: str, account_id: str) -> None:
    org_id = get_default_org_id_for_user(user_id)
    client = get_supabase_client()
    try:
        updated = (
            client.table("sns_accounts")
            .update({"is_active": False})
            .eq("id", account_id)
            .eq("org_id", org_id)
            .eq("is_active", True)
            .execute()
            .data
        )
    except APIError as exc:
        raise _normalize_api_error(exc, "Failed to deactivate SNS account") from exc

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SNS account not found",
        )
