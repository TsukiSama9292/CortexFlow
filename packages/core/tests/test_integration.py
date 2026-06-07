from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from cortexflow.core.db import Database
from cortexflow.core.pipeline import Pipeline
from cortexflow.core.schema import PipelineInput

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.asyncio
async def test_pipeline_integration_demo(tmp_path: Path, db: Database) -> None:
    """測試完整 Pipeline 在 Demo 模式下的端到端執行。"""
    output_path = tmp_path / "report.md"
    inp = PipelineInput(
        topic="AI Agents",
        sources=["reddit", "github"],
        max_results_per_source=2,
        output_path=str(output_path),
    )

    pipeline = Pipeline(inp, demo=True)
    pipeline.db = db  # 注入測試資料庫
    result = await pipeline.run()

    # 驗證執行結果
    assert result is not None
    assert len(result.articles) > 0
    assert result.report_content is not None
    assert output_path.exists()

    # 驗證報告內容包含主題
    report_text = output_path.read_text()
    assert "AI Agents" in report_text
    assert "報告" in report_text


@pytest.mark.asyncio
async def test_pipeline_integration_json(tmp_path: Path, db: Database) -> None:
    """測試完整 Pipeline 在 Demo 模式下輸出 JSON。"""
    output_path = tmp_path / "report.json"
    inp = PipelineInput(
        topic="Rust",
        sources=["github"],
        max_results_per_source=1,
        output_format="json",
        output_path=str(output_path),
    )

    pipeline = Pipeline(inp, demo=True)
    pipeline.db = db  # 注入測試資料庫
    result = await pipeline.run()

    assert output_path.exists()
    assert result.input.output_format == "json"
    content = output_path.read_text()
    assert '"topic": "Rust"' in content
