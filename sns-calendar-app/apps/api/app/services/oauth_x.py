from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from fastapi import HTTPException, status

from app.config import get_settings

X_REQUEST_TOKEN_URL = "https://api.x.com/oauth/request_token"
X_AUTHORIZE_URL = "https://api.x.com/oauth/authorize"
X_ACCESS_TOKEN_URL = "https://api.x.com/oauth/access_token"


def _require_x_settings() -> tuple[str, str]:
    settings = get_settings()
    if not settings.x_consumer_key or not settings.x_consumer_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="X OAuth settings are not configured",
        )
    return settings.x_consumer_key, settings.x_consumer_secret


def build_authorization_url(callback_url: str) -> tuple[str, str, str]:
    consumer_key, consumer_secret = _require_x_settings()

    try:
        from requests_oauthlib import OAuth1Session
    except ModuleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="requests-oauthlib is not installed",
        ) from exc

    try:
        session = OAuth1Session(
            consumer_key,
            client_secret=consumer_secret,
            callback_uri=callback_url,
        )
        token_payload = session.fetch_request_token(X_REQUEST_TOKEN_URL)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to obtain X request token",
        ) from exc

    request_token = token_payload.get("oauth_token")
    request_token_secret = token_payload.get("oauth_token_secret")
    if not request_token or not request_token_secret:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="X did not return a valid request token",
        )

    authorization_url = f"{X_AUTHORIZE_URL}?{urlencode({'oauth_token': request_token})}"
    return authorization_url, request_token, request_token_secret


def exchange_code(
    oauth_token: str,
    oauth_verifier: str,
    request_token_secret: str,
) -> dict[str, Any]:
    consumer_key, consumer_secret = _require_x_settings()

    try:
        from requests_oauthlib import OAuth1Session
    except ModuleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="requests-oauthlib is not installed",
        ) from exc

    try:
        session = OAuth1Session(
            consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=oauth_token,
            resource_owner_secret=request_token_secret,
            verifier=oauth_verifier,
        )
        token_payload = session.fetch_access_token(X_ACCESS_TOKEN_URL)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to exchange X access token",
        ) from exc

    access_token = token_payload.get("oauth_token")
    access_token_secret = token_payload.get("oauth_token_secret")
    screen_name = token_payload.get("screen_name")
    user_id = token_payload.get("user_id")

    if not access_token or not access_token_secret or not screen_name or not user_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="X access token response was incomplete",
        )

    return {
        "access_token": access_token,
        "access_token_secret": access_token_secret,
        "screen_name": screen_name,
        "user_id": user_id,
    }
