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


@pytest.mark.skipif(
    not _has_local_supabase_env() or not _can_reach_local_supabase(),
    reason="Local Supabase environment variables are not configured or the local Supabase API is unreachable.",
)
def test_initial_schema_tables_exist() -> None:
    client = get_supabase_client()

    organizations = client.table("organizations").select("id").limit(1).execute()
    org_members = client.table("org_members").select("id").limit(1).execute()
    users = client.table("users").select("id").limit(1).execute()

    assert organizations.data is not None
    assert org_members.data is not None
    assert users.data is not None


@pytest.mark.skipif(
    not _has_local_supabase_env() or not _can_reach_local_supabase(),
    reason="Local Supabase environment variables are not configured or the local Supabase API is unreachable.",
)
def test_initial_schema_foreign_keys_enforced() -> None:
    client = get_supabase_client()
    user_email = f"schema-test-{uuid.uuid4()}@example.com"
    created_user = client.auth.admin.create_user(
        {
            "email": user_email,
            "password": "Password123!",
            "email_confirm": True,
            "user_metadata": {"display_name": "Schema Test"},
        }
    )
    user_id = created_user.user.id
    invalid_uuid = str(uuid.uuid4())

    try:
        profile_rows = (
            client.table("users")
            .select("id,default_org_id")
            .eq("id", user_id)
            .limit(1)
            .execute()
            .data
        )

        assert profile_rows
        assert profile_rows[0]["default_org_id"] is not None

        with pytest.raises(APIError):
            client.table("organizations").insert(
                {
                    "name": "Broken Org",
                    "owner_user_id": invalid_uuid,
                }
            ).execute()

        with pytest.raises(APIError):
            client.table("org_members").insert(
                {
                    "org_id": invalid_uuid,
                    "user_id": user_id,
                    "role": "member",
                }
            ).execute()

        with pytest.raises(APIError):
            client.table("users").update({"default_org_id": invalid_uuid}).eq("id", user_id).execute()
    finally:
        client.auth.admin.delete_user(user_id)
