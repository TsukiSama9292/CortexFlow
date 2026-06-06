from __future__ import annotations

from pathlib import Path
from cortexflow.reporter.json_reporter import JSONReporter
from cortexflow.reporter.markdown_reporter import MarkdownReporter
from cortexflow.core.schema import PipelineInput, Article, ReportContent, ReportSection
from cortexflow.core.pipeline import StageResult


def test_json_reporter_generate(tmp_path: Path) -> None:
    """測試 JSONReporter 產生檔案。"""
    output_file = tmp_path / "report.json"
    inp = PipelineInput(topic="test", output_path=str(output_file))
    articles = [Article(id="1", source="reddit", source_id="1", title="Title")]
    stage_results = [StageResult(stage_name="Fetch", success=True, duration=0.1, items_count=1)]

    reporter = JSONReporter()
    reporter.generate(articles, inp, stage_results, errors=[], report_content=None)

    assert output_file.exists()
    assert '"topic": "test"' in output_file.read_text()


def test_markdown_reporter_simple(tmp_path: Path) -> None:
    """測試 MarkdownReporter 產生簡潔版報告。"""
    output_file = tmp_path / "report.md"
    inp = PipelineInput(topic="test", output_path=str(output_file))
    articles = [Article(id="1", source="reddit", source_id="1", title="Title", author="Me")]
    stage_results = [StageResult(stage_name="Fetch", success=True, duration=0.1, items_count=1)]

    reporter = MarkdownReporter()
    reporter.generate(articles, inp, stage_results, errors=[], report_content=None)

    assert output_file.exists()
    content = output_file.read_text()
    assert "# 情報報告: test" in content
    assert "Title" in content


def test_markdown_reporter_rich(tmp_path: Path) -> None:
    """測試 MarkdownReporter 產生豐富版報告。"""
    output_file = tmp_path / "report.md"
    inp = PipelineInput(topic="test", output_path=str(output_file))

    rc = ReportContent(
        title="Deep Insight",
        sections=[ReportSection(emoji="🚀", title="Future", content="It's bright.")],
        key_points=["Point 1"],
        links=["https://example.com"]
    )

    reporter = MarkdownReporter()
    reporter.generate([], inp, [], errors=[], report_content=rc)

    assert output_file.exists()
    content = output_file.read_text()
    assert "# Deep Insight" in content
    assert "Rocket" not in content  # emoji is there, but word Rocket shouldn't be
    assert "🚀 Future" in content
    assert "It's bright." in content
