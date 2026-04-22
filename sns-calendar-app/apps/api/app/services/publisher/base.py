from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PublishResult:
    success: bool
    platform_post_id: str | None
    error_message: str | None
    extra: dict[str, Any] | None = None


class Publisher(ABC):
    platform: str

    @abstractmethod
    def publish(
        self,
        *,
        text: str,
        image_urls: list[str],
        account: dict[str, Any],
        options: dict[str, Any] | None = None,
    ) -> PublishResult:
        """Publish content to the remote platform and return a normalized result."""
