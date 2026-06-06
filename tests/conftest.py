from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cortexflow.core.schema import (
    Article,
    ArticleAnalysis,
    PipelineInput,
    ReportContent,
    ReportSection,
)


@pytest.fixture
def sample_article() -> Article:
    return Article(
        id="abc123",
        source="github",
        source_id="owner/repo",
        title="test/repo",
        author="owner",
        text="A sample repository description for testing.",
        url="https://github.com/owner/repo",
        score=100,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


@pytest.fixture
def sample_analysis() -> ArticleAnalysis:
    return ArticleAnalysis(
        article_id="abc123",
        title="test/repo",
        url="https://github.com/owner/repo",
        relevance_score=8.5,
        summary="這是一個測試摘要。",
        sub_analysis="深度子分析內容。",
        key_insights=["insight 1", "insight 2"],
    )


@pytest.fixture
def sample_report_content() -> ReportContent:
    return ReportContent(
        title="測試報告",
        sections=[
            ReportSection(emoji="📌", title="章節一", content="內容一"),
        ],
        key_points=["重點 1", "重點 2"],
        links=["https://example.com"],
    )


@pytest.fixture
def sample_pipeline_input() -> PipelineInput:
    return PipelineInput(
        topic="test topic",
        sources=["reddit", "github"],
        max_results_per_source=10,
        relevance_threshold=5.0,
        output_format="markdown",
        output_path="/tmp/test_output.md",
    )


@pytest.fixture
def sample_articles() -> list[Article]:
    return [
        Article(
            id=f"article_{i}",
            source="github",
            source_id=f"owner/repo{i}",
            title=f"repo{i}",
            author="owner",
            text=f"Description for repo {i} with some content for testing.",
            url=f"https://github.com/owner/repo{i}",
            score=i * 10,
        )
        for i in range(5)
    ]
