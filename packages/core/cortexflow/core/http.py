"""HTTP Client Utility — 統一管理 Proxy 與 User-Agent。."""

from __future__ import annotations

from typing import Any

import httpx
from fake_useragent import UserAgent
from loguru import logger

from cortexflow.config.settings import settings

# 初始化 UserAgent 物件
_ua = UserAgent()


def get_async_client(**kwargs: Any) -> httpx.AsyncClient:  # noqa: ANN401
    """獲取配置好的 httpx.AsyncClient。 .

    自動注入:
    - 隨機 User-Agent
    - Proxy (若 settings.proxy_url 有設定)
    """
    headers = kwargs.pop("headers", {})
    if "User-Agent" not in headers:
        headers["User-Agent"] = _ua.random

    proxy = settings.proxy_url or None
    if proxy:
        logger.debug("使用 Proxy: {proxy}", proxy=proxy)

    timeout = kwargs.pop("timeout", settings.request_timeout)
    follow_redirects = kwargs.pop("follow_redirects", True)

    return httpx.AsyncClient(
        headers=headers,
        proxy=proxy,
        timeout=timeout,
        follow_redirects=follow_redirects,
        **kwargs,
    )
