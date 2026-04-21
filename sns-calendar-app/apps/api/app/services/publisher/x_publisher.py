from __future__ import annotations

import logging
import mimetypes
from os.path import basename
from typing import Any

import requests
from requests_oauthlib import OAuth1

from .base import Publisher, PublishResult

logger = logging.getLogger(__name__)

MEDIA_UPLOAD_URL = "https://upload.twitter.com/1.1/media/upload.json"
TWEET_CREATE_URL = "https://api.x.com/2/tweets"
REQUEST_TIMEOUT_SECONDS = 30


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
        detail = data.get("detail")
        if detail:
            return str(detail)
        errors = data.get("errors")
        if isinstance(errors, list) and errors:
            first = errors[0]
            if isinstance(first, dict):
                return str(first.get("message") or first.get("detail") or first)
            return str(first)
    if data is not None:
        return str(data)
    return "empty response body"


class XPublisher(Publisher):
    platform = "x"

    def __init__(self, *, consumer_key: str, consumer_secret: str) -> None:
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret

    def publish(
        self,
        *,
        text: str,
        image_urls: list[str],
        account: dict[str, Any],
        options: dict[str, Any] | None = None,
    ) -> PublishResult:
        try:
            auth = self._build_auth(account)
        except ValueError as exc:
            return PublishResult(
                success=False,
                platform_post_id=None,
                error_message=str(exc),
            )

        media_ids = []
        for image_url in image_urls:
            media_id = self._upload_media(image_url=image_url, auth=auth)
            if media_id:
                media_ids.append(media_id)

        payload: dict[str, Any] = {"text": text}
        if media_ids:
            payload["media"] = {"media_ids": media_ids}

        reply_to = (options or {}).get("reply_to")
        if reply_to:
            payload["reply"] = {"in_reply_to_tweet_id": reply_to}

        try:
            response = requests.post(
                TWEET_CREATE_URL,
                auth=auth,
                json=payload,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            logger.error("X publish request failed: %s", exc.__class__.__name__)
            return PublishResult(
                success=False,
                platform_post_id=None,
                error_message=f"X publish request failed: {exc}",
            )

        request_id = response.headers.get("x-request-id", "-")
        if response.status_code not in (200, 201):
            logger.warning(
                "X publish failed status=%s request_id=%s",
                response.status_code,
                request_id,
            )
            return PublishResult(
                success=False,
                platform_post_id=None,
                error_message=(
                    f"X publish failed with status {response.status_code}: "
                    f"{_extract_error_summary(response)}"
                ),
            )

        data = _parse_json_safely(response)
        tweet_id = None
        if isinstance(data, dict):
            tweet_id = (data.get("data") or {}).get("id")
        if not tweet_id:
            logger.warning(
                "X publish missing tweet id status=%s request_id=%s",
                response.status_code,
                request_id,
            )
            return PublishResult(
                success=False,
                platform_post_id=None,
                error_message="X publish succeeded but tweet id was missing",
            )

        logger.info(
            "X publish succeeded tweet_id=%s status=%s request_id=%s",
            tweet_id,
            response.status_code,
            request_id,
        )
        return PublishResult(
            success=True,
            platform_post_id=str(tweet_id),
            error_message=None,
            extra={"media_count": len(media_ids)},
        )

    def _build_auth(self, account: dict[str, Any]) -> OAuth1:
        raw_access_token = account.get("access_token")
        if not raw_access_token:
            raise ValueError("X account access token is missing")

        oauth_token, separator, oauth_token_secret = str(raw_access_token).partition(":")
        if separator != ":" or not oauth_token or not oauth_token_secret:
            raise ValueError("X account access token is malformed")

        return OAuth1(
            self._consumer_key,
            self._consumer_secret,
            oauth_token,
            oauth_token_secret,
        )

    def _upload_media(self, *, image_url: str, auth: OAuth1) -> str | None:
        try:
            download_response = requests.get(image_url, timeout=REQUEST_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            logger.warning("Image download failed url=%s error=%s", image_url, exc.__class__.__name__)
            return None

        if download_response.status_code != 200:
            logger.warning(
                "Image download failed status=%s url=%s",
                download_response.status_code,
                image_url,
            )
            return None

        media_type = download_response.headers.get("Content-Type") or mimetypes.guess_type(image_url)[0]
        if not media_type:
            media_type = "application/octet-stream"

        filename = basename(image_url.split("?", 1)[0]) or "upload.bin"
        try:
            upload_response = requests.post(
                MEDIA_UPLOAD_URL,
                auth=auth,
                files={"media": (filename, download_response.content, media_type)},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            logger.warning("Image upload failed url=%s error=%s", image_url, exc.__class__.__name__)
            return None

        request_id = upload_response.headers.get("x-request-id", "-")
        if upload_response.status_code not in (200, 201):
            logger.warning(
                "Image upload failed status=%s request_id=%s",
                upload_response.status_code,
                request_id,
            )
            return None

        payload = _parse_json_safely(upload_response)
        if not isinstance(payload, dict) or not payload.get("media_id_string"):
            logger.warning(
                "Image upload response missing media id status=%s request_id=%s",
                upload_response.status_code,
                request_id,
            )
            return None

        media_id = str(payload["media_id_string"])
        logger.info(
            "Image upload succeeded media_id=%s status=%s request_id=%s",
            media_id,
            upload_response.status_code,
            request_id,
        )
        return media_id
