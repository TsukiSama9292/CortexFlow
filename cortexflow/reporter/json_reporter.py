"""JSON Reporter — 將情報結果輸出為結構化 JSON 檔案。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from cortexflow.core.schema import Article, PipelineInput, ReportContent

if TYPE_CHECKING:
    from cortexflow.core.pipeline import StageResult


class JSONReporter:
    """以 JSON 格式輸出情報報告。"""

    def generate(
        self,
        articles: list[Article],
        inp: PipelineInput,
        stage_results: list[StageResult],
        errors: list[dict],
        report_content: ReportContent | None = None,
    ) -> None:
        """產生 JSON 報告並寫入 inp.output_path。"""
        report = self._build(articles, inp, stage_results, errors, report_content)
        output = Path(inp.output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _build(
        self,
        articles: list[Article],
        inp: PipelineInput,
        stage_results: list[StageResult],
        errors: list[dict],
        report_content: ReportContent | None = None,
    ) -> dict:
        meta = {
            "topic": inp.topic,
            "sources": inp.sources,
            "generated_at": datetime.now().isoformat(),
            "total_articles": len(articles),
        }

        stage_stats: dict[str, dict] = {}
        for sr in stage_results:
            stage_stats[sr.stage_name] = {
                "success": sr.success,
                "duration_seconds": sr.duration,
                "items_count": sr.items_count,
                "error": sr.error,
            }

        passed_articles = [a for a in articles if a.llm_judge_passed is not False]
        articles_data = [self._serialize_article(a) for a in passed_articles]

        result: dict = {
            "meta": meta,
            "stage_stats": stage_stats,
            "articles": articles_data,
            "errors": errors,
        }

        if report_content:
            result["report_content"] = report_content.model_dump()

        return result

    def _serialize_article(self, article: Article) -> dict:
        data = article.model_dump()
        for field in ("created_at", "fetched_at"):
            val = data.get(field)
            if isinstance(val, datetime):
                data[field] = val.isoformat()
        return data
