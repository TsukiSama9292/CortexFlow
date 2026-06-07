from __future__ import annotations

import pytest
from sqlalchemy import text
from cortexflow.core.db import Database
from cortexflow.core.schema import Article, PipelineInput, PipelineOutput


@pytest.mark.asyncio
async def test_db_initialization(db: Database) -> None:
    """測試資料庫初始化與資料表建立。"""
    async with db.SessionLocal() as session:
        # 驗證資料表是否存在
        result = await session.execute(
            text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'")
        )
        tables = [row[0] for row in result.fetchall()]
        assert "executions" in tables


@pytest.mark.asyncio
async def test_db_save_and_get_execution(db: Database) -> None:
    """測試儲存與讀取執行記錄。"""
    inp = PipelineInput(topic="test topic", sources=["reddit"])
    output = PipelineOutput(
        input=inp,
        articles=[Article(id="1", source="reddit", source_id="1", title="Test")],
        llm_usage={"total_tokens": 100, "total_cost_usd": 0.001, "calls": 1},
    )

    exec_id = await db.save_execution(output, status="success", demo=True, last_stage="report")
    assert exec_id > 0

    # 測試讀取
    exec_data = await db.get_execution(exec_id)
    assert exec_data is not None
    assert exec_data["topic"] == "test topic"
    assert exec_data["status"] == "success"
    assert exec_data["demo"] is True
    assert exec_data["last_completed_stage"] == "report"


@pytest.mark.asyncio
async def test_db_update_execution(db: Database) -> None:
    """測試更新執行記錄。."""
    inp = PipelineInput(topic="update test", sources=["github"])
    output = PipelineOutput(input=inp)

    exec_id = await db.save_execution(output, status="running")

    # 更新狀態
    output.llm_usage = {"total_tokens": 500}
    await db.update_execution(exec_id, output, status="success", last_stage="extract")

    updated = await db.get_execution(exec_id)
    assert updated is not None
    assert updated["status"] == "success"
    assert updated["total_tokens"] == 500
    assert updated["last_completed_stage"] == "extract"


@pytest.mark.asyncio
async def test_db_history(db: Database) -> None:
    """測試取得歷史記錄列表。."""
    inp = PipelineInput(topic="h1", sources=["reddit"])
    await db.save_execution(PipelineOutput(input=inp))

    inp2 = PipelineInput(topic="h2", sources=["github"])
    await db.save_execution(PipelineOutput(input=inp2))

    history = await db.get_history(limit=5)
    assert len(history) == 2
    assert history[0]["topic"] == "h2"  # 最新優先
