"""Google Drive 連携サービス (画像ピッカー).

共有フォルダに置かれた画像を、サービスアカウント権限で一覧・ダウンロードする。
Picker や個別 OAuth は使わず、SA に共有されたフォルダのみアクセスする方式
(シニアユーザー向けにログイン不要)。Drive の権限モデルが「SA に共有された
範囲のみ」を保証するため、アプリ側で追加のツリー検査は行わない。

依存は google-auth (SA トークン発行) と既存の requests のみ。重い
google-api-python-client は使わず Drive REST v3 を直接叩く。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

from app.config import Settings

logger = logging.getLogger(__name__)

DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
FOLDER_MIME = "application/vnd.google-apps.folder"
SUPPORTED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}
MAX_DOWNLOAD_SIZE = 15 * 1024 * 1024  # 15 MB。R2 アップロード上限(10MB)より少し広く取る
REQUEST_TIMEOUT = 30


class DriveError(RuntimeError):
    """Drive アクセス全般のエラー。"""


class DriveNotConfigured(DriveError):
    """SA 資格情報や共有フォルダ ID が未設定。"""


class DriveClient:
    def __init__(self, settings: Settings, *, session: AuthorizedSession | None = None) -> None:
        self._settings = settings
        self._session = session

    # --- 認証 -----------------------------------------------------------------
    def _load_credentials(self) -> service_account.Credentials:
        raw_json = self._settings.google_service_account_json
        file_path = self._settings.google_service_account_file
        if raw_json is not None:
            try:
                info = json.loads(raw_json.get_secret_value())
            except json.JSONDecodeError as exc:
                raise DriveNotConfigured("GOOGLE_SERVICE_ACCOUNT_JSON が不正な JSON です") from exc
            return service_account.Credentials.from_service_account_info(info, scopes=DRIVE_SCOPES)
        if file_path:
            return service_account.Credentials.from_service_account_file(
                file_path, scopes=DRIVE_SCOPES
            )
        raise DriveNotConfigured("サービスアカウント資格情報が未設定です")

    def _get_session(self) -> AuthorizedSession:
        if self._session is None:
            self._session = AuthorizedSession(self._load_credentials())
        return self._session

    def _resolve_folder_id(self, folder_id: str | None) -> str:
        resolved = folder_id or self._settings.drive_shared_folder_id
        if not resolved:
            raise DriveNotConfigured("DRIVE_SHARED_FOLDER_ID が未設定です")
        return resolved

    # --- 一覧 -----------------------------------------------------------------
    def list_folder(self, folder_id: str | None = None) -> dict[str, Any]:
        """指定フォルダ直下のサブフォルダと画像を返す。folder_id 省略時は共有ルート。"""
        resolved = self._resolve_folder_id(folder_id)
        session = self._get_session()
        params = {
            "q": f"'{resolved}' in parents and trashed = false",
            "fields": (
                "files(id,name,mimeType,size,"
                "imageMediaMetadata(width,height))"
            ),
            "orderBy": "folder,name",
            "pageSize": "200",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
        response = session.get(
            f"{DRIVE_API_BASE}/files", params=params, timeout=REQUEST_TIMEOUT
        )
        if response.status_code == 404:
            raise DriveError("フォルダが見つからないか、アクセス権がありません")
        if not response.ok:
            logger.warning("Drive list failed: %s %s", response.status_code, response.text[:200])
            raise DriveError("Drive の一覧取得に失敗しました")

        files = response.json().get("files", [])
        folders: list[dict[str, Any]] = []
        images: list[dict[str, Any]] = []
        for item in files:
            mime = item.get("mimeType")
            if mime == FOLDER_MIME:
                folders.append({"id": item["id"], "name": item.get("name", "")})
            elif mime in SUPPORTED_IMAGE_MIMES:
                meta = item.get("imageMediaMetadata") or {}
                images.append(
                    {
                        "id": item["id"],
                        "name": item.get("name", ""),
                        "mime_type": mime,
                        "width": meta.get("width"),
                        "height": meta.get("height"),
                    }
                )
        return {"folder_id": resolved, "folders": folders, "images": images}

    # --- ダウンロード ---------------------------------------------------------
    def _get_metadata(self, file_id: str) -> dict[str, Any]:
        session = self._get_session()
        response = session.get(
            f"{DRIVE_API_BASE}/files/{file_id}",
            params={
                "fields": "id,name,mimeType,size,thumbnailLink",
                "supportsAllDrives": "true",
            },
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 404:
            raise DriveError("ファイルが見つからないか、アクセス権がありません")
        if not response.ok:
            raise DriveError("Drive のメタデータ取得に失敗しました")
        return response.json()

    def download_file(self, file_id: str) -> tuple[bytes, str, str]:
        """(bytes, mime_type, name) を返す。画像以外・サイズ超過は拒否。"""
        meta = self._get_metadata(file_id)
        mime = meta.get("mimeType", "")
        if mime not in SUPPORTED_IMAGE_MIMES:
            raise DriveError(f"未対応の形式です: {mime or 'unknown'}")
        size = int(meta.get("size") or 0)
        if size and size > MAX_DOWNLOAD_SIZE:
            raise DriveError("ファイルサイズが上限を超えています")

        session = self._get_session()
        response = session.get(
            f"{DRIVE_API_BASE}/files/{file_id}",
            params={"alt": "media", "supportsAllDrives": "true"},
            timeout=REQUEST_TIMEOUT,
        )
        if not response.ok:
            raise DriveError("Drive からのダウンロードに失敗しました")
        content = response.content
        if len(content) > MAX_DOWNLOAD_SIZE:
            raise DriveError("ファイルサイズが上限を超えています")
        return content, mime, meta.get("name", file_id)

    def get_thumbnail(self, file_id: str) -> tuple[bytes, str]:
        """サムネイル用に小サイズ画像バイトを返す。

        Drive の thumbnailLink (既製の小サムネ) を優先し、グリッド表示でフル解像度を
        毎回 DL しないようにする。thumbnailLink は要認証なのでバックエンドで
        プロキシする。利用不可ならフル画像にフォールバック。
        """
        meta = self._get_metadata(file_id)
        mime = meta.get("mimeType", "")
        if mime not in SUPPORTED_IMAGE_MIMES:
            raise DriveError(f"未対応の形式です: {mime or 'unknown'}")

        thumbnail_link = meta.get("thumbnailLink")
        if thumbnail_link:
            session = self._get_session()
            response = session.get(thumbnail_link, params={}, timeout=REQUEST_TIMEOUT)
            if response.ok and response.content:
                content_type = response.headers.get("Content-Type", "image/jpeg")
                return response.content, content_type.split(";")[0].strip()

        content, full_mime, _ = self.download_file(file_id)
        return content, full_mime
