from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.publisher.base import PublishResult
from app.services.publisher.orchestrator import PublishStore, publish_target


@dataclass
class InMemoryPublishStore(PublishStore):
    posts: dict[str, dict] = field(default_factory=dict)
    targets: dict[str, dict] = field(default_factory=dict)
    media: list[dict] = field(default_factory=list)
    accounts: list[dict] = field(default_factory=list)

    def get_target(self, target_id: str) -> dict | None:
        return self.targets.get(target_id)

    def get_post(self, post_id: str) -> dict | None:
        return self.posts.get(post_id)

    def list_media(self, post_id: str, limit: int = 4) -> list[dict]:
        rows = [row for row in self.media if row["post_id"] == post_id]
        rows.sort(key=lambda row: row.get("sort_order", 0))
        return rows[:limit]

    def get_active_account(self, *, org_id: str, platform: str) -> dict | None:
        rows = [
            row
            for row in self.accounts
            if row["org_id"] == org_id
            and row["platform"] == platform
            and row["is_active"] is True
        ]
        rows.sort(key=lambda row: row["created_at"], reverse=True)
        return rows[0] if rows else None

    def update_target(self, target_id: str, updates: dict) -> None:
        self.targets[target_id].update(updates)

    def list_targets(self, post_id: str) -> list[dict]:
        return [row for row in self.targets.values() if row["post_id"] == post_id]

    def update_post(self, post_id: str, updates: dict) -> None:
        self.posts[post_id].update(updates)


@pytest.fixture
def publish_store() -> InMemoryPublishStore:
    now = datetime.now(UTC).isoformat()
    post_id = str(uuid4())
    target_id = str(uuid4())
    sibling_target_id = str(uuid4())
    org_id = str(uuid4())
    return InMemoryPublishStore(
        posts={
            post_id: {
                "id": post_id,
                "org_id": org_id,
                "content_text": "hello world",
                "status": "scheduled",
                "published_at": None,
            }
        },
        targets={
            target_id: {
                "id": target_id,
                "post_id": post_id,
                "platform": "x",
                "status": "scheduled",
                "platform_post_id": None,
                "published_at": None,
                "error_message": None,
            },
            sibling_target_id: {
                "id": sibling_target_id,
                "post_id": post_id,
                "platform": "x",
                "status": "scheduled",
                "platform_post_id": None,
                "published_at": None,
                "error_message": None,
            },
        },
        media=[
            {
                "post_id": post_id,
                "storage_path": "https://cdn.example.com/a.jpg",
                "sort_order": 2,
            },
            {
                "post_id": post_id,
                "storage_path": "not-http",
                "sort_order": 1,
            },
        ],
        accounts=[
            {
                "org_id": org_id,
                "platform": "x",
                "is_active": True,
                "access_token": "token:secret",
                "created_at": now,
            }
        ],
    )


