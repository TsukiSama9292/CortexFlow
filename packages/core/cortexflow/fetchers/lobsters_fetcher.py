"""Lobste.rs 資料採集器。.

透過 Lobste.rs 的 JSON API 獲取最新的技術討論。
不需要 API Key。
"""

from __future__ import annotations

import contextlib
import hashlib
from datetime import UTC, datetime

from loguru import logger

from cortexflow.core.http import get_async_client
from cortexflow.core.schema import Article
from cortexflow.fetchers.base import BaseFetcher


class LobstersFetcher(BaseFetcher):
    """從 Lobste.rs 採集最新討論。."""

    LATEST_URL = "https://lobste.rs/hottest.json"

    @property
    def name(self) -> str:
        """傳回採集器名稱。."""
        return "lobsters"

    async def fetch(
        self, topic: str, max_results: int = 20, *, demo: bool = False
    ) -> list[Article]:
        """獲取 Lobsters 熱門貼文並依主題過濾。."""
        if demo:
            return self._fetch_demo(topic)

        logger.debug("從 Lobsters 搜尋（依 hottest API 過濾主題: {topic}）", topic=topic)

        try:
            async with get_async_client() as client:
                resp = await client.get(self.LATEST_URL)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:  # noqa: BLE001
            logger.error("Lobste.rs API 請求失敗: {error}", error=e)
            return []

        articles: list[Article] = []
        topic_lower = topic.lower()

        for item in data:
            title = item.get("title", "")
            description = item.get("description", "")
            tags = " ".join(item.get("tags", []))

            # Lobsters 沒有搜尋 API，我們手動做簡單關鍵字過濾
            combined = f"{title} {description} {tags}".lower()
            if topic_lower and topic_lower not in combined:
                continue

            short_id = item.get("short_id", "")
            url = item.get("url") or f"https://lobste.rs/s/{short_id}"
            author = item.get("submitter_user", {}).get("username", "")
            score = item.get("score", 0)
            created_at_str = item.get("created_at")

            created_at = None
            if created_at_str:
                with contextlib.suppress(ValueError):
                    created_at = datetime.fromisoformat(created_at_str)

            uid = f"lobsters-{short_id}"
            articles.append(
                Article(
                    id=hashlib.sha256(uid.encode()).hexdigest()[:16],
                    source="lobsters",
                    source_id=short_id,
                    title=title,
                    text=description or title,
                    author=author,
                    url=url,
                    score=score,
                    created_at=created_at,
                )
            )

            if len(articles) >= max_results:
                break

        logger.info("Lobste.rs 採集成功: {count} 篇文章", count=len(articles))
        return articles

    def _fetch_demo(self, topic: str) -> list[Article]:
        """產生 Lobsters 的模擬資料。."""
        logger.debug("Lobsters 使用 Demo 模式產出模擬資料")

        items = [
            ("CortexFlow: Pluggable fetchers and more", "abc123"),
            ("Show L: My new project in Rust", "def456"),
        ]
        articles: list[Article] = []
        topic_l = topic.lower()
        for title, short_id in items:
            if "test" not in topic_l and topic_l != "demo" and topic_l not in title.lower():
                continue
            uid = f"lobsters-{short_id}"
            articles.append(
                Article(
                    id=hashlib.sha256(uid.encode()).hexdigest()[:16],
                    source="lobsters",
                    source_id=short_id,
                    title=title,
                    text=title,
                    author="lobster_guy",
                    url=f"https://lobste.rs/s/{short_id}",
                    score=50,
                    created_at=datetime.now(tz=UTC),
                )
            )
        return articles
