from __future__ import annotations

import io
from typing import Any
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws
from PIL import Image

from app.config import Settings
from app.services.media_processor import (
    IG_TARGET_HEIGHT,
    IG_TARGET_WIDTH,
    MediaProcessor,
    MediaProcessorError,
    MediaProcessorNotConfigured,
)


def _settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "R2_ACCOUNT_ID": "test-account",
        "R2_ACCESS_KEY_ID": "test-key",
        "R2_SECRET_ACCESS_KEY": "test-secret",
        "R2_BUCKET_NAME": "test-bucket",
        "R2_PUBLIC_URL": "https://cdn.example.com/media",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)


def _make_image(width: int, height: int, *, mode: str = "RGB", fmt: str = "JPEG") -> bytes:
    colour = (30, 200, 120) if mode == "RGB" else (30, 200, 120, 128)
    img = Image.new(mode, (width, height), colour)
    buf = io.BytesIO()
    save_kwargs: dict[str, Any] = {}
    if fmt == "JPEG":
        save_kwargs["quality"] = 85
        if mode != "RGB":
            img = img.convert("RGB")
    img.save(buf, format=fmt, **save_kwargs)
    return buf.getvalue()


def _read_size(data: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(data)) as img:
        return img.size


def test_process_for_ig_landscape_pads_to_4x5() -> None:
    processor = MediaProcessor(_settings())
    source = _make_image(1600, 900, mode="RGB", fmt="JPEG")

    result = processor.process_for_ig(source)

    assert _read_size(result) == (IG_TARGET_WIDTH, IG_TARGET_HEIGHT)


def test_process_for_ig_portrait_pads_to_4x5() -> None:
    processor = MediaProcessor(_settings())
    source = _make_image(600, 1600, mode="RGB", fmt="JPEG")

    result = processor.process_for_ig(source)

    assert _read_size(result) == (IG_TARGET_WIDTH, IG_TARGET_HEIGHT)


def test_process_for_ig_already_target_ratio() -> None:
    processor = MediaProcessor(_settings())
    source = _make_image(IG_TARGET_WIDTH, IG_TARGET_HEIGHT, mode="RGB", fmt="JPEG")

    result = processor.process_for_ig(source)

    assert _read_size(result) == (IG_TARGET_WIDTH, IG_TARGET_HEIGHT)


def test_process_for_ig_accepts_png_source() -> None:
    processor = MediaProcessor(_settings())
    source = _make_image(900, 900, mode="RGB", fmt="PNG")

    result = processor.process_for_ig(source)

    with Image.open(io.BytesIO(result)) as img:
        assert img.size == (IG_TARGET_WIDTH, IG_TARGET_HEIGHT)
        assert img.format == "JPEG"


def test_process_for_ig_rgba_uses_white_background() -> None:
    processor = MediaProcessor(_settings())
    img = Image.new("RGBA", (1080, 1080), (10, 10, 10, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    result = processor.process_for_ig(buf.getvalue())

    with Image.open(io.BytesIO(result)) as out:
        assert out.mode == "RGB"
        # top-left corner should be white padding since source is smaller than target width
        assert out.getpixel((0, 0)) == (255, 255, 255)


def test_process_for_ig_rejects_unidentifiable_bytes() -> None:
    processor = MediaProcessor(_settings())

    with pytest.raises(MediaProcessorError):
        processor.process_for_ig(b"not an image")


def test_upload_original_stores_object_and_returns_public_url() -> None:
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")

        processor = MediaProcessor(_settings(), s3_client=s3)
        org_id = str(uuid4())
        payload = _make_image(800, 600, fmt="JPEG")

        public_url, storage_path, (width, height) = processor.upload_original(
            org_id=org_id,
            file_bytes=payload,
            mime="image/jpeg",
        )

        assert public_url.startswith("https://cdn.example.com/media/post-media/")
        assert storage_path.startswith(f"post-media/{org_id}/")
        assert storage_path.endswith(".jpg")
        assert public_url.endswith(storage_path)
        assert (width, height) == (800, 600)

        listing = s3.list_objects_v2(Bucket="test-bucket")
        assert listing["KeyCount"] == 1
        stored = s3.get_object(Bucket="test-bucket", Key=storage_path)
        assert stored["ContentType"] == "image/jpeg"
        assert stored["Body"].read() == payload


def test_upload_original_rejects_unsupported_mime() -> None:
    processor = MediaProcessor(_settings(), s3_client=object())

    with pytest.raises(MediaProcessorError):
        processor.upload_original(
            org_id=str(uuid4()),
            file_bytes=_make_image(100, 100, fmt="JPEG"),
            mime="image/tiff",
        )


def test_upload_original_requires_r2_settings() -> None:
    processor = MediaProcessor(_settings(R2_ACCOUNT_ID=None))

    with pytest.raises(MediaProcessorNotConfigured):
        processor.upload_original(
            org_id=str(uuid4()),
            file_bytes=_make_image(100, 100, fmt="JPEG"),
            mime="image/jpeg",
        )


def test_delete_is_noop_when_storage_path_empty() -> None:
    processor = MediaProcessor(_settings(), s3_client=object())
    processor.delete("")


def test_delete_swallows_errors() -> None:
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")

        class _FailingClient:
            def delete_object(self, **_: Any) -> None:
                raise ClientError({"Error": {"Code": "500"}}, "DeleteObject")

        processor = MediaProcessor(_settings(), s3_client=_FailingClient())
        # Must not raise
        processor.delete("post-media/xxx.jpg")
