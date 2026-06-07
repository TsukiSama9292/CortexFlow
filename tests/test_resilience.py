from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from cortexflow.core.pipeline import Pipeline
from cortexflow.core.schema import Article, PipelineInput
from cortexflow.filter.article_analyzer import FallbackAnalyzer


@pytest.mark.asyncio
async def test_pipeline_timeout() -> None:
    """測試 Stage 超時控制。"""
    inp = PipelineInput(topic="test", sources=["github"])
    pipeline = Pipeline(inp, demo=True)

    # 模擬一個會卡住的 stage
    async def slow_fn():
        await asyncio.sleep(2)

    from cortexflow.config.settings import settings

    original_timeout = settings.stage_timeout
    settings.stage_timeout = 0.1  # 設極短超時

    from rich.console import Console

    console = Console()

    try:
        await pipeline._run_stage("test_stage", slow_fn, console)
        # 應該會失敗並記錄錯誤
        assert pipeline.stage_results[0].success is False
        assert "TimeoutError" in pipeline.stage_results[0].error
    finally:
        settings.stage_timeout = original_timeout


def test_fallback_analyzer() -> None:
    """測試降級分析器。"""
    # 使用單一單詞確保匹配
    analyzer = FallbackAnalyzer(topic="Python")
    articles = [
        Article(
            id="1",
            source="github",
            source_id="1",
            title="Python is cool",
            text="Some description",
        ),
        Article(id="2", source="github", source_id="2", title="Unrelated", text="Nothing here"),
        Article(id="3", source="github", source_id="3", title="RUST project", text="Fast and safe"),
    ]

    results = analyzer.analyze(articles)

    assert len(results) >= 1
    assert "Python" in results[0].title
    assert "降級模式" in results[0].sub_analysis


@pytest.mark.asyncio
async def test_article_analyzer_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    """測試 ArticleAnalyzer 的重試機制。"""
    from cortexflow.filter.article_analyzer import ArticleAnalyzer

    analyzer = ArticleAnalyzer(topic="test")

    # 模擬 LLM 呼叫，前兩次失敗，第三次成功
    mock_chain = AsyncMock()
    mock_chain.ainvoke.side_effect = [
        Exception("API Error 1"),
        Exception("API Error 2"),
        {
            "raw": MagicMock(usage_metadata={"input_tokens": 10, "output_tokens": 10}),
            "parsed": MagicMock(
                relevance_score=8.0,
                summary="ok",
                sub_analysis="ok",
                key_insights=[],
            ),
        },
    ]
    monkeypatch.setattr(analyzer, "_chain", mock_chain)

    from cortexflow.config.settings import settings

    original_retries = settings.max_retries
    original_wait = settings.retry_min_wait
    settings.max_retries = 3
    settings.retry_min_wait = 0.1  # 縮短等待時間

    try:
        article = Article(id="1", source="reddit", source_id="1", title="Test")
        result = await analyzer._rate_and_analyze(article, threshold=5.0)

        assert result is not None
        assert result.relevance_score == 8.0
        assert mock_chain.ainvoke.call_count == 3
    finally:
        settings.max_retries = original_retries
        settings.retry_min_wait = original_wait
