"""CortexFlow 資料庫模組 — 負責執行記錄持久化。."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from cortexflow.core.schema import PipelineInput, PipelineOutput


class Database:
    """SQLite 資料庫管理類，儲存執行歷史。."""

    def __init__(self, db_path: str = "outputs/history.db") -> None:
        """初始化資料庫並建立資料表。."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        """建立必要的資料表。."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    input_json TEXT NOT NULL,
                    output_json TEXT,
                    status TEXT,
                    duration_seconds REAL,
                    total_tokens INTEGER DEFAULT 0,
                    demo INTEGER DEFAULT 0
                )
                """
            )
            conn.commit()

    def save_execution(self, output: PipelineOutput, status: str = "success", demo: bool = False) -> int:
        """儲存一次 Pipeline 執行結果。."""
        # 計算總耗時
        duration = sum(s.get("duration", 0) for s in output.stage_stats.values())
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO executions (
                    topic, timestamp, input_json, output_json, status, duration_seconds, total_tokens, demo
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    output.input.topic,
                    datetime.now(UTC).isoformat(),
                    output.input.model_dump_json(),
                    output.model_dump_json(),
                    status,
                    duration,
                    output.llm_usage.get("total_tokens", 0),
                    1 if demo else 0,
                ),
            )
            conn.commit()
            return cursor.lastrowid or 0

    def get_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """取得最近的執行記錄。."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id, topic, timestamp, status, duration_seconds, total_tokens "
                "FROM executions ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_execution(self, execution_id: int) -> dict[str, Any] | None:
        """取得特定執行記錄的完整資料。."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM executions WHERE id = ?", (execution_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
