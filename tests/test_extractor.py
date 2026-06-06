from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from cortexflow.core.schema import Article
from cortexflow.extractor.fast_extractor import FastExtractor

if TYPE_CHECKING:
    from pytest_httpx import HTTPXMock


@pytest.mark.asyncio
async def test_fast_extractor_trafilatura_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """測試 FastExtractor 使用 trafilatura 提取成功。"""
    async def mock_trafilatura(self, url: str) -> str | None:
        return "Extracted Content"

    monkeypatch.setattr(FastExtractor, "_try_trafilatura", mock_trafilatura)

    extractor = FastExtractor()
    article = Article(id="1", source="reddit", source_id="1", url="https://example.com")
    await extractor.extract_all([article])

    assert article.extracted_html == "Extracted Content"


@pytest.mark.asyncio
async def test_fast_extractor_bs4_fallback(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """測試 FastExtractor 在 trafilatura 失敗時回退到 BeautifulSoup。"""
    async def mock_trafilatura_fail(self, url: str) -> str | None:
        return None

    monkeypatch.setattr(FastExtractor, "_try_trafilatura", mock_trafilatura_fail)

    # Mock HTTP 響應
    html_content = (
        "<html><body><main>BS4 Content that is long enough to be valid. "
        "Adding more text to ensure it exceeds fifty characters threshold.</main></body></html>"
    )
    httpx_mock.add_response(url="https://example.com", html=html_content)

    extractor = FastExtractor()
    article = Article(id="1", source="reddit", source_id="1", url="https://example.com")
    await extractor.extract_all([article])

    assert article.extracted_html is not None
    assert "BS4 Content" in article.extracted_html


@pytest.mark.asyncio
async def test_fast_extractor_no_url() -> None:
    """測試 FastExtractor 處理沒有 URL 的文章。"""
    extractor = FastExtractor()
    article = Article(id="1", source="reddit", source_id="1", url="")
    await extractor.extract_all([article])

    assert article.extracted_html is None
