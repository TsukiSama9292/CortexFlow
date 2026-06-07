"""CortexFlow 資料庫模組 — 基於 SQLAlchemy ORM 與 PostgreSQL。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from cortexflow.config.settings import settings
from cortexflow.core.models import Execution

if TYPE_CHECKING:
    from cortexflow.core.schema import PipelineOutput


class Database:
    """SQLAlchemy 資料庫管理類，負責執行紀錄持久化。"""

    def __init__(self, database_url: str | None = None) -> None:
        """初始化異步引擎與 Session 工廠。"""
        url = database_url or settings.database_url
        self.engine = create_async_engine(url, pool_pre_ping=True)
        self.SessionLocal = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def save_execution(
        self,
        output: PipelineOutput,
        status: str = "success",
        *,
        demo: bool = False,
        last_stage: str | None = None,
    ) -> int:
        """儲存一次 Pipeline 執行結果。"""
        duration = sum(s.get("duration", 0) for s in output.stage_stats.values())

        async with self.SessionLocal() as session:
            execution = Execution(
                topic=output.input.topic,
                timestamp=datetime.now(UTC),
                input_json=output.input.model_dump(mode="json"),
                output_json=output.model_dump(mode="json"),
                status=status,
                duration_seconds=duration,
                total_tokens=output.llm_usage.get("total_tokens", 0),
                demo=1 if demo else 0,
                last_completed_stage=last_stage,
            )
            session.add(execution)
            await session.commit()
            await session.refresh(execution)
            return execution.id

    async def update_execution(
        self,
        execution_id: int,
        output: PipelineOutput,
        status: str,
        *,
        last_stage: str | None = None,
    ) -> None:
        """更新現有的執行記錄。"""
        duration = sum(s.get("duration", 0) for s in output.stage_stats.values())

        async with self.SessionLocal() as session:
            stmt = (
                update(Execution)
                .where(Execution.id == execution_id)
                .values(
                    output_json=output.model_dump(mode="json"),
                    status=status,
                    duration_seconds=duration,
                    total_tokens=output.llm_usage.get("total_tokens", 0),
                    last_completed_stage=last_stage,
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def get_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """取得最近的執行記錄。"""
        async with self.SessionLocal() as session:
            stmt = select(Execution).order_by(Execution.timestamp.desc()).limit(limit)
            result = await session.execute(stmt)
            executions = result.scalars().all()
            return [
                {
                    "id": e.id,
                    "topic": e.topic,
                    "timestamp": e.timestamp.isoformat(),
                    "status": e.status,
                    "duration_seconds": e.duration_seconds,
                    "total_tokens": e.total_tokens,
                    "last_completed_stage": e.last_completed_stage,
                }
                for e in executions
            ]

    async def get_execution(self, execution_id: int) -> dict[str, Any] | None:
        """取得特定執行記錄的完整資料。"""
        async with self.SessionLocal() as session:
            stmt = select(Execution).where(Execution.id == execution_id)
            result = await session.execute(stmt)
            e = result.scalar_one_or_none()
            if not e:
                return None
            return {
                "id": e.id,
                "topic": e.topic,
                "timestamp": e.timestamp.isoformat(),
                "input_json": e.input_json,
                "output_json": e.output_json,
                "status": e.status,
                "duration_seconds": e.duration_seconds,
                "total_tokens": e.total_tokens,
                "demo": bool(e.demo),
                "last_completed_stage": e.last_completed_stage,
            }

    async def close(self) -> None:
        """關閉資料庫引擎。"""
        await self.engine.dispose()
