from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from cortexflow.core.pipeline import Pipeline
from cortexflow.core.schema import Article, PipelineInput, PipelineOutput

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.asyncio
async def test_pipeline_resume(tmp_path: Path) -> None:
    """測試 Pipeline 續傳功能。"""
    db_file = tmp_path / "resume.db"

    # 1. 模擬一個執行到一半失敗的記錄
    inp = PipelineInput(topic="resume test", sources=["reddit"])
    output = PipelineOutput(
        input=inp,
        articles=[Article(id="r1", source="reddit", source_id="r1", title="Already Fetched")],
        # 模擬已經完成了 fetch_reddit 和 normalize
        stage_stats={
            "fetch_reddit": {"success": True, "duration": 0.1, "items_count": 1},
            "normalize": {"success": True, "duration": 0.1, "items_count": 1},
        },
    )

    from cortexflow.core.db import Database

    db = Database(str(db_file))
    exec_id = db.save_execution(output, status="failed", last_stage="normalize")

    # 2. 建立續傳 Pipeline
    pipeline = Pipeline(inp, demo=True, execution_id=exec_id)
    pipeline.db = db  # 使用測試資料庫

    # 3. 執行 Pipeline
    await pipeline.run()

    # 4. 驗證是否跳過了前面的 Stage
    assert len(pipeline.stage_results) >= 2
    # 檢查是否包含之前完成的 stage
    names = [r.stage_name for r in pipeline.stage_results]
    assert "fetch_reddit" in names
    assert "normalize" in names
    assert "extract" in names  # 這是續傳後執行的第一個 Stage

    # 驗證資料是否被還原
    assert len(pipeline.articles) > 0
    assert pipeline.articles[0].title == "Already Fetched"
