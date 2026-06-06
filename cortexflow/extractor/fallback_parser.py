"""BeautifulSoup 備援解析器 — 當 FireCrawl 失效時的 fallback 策略。"""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from cortexflow.config.settings import settings


class FallbackParser:
    """使用 httpx + BeautifulSoup 進行基礎的網頁內容提取。"""

    async def extract(self, url: str) -> str | None:
        """下載 HTML 並嘗試提取主要內容。"""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        async with httpx.AsyncClient(timeout=settings.request_timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            html = resp.text

        soup = BeautifulSoup(html, "lxml")

        # 移除干擾元素
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        # 嘗試主要內容區塊
        for selector in ["article", "main", ".post-content", ".entry-content", "#content", ".content"]:
            container = soup.select_one(selector)
            if container:
                return container.get_text(separator="\n", strip=True)

        # fallback: 回傳 body 文字
        body = soup.find("body")
        if body:
            return body.get_text(separator="\n", strip=True)

        return None
