from __future__ import annotations

import pytest

from cortexflow.core.pipeline import Pipeline, StageResult
from cortexflow.core.schema import PipelineInput


@pytest.mark.asyncio
async def test_pipeline_demo_mode():
    inp = PipelineInput(
        topic="test",
        sources=["github"],
        max_results_per_source=5,
        relevance_threshold=5.0,
        output_format="markdown",
        output_path="/tmp/test_pipeline_output.md",
    )
    pipeline = Pipeline(inp, demo=True)
    result = await pipeline.run()

    assert len(result.articles) > 0
    assert len(result.stage_stats) > 0
    assert result.report_content is not None
    assert result.llm_usage["total_tokens"] == 0


@pytest.mark.asyncio
async def test_pipeline_stage_results():
    inp = PipelineInput(topic="test", sources=["github"])
    pipeline = Pipeline(inp, demo=True)
    result = await pipeline.run()

    assert "fetch_github" in result.stage_stats
    assert "normalize" in result.stage_stats
    assert "extract" in result.stage_stats
    assert "analyze" in result.stage_stats
    assert "synthesize" in result.stage_stats
    assert "report" in result.stage_stats

    for _name, stats in result.stage_stats.items():
        assert stats["success"] is True
        assert isinstance(stats["duration_seconds"], float)


@pytest.mark.asyncio
async def test_pipeline_two_sources():
    inp = PipelineInput(topic="test", sources=["reddit", "github"])
    pipeline = Pipeline(inp, demo=True)
    result = await pipeline.run()

    assert "fetch_reddit" in result.stage_stats
    assert "fetch_github" in result.stage_stats


@pytest.mark.asyncio
async def test_pipeline_errors_empty():
    inp = PipelineInput(topic="test", sources=["github"])
    pipeline = Pipeline(inp, demo=True)
    result = await pipeline.run()
    assert len(result.errors) == 0


class TestStageResult:
    def test_stage_result_defaults(self):
        sr = StageResult(stage_name="test", success=True, duration=1.5)
        assert sr.items_count == 0
        assert sr.error is None

    def test_stage_result_with_error(self):
        sr = StageResult(
            stage_name="test", success=False, duration=2.0, error="fail",
        )
        assert sr.error == "fail"


@pytest.mark.asyncio
async def test_pipeline_no_sources():
    inp = PipelineInput(topic="test", sources=[])
    pipeline = Pipeline(inp, demo=True)
    result = await pipeline.run()

    assert "fetch_reddit" not in result.stage_stats
    assert "fetch_github" not in result.stage_stats
    assert len(result.articles) == 0


@pytest.mark.asyncio
async def test_pipeline_report_content_demo():
    inp = PipelineInput(topic="test topic", sources=["github"])
    pipeline = Pipeline(inp, demo=True)
    result = await pipeline.run()

    assert result.report_content is not None
    assert "test topic" in result.report_content.title
    assert len(result.report_content.links) > 0
