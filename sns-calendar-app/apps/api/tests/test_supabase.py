import os

import pytest

from app.config import get_settings
from app.core.supabase import get_supabase_client


supabase = pytest.importorskip("supabase")


@pytest.mark.skipif(
    not all(
        (
            os.environ.get("SUPABASE_URL"),
            os.environ.get("SUPABASE_ANON_KEY"),
            os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
        )
    ),
    reason="Supabase environment variables are not configured.",
)
def test_get_supabase_client() -> None:
    settings = get_settings()
    client = get_supabase_client()

    assert isinstance(client, supabase.Client)
    assert getattr(client, "supabase_url", getattr(client, "url", None)) == settings.supabase_url
