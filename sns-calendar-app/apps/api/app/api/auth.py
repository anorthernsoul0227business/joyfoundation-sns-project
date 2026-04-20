from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import CurrentUser, get_current_user
from app.core.supabase import get_anon_client, get_supabase_client
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    SessionResponse,
    SignupRequest,
    UserResponse,
)

router = APIRouter()


def _extract_error_message(error: Exception) -> str:
    details = getattr(error, "message", None)
    if details:
        return str(details)

    args = getattr(error, "args", ())
    if args:
        return str(args[0])

    return "Supabase request failed"


def _to_http_exception(error: Exception) -> HTTPException:
    message = _extract_error_message(error)
    lowered = message.lower()
    if "invalid login credentials" in lowered or "invalid refresh token" in lowered:
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)
    if "already registered" in lowered or "already been registered" in lowered:
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


def _normalize_user(user: Any, profile: dict[str, Any] | None = None) -> UserResponse:
    metadata = getattr(user, "user_metadata", None) or {}
    source = profile or {}
    email = source.get("email") or getattr(user, "email", None)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase response did not include a user email",
        )

    return UserResponse(
        id=user.id,
        email=email,
        display_name=source.get("display_name") or metadata.get("display_name"),
        ui_mode=source.get("ui_mode", "simple"),
        help_mode_enabled=source.get("help_mode_enabled", True),
        default_org_id=source.get("default_org_id"),
    )


def _build_session_response(auth_response: Any) -> SessionResponse:
    session = getattr(auth_response, "session", None)
    user = getattr(auth_response, "user", None)
    if session is None or user is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase did not return an authenticated session",
        )

    return SessionResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in,
        token_type=getattr(session, "token_type", "bearer") or "bearer",
        user=_normalize_user(user),
    )


@router.post(
    "/signup",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def signup(payload: SignupRequest) -> SessionResponse:
    client = get_anon_client()
    credentials: dict[str, Any] = {
        "email": payload.email,
        "password": payload.password.get_secret_value(),
    }
    if payload.display_name:
        credentials["options"] = {"data": {"display_name": payload.display_name}}

    try:
        auth_response = client.auth.sign_up(credentials)
    except Exception as exc:
        raise _to_http_exception(exc) from exc

    return _build_session_response(auth_response)


@router.post("/login", response_model=SessionResponse)
def login(payload: LoginRequest) -> SessionResponse:
    client = get_anon_client()

    try:
        auth_response = client.auth.sign_in_with_password(
            {
                "email": payload.email,
                "password": payload.password.get_secret_value(),
            }
        )
    except Exception as exc:
        raise _to_http_exception(exc) from exc

    return _build_session_response(auth_response)


@router.post("/logout", response_model=MessageResponse)
def logout(
    current_user: CurrentUser = Depends(get_current_user),
) -> MessageResponse:
    client = get_anon_client()

    try:
        client.auth.admin.sign_out(current_user.access_token, "global")
    except Exception as exc:
        raise _to_http_exception(exc) from exc

    return MessageResponse(message="Logged out")


@router.post("/refresh", response_model=SessionResponse)
def refresh(payload: RefreshRequest) -> SessionResponse:
    client = get_anon_client()

    try:
        auth_response = client.auth.refresh_session(payload.refresh_token)
    except Exception as exc:
        raise _to_http_exception(exc) from exc

    return _build_session_response(auth_response)


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser = Depends(get_current_user)) -> UserResponse:
    client = get_supabase_client()

    profile_rows = (
        client.table("users")
        .select("id,email,display_name,ui_mode,help_mode_enabled,default_org_id")
        .eq("id", current_user.id)
        .limit(1)
        .execute()
        .data
    )

    if not profile_rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    return UserResponse.model_validate(profile_rows[0])
