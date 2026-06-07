"""Hacker News 資料採集器。.

透過 Algolia Search API 搜尋 Hacker News 上的熱門討論。
不需要 API Key。
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import httpx
from loguru import logger

from cortexflow.config.settings import settings
from cortexflow.core.schema import Article
from cortexflow.fetchers.base import BaseFetcher


class HackerNewsFetcher(BaseFetcher):
    """從 Hacker News 採集熱門討論。."""

    SEARCH_API_URL = "https://hn.algolia.com/api/v1/search"

    @property
    def name(self) -> str:
        return "hackernews"

    async def fetch(
        self, topic: str, max_results: int = 20, *, demo: bool = False
    ) -> list[Article]:
        """透過 Algolia API 搜尋 HN 貼文。."""
        if demo:
            return self._fetch_demo(topic)

        logger.debug("從 Hacker News 搜尋主題: {topic}", topic=topic)

        params = {
            "query": topic,
            "tags": "story",
            "hitsPerPage": min(max_results, 100),
        }

        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                resp = await client.get(self.SEARCH_API_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:  # noqa: BLE001
            logger.error("Hacker News API 請求失敗: {error}", error=e)
            return []

        articles: list[Article] = []
        for hit in data.get("hits", []):
            hn_id = hit.get("objectID", "")
            title = hit.get("title", "")
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hn_id}"
            author = hit.get("author", "")
            score = hit.get("points", 0)
            created_at_str = hit.get("created_at")

            created_at = None
            if created_at_str:
                try:
                    # Algolia 回傳格式如 "2024-01-01T12:00:00Z"
                    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                except ValueError:
                    pass

            uid = f"hn-{hn_id}"
            articles.append(
                Article(
                    id=hashlib.sha256(uid.encode()).hexdigest()[:16],
                    source="hackernews",
                    source_id=hn_id,
                    title=title,
                    text=hit.get("story_text") or title,
                    author=author,
                    url=url,
                    score=score,
                    created_at=created_at,
                )
            )

        logger.info("Hacker News 採集成功: {count} 篇文章", count=len(articles))
        return articles

    def _fetch_demo(self, topic: str) -> list[Article]:
        """產生 Hacker News 的模擬資料。."""
        logger.debug("Hacker News 使用 Demo 模式產出模擬資料")

        stories = [
            ("Show HN: CortexFlow - An open source intelligence ETL pipeline", "123456"),
            ("Building a pluggable architecture in Python", "234567"),
            ("Why I switched from Reddit to Hacker News for tech news", "345678"),
        ]
        articles: list[Article] = []
        topic_l = topic.lower()
        for title, hn_id in stories:
            if "test" not in topic_l and topic_l != "demo":
                if topic_l not in title.lower():
                    continue
            uid = f"hn-{hn_id}"
            articles.append(
                Article(
                    id=hashlib.sha256(uid.encode()).hexdigest()[:16],
                    source="hackernews",
                    source_id=hn_id,
                    title=title,
                    text=title,
                    author="hn_user",
                    url=f"https://news.ycombinator.com/item?id={hn_id}",
                    score=200,
                    created_at=datetime.now(tz=UTC),
                )
            )
        return articles
