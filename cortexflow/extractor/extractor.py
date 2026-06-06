"""Stage 3: 內容提取層 — FireCrawl 為主、BeautifulSoup 為備援。"""

from __future__ import annotations

import asyncio

from rich.console import Console

from cortexflow.core.schema import Article

console = Console()


class Extractor:
    """對 Articles 進行全文內容提取。"""

    async def extract_all(self, articles: list[Article]) -> None:
        """對有 URL 的文章進行內容提取。"""
        if not articles:
            return

        to_extract = [a for a in articles if a.url and not a.extracted_html]
        if not to_extract:
            return

        console.print(f"  內容提取: {len(to_extract)} 篇文章")

        # 非同步並行提取，控制並發數避免被限流
        sem = asyncio.Semaphore(5)

        async def _extract_one(article: Article) -> None:
            async with sem:
                try:
                    await self._extract(article)
                except Exception as exc:
                    console.print(f"    [yellow]⚠ 提取失敗 ({article.url[:60]}): {exc}")

        await asyncio.gather(*[_extract_one(a) for a in to_extract])

    async def _extract(self, article: Article) -> None:
        """依序嘗試 FireCrawl → Fallback。"""
        # 先試 FireCrawl
        try:
            from cortexflow.extractor.firecrawl_client import FireCrawlClient

            client = FireCrawlClient()
            content = await client.extract(article.url)
            if content:
                article.extracted_html = content
                return
        except Exception:
            pass

        # Fallback: BeautifulSoup
        try:
            from cortexflow.extractor.fallback_parser import FallbackParser

            parser = FallbackParser()
            content = await parser.extract(article.url)
            if content:
                article.extracted_html = content
                return
        except Exception:
            pass

        # 如果都失敗，保留 extracted_html = None
        article.extracted_html = None
