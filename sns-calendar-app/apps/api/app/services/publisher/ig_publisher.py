from __future__ import annotations

import logging
import time
from typing import Any

import requests

from .base import Publisher, PublishResult

logger = logging.getLogger(__name__)

GRAPH_API_BASE_URL = "https://graph.facebook.com/v19.0"
REQUEST_TIMEOUT_SECONDS = 30
MAX_CONTAINER_STATUS_POLLS = 5
CONTAINER_STATUS_POLL_INTERVAL_SECONDS = 1


def _parse_json_safely(response: requests.Response) -> Any:
    body = (response.text or "").strip()
    if not body:
        return None
    try:
        return response.json()
    except ValueError:
        return None


def _extract_error_summary(response: requests.Response) -> str:
    data = _parse_json_safely(response)
    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if message:
                return str(message)
        message = data.get("message")
        if message:
            return str(message)
    if data is not None:
        return str(data)
    return "empty response body"


class IgPublisher(Publisher):
    platform = "ig"

    def publish(
        self,
        *,
        text: str,
        image_urls: list[str],
        account: dict[str, Any],
        options: dict[str, Any] | None = None,
    ) -> PublishResult:
        access_token = account.get("access_token")
        if not access_token:
            return PublishResult(
                success=False,
                platform_post_id=None,
                error_message="IG account access token is missing",
            )

        ig_account_id = account.get("platform_account_id")
        if not ig_account_id:
            return PublishResult(
                success=False,
                platform_post_id=None,
                error_message="IG platform account id is missing",
            )

        if not image_urls:
            return PublishResult(
                success=False,
                platform_post_id=None,
                error_message="IG requires at least one image",
            )

        if len(image_urls) > 10:
            return PublishResult(
                success=False,
                platform_post_id=None,
                error_message="IG carousel supports up to 10 images",
            )

        try:
            if len(image_urls) == 1:
                container_id = self._create_media_container(
                    ig_account_id=str(ig_account_id),
                    access_token=str(access_token),
                    image_url=image_urls[0],
                    caption=text,
                )
            else:
                container_id = self._create_carousel_container(
                    ig_account_id=str(ig_account_id),
                    access_token=str(access_token),
                    image_urls=image_urls,
                    caption=text,
                )

            if not self._wait_until_container_finished(
                container_id=container_id,
                access_token=str(access_token),
            ):
                return PublishResult(
                    success=False,
                    platform_post_id=None,
                    error_message="IG media container did not finish processing",
                )

            post_id = self._publish_media(
                ig_account_id=str(ig_account_id),
                access_token=str(access_token),
                creation_id=container_id,
            )
        except requests.RequestException as exc:
            logger.warning("IG publish request failed: %s", exc.__class__.__name__)
            return PublishResult(
                success=False,
                platform_post_id=None,
                error_message=f"IG publish request failed: {exc}",
            )
        except ValueError as exc:
            return PublishResult(
                success=False,
                platform_post_id=None,
                error_message=str(exc),
            )

        return PublishResult(
            success=True,
            platform_post_id=post_id,
            error_message=None,
        )

    def _create_media_container(
        self,
        *,
        ig_account_id: str,
        access_token: str,
        image_url: str,
        caption: str | None = None,
        is_carousel_item: bool = False,
        children: list[str] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "access_token": access_token,
        }
        if children:
            payload["media_type"] = "CAROUSEL"
            payload["children"] = ",".join(children)
            payload["caption"] = caption or ""
        else:
            payload["image_url"] = image_url
            if is_carousel_item:
                payload["is_carousel_item"] = "true"
            else:
                payload["caption"] = caption or ""

        response = requests.post(
            f"{GRAPH_API_BASE_URL}/{ig_account_id}/media",
            data=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code not in (200, 201):
            raise ValueError(
                f"IG media creation failed with status {response.status_code}: "
                f"{_extract_error_summary(response)}"
            )

        data = _parse_json_safely(response)
        container_id = data.get("id") if isinstance(data, dict) else None
        if not container_id:
            raise ValueError("IG media creation succeeded but container id was missing")
        return str(container_id)

    def _create_carousel_container(
        self,
        *,
        ig_account_id: str,
        access_token: str,
        image_urls: list[str],
        caption: str,
    ) -> str:
        child_container_ids: list[str] = []
        for image_url in image_urls:
            child_container_ids.append(
                self._create_media_container(
                    ig_account_id=ig_account_id,
                    access_token=access_token,
                    image_url=image_url,
                    is_carousel_item=True,
                )
            )

        return self._create_media_container(
            ig_account_id=ig_account_id,
            access_token=access_token,
            image_url="",
            caption=caption,
            children=child_container_ids,
        )

    def _wait_until_container_finished(
        self,
        *,
        container_id: str,
        access_token: str,
    ) -> bool:
        for attempt in range(MAX_CONTAINER_STATUS_POLLS):
            response = requests.get(
                f"{GRAPH_API_BASE_URL}/{container_id}",
                params={
                    "fields": "status_code",
                    "access_token": access_token,
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            if response.status_code != 200:
                raise ValueError(
                    f"IG container status check failed with status {response.status_code}: "
                    f"{_extract_error_summary(response)}"
                )

            data = _parse_json_safely(response)
            status_code = data.get("status_code") if isinstance(data, dict) else None
            if status_code == "FINISHED":
                return True
            if status_code == "ERROR":
                raise ValueError("IG media container processing failed")
            if attempt < MAX_CONTAINER_STATUS_POLLS - 1:
                time.sleep(CONTAINER_STATUS_POLL_INTERVAL_SECONDS)
        return False

    def _publish_media(
        self,
        *,
        ig_account_id: str,
        access_token: str,
        creation_id: str,
    ) -> str:
        response = requests.post(
            f"{GRAPH_API_BASE_URL}/{ig_account_id}/media_publish",
            data={
                "creation_id": creation_id,
                "access_token": access_token,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code not in (200, 201):
            raise ValueError(
                f"IG publish failed with status {response.status_code}: "
                f"{_extract_error_summary(response)}"
            )

        data = _parse_json_safely(response)
        post_id = data.get("id") if isinstance(data, dict) else None
        if not post_id:
            raise ValueError("IG publish succeeded but post id was missing")
        return str(post_id)
