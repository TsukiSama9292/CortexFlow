"""JSON Reporter — 將情報結果輸出為結構化 JSON 檔案。."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortexflow.core.pipeline import StageResult
    from cortexflow.core.schema import Article, PipelineInput, ReportContent


class JSONReporter:
    """以 JSON 格式輸出情報報告。."""

    def generate(
        self,
        articles: list[Article],
        inp: PipelineInput,
        stage_results: list[StageResult],
        errors: list[dict[str, str]],
        report_content: ReportContent | None = None,
    ) -> None:
        """產生 JSON 報告並寫入 inp.output_path。."""
        report = self._build(articles, inp, stage_results, errors, report_content)
        output = Path(inp.output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    def _build(
        self,
        articles: list[Article],
        inp: PipelineInput,
        stage_results: list[StageResult],
        errors: list[dict[str, str]],
        report_content: ReportContent | None = None,
    ) -> dict[str, Any]:
        meta = {
            "topic": inp.topic,
            "sources": inp.sources,
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "total_articles": len(articles),
        }

        stage_stats: dict[str, dict[str, Any]] = {}
        for sr in stage_results:
            stage_stats[sr.stage_name] = {
                "success": sr.success,
                "duration": sr.duration,
                "items_count": sr.items_count,
                "error": sr.error,
            }

        articles_data = [self._serialize_article(a) for a in articles]

        result: dict[str, Any] = {
            "meta": meta,
            "stages": stage_stats,
            "errors": errors,
            "articles": articles_data,
        }
        if report_content:
            result["analysis"] = report_content.model_dump(mode="json")

        return result

    def _serialize_article(self, article: Article) -> dict[str, Any]:
        return article.model_dump(mode="json")
