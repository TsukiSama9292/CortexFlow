from __future__ import annotations

from datetime import UTC, datetime

import pytest
from testcontainers.postgres import PostgresContainer

from cortexflow.core.db import Database
from cortexflow.core.models import Base
from cortexflow.core.schema import (
    Article,
    ArticleAnalysis,
    PipelineInput,
    ReportContent,
    ReportSection,
)


@pytest.fixture(scope="session")
def postgres_container():
    """啟動一個帶有 pgvector 的 Postgres 容器。"""
    with PostgresContainer("pgvector/pgvector:0.8.2-pg18-trixie", driver="asyncpg") as postgres:
        yield postgres


@pytest.fixture
async def db(postgres_container: PostgresContainer):
    """建立資料庫連線並初始化資料表。"""
    url = postgres_container.get_connection_url()
    database = Database(url)

    # 手動建立資料表（測試用，不經 alembic）
    async with database.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield database

    # 清理資料表以確保測試隔離
    async with database.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await database.close()


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
