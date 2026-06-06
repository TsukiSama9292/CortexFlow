from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from cortexflow.fetchers.github_fetcher import GitHubFetcher
from cortexflow.fetchers.reddit_fetcher import RedditFetcher

if TYPE_CHECKING:
    from pytest_httpx import HTTPXMock


@pytest.mark.asyncio
async def test_reddit_fetcher_api_success(httpx_mock: HTTPXMock) -> None:
    """測試 RedditFetcher 從 API 成功採集。"""
    mock_response = {
        "data": {
            "children": [
                {
                    "data": {
                        "id": "t1_abc",
                        "title": "Mock Reddit Post",
                        "selftext": "Content",
                        "author": "tester",
                        "permalink": "/r/test/comments/abc/",
                        "score": 100,
                        "created_utc": 1600000000.0,
                    },
                },
            ],
        },
    }
    search_url = "https://www.reddit.com/search.json?q=test&limit=20&sort=relevance&type=link"
    httpx_mock.add_response(url=search_url, json=mock_response)

    fetcher = RedditFetcher()
    articles = await fetcher.fetch("test", max_results=20)

    assert len(articles) == 1
    assert articles[0].title == "Mock Reddit Post"
    assert articles[0].source == "reddit"
    assert articles[0].score == 100


@pytest.mark.asyncio
async def test_reddit_fetcher_demo_fallback(httpx_mock: HTTPXMock) -> None:
    """測試 RedditFetcher 在 API 失敗時回退到 Demo 模式。"""
    httpx_mock.add_response(status_code=500)  # 主端點失敗
    httpx_mock.add_response(status_code=500)  # 備援端點失敗

    fetcher = RedditFetcher()
    articles = await fetcher.fetch("test", max_results=5)

    assert len(articles) > 0
    assert "test" in articles[0].title.lower() or "test" in articles[0].text.lower()


@pytest.mark.asyncio
async def test_github_fetcher_success(httpx_mock: HTTPXMock) -> None:
    """測試 GitHubFetcher 成功解析 Trending 頁面。"""
    mock_html = """
    <html>
        <body>
            <article class="Box-row">
                <h2 class="h3 a">
                    <a href="/owner/repo">owner / repo</a>
                </h2>
                <p class="col-9">Interesting project about test</p>
                <span itemprop="programmingLanguage">Python</span>
                <a href="/owner/repo/stargazers">1,234</a>
                <span class="d-inline-block float-sm-right">123 stars today</span>
            </article>
        </body>
    </html>
    """
    httpx_mock.add_response(url="https://github.com/trending?since=weekly", html=mock_html)

    fetcher = GitHubFetcher()
    articles = await fetcher.fetch("test", max_results=10)

    assert len(articles) == 1
    assert articles[0].title == "owner/repo"
    assert articles[0].source == "github"
    assert articles[0].score == 1234
    assert "test" in articles[0].text.lower()


@pytest.mark.asyncio
async def test_github_fetcher_language_filter(httpx_mock: HTTPXMock) -> None:
    """測試 GitHubFetcher 語言過濾。"""
    trending_url = "https://github.com/trending/python?since=weekly"
    httpx_mock.add_response(url=trending_url, html="<html></html>")

    fetcher = GitHubFetcher()
    await fetcher.fetch("python", max_results=10)

    # 驗證請求 URL 是否包含 /python
    params = httpx_mock.get_request().url.path
    assert "/python" in params
