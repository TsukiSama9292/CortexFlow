from __future__ import annotations

from typing import TYPE_CHECKING

from cortexflow.fetchers.base import BaseFetcher
from cortexflow.fetchers.registry import registry

if TYPE_CHECKING:
    from cortexflow.core.schema import Article


class MockFetcher(BaseFetcher):
    """模擬用的 Fetcher。."""

    @property
    def name(self) -> str:
        return "mock_source"

    async def fetch(self, topic: str, max_results: int, *, demo: bool = False) -> list[Article]:
        return []


def test_registry_discovery() -> None:
    """測試自動發現插件功能。"""
    available = registry.list_available()
    assert "reddit" in available
    assert "github" in available
    assert "hackernews" in available
    assert "lobsters" in available


def test_registry_manual_registration() -> None:
    """測試手動註冊 Fetcher。."""
    mock = MockFetcher()
    registry.register(mock)

    assert registry.get("mock_source") == mock
    assert "mock_source" in registry.list_available()


def test_registry_get_nonexistent() -> None:
    """測試取得不存在的 Fetcher。."""
    assert registry.get("nonexistent_xyz") is None
