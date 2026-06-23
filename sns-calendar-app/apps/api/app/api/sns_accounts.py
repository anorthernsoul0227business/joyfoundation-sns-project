from __future__ import annotations

import secrets
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.core.security import CurrentUser, get_current_user
from app.schemas.sns_account import ConnectResponse, Platform, SnsAccountListResponse
from app.services import oauth_ig, oauth_x
from app.services import sns_accounts as sns_account_service

router = APIRouter()


def _validate_platform(platform: str) -> Platform:
    if platform not in {"x", "ig"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="platform must be one of: x, ig",
        )
    return platform


def _require_oauth_redirect_base() -> str:
    settings = get_settings()
    if not settings.oauth_redirect_base:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAUTH_REDIRECT_BASE is not configured",
        )
    return settings.oauth_redirect_base.rstrip("/")


def _callback_url(platform: Platform) -> str:
    return f"{_require_oauth_redirect_base()}/api/sns-accounts/callback/{platform}"


def _settings_redirect_url(platform: Platform | None = None, handle: str | None = None) -> str:
    settings = get_settings()
    frontend_base = (settings.frontend_url or _require_oauth_redirect_base()).rstrip("/")
    base = f"{frontend_base}/settings/sns"
    if platform and handle:
        return f"{base}?{urlencode({'connected': platform, 'handle': handle})}"
    return base


def _error_redirect_url(reason: str) -> str:
    return f"{_settings_redirect_url()}?{urlencode({'error': reason})}"


def _account_handle(saved_account: object) -> str:
    if hasattr(saved_account, "handle"):
        return str(saved_account.handle)
    if isinstance(saved_account, dict) and "handle" in saved_account:
        return str(saved_account["handle"])
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Saved SNS account did not include a handle",
    )


@router.post("/connect/{platform}", response_model=ConnectResponse)
def connect_sns_account(
    platform: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ConnectResponse:
    normalized_platform = _validate_platform(platform)
    org_id = sns_account_service.get_default_org_id_for_user(current_user.id)
    state = secrets.token_urlsafe(32)
    callback_url = _callback_url(normalized_platform)

    request_token: str | None = None
    request_token_secret: str | None = None

    if normalized_platform == "x":
        authorization_url, request_token, request_token_secret = oauth_x.build_authorization_url(
            callback_url
        )
    else:
        authorization_url = oauth_ig.build_authorization_url(state, callback_url)

    sns_account_service.create_oauth_state(
        state=state,
        user_id=current_user.id,
        org_id=org_id,
        platform=normalized_platform,
        redirect_uri=callback_url,
        request_token=request_token,
        request_token_secret=request_token_secret,
    )
    return ConnectResponse(authorization_url=authorization_url, state=state)


@router.get("/callback/{platform}", response_class=Response)
def sns_account_callback(
    platform: str,
    state: Annotated[str | None, Query()] = None,
    code: Annotated[str | None, Query()] = None,
    oauth_token: Annotated[str | None, Query()] = None,
    oauth_verifier: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
    error_reason: Annotated[str | None, Query()] = None,
    denied: Annotated[str | None, Query()] = None,
) -> Response:
    normalized_platform = _validate_platform(platform)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth state",
        )

    state_row = sns_account_service.consume_oauth_state(state, normalized_platform)

    if error or error_reason or denied:
        reason = error_reason or error or "provider_denied"
        return RedirectResponse(url=_error_redirect_url(reason), status_code=status.HTTP_302_FOUND)

    try:
        if normalized_platform == "x":
            if not oauth_token or not oauth_verifier:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing X OAuth callback parameters",
                )
            if oauth_token != state_row.get("request_token"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="X OAuth token did not match the original request token",
                )
            token_data = oauth_x.exchange_code(
                oauth_token=oauth_token,
                oauth_verifier=oauth_verifier,
                request_token_secret=state_row["request_token_secret"],
            )
            saved_account = sns_account_service.upsert_sns_account(
                org_id=state_row["org_id"],
                platform=normalized_platform,
                handle=token_data["screen_name"],
                display_name=token_data["screen_name"],
                access_token=(
                    f"{token_data['access_token']}:{token_data['access_token_secret']}"
                ),
                platform_account_id=token_data["user_id"],
            )
        else:
            if not code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing Instagram authorization code",
                )
            token_data = oauth_ig.exchange_code(code=code, redirect_uri=state_row["redirect_uri"])
            saved_account = sns_account_service.upsert_sns_account(
                org_id=state_row["org_id"],
                platform=normalized_platform,
                handle=token_data["handle"],
                display_name=token_data.get("display_name"),
                access_token=token_data["access_token"],
                platform_account_id=token_data["user_id"],
                expires_at=token_data.get("expires_at"),
            )
    except HTTPException as exc:
        if exc.status_code == status.HTTP_400_BAD_REQUEST:
            raise
        return RedirectResponse(
            url=_error_redirect_url(exc.detail.replace(" ", "_").lower()),
            status_code=status.HTTP_302_FOUND,
        )

    return RedirectResponse(
        url=_settings_redirect_url(normalized_platform, _account_handle(saved_account)),
        status_code=status.HTTP_302_FOUND,
    )


@router.get("", response_model=SnsAccountListResponse)
def list_sns_accounts(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> SnsAccountListResponse:
    accounts = sns_account_service.list_sns_accounts_for_user(current_user.id)
    return SnsAccountListResponse(accounts=accounts)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sns_account(
    account_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> Response:
    sns_account_service.deactivate_sns_account_for_user(current_user.id, account_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
