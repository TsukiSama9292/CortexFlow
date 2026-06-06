"""FastExtractor — 以 trafilatura 為主的快速內容提取器。.

1. trafilatura（主要）：本地快速提取，不需外部服務
2. BeautifulSoup（備援）：當 trafilatura 失敗時使用
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import httpx
import trafilatura
from bs4 import BeautifulSoup
from rich.console import Console

from cortexflow.config.settings import settings

if TYPE_CHECKING:
    from cortexflow.core.schema import Article

console = Console()


class FastExtractor:
    """對 Articles 進行全文內容提取（trafilatura + BS4 fallback）。."""

    async def extract_all(self, articles: list[Article]) -> None:
        """對有 URL 的文章進行內容提取（併發執行）。."""
        to_extract = [a for a in articles if a.url and not a.extracted_html]
        if not to_extract:
            return

        console.print(f"  內容提取: {len(to_extract)} 篇文章")

        sem = asyncio.Semaphore(10)  # 併發上限

        async def _extract_one(article: Article) -> None:
            async with sem:
                try:
                    article.extracted_html = await self._extract(article.url)
                except Exception as exc:  # noqa: BLE001
                    console.print(f"    [yellow]⚠ 提取失敗 ({article.title[:30]}): {exc}")
                    article.extracted_html = None

        await asyncio.gather(*[_extract_one(a) for a in to_extract])

        success = sum(1 for a in to_extract if a.extracted_html)
        console.print(f"  提取成功: {success}/{len(to_extract)}")

    async def _extract(self, url: str) -> str | None:
        """依序嘗試 trafilatura → BeautifulSoup。."""
        content = await self._try_trafilatura(url)
        if content:
            return content

        return await self._try_beautifulsoup(url)

    async def _try_trafilatura(self, url: str) -> str | None:
        """使用 trafilatura 提取主要內容（本地快速）。."""
        try:
            # trafilatura.download 是同步的，用 loop.run_in_executor 避免阻塞
            downloaded = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: trafilatura.fetch_url(url),
            )
            if not downloaded:
                return None

            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: trafilatura.extract(
                    downloaded,
                    include_links=True,
                    include_tables=True,
                    output_format="markdown",
                ),
            )
            return result if result and len(result) > 50 else None
        except Exception:  # noqa: BLE001
            return None

    async def _try_beautifulsoup(self, url: str) -> str | None:
        """BeautifulSoup 備援解析。."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        try:
            async with httpx.AsyncClient(
                timeout=settings.request_timeout, follow_redirects=True,
            ) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                html = resp.text

            soup = BeautifulSoup(html, "lxml")
            for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
                tag.decompose()

            for selector in [
                "article",
                "main",
                ".post-content",
                ".entry-content",
                "#content",
                ".content",
            ]:
                container = soup.select_one(selector)
                if container:
                    text = container.get_text(separator="\n", strip=True)
                    if len(text) > 50:
                        return text

            body = soup.find("body")
            if body:
                text = body.get_text(separator="\n", strip=True)
                if len(text) > 50:
                    return text

            return None
        except Exception:  # noqa: BLE001
            return None
