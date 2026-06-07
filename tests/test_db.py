from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from cortexflow.core.db import Database
from cortexflow.core.schema import Article, PipelineInput, PipelineOutput

if TYPE_CHECKING:
    from pathlib import Path


def test_db_initialization(tmp_path: Path) -> None:
    """測試資料庫初始化與資料表建立。"""
    db_file = tmp_path / "test.db"
    # 初始化資料庫
    _ = Database(str(db_file))

    assert db_file.exists()

    # 驗證資料表是否存在
    with sqlite3.connect(db_file) as conn:
        sql = "SELECT name FROM sqlite_master WHERE type='table' AND name='executions'"
        cursor = conn.execute(sql)
        assert cursor.fetchone() is not None


def test_db_save_and_get_execution(tmp_path: Path) -> None:
    """測試儲存與讀取執行記錄。"""
    db = Database(str(tmp_path / "test.db"))

    inp = PipelineInput(topic="test topic", sources=["reddit"])
    output = PipelineOutput(
        input=inp,
        articles=[Article(id="1", source="reddit", source_id="1", title="Test")],
        llm_usage={"total_tokens": 100, "total_cost_usd": 0.001, "calls": 1},
    )

    exec_id = db.save_execution(output, status="success", demo=True, last_stage="report")
    assert exec_id > 0

    # 測試讀取
    exec_data = db.get_execution(exec_id)
    assert exec_data is not None
    assert exec_data["topic"] == "test topic"
    assert exec_data["status"] == "success"
    assert exec_data["demo"] == 1
    assert exec_data["last_completed_stage"] == "report"


def test_db_update_execution(tmp_path: Path) -> None:
    """測試更新執行記錄。."""
    db = Database(str(tmp_path / "test.db"))

    inp = PipelineInput(topic="update test", sources=["github"])
    output = PipelineOutput(input=inp)

    exec_id = db.save_execution(output, status="running")

    # 更新狀態
    output.llm_usage = {"total_tokens": 500}
    db.update_execution(exec_id, output, status="success", last_stage="extract")

    updated = db.get_execution(exec_id)
    assert updated is not None
    assert updated["status"] == "success"
    assert updated["total_tokens"] == 500
    assert updated["last_completed_stage"] == "extract"


def test_db_history(tmp_path: Path) -> None:
    """測試取得歷史記錄列表。."""
    db = Database(str(tmp_path / "test.db"))

    inp = PipelineInput(topic="h1", sources=["reddit"])
    db.save_execution(PipelineOutput(input=inp))

    inp2 = PipelineInput(topic="h2", sources=["github"])
    db.save_execution(PipelineOutput(input=inp2))

    history = db.get_history(limit=5)
    assert len(history) == 2
    assert history[0]["topic"] == "h2"  # 最新優先
