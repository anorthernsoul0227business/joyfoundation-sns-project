"""Google Drive 画像ピッカー API.

`/api/media/drive/*` 配下。共有フォルダ (サービスアカウントに共有済み) の
画像を一覧・サムネイル表示し、選択した画像を R2 にコピーして既存の
メディアアップロードと同じ `public_url` を返す。これにより投稿の storage_path は
従来どおり R2 の http URL となり、publisher と完全整合する。
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel

from app.api.media import MediaUploadItem
from app.config import Settings, get_settings
from app.core.security import CurrentUser, get_current_user
from app.services.drive import DriveClient, DriveError, DriveNotConfigured
from app.services.media_processor import (
    IG_OUTPUT_MIME,
    MediaProcessor,
    MediaProcessorError,
    MediaProcessorNotConfigured,
)
from app.services.sns_accounts import get_default_org_id_for_user

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_settings_dep() -> Settings:
    return get_settings()


def _get_drive_client(
    settings: Annotated[Settings, Depends(_get_settings_dep)],
) -> DriveClient:
    return DriveClient(settings)


def _get_processor(
    settings: Annotated[Settings, Depends(_get_settings_dep)],
) -> MediaProcessor:
    return MediaProcessor(settings)


class DriveFolder(BaseModel):
    id: str
    name: str


class DriveImage(BaseModel):
    id: str
    name: str
    mime_type: str
    width: int | None = None
    height: int | None = None


class DriveListResponse(BaseModel):
    folder_id: str
    folders: list[DriveFolder]
    images: list[DriveImage]


class DriveImportRequest(BaseModel):
    file_id: str
    auto_resize_ig: bool = False


def _drive_error_to_http(exc: DriveError) -> HTTPException:
    if isinstance(exc, DriveNotConfigured):
        logger.warning("Drive not configured: %s", exc)
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Drive 連携が設定されていません",
        )
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/list", response_model=DriveListResponse)
def list_drive_folder(
    _current_user: Annotated[CurrentUser, Depends(get_current_user)],
    drive: Annotated[DriveClient, Depends(_get_drive_client)],
    folder_id: Annotated[str | None, Query()] = None,
) -> DriveListResponse:
    try:
        result = drive.list_folder(folder_id)
    except DriveError as exc:
        raise _drive_error_to_http(exc) from exc
    return DriveListResponse(**result)


@router.get("/thumbnail/{file_id}")
def get_drive_thumbnail(
    _current_user: Annotated[CurrentUser, Depends(get_current_user)],
    drive: Annotated[DriveClient, Depends(_get_drive_client)],
    file_id: str,
) -> Response:
    try:
        content, mime = drive.get_thumbnail(file_id)
    except DriveError as exc:
        raise _drive_error_to_http(exc) from exc
    return Response(
        content=content,
        media_type=mime,
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.post(
    "/import",
    response_model=MediaUploadItem,
    status_code=status.HTTP_201_CREATED,
)
def import_drive_image(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    payload: DriveImportRequest,
    drive: Annotated[DriveClient, Depends(_get_drive_client)],
    processor: Annotated[MediaProcessor, Depends(_get_processor)],
) -> MediaUploadItem:
    try:
        file_bytes, mime, _name = drive.download_file(payload.file_id)
    except DriveError as exc:
        raise _drive_error_to_http(exc) from exc

    org_id = get_default_org_id_for_user(current_user.id)
    try:
        if payload.auto_resize_ig:
            file_bytes = processor.process_for_ig(file_bytes)
            mime = IG_OUTPUT_MIME
        public_url, storage_path, size = processor.upload_original(
            org_id=org_id,
            file_bytes=file_bytes,
            mime=mime,
        )
    except MediaProcessorNotConfigured as exc:
        logger.warning("Drive import rejected: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Media storage is not configured",
        ) from exc
    except MediaProcessorError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return MediaUploadItem(
        public_url=public_url,
        storage_path=storage_path,
        width=size[0],
        height=size[1],
        mime_type=mime,
    )
