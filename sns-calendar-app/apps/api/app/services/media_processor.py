"""画像アップロード + IG向けリサイズサービス (WEB-024).

Cloudflare R2 (S3互換) に公開配信用画像を保存し、公開URLと
ストレージパスを返す。IG向けは 4:5 (1080x1350) 白余白パディング。
"""

from __future__ import annotations

import io
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import Settings

logger = logging.getLogger(__name__)

IG_TARGET_WIDTH = 1080
IG_TARGET_HEIGHT = 1350
IG_BG_COLOR = (255, 255, 255)
IG_JPEG_QUALITY = 90
IG_OUTPUT_MIME = "image/jpeg"

SUPPORTED_MIME_TYPES = frozenset(
    {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
    }
)

_EXT_BY_MIME = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class MediaProcessorError(RuntimeError):
    """MediaProcessor 内の回復不能エラー."""


class MediaProcessorNotConfigured(MediaProcessorError):
    """R2 資格情報が揃っていない."""


class MediaProcessor:
    """Cloudflare R2 に画像をアップロード / 削除 / IG向けリサイズ."""

    def __init__(self, settings: Settings, *, s3_client: Any | None = None) -> None:
        self._settings = settings
        self._s3_client_override = s3_client

    def _client(self) -> Any:
        if self._s3_client_override is not None:
            return self._s3_client_override
        settings = self._settings
        if not (
            settings.r2_account_id
            and settings.r2_access_key_id
            and settings.r2_secret_access_key is not None
            and settings.r2_bucket_name
            and settings.r2_public_url
        ):
            raise MediaProcessorNotConfigured("R2 credentials are not configured")
        endpoint_url = f"https://{settings.r2_account_id}.r2.cloudflarestorage.com"
        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
            region_name="auto",
        )

    def process_for_ig(self, file_bytes: bytes) -> bytes:
        """入力画像を 4:5 白余白パディングして JPEG bytes を返す."""
        try:
            source = Image.open(io.BytesIO(file_bytes))
            source.load()
        except (UnidentifiedImageError, OSError) as exc:
            raise MediaProcessorError(f"Unsupported or corrupt image: {exc}") from exc

        img = ImageOps.exif_transpose(source) or source

        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, IG_BG_COLOR)
            if img.mode == "P":
                img = img.convert("RGBA")
            if "A" in img.getbands():
                alpha = img.split()[-1]
                background.paste(img.convert("RGB"), mask=alpha)
            else:
                background.paste(img)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        img_w, img_h = img.size
        scale = min(IG_TARGET_WIDTH / img_w, IG_TARGET_HEIGHT / img_h)
        new_w = max(1, int(img_w * scale))
        new_h = max(1, int(img_h * scale))
        resized = img.resize((new_w, new_h), Image.LANCZOS)

        canvas = Image.new("RGB", (IG_TARGET_WIDTH, IG_TARGET_HEIGHT), IG_BG_COLOR)
        canvas.paste(
            resized,
            ((IG_TARGET_WIDTH - new_w) // 2, (IG_TARGET_HEIGHT - new_h) // 2),
        )

        output = io.BytesIO()
        canvas.save(output, format="JPEG", quality=IG_JPEG_QUALITY)
        return output.getvalue()

    def upload_original(
        self,
        *,
        org_id: str,
        file_bytes: bytes,
        mime: str,
    ) -> tuple[str, str, tuple[int, int]]:
        """R2 に保存して (public_url, storage_path, (width, height)) を返す."""
        normalized_mime = mime.lower()
        if normalized_mime not in SUPPORTED_MIME_TYPES:
            raise MediaProcessorError(f"Unsupported mime type: {mime}")

        try:
            with Image.open(io.BytesIO(file_bytes)) as probe:
                width, height = probe.size
        except (UnidentifiedImageError, OSError) as exc:
            raise MediaProcessorError(f"Invalid image payload: {exc}") from exc

        ext = _EXT_BY_MIME[normalized_mime]
        now = datetime.now(UTC)
        object_key = (
            f"post-media/{org_id}/{now:%Y/%m/%d}/{uuid.uuid4().hex}.{ext}"
        )

        client = self._client()
        bucket = self._settings.r2_bucket_name
        public_base = self._settings.r2_public_url or ""

        try:
            client.put_object(
                Bucket=bucket,
                Key=object_key,
                Body=file_bytes,
                ContentType=normalized_mime,
                CacheControl="public, max-age=600",
            )
        except (BotoCoreError, ClientError) as exc:
            logger.warning("R2 upload failed for key=%s: %s", object_key, exc)
            raise MediaProcessorError("R2 upload failed") from exc

        public_url = f"{public_base.rstrip('/')}/{object_key}"
        return public_url, object_key, (width, height)

    def delete(self, storage_path: str) -> None:
        """R2 から削除。失敗は握り潰して warning ログ."""
        if not storage_path:
            return
        try:
            client = self._client()
            client.delete_object(
                Bucket=self._settings.r2_bucket_name,
                Key=storage_path,
            )
        except MediaProcessorNotConfigured:
            logger.warning("R2 delete skipped (unconfigured) for key=%s", storage_path)
        except (BotoCoreError, ClientError) as exc:
            logger.warning("R2 delete failed for key=%s: %s", storage_path, exc)
