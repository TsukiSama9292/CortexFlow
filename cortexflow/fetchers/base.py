"""Fetcher 抽象基底類別 — 所有渠道採集器需實作此介面。."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortexflow.core.schema import Article


class BaseFetcher(ABC):
    """資料採集器抽象基底。."""

    @abstractmethod
    async def fetch(self, topic: str, max_results: int) -> list[Article]:
        """根據主題從特定渠道採集資料。."""
