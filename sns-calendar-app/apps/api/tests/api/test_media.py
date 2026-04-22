from __future__ import annotations

import io
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws
from PIL import Image

from app.api import media as media_api
from app.core.security import CurrentUser, get_current_user
from app.main import app
from app.services.media_processor import MediaProcessor


def _jpeg(width: int, height: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (100, 150, 200)).save(buf, format="JPEG", quality=80)
    return buf.getvalue()


class _Settings:
    r2_account_id = "acct"
    r2_access_key_id = "key"
    r2_bucket_name = "test-bucket"
    r2_public_url = "https://cdn.example.com/media"

    class _Secret:
        def get_secret_value(self) -> str:
            return "secret"

    r2_secret_access_key = _Secret()


@pytest.fixture
def r2_context() -> Iterator[tuple[Any, MediaProcessor]]:
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")
        processor = MediaProcessor(_Settings(), s3_client=s3)  # type: ignore[arg-type]
        yield s3, processor


@pytest.fixture
def authenticated_client(
    r2_context: tuple[Any, MediaProcessor],
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    _, processor = r2_context
    user_id = str(uuid4())
    org_id = str(uuid4())

    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=user_id,
        email="tester@example.com",
        role="authenticated",
        access_token="test-token",
    )
    app.dependency_overrides[media_api._get_processor] = lambda: processor
    monkeypatch.setattr(
        media_api,
        "get_default_org_id_for_user",
        lambda _user_id: org_id,
    )

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client() -> Iterator[TestClient]:
    yield TestClient(app)


def test_upload_media_returns_public_url_and_storage_path(
    authenticated_client: TestClient,
    r2_context: tuple[Any, MediaProcessor],
) -> None:
    s3, _ = r2_context
    files = [("files", ("sample.jpg", _jpeg(800, 600), "image/jpeg"))]

    response = authenticated_client.post("/api/media/upload", files=files)

    assert response.status_code == 201, response.text
    body = response.json()
    assert len(body["media"]) == 1
    item = body["media"][0]
    assert item["public_url"].startswith("https://cdn.example.com/media/post-media/")
    assert item["storage_path"].startswith("post-media/")
    assert item["storage_path"].endswith(".jpg")
    assert item["width"] == 800
    assert item["height"] == 600
    assert item["mime_type"] == "image/jpeg"

    listed = s3.list_objects_v2(Bucket="test-bucket")
    assert listed["KeyCount"] == 1


def test_upload_media_auto_resize_ig_pads_to_1080x1350(
    authenticated_client: TestClient,
    r2_context: tuple[Any, MediaProcessor],
) -> None:
    s3, _ = r2_context
    files = [("files", ("wide.jpg", _jpeg(1600, 900), "image/jpeg"))]

    response = authenticated_client.post(
        "/api/media/upload",
        files=files,
        params={"auto_resize_ig": "true"},
    )

    assert response.status_code == 201, response.text
    item = response.json()["media"][0]
    assert item["width"] == 1080
    assert item["height"] == 1350
    assert item["mime_type"] == "image/jpeg"

    key = item["storage_path"]
    obj = s3.get_object(Bucket="test-bucket", Key=key)
    with Image.open(io.BytesIO(obj["Body"].read())) as out:
        assert out.size == (1080, 1350)


def test_upload_media_rejects_non_image_mime(authenticated_client: TestClient) -> None:
    files = [("files", ("notes.txt", b"hello", "text/plain"))]

    response = authenticated_client.post("/api/media/upload", files=files)

    assert response.status_code == 400


def test_upload_media_rejects_files_over_10mb(authenticated_client: TestClient) -> None:
    big_payload = b"\xff" * (10 * 1024 * 1024 + 1)
    files = [("files", ("big.jpg", big_payload, "image/jpeg"))]

    response = authenticated_client.post("/api/media/upload", files=files)

    assert response.status_code == 413


def test_upload_media_rejects_more_than_ten_files(
    authenticated_client: TestClient,
) -> None:
    payload = _jpeg(100, 100)
    files = [("files", (f"img{i}.jpg", payload, "image/jpeg")) for i in range(11)]

    response = authenticated_client.post("/api/media/upload", files=files)

    assert response.status_code == 400


def test_upload_media_requires_authentication(
    unauthenticated_client: TestClient,
) -> None:
    files = [("files", ("sample.jpg", _jpeg(100, 100), "image/jpeg"))]

    response = unauthenticated_client.post("/api/media/upload", files=files)

    assert response.status_code == 401
