"""Schema verification for WEB-010 (posts / post_targets / post_media / sns_accounts)."""

from __future__ import annotations

import os
import socket
import uuid

import pytest
from postgrest import APIError

from app.core.supabase import get_supabase_client


def _has_local_supabase_env() -> bool:
    url = os.environ.get("SUPABASE_URL", "")
    return all(
        (
            url,
            os.environ.get("SUPABASE_ANON_KEY"),
            os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
        )
    ) and ("127.0.0.1" in url or "localhost" in url)


def _can_reach_local_supabase() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 54321), timeout=1):
            return True
    except OSError:
        return False


skip_unless_local = pytest.mark.skipif(
    not _has_local_supabase_env() or not _can_reach_local_supabase(),
    reason="Local Supabase is required.",
)


@skip_unless_local
def test_posts_schema_tables_exist() -> None:
    client = get_supabase_client()
    for table in ("posts", "post_targets", "post_media", "sns_accounts"):
        resp = client.table(table).select("id").limit(0).execute()
        assert resp.data is not None, f"{table} should be queryable"


@skip_unless_local
def test_sns_accounts_safe_view_exists_and_excludes_tokens() -> None:
    client = get_supabase_client()
    resp = client.table("sns_accounts_safe").select("*").limit(0).execute()
    assert resp.data is not None

    user_email = f"schema-posts-{uuid.uuid4()}@example.com"
    created_user = client.auth.admin.create_user(
        {
            "email": user_email,
            "password": "Password123!",
            "email_confirm": True,
            "user_metadata": {"display_name": "Schema Posts"},
        }
    )
    user_id = created_user.user.id
    try:
        profile_rows = (
            client.table("users")
            .select("default_org_id")
            .eq("id", user_id)
            .limit(1)
            .execute()
            .data
        )
        org_id = profile_rows[0]["default_org_id"]

        inserted = (
            client.table("sns_accounts")
            .insert(
                {
                    "org_id": org_id,
                    "platform": "x",
                    "handle": f"test-{uuid.uuid4()}",
                    "access_token": "secret-access-token-value",
                    "refresh_token": "secret-refresh-token-value",
                }
            )
            .execute()
        )
        account_id = inserted.data[0]["id"]

        safe_row = (
            client.table("sns_accounts_safe")
            .select("*")
            .eq("id", account_id)
            .limit(1)
            .execute()
            .data[0]
        )
        assert "access_token" not in safe_row
        assert "refresh_token" not in safe_row
        assert safe_row["org_id"] == org_id
    finally:
        client.auth.admin.delete_user(user_id)


@skip_unless_local
def test_posts_status_enum_rejects_invalid_value() -> None:
    client = get_supabase_client()
    user_email = f"posts-enum-{uuid.uuid4()}@example.com"
    created_user = client.auth.admin.create_user(
        {
            "email": user_email,
            "password": "Password123!",
            "email_confirm": True,
        }
    )
    user_id = created_user.user.id
    try:
        profile_rows = (
            client.table("users")
            .select("default_org_id")
            .eq("id", user_id)
            .limit(1)
            .execute()
            .data
        )
        org_id = profile_rows[0]["default_org_id"]

        with pytest.raises(APIError):
            client.table("posts").insert(
                {
                    "org_id": org_id,
                    "user_id": user_id,
                    "status": "not_a_valid_status",
                    "content_text": "bad",
                }
            ).execute()
    finally:
        client.auth.admin.delete_user(user_id)


@skip_unless_local
def test_post_media_cascades_on_post_delete() -> None:
    client = get_supabase_client()
    user_email = f"posts-cascade-{uuid.uuid4()}@example.com"
    created_user = client.auth.admin.create_user(
        {
            "email": user_email,
            "password": "Password123!",
            "email_confirm": True,
        }
    )
    user_id = created_user.user.id
    try:
        profile_rows = (
            client.table("users")
            .select("default_org_id")
            .eq("id", user_id)
            .limit(1)
            .execute()
            .data
        )
        org_id = profile_rows[0]["default_org_id"]

        post_row = (
            client.table("posts")
            .insert(
                {
                    "org_id": org_id,
                    "user_id": user_id,
                    "content_text": "cascade test",
                }
            )
            .execute()
            .data[0]
        )
        post_id = post_row["id"]

        client.table("post_media").insert(
            {
                "post_id": post_id,
                "storage_path": "tmp/cascade.png",
                "mime_type": "image/png",
            }
        ).execute()
        client.table("post_targets").insert(
            {
                "post_id": post_id,
                "platform": "x",
            }
        ).execute()

        client.table("posts").delete().eq("id", post_id).execute()

        remaining_media = (
            client.table("post_media")
            .select("id")
            .eq("post_id", post_id)
            .execute()
            .data
        )
        remaining_targets = (
            client.table("post_targets")
            .select("id")
            .eq("post_id", post_id)
            .execute()
            .data
        )
        assert remaining_media == []
        assert remaining_targets == []
    finally:
        client.auth.admin.delete_user(user_id)


@skip_unless_local
def test_posts_scheduled_status_requires_scheduled_at() -> None:
    client = get_supabase_client()
    user_email = f"posts-scheduled-{uuid.uuid4()}@example.com"
    created_user = client.auth.admin.create_user(
        {
            "email": user_email,
            "password": "Password123!",
            "email_confirm": True,
        }
    )
    user_id = created_user.user.id
    try:
        profile_rows = (
            client.table("users")
            .select("default_org_id")
            .eq("id", user_id)
            .limit(1)
            .execute()
            .data
        )
        org_id = profile_rows[0]["default_org_id"]

        with pytest.raises(APIError):
            client.table("posts").insert(
                {
                    "org_id": org_id,
                    "user_id": user_id,
                    "status": "scheduled",
                    "content_text": "forgot scheduled_at",
                }
            ).execute()
    finally:
        client.auth.admin.delete_user(user_id)
