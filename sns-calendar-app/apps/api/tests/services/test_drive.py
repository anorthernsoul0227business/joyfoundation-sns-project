"""DriveClient の単体テスト (Drive REST はフェイクセッションで差し替え)。"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.services.drive import DriveClient, DriveError, DriveNotConfigured


class FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        json_data: dict[str, Any] | None = None,
        content: bytes = b"",
        text: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._json = json_data or {}
        self.content = content
        self.text = text
        self.headers = headers or {}

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self) -> dict[str, Any]:
        return self._json


class FakeSession:
    """params から list / metadata / media を判別して応答するフェイク。"""

    def __init__(
        self,
        *,
        list_response: FakeResponse | None = None,
        metadata_response: FakeResponse | None = None,
        media_response: FakeResponse | None = None,
        thumbnail_response: FakeResponse | None = None,
    ) -> None:
        self.list_response = list_response
        self.metadata_response = metadata_response
        self.media_response = media_response
        self.thumbnail_response = thumbnail_response
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, params: dict[str, Any], timeout: int) -> FakeResponse:
        self.calls.append({"url": url, "params": params})
        if url.endswith("/files"):
            assert self.list_response is not None
            return self.list_response
        if "/files/" in url and "fields" in params:
            assert self.metadata_response is not None
            return self.metadata_response
        if params.get("alt") == "media":
            assert self.media_response is not None
            return self.media_response
        # 外部サムネイルリンク (thumbnailLink) への取得
        assert self.thumbnail_response is not None
        return self.thumbnail_response


def _settings(folder_id: str | None = "shared-root") -> Any:
    return SimpleNamespace(
        google_service_account_json=None,
        google_service_account_file=None,
        drive_shared_folder_id=folder_id,
    )


def test_list_folder_splits_folders_and_images() -> None:
    session = FakeSession(
        list_response=FakeResponse(
            json_data={
                "files": [
                    {"id": "f1", "name": "X投稿", "mimeType": "application/vnd.google-apps.folder"},
                    {
                        "id": "i1",
                        "name": "a.jpg",
                        "mimeType": "image/jpeg",
                        "imageMediaMetadata": {"width": 800, "height": 600},
                    },
                    {"id": "x1", "name": "note.txt", "mimeType": "text/plain"},
                ]
            }
        ),
    )
    client = DriveClient(_settings(), session=session)

    result = client.list_folder()

    assert result["folder_id"] == "shared-root"
    assert result["folders"] == [{"id": "f1", "name": "X投稿"}]
    assert len(result["images"]) == 1
    assert result["images"][0] == {
        "id": "i1",
        "name": "a.jpg",
        "mime_type": "image/jpeg",
        "width": 800,
        "height": 600,
    }
    # 共有ルートが query に入っていること
    assert "'shared-root' in parents" in session.calls[0]["params"]["q"]


def test_list_folder_uses_explicit_folder_id() -> None:
    session = FakeSession(list_response=FakeResponse(json_data={"files": []}))
    client = DriveClient(_settings(), session=session)

    client.list_folder("sub-folder")

    assert "'sub-folder' in parents" in session.calls[0]["params"]["q"]


def test_list_folder_raises_when_no_folder_configured() -> None:
    session = FakeSession(list_response=FakeResponse(json_data={"files": []}))
    client = DriveClient(_settings(folder_id=None), session=session)

    with pytest.raises(DriveNotConfigured):
        client.list_folder()


def test_list_folder_maps_404_to_drive_error() -> None:
    session = FakeSession(list_response=FakeResponse(status_code=404, text="not found"))
    client = DriveClient(_settings(), session=session)

    with pytest.raises(DriveError):
        client.list_folder()


def test_download_file_returns_bytes_for_image() -> None:
    session = FakeSession(
        metadata_response=FakeResponse(
            json_data={"id": "i1", "name": "a.png", "mimeType": "image/png", "size": "1024"}
        ),
        media_response=FakeResponse(content=b"PNGDATA"),
    )
    client = DriveClient(_settings(), session=session)

    content, mime, name = client.download_file("i1")

    assert content == b"PNGDATA"
    assert mime == "image/png"
    assert name == "a.png"


def test_download_file_rejects_non_image() -> None:
    session = FakeSession(
        metadata_response=FakeResponse(
            json_data={"id": "x1", "name": "n.txt", "mimeType": "text/plain", "size": "10"}
        ),
    )
    client = DriveClient(_settings(), session=session)

    with pytest.raises(DriveError):
        client.download_file("x1")


def test_get_thumbnail_uses_thumbnail_link() -> None:
    session = FakeSession(
        metadata_response=FakeResponse(
            json_data={
                "id": "i1",
                "mimeType": "image/jpeg",
                "thumbnailLink": "https://lh3.googleusercontent.com/thumb",
            }
        ),
        thumbnail_response=FakeResponse(
            content=b"THUMB", headers={"Content-Type": "image/jpeg"}
        ),
    )
    client = DriveClient(_settings(), session=session)

    content, mime = client.get_thumbnail("i1")

    assert content == b"THUMB"
    assert mime == "image/jpeg"


def test_get_thumbnail_falls_back_to_full_download() -> None:
    session = FakeSession(
        metadata_response=FakeResponse(
            json_data={"id": "i1", "mimeType": "image/png", "size": "100"}
        ),
        media_response=FakeResponse(content=b"FULL"),
    )
    client = DriveClient(_settings(), session=session)

    content, mime = client.get_thumbnail("i1")

    assert content == b"FULL"
    assert mime == "image/png"


def test_get_thumbnail_rejects_non_image() -> None:
    session = FakeSession(
        metadata_response=FakeResponse(json_data={"id": "x", "mimeType": "text/plain"}),
    )
    client = DriveClient(_settings(), session=session)

    with pytest.raises(DriveError):
        client.get_thumbnail("x")


def test_download_file_rejects_oversize() -> None:
    session = FakeSession(
        metadata_response=FakeResponse(
            json_data={
                "id": "big",
                "name": "big.jpg",
                "mimeType": "image/jpeg",
                "size": str(99 * 1024 * 1024),
            }
        ),
    )
    client = DriveClient(_settings(), session=session)

    with pytest.raises(DriveError):
        client.download_file("big")
