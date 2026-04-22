from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import requests
from fastapi import HTTPException, status

from app.config import get_settings

logger = logging.getLogger(__name__)

META_DIALOG_URL = "https://www.facebook.com/v19.0/dialog/oauth"
META_GRAPH_URL = "https://graph.facebook.com/v19.0"
META_SCOPES = (
    "instagram_basic",
    "instagram_content_publish",
    "pages_show_list",
    "pages_read_engagement",
)


def _require_meta_settings() -> tuple[str, str]:
    settings = get_settings()
    if not settings.meta_app_id or not settings.meta_app_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Instagram OAuth settings are not configured",
        )
    return settings.meta_app_id, settings.meta_app_secret


def _request_json(path: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.get(f"{META_GRAPH_URL}{path}", params=params, timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Instagram API request failed",
        ) from exc
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Instagram API is unreachable",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Instagram API returned invalid JSON",
        ) from exc


def build_authorization_url(state: str, redirect_uri: str) -> str:
    app_id, _ = _require_meta_settings()
    query = urlencode(
        {
            "client_id": app_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": ",".join(META_SCOPES),
            "response_type": "code",
        }
    )
    return f"{META_DIALOG_URL}?{query}"


def exchange_code(code: str, redirect_uri: str) -> dict[str, Any]:
    app_id, app_secret = _require_meta_settings()

    short_lived = _request_json(
        "/oauth/access_token",
        {
            "client_id": app_id,
            "client_secret": app_secret,
            "redirect_uri": redirect_uri,
            "code": code,
        },
    )
    short_token = short_lived.get("access_token")
    if not short_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Instagram did not return a short-lived access token",
        )

    long_lived = _request_json(
        "/oauth/access_token",
        {
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_token,
        },
    )
    access_token = long_lived.get("access_token")
    expires_in = long_lived.get("expires_in")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Instagram did not return a long-lived access token",
        )

    pages_response = _request_json(
        "/me/accounts",
        {
            "access_token": access_token,
            "fields": "id,name,access_token",
        },
    )
    pages = pages_response.get("data") or []
    if not pages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Facebook Pages linked to this Instagram account",
        )
    if len(pages) > 1:
        logger.warning("Multiple Facebook Pages found for Instagram OAuth; using the first page")

    selected_page = pages[0]
    page_token = selected_page.get("access_token") or access_token
    page_info = _request_json(
        f"/{selected_page['id']}",
        {
            "fields": "instagram_business_account",
            "access_token": page_token,
        },
    )

    ig_business_account = page_info.get("instagram_business_account") or {}
    ig_account_id = ig_business_account.get("id")
    if not ig_account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Instagram Business Account is connected to the selected Facebook Page",
        )

    ig_profile = _request_json(
        f"/{ig_account_id}",
        {
            "fields": "username",
            "access_token": page_token,
        },
    )
    handle = ig_profile.get("username")
    if not handle:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Instagram profile response did not include a username",
        )

    expires_at = None
    if isinstance(expires_in, int):
        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)

    return {
        "access_token": access_token,
        "user_id": ig_account_id,
        "handle": handle,
        "display_name": selected_page.get("name"),
        "pages": pages,
        "ig_business_account": ig_business_account,
        "expires_at": expires_at,
    }
