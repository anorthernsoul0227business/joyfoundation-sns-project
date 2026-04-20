import os
import socket
import uuid

import pytest
from supabase import Client, create_client

LOCAL_SUPABASE_URL = "http://127.0.0.1:54321"


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


def _create_service_client() -> Client:
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


def _create_authenticated_client(email: str, password: str) -> Client:
    client = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_ANON_KEY"],
    )
    auth_response = client.auth.sign_in_with_password(
        {
            "email": email,
            "password": password,
        }
    )
    session = auth_response.session
    assert session is not None
    client.postgrest.auth(session.access_token)
    return client


def _create_test_user(service_client: Client, label: str) -> dict[str, str]:
    email = f"rls-{label}-{uuid.uuid4()}@example.com"
    password = "Password123!"
    created_user = service_client.auth.admin.create_user(
        {
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"display_name": f"RLS {label}"},
        }
    )
    user_id = created_user.user.id

    profile_rows = (
        service_client.table("users")
        .select("id,default_org_id")
        .eq("id", user_id)
        .limit(1)
        .execute()
        .data
    )

    assert profile_rows
    default_org_id = profile_rows[0]["default_org_id"]
    assert default_org_id is not None

    return {
        "id": user_id,
        "email": email,
        "password": password,
        "org_id": default_org_id,
    }


@pytest.mark.skipif(
    not _has_local_supabase_env() or not _can_reach_local_supabase(),
    reason="Local Supabase environment variables are not configured or the local Supabase API is unreachable.",
)
def test_rls_policies_isolate_org_data() -> None:
    assert os.environ["SUPABASE_URL"].rstrip("/") == LOCAL_SUPABASE_URL

    service_client = _create_service_client()
    user_a = _create_test_user(service_client, "a")
    user_b = _create_test_user(service_client, "b")

    try:
        user_a_client = _create_authenticated_client(user_a["email"], user_a["password"])

        profile_a = (
            user_a_client.table("users")
            .select("id,email")
            .eq("id", user_a["id"])
            .limit(1)
            .execute()
            .data
        )
        assert profile_a
        assert profile_a[0]["id"] == user_a["id"]

        org_a = (
            user_a_client.table("organizations")
            .select("id,name")
            .eq("id", user_a["org_id"])
            .limit(1)
            .execute()
            .data
        )
        assert org_a
        assert org_a[0]["id"] == user_a["org_id"]

        org_b = (
            user_a_client.table("organizations")
            .select("id")
            .eq("id", user_b["org_id"])
            .execute()
            .data
        )
        assert org_b == []

        profile_b = (
            user_a_client.table("users")
            .select("id")
            .eq("id", user_b["id"])
            .execute()
            .data
        )
        assert profile_b == []

        updated_org_name = f"Blocked-{uuid.uuid4()}"
        user_a_client.table("organizations").update({"name": updated_org_name}).eq(
            "id",
            user_b["org_id"],
        ).execute()

        org_b_after = (
            service_client.table("organizations")
            .select("id,name")
            .eq("id", user_b["org_id"])
            .limit(1)
            .execute()
            .data
        )
        assert org_b_after
        assert org_b_after[0]["name"] != updated_org_name

        toggled_help_mode = False
        user_a_client.table("users").update(
            {"help_mode_enabled": toggled_help_mode}
        ).eq("id", user_a["id"]).execute()

        user_a_profile_after_update = (
            user_a_client.table("users")
            .select("id,help_mode_enabled")
            .eq("id", user_a["id"])
            .limit(1)
            .execute()
            .data
        )
        assert user_a_profile_after_update
        assert user_a_profile_after_update[0]["help_mode_enabled"] is toggled_help_mode

        service_visible_users = service_client.table("users").select("id").in_(
            "id",
            [user_a["id"], user_b["id"]],
        ).execute().data
        assert service_visible_users is not None
        assert {row["id"] for row in service_visible_users} == {user_a["id"], user_b["id"]}
    finally:
        service_client.auth.admin.delete_user(user_a["id"])
        service_client.auth.admin.delete_user(user_b["id"])
