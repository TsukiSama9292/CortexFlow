"""FireCrawl API 客戶端 — 網頁內容提取（主要策略）。"""

from __future__ import annotations

import httpx

from cortexflow.config.settings import settings


class FireCrawlClient:
    """封裝 FireCrawl API 的內容提取呼叫。"""

    async def extract(self, url: str) -> str | None:
        """對指定 URL 執行 FireCrawl 提取，回傳 Markdown 內容。"""
        if not settings.firecrawl_api_key:
            return None

        api_url = f"{settings.firecrawl_api_url}/v1/scrape"
        headers = {
            "Authorization": f"Bearer {settings.firecrawl_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "url": url,
            "formats": ["markdown"],
        }

        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            resp = await client.post(api_url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        if data.get("success") and data.get("data"):
            return data["data"].get("markdown") or data["data"].get("content")

        return None
