from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from cortexflow.core.schema import (
    Article,
    ArticleAnalysis,
    PipelineInput,
    PipelineOutput,
    ReportContent,
    ReportSection,
)


class TestArticle:
    def test_minimal_article(self):
        a = Article(id="x1", source="github", source_id="repo")
        assert a.title == ""
        assert a.score == 0
        assert isinstance(a.fetched_at, datetime)

    def test_full_article(self):
        a = Article(
            id="x1",
            source="reddit",
            source_id="abc123",
            title="Test Title",
            author="user1",
            text="Some text content",
            url="https://reddit.com/r/test",
            score=42,
            created_at=datetime(2026, 6, 1),
            extracted_html="<p>html</p>",
            relevance_score=7.5,
            summary="summary",
            sub_analysis="analysis",
            key_insights=["i1", "i2"],
            llm_judge_passed=True,
        )
        assert a.source == "reddit"
        assert a.relevance_score == 7.5
        assert a.key_insights == ["i1", "i2"]

    def test_invalid_source(self):
        with pytest.raises(ValidationError):
            Article(id="x1", source="twitter", source_id="1")

    def test_relevance_score_range(self):
        with pytest.raises(ValidationError):
            Article(
                id="x1", source="github", source_id="1", relevance_score=15.0
            )

    def test_score_default_zero(self, sample_article):
        assert sample_article.score == 100

    def test_id_generation_not_automatic(self):
        a = Article(id="custom_id", source="github", source_id="repo")
        assert a.id == "custom_id"


class TestArticleAnalysis:
    def test_minimal_analysis(self):
        a = ArticleAnalysis(
            article_id="x1",
            title="t",
            url="https://example.com",
            relevance_score=5.0,
            summary="sum",
            sub_analysis="sub",
            key_insights=["k1"],
        )
        assert a.article_id == "x1"

    def test_invalid_score_range(self):
        with pytest.raises(ValidationError):
            ArticleAnalysis(
                article_id="x1",
                title="t",
                url="https://example.com",
                relevance_score=11.0,
                summary="sum",
                sub_analysis="sub",
                key_insights=["k1"],
            )

    def test_empty_key_insights_allowed(self):
        a = ArticleAnalysis(
            article_id="x1",
            title="t",
            url="https://example.com",
            relevance_score=3.0,
            summary="sum",
            sub_analysis="sub",
            key_insights=[],
        )
        assert a.key_insights == []


class TestReportContent:
    def test_minimal_report(self):
        rc = ReportContent(
            title="Report",
            sections=[],
            key_points=[],
            links=[],
        )
        assert rc.title == "Report"

    def test_with_sections(self, sample_report_content):
        assert len(sample_report_content.sections) == 1
        assert sample_report_content.sections[0].emoji == "📌"

    def test_links(self):
        rc = ReportContent(
            title="T",
            sections=[],
            key_points=[],
            links=["https://a.com", "https://b.com"],
        )
        assert len(rc.links) == 2


class TestPipelineInput:
    def test_defaults(self):
        inp = PipelineInput(topic="test")
        assert inp.sources == ["reddit", "github"]
        assert inp.max_results_per_source == 20
        assert inp.relevance_threshold == 5.0
        assert inp.output_format == "markdown"

    def test_topic_required(self):
        with pytest.raises(ValidationError):
            PipelineInput()

    def test_custom_values(self, sample_pipeline_input):
        assert sample_pipeline_input.topic == "test topic"
        assert sample_pipeline_input.max_results_per_source == 10

    def test_invalid_source(self):
        with pytest.raises(ValidationError):
            PipelineInput(topic="t", sources=["facebook"])

    def test_invalid_format(self):
        with pytest.raises(ValidationError):
            PipelineInput(topic="t", output_format="pdf")


class TestPipelineOutput:
    def test_minimal_output(self, sample_pipeline_input):
        out = PipelineOutput(input=sample_pipeline_input)
        assert out.articles == []
        assert out.errors == []
        assert out.report_content is None

    def test_with_articles(self, sample_pipeline_input, sample_article):
        out = PipelineOutput(
            input=sample_pipeline_input,
            articles=[sample_article],
            stage_stats={"fetch": {"success": True}},
        )
        assert len(out.articles) == 1
        assert out.stage_stats["fetch"]["success"] is True
