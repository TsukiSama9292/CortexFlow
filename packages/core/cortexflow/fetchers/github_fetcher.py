"""GitHub Trending 資料採集器。.

從 https://github.com/trending 爬取當前的趨勢專案，更貼近開發者社群時事。
不需要 API Token（無 Token 時以未認證身份請求，rate limit 較低但仍可使用）。
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime

from bs4 import BeautifulSoup, Tag
from loguru import logger

from cortexflow.config.settings import settings
from cortexflow.core.errors import FetchError
from cortexflow.core.http_client import get_async_client
from cortexflow.core.schema import Article
from cortexflow.fetchers.base import BaseFetcher


class GitHubFetcher(BaseFetcher):
    """從 GitHub Trending 頁面採集熱門專案。."""

    TRENDING_URL = "https://github.com/trending"

    @property
    def name(self) -> str:
        """傳回採集器名稱。."""
        return "github"

    async def fetch(
        self, topic: str, max_results: int = 20, *, demo: bool = False
    ) -> list[Article]:
        """根據主題從特定渠道採集資料。."""
        if demo:
            return self._fetch_demo(topic)

        logger.debug("從 GitHub Trending 搜尋主題: {topic}", topic=topic)

        headers = {"Accept": "text/html"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"

        # 判斷 topic 是否為程式語言（用於語言篩選）
        lang = self._detect_language(topic)

        # 組建 Trending URL，支援語言過濾與時間範圍
        trending_url = self.TRENDING_URL
        if lang:
            trending_url += f"/{lang}"
        trending_url += "?since=weekly"

        try:
            async with get_async_client(headers=headers) as client:
                resp = await client.get(trending_url)
                resp.raise_for_status()
                html = resp.text
        except Exception as exc:
            logger.error("GitHub Trending 頁面請求失敗: {error}", error=exc)
            raise FetchError("github", f"Trending 頁面請求失敗: {exc}", cause=exc) from exc

        articles = self._parse_trending(html, topic, max_results)
        logger.info("GitHub Trending 採集成功: {count} 篇文章", count=len(articles))
        return articles

    # ─────────────────────────────────────────────
    # 內部方法
    # ─────────────────────────────────────────────

    def _fetch_demo(self, topic: str) -> list[Article]:
        """產生 GitHub 的模擬資料。."""
        logger.debug("GitHub 使用 Demo 模式產出模擬資料")

        repos = [
            ("cortexflow/cortexflow", "情報 ETL Pipeline — 從社群雜訊到結構化情報"),
            ("langchain-ai/langchain", "Building applications with LLMs through composability"),
            ("openai/openai-cookbook", "Examples and guides for using the OpenAI API"),
            ("pydantic/pydantic", "Data validation using Python type hints"),
            ("encode/httpx", "A next generation HTTP client for Python"),
        ]
        articles: list[Article] = []
        topic_l = topic.lower()
        for full_name, desc in repos:
            # 測試或 Demo 模式下放寬過濾
            if (
                "test" not in topic_l
                and topic_l != "demo"
                and topic_l not in (full_name + desc).lower()
            ):
                continue

            uid = f"github-{full_name}"
            articles.append(
                Article(
                    id=hashlib.sha256(uid.encode()).hexdigest()[:16],
                    source="github",
                    source_id=full_name,
                    title=full_name,
                    text=desc,
                    author=full_name.split("/")[0] if "/" in full_name else "",
                    url=f"https://github.com/{full_name}",
                    score=100,
                    created_at=datetime.now(tz=UTC),
                )
            )
        return articles

    def _detect_language(self, topic: str) -> str | None:
        """若 topic 是常見程式語言名稱，回傳該語言 slug，否則 None。.

        例如 "python", "rust", "typescript" 會被辨識為語言過濾條件。
        """
        known_languages = {
            "python",
            "rust",
            "typescript",
            "javascript",
            "go",
            "java",
            "c++",
            "c",
            "c#",
            "ruby",
            "swift",
            "kotlin",
            "php",
            "scala",
            "r",
            "dart",
            "elixir",
            "haskell",
            "lua",
            "zig",
            "nim",
        }
        normalized = topic.strip().lower()
        if normalized in known_languages:
            return normalized

        # 也支援 "--lang python" 這類明確指定
        m = re.match(r"--lang\s+(\w+)", topic)
        if m:
            lang = m.group(1).lower()
            return lang if lang in known_languages else None

        return None

    def _parse_trending(self, html: str, topic: str, max_results: int) -> list[Article]:
        """解析 Trending 頁面的 HTML，回傳符合主題的 Article 列表。."""
        soup = BeautifulSoup(html, "lxml")
        rows = soup.select("article.Box-row")
        articles: list[Article] = []

        topic_lower = topic.lower()

        for row in rows:
            # ── 專案名稱與連結 ──
            h2 = row.select_one("h2.h3 a")
            if not h2:
                continue
            full_name = h2.get_text(strip=True).replace(" ", "")

            # ── 描述 ──
            p = row.select_one("p.col-9")
            description = p.get_text(strip=True) if p else ""

            # ── 語言 ──
            lang_span = row.select_one("[itemprop='programmingLanguage']")
            language = lang_span.get_text(strip=True) if lang_span else ""

            # ── 星星數 ──
            stars_link = row.select_one("a[href$='/stargazers']")
            stars = 0
            if stars_link:
                stars_text = stars_link.get_text(strip=True).replace(",", "")
                try:
                    stars = int(stars_text)
                except ValueError:
                    stars = 0

            # ── 今日新增星星 ──
            today_stars_span = row.find("span", class_="d-inline-block float-sm-right")
            if isinstance(today_stars_span, Tag):
                match = re.search(r"(\d[\d,]*)", today_stars_span.get_text())
                if match:
                    import contextlib

                    with contextlib.suppress(ValueError):
                        int(match.group(1).replace(",", ""))

            # ── 主題過濾 ──
            combined = f"{full_name} {description} {language}".lower()
            if topic_lower and not self._is_relevant(combined, topic_lower):
                continue

            uid = f"github-{full_name.replace('/', '-')}"
            articles.append(
                Article(
                    id=hashlib.sha256(uid.encode()).hexdigest()[:16],
                    source="github",
                    source_id=full_name,
                    title=full_name,
                    text=description,
                    author=full_name.split("/")[0] if "/" in full_name else "",
                    url=f"https://github.com/{full_name}",
                    score=stars,  # 使用總星星數作為權重
                    created_at=datetime.now(tz=UTC),  # Trending 不提供建立時間
                ),
            )

            if len(articles) >= max_results:
                break

        return articles

    @staticmethod
    def _is_relevant(combined: str, topic: str) -> bool:
        """檢查 trending 專案的名稱/描述是否與主題相關。."""
        # 完全比對
        if topic in combined:
            return True

        # 分詞比對（適用於 "AI coding assistants" 這類多詞主題）
        tokens = [t.strip() for t in topic.split() if len(t.strip()) > 2]
        if tokens:
            return any(t in combined for t in tokens)

        return False
