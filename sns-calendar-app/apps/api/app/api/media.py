"""画像アップロード API (WEB-024).

`POST /api/media/upload` はフロントから multipart/form-data で送られた画像を
Cloudflare R2 に保存し、`post_media.storage_path` に入れる公開URLを返す。
`auto_resize_ig=true` 指定時は IG 向けに 4:5 白余白パディングしてから保存する。
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, ConfigDict

from app.core.security import CurrentUser, get_current_user
from app.services.media_processor import (
    IG_OUTPUT_MIME,
    SUPPORTED_MIME_TYPES,
    MediaProcessor,
    MediaProcessorError,
    MediaProcessorNotConfigured,
)
from app.services.sns_accounts import get_default_org_id_for_user

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB per file (IG カルーセル単体上限)
MAX_FILES_PER_REQUEST = 10


class MediaUploadItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_url: str
    storage_path: str
    width: int
    height: int
    mime_type: str


class MediaUploadResponse(BaseModel):
    media: list[MediaUploadItem]


def _get_processor() -> MediaProcessor:
    from app.config import get_settings

    return MediaProcessor(get_settings())


@router.post(
    "/upload",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_media(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    files: Annotated[list[UploadFile], File(description="1-10 枚の画像")],
    processor: Annotated[MediaProcessor, Depends(_get_processor)],
    auto_resize_ig: Annotated[bool, Query()] = False,
) -> MediaUploadResponse:
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files were provided",
        )
    if len(files) > MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files: {len(files)} > {MAX_FILES_PER_REQUEST}",
        )

    org_id = get_default_org_id_for_user(current_user.id)

    items: list[MediaUploadItem] = []
    for upload in files:
        payload = await upload.read()
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{upload.filename}' is empty",
            )
        if len(payload) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"File '{upload.filename}' exceeds {MAX_FILE_SIZE} bytes"
                ),
            )

        declared_mime = (upload.content_type or "").lower()
        if declared_mime not in SUPPORTED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported mime type: {declared_mime or 'unknown'}",
            )

        try:
            if auto_resize_ig:
                processed_bytes = processor.process_for_ig(payload)
                public_url, storage_path, size = processor.upload_original(
                    org_id=org_id,
                    file_bytes=processed_bytes,
                    mime=IG_OUTPUT_MIME,
                )
                resulting_mime = IG_OUTPUT_MIME
            else:
                public_url, storage_path, size = processor.upload_original(
                    org_id=org_id,
                    file_bytes=payload,
                    mime=declared_mime,
                )
                resulting_mime = declared_mime
        except MediaProcessorNotConfigured as exc:
            logger.warning("Media upload rejected: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Media storage is not configured",
            ) from exc
        except MediaProcessorError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        items.append(
            MediaUploadItem(
                public_url=public_url,
                storage_path=storage_path,
                width=size[0],
                height=size[1],
                mime_type=resulting_mime,
            )
        )

    return MediaUploadResponse(media=items)
