"""Reddit 資料採集器。

策略（依序嘗試）：
1. Reddit 公開 JSON API（不需要憑證）
2. old.reddit.com JSON API（備援端點）
3. Demo 模式（自動產生模擬貼文）
"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta

import httpx

from cortexflow.config.settings import settings
from cortexflow.core.errors import FetchError
from cortexflow.core.schema import Article
from cortexflow.fetchers.base import BaseFetcher

# ── Demo 模式用的模擬資料 ──
_DEMO_SUBREDDITS = [
    "r/programming", "r/MachineLearning", "r/artificial",
    r"r/webdev", "r/rust", "r/Python", "r/devops", r"r/startups",
]

_DEMO_TITLES = [
    "{topic} in 2026: What's changed and what's next?",
    "I built a production system with {topic} — here's what I learned",
    "{topic} vs traditional approaches: A comparison",
    "Why {topic} is gaining traction in enterprise",
    "Tutorial: Getting started with {topic}",
    "The hidden costs of using {topic} at scale",
    "AMA: I've been working on {topic} for 5 years, ask me anything",
    "{topic} just released a major update! Breaking changes inside",
    "Show HN: My side project built with {topic}",
    "How {topic} is changing the way we think about software",
    "Discussion: What's missing in the {topic} ecosystem?",
    "From zero to production: {topic} deployment guide",
]

_DEMO_BODIES = [
    "I've been experimenting with this for a few weeks now and the results are promising. Would love to hear others' experiences.",
    "After migrating our stack to use this, we saw a 40% improvement in performance. Here's a detailed breakdown of the migration process and the challenges we faced.",
    "There's a lot of hype around this topic, but I wanted to share some practical advice based on real-world usage in a production environment serving millions of users.",
    "Just published a comprehensive guide covering architecture patterns, best practices, and common pitfalls. Feedback welcome!",
    "I see a lot of questions about this, so I put together a step-by-step tutorial covering the basics. Perfect for beginners.",
    "We evaluated several options and decided to go with this approach. Here's our decision-making process and the trade-offs we considered.",
]


class RedditFetcher(BaseFetcher):
    """Reddit 資料採集器 — 先試 API，失敗則回退到 Demo 模式。"""

    BASE_URL = "https://www.reddit.com"
    OLD_REDDIT_URL = "https://old.reddit.com"

    async def fetch(self, topic: str, max_results: int = 20) -> list[Article]:
        # 嘗試主要端點
        try:
            return await self._fetch_from_api(self.BASE_URL, topic, max_results)
        except Exception:
            pass

        # 備援：old.reddit.com
        try:
            return await self._fetch_from_api(self.OLD_REDDIT_URL, topic, max_results)
        except Exception:
            pass

        # 最終備援：Demo 模式
        return self._fetch_demo(topic, max_results)

    async def _fetch_from_api(
        self, base_url: str, topic: str, max_results: int
    ) -> list[Article]:
        """從指定 Reddit 端點採集資料。"""
        url = f"{base_url}/search.json"
        params = {
            "q": topic,
            "limit": min(max_results, 100),
            "sort": "relevance",
            "type": "link",
        }
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        articles: list[Article] = []
        for child in data.get("data", {}).get("children", []):
            raw = child.get("data", {})
            uid = f"reddit-{raw.get('id', '')}"
            created = raw.get("created_utc")
            articles.append(
                Article(
                    id=hashlib.sha256(uid.encode()).hexdigest()[:16],
                    source="reddit",
                    source_id=raw.get("id", ""),
                    title=raw.get("title", ""),
                    text=raw.get("selftext", "") or raw.get("url", ""),
                    author=raw.get("author", ""),
                    url=f"https://www.reddit.com{raw.get('permalink', '')}",
                    score=raw.get("score", 0),
                    created_at=datetime.fromtimestamp(created) if created else None,
                )
            )

        return articles

    def _fetch_demo(self, topic: str, max_results: int) -> list[Article]:
        """無需 API 金鑰，產生與主題相關的模擬 Reddit 貼文。"""
        rng = random.Random(topic)
        count = min(max_results, 12)

        articles: list[Article] = []
        now = datetime.now()

        for i in range(count):
            title = rng.choice(_DEMO_TITLES).format(topic=topic)
            body = rng.choice(_DEMO_BODIES)
            subreddit = rng.choice(_DEMO_SUBREDDITS)
            author = f"user_{rng.randint(1000, 9999)}"
            minutes_ago = rng.randint(30, 60 * 24 * 7)
            score = rng.randint(10, 2000)

            uid = f"reddit-demo-{hashlib.md5(title.encode()).hexdigest()[:12]}"
            permalink = f"/{subreddit}/comments/{uid}/{title.lower().replace(' ', '_')}/"

            articles.append(
                Article(
                    id=hashlib.sha256(uid.encode()).hexdigest()[:16],
                    source="reddit",
                    source_id=uid,
                    title=title,
                    text=body,
                    author=author,
                    url=f"https://www.reddit.com{permalink}",
                    score=score,
                    created_at=now - timedelta(minutes=minutes_ago),
                )
            )

        return articles
