from __future__ import annotations

import pytest
import responses

from app.services.publisher.ig_publisher import GRAPH_API_BASE_URL, IgPublisher


@pytest.fixture
def publisher(monkeypatch: pytest.MonkeyPatch) -> IgPublisher:
    monkeypatch.setattr("app.services.publisher.ig_publisher.time.sleep", lambda _: None)
    return IgPublisher()


def build_account(
    *,
    access_token: str = "ig-long-lived-token",
    platform_account_id: str = "178414",
) -> dict[str, str]:
    return {
        "access_token": access_token,
        "platform_account_id": platform_account_id,
    }


def _status_url(container_id: str) -> str:
    return f"{GRAPH_API_BASE_URL}/{container_id}"


def _media_url(account_id: str = "178414") -> str:
    return f"{GRAPH_API_BASE_URL}/{account_id}/media"


def _publish_url(account_id: str = "178414") -> str:
    return f"{GRAPH_API_BASE_URL}/{account_id}/media_publish"


@responses.activate
def test_publish_single_image_success(publisher: IgPublisher) -> None:
    responses.post(_media_url(), json={"id": "container-1"}, status=200)
    responses.get(_status_url("container-1"), json={"status_code": "FINISHED"}, status=200)
    responses.post(_publish_url(), json={"id": "ig-post-1"}, status=200)

    result = publisher.publish(
        text="caption",
        image_urls=["https://cdn.example.com/a.jpg"],
        account=build_account(),
    )

    assert result.success is True
    assert result.platform_post_id == "ig-post-1"


@responses.activate
def test_publish_carousel_success(publisher: IgPublisher) -> None:
    responses.post(_media_url(), json={"id": "child-1"}, status=200)
    responses.post(_media_url(), json={"id": "child-2"}, status=200)
    responses.post(_media_url(), json={"id": "child-3"}, status=200)
    responses.post(_media_url(), json={"id": "parent-1"}, status=200)
    responses.get(_status_url("parent-1"), json={"status_code": "FINISHED"}, status=200)
    responses.post(_publish_url(), json={"id": "ig-post-2"}, status=200)

    result = publisher.publish(
        text="caption",
        image_urls=[
            "https://cdn.example.com/a.jpg",
            "https://cdn.example.com/b.jpg",
            "https://cdn.example.com/c.jpg",
        ],
        account=build_account(),
    )

    assert result.success is True
    assert result.platform_post_id == "ig-post-2"
    assert len(responses.calls) == 6
    parent_request = responses.calls[3].request
    request_body = (
        parent_request.body.decode()
        if isinstance(parent_request.body, bytes)
        else str(parent_request.body)
    )
    assert "media_type=CAROUSEL" in request_body
    assert "children=child-1%2Cchild-2%2Cchild-3" in request_body


def test_publish_fails_with_zero_images(publisher: IgPublisher) -> None:
    result = publisher.publish(text="caption", image_urls=[], account=build_account())

    assert result.success is False
    assert result.error_message == "IG requires at least one image"


def test_publish_fails_with_more_than_ten_images(publisher: IgPublisher) -> None:
    result = publisher.publish(
        text="caption",
        image_urls=[f"https://cdn.example.com/{index}.jpg" for index in range(11)],
        account=build_account(),
    )

    assert result.success is False
    assert result.error_message == "IG carousel supports up to 10 images"


@responses.activate
def test_publish_polls_until_container_finishes(publisher: IgPublisher) -> None:
    responses.post(_media_url(), json={"id": "container-2"}, status=200)
    responses.get(_status_url("container-2"), json={"status_code": "IN_PROGRESS"}, status=200)
    responses.get(_status_url("container-2"), json={"status_code": "IN_PROGRESS"}, status=200)
    responses.get(_status_url("container-2"), json={"status_code": "FINISHED"}, status=200)
    responses.post(_publish_url(), json={"id": "ig-post-3"}, status=200)

    result = publisher.publish(
        text="caption",
        image_urls=["https://cdn.example.com/a.jpg"],
        account=build_account(),
    )

    assert result.success is True
    assert result.platform_post_id == "ig-post-3"


@responses.activate
def test_publish_fails_when_container_status_is_error(publisher: IgPublisher) -> None:
    responses.post(_media_url(), json={"id": "container-3"}, status=200)
    responses.get(_status_url("container-3"), json={"status_code": "ERROR"}, status=200)

    result = publisher.publish(
        text="caption",
        image_urls=["https://cdn.example.com/a.jpg"],
        account=build_account(),
    )

    assert result.success is False
    assert result.error_message == "IG media container processing failed"


def test_publish_fails_when_access_token_missing(publisher: IgPublisher) -> None:
    result = publisher.publish(
        text="caption",
        image_urls=["https://cdn.example.com/a.jpg"],
        account={"platform_account_id": "178414"},
    )

    assert result.success is False
    assert result.error_message == "IG account access token is missing"


def test_publish_fails_when_platform_account_id_missing(publisher: IgPublisher) -> None:
    result = publisher.publish(
        text="caption",
        image_urls=["https://cdn.example.com/a.jpg"],
        account={"access_token": "ig-token"},
    )

    assert result.success is False
    assert result.error_message == "IG platform account id is missing"


@responses.activate
def test_publish_returns_failure_for_4xx(publisher: IgPublisher) -> None:
    responses.post(
        _media_url(),
        json={"error": {"message": "Invalid OAuth access token."}},
        status=401,
    )

    result = publisher.publish(
        text="caption",
        image_urls=["https://cdn.example.com/a.jpg"],
        account=build_account(),
    )

    assert result.success is False
    assert "401" in (result.error_message or "")
    assert "Invalid OAuth access token." in (result.error_message or "")


@responses.activate
def test_publish_fails_when_container_never_finishes(publisher: IgPublisher) -> None:
    responses.post(_media_url(), json={"id": "container-4"}, status=200)
    for _ in range(5):
        responses.get(_status_url("container-4"), json={"status_code": "IN_PROGRESS"}, status=200)

    result = publisher.publish(
        text="caption",
        image_urls=["https://cdn.example.com/a.jpg"],
        account=build_account(),
    )

    assert result.success is False
    assert result.error_message == "IG media container did not finish processing"