def test_publish_target_reads_rows_and_marks_target_published(
    publish_store: InMemoryPublishStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_id = next(iter(publish_store.targets))
    calls: dict[str, object] = {}

    class FakePublisher:
        def publish(self, *, text: str, image_urls: list[str], account: dict, options: dict | None = None) -> PublishResult:
            calls["text"] = text
            calls["image_urls"] = image_urls
            calls["account"] = account
            calls["options"] = options
            return PublishResult(success=True, platform_post_id="tweet-1", error_message=None)

    monkeypatch.setattr(
        "app.services.publisher.orchestrator.get_publisher",
        lambda platform: FakePublisher(),
    )

    result = publish_target(target_id, store=publish_store)

    assert result.success is True
    assert calls["text"] == "hello world"
    assert calls["image_urls"] == ["https://cdn.example.com/a.jpg"]
    assert publish_store.targets[target_id]["status"] == "published"
    assert publish_store.targets[target_id]["platform_post_id"] == "tweet-1"


def test_publish_target_marks_parent_post_published_when_all_targets_done(
    publish_store: InMemoryPublishStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_ids = list(publish_store.targets)
    publish_store.targets[target_ids[1]]["status"] = "published"
    monkeypatch.setattr(
        "app.services.publisher.orchestrator.get_publisher",
        lambda platform: type(
            "FakePublisher",
            (),
            {
                "publish": lambda self, **kwargs: PublishResult(
                    success=True,
                    platform_post_id="tweet-2",
                    error_message=None,
                )
            },
        )(),
    )

    publish_target(target_ids[0], store=publish_store)

    post = next(iter(publish_store.posts.values()))
    assert post["status"] == "published"
    assert post["published_at"] is not None


def test_publish_target_marks_failed_when_no_active_account(
    publish_store: InMemoryPublishStore,
) -> None:
    target_id = next(iter(publish_store.targets))
    publish_store.accounts.clear()

    result = publish_target(target_id, store=publish_store)

    assert result.success is False
    assert result.error_message == "No active X account connected"
    assert publish_store.targets[target_id]["status"] == "failed"


def test_publish_target_marks_failed_when_no_active_ig_account(
    publish_store: InMemoryPublishStore,
) -> None:
    target_id = next(iter(publish_store.targets))
    publish_store.targets[target_id]["platform"] = "ig"
    publish_store.accounts.clear()

    result = publish_target(target_id, store=publish_store)

    assert result.success is False
    assert result.error_message == "No active IG account connected"
    assert publish_store.targets[target_id]["status"] == "failed"


def test_publish_target_is_idempotent_when_already_publishing(
    publish_store: InMemoryPublishStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_id = next(iter(publish_store.targets))
    publish_store.targets[target_id]["status"] = "publishing"
    monkeypatch.setattr(
        "app.services.publisher.orchestrator.get_publisher",
        lambda platform: pytest.fail("publisher should not be called"),
    )

    result = publish_target(target_id, store=publish_store)

    assert result.success is True
    assert result.extra == {"status": "publishing"}


def test_publish_target_wraps_unexpected_exceptions_and_updates_target(
    publish_store: InMemoryPublishStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_id = next(iter(publish_store.targets))

    class ExplodingPublisher:
        def publish(self, **kwargs: object) -> PublishResult:
            raise RuntimeError("boom")

    monkeypatch.setattr(
        "app.services.publisher.orchestrator.get_publisher",
        lambda platform: ExplodingPublisher(),
    )

    result = publish_target(target_id, store=publish_store)

    assert result.success is False
    assert "boom" in (result.error_message or "")
    assert publish_store.targets[target_id]["status"] == "failed"


def test_publish_target_raises_404_when_target_missing() -> None:
    with pytest.raises(HTTPException) as exc_info:
        publish_target(str(uuid4()), store=InMemoryPublishStore())

    assert exc_info.value.status_code == 404


def test_publish_target_passes_platform_account_id_to_ig_publisher(
    publish_store: InMemoryPublishStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_id = next(iter(publish_store.targets))
    post_id = publish_store.targets[target_id]["post_id"]
    publish_store.targets[target_id]["platform"] = "ig"
    publish_store.media = [
        {
            "post_id": post_id,
            "storage_path": f"https://cdn.example.com/{index}.jpg",
            "sort_order": index,
        }
        for index in range(1, 6)
    ]
    publish_store.accounts = [
        {
            "org_id": publish_store.posts[post_id]["org_id"],
            "platform": "ig",
            "is_active": True,
            "access_token": "ig-token",
            "platform_account_id": "178414",
            "created_at": datetime.now(UTC).isoformat(),
        }
    ]
    calls: dict[str, object] = {}

    class FakePublisher:
        def publish(self, *, text: str, image_urls: list[str], account: dict, options: dict | None = None) -> PublishResult:
            calls["text"] = text
            calls["image_urls"] = image_urls
            calls["account"] = account
            calls["options"] = options
            return PublishResult(success=True, platform_post_id="ig-post-1", error_message=None)

    monkeypatch.setattr(
        "app.services.publisher.orchestrator.get_publisher",
        lambda platform: FakePublisher(),
    )

    result = publish_target(target_id, store=publish_store)

    assert result.success is True
    assert calls["text"] == "hello world"
    assert calls["image_urls"] == [
        "https://cdn.example.com/1.jpg",
        "https://cdn.example.com/2.jpg",
        "https://cdn.example.com/3.jpg",
        "https://cdn.example.com/4.jpg",
        "https://cdn.example.com/5.jpg",
    ]
    assert calls["account"] == publish_store.accounts[0]
