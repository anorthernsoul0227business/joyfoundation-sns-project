"""Drive 画像ピッカー API の統合テスト (Drive はフェイク, R2 は moto)。"""

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

from app.api import drive as drive_api
from app.core.security import CurrentUser, get_current_user
from app.main import app
from app.services.drive import DriveError
from app.services.media_processor import MediaProcessor


def _png(width: int, height: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (120, 180, 90)).save(buf, format="PNG")
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


class FakeDriveClient:
    def __init__(self, image_bytes: bytes) -> None:
        self._image_bytes = image_bytes

    def list_folder(self, folder_id: str | None = None) -> dict[str, Any]:
        if folder_id == "denied":
            raise DriveError("アクセス権がありません")
        return {
            "folder_id": folder_id or "shared-root",
            "folders": [{"id": "sub1", "name": "X投稿"}],
            "images": [
                {
                    "id": "img1",
                    "name": "a.png",
                    "mime_type": "image/png",
                    "width": 800,
                    "height": 600,
                }
            ],
        }

    def download_file(self, file_id: str) -> tuple[bytes, str, str]:
        if file_id == "missing":
            raise DriveError("ファイルが見つかりません")
        return self._image_bytes, "image/png", "a.png"

    def get_thumbnail(self, file_id: str) -> tuple[bytes, str]:
        return self._image_bytes, "image/png"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")
        processor = MediaProcessor(_Settings(), s3_client=s3)  # type: ignore[arg-type]
        fake_drive = FakeDriveClient(_png(800, 600))
        org_id = str(uuid4())

        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            id=str(uuid4()),
            email="tester@example.com",
            role="authenticated",
            access_token="test-token",
        )
        app.dependency_overrides[drive_api._get_drive_client] = lambda: fake_drive
        app.dependency_overrides[drive_api._get_processor] = lambda: processor
        monkeypatch.setattr(drive_api, "get_default_org_id_for_user", lambda _uid: org_id)

        try:
            yield TestClient(app)
        finally:
            app.dependency_overrides.clear()


def test_list_returns_folders_and_images(client: TestClient) -> None:
    response = client.get("/api/media/drive/list")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["folder_id"] == "shared-root"
    assert body["folders"] == [{"id": "sub1", "name": "X投稿"}]
    assert body["images"][0]["id"] == "img1"


def test_list_maps_drive_error_to_400(client: TestClient) -> None:
    response = client.get("/api/media/drive/list", params={"folder_id": "denied"})
    assert response.status_code == 400


def test_import_copies_to_r2_and_returns_public_url(client: TestClient) -> None:
    response = client.post("/api/media/drive/import", json={"file_id": "img1"})

    assert response.status_code == 201, response.text
    item = response.json()
    assert item["public_url"].startswith("https://cdn.example.com/media/post-media/")
    assert item["storage_path"].startswith("post-media/")
    assert item["mime_type"] == "image/png"
    assert item["width"] == 800
    assert item["height"] == 600


def test_import_auto_resize_ig_outputs_jpeg(client: TestClient) -> None:
    response = client.post(
        "/api/media/drive/import",
        json={"file_id": "img1", "auto_resize_ig": True},
    )

    assert response.status_code == 201, response.text
    item = response.json()
    assert item["mime_type"] == "image/jpeg"
    assert item["width"] == 1080
    assert item["height"] == 1350


def test_import_missing_file_returns_400(client: TestClient) -> None:
    response = client.post("/api/media/drive/import", json={"file_id": "missing"})
    assert response.status_code == 400


def test_thumbnail_returns_image_bytes(client: TestClient) -> None:
    response = client.get("/api/media/drive/thumbnail/img1")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_drive_endpoints_require_auth() -> None:
    app.dependency_overrides.clear()
    unauth = TestClient(app)
    assert unauth.get("/api/media/drive/list").status_code == 401
