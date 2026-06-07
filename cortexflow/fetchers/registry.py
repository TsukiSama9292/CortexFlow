"""Fetcher 註冊中心 — 負責自動發現與管理所有資料採集器。."""

from __future__ import annotations

import importlib
import pkgutil
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from cortexflow.fetchers.base import BaseFetcher


class FetcherRegistry:
    """管理所有可用的 Fetcher 插件。."""

    def __init__(self) -> None:
        self._fetchers: dict[str, BaseFetcher] = {}
        self._discover_plugins()

    def _discover_plugins(self) -> None:
        """自動從 fetchers 套件目錄中發現並載入 Fetcher。."""
        import cortexflow.fetchers as fetchers_pkg

        # 遍歷 fetchers 套件下的所有模組
        for _, name, is_pkg in pkgutil.iter_modules(fetchers_pkg.__path__):
            if is_pkg or name in ("base", "registry"):
                continue

            module_name = f"cortexflow.fetchers.{name}"
            try:
                module = importlib.import_module(module_name)
                # 尋找繼承自 BaseFetcher 的類別並實例化
                from cortexflow.fetchers.base import BaseFetcher

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseFetcher)
                        and attr is not BaseFetcher
                    ):
                        fetcher_instance = attr()
                        self.register(fetcher_instance)
                        logger.debug(
                            "發現 Fetcher 插件: {name} ({class_name})",
                            name=fetcher_instance.name,
                            class_name=attr.__name__,
                        )
            except Exception as e:  # noqa: BLE001
                logger.error("載入插件 {name} 失敗: {error}", name=module_name, error=e)

    def register(self, fetcher: BaseFetcher) -> None:
        """手動註冊一個 Fetcher。."""
        self._fetchers[fetcher.name] = fetcher

    def get(self, name: str) -> BaseFetcher | None:
        """根據名稱取得 Fetcher 實例。."""
        return self._fetchers.get(name)

    def list_available(self) -> list[str]:
        """列出所有已註冊的 Fetcher 名稱。."""
        return sorted(self._fetchers.keys())


# 全域單例
registry = FetcherRegistry()
