"""Supabase client helpers for FastAPI."""

from functools import lru_cache
from typing import TYPE_CHECKING, Any

from app.config import get_settings

if TYPE_CHECKING:
    from supabase import Client
else:
    Client = Any


def _require_supabase_settings(client_name: str) -> tuple[str, str]:
    settings = get_settings()

    if client_name == "service_role":
        key = (
            settings.supabase_service_role_key.get_secret_value()
            if settings.supabase_service_role_key is not None
            else None
        )
    else:
        key = settings.supabase_anon_key

    if not settings.supabase_url or not key:
        raise RuntimeError(
            "Supabase environment variables are not configured. "
            "Set SUPABASE_URL and the required key in .env."
        )

    return settings.supabase_url, key


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Return a cached service-role client for backend use."""
    from supabase import create_client

    url, key = _require_supabase_settings("service_role")
    return create_client(url, key)


def get_anon_client() -> Client:
    """Return a client initialized with the publishable key."""
    from supabase import create_client

    url, key = _require_supabase_settings("anon")
    return create_client(url, key)
