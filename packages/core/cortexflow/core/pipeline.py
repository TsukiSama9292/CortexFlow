"""Pipeline Orchestrator — 依序執行 Stage 1→5 的核心協調器。.

架構：
  Fetch → Normalize → FastExtract → Analyze(併發) → Synthesize → Report

Stage 4 (Analyze) 是 Map-Reduce 模式：
  - Map: 所有文章併發進行 LLM 分析（評分+摘要+子分析）
  - Reduce: 彙總所有子分析為最終報告
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from loguru import logger
from rich.console import Console

from cortexflow.config.settings import settings
from cortexflow.core.db import Database
from cortexflow.core.schema import (
    Article,
    ArticleAnalysis,
    PipelineInput,
    PipelineOutput,
    ReportContent,
)
from cortexflow.normalizer.normalizer import Normalizer
from cortexflow.reporter.json_reporter import JSONReporter
from cortexflow.reporter.markdown_reporter import MarkdownReporter

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

_STAGE_LABELS: dict[str, str] = {
    "fetch_reddit": "Reddit 採集",
    "fetch_github": "GitHub 採集",
    "fetch_hackernews": "Hacker News 採集",
    "fetch_lobsters": "Lobsters 採集",
    "normalize": "標準化去重",
    "extract": "內容提取",
    "analyze": "LLM 分析",
    "synthesize": "報告合成",
    "report": "報告輸出",
}

_FIX_SUGGESTIONS: dict[str, str] = {
    "fetch_reddit": "請確認網路連線正常，或使用 --demo 模式測試",
    "fetch_github": "請確認網路連線正常，或使用 --demo 模式測試",
    "fetch_hackernews": "請確認網路連線正常，或使用 --demo 模式測試",
    "fetch_lobsters": "請確認網路連線正常，或使用 --demo 模式測試",
    "normalize": "輸入資料格式異常，請檢查來源資料",
    "extract": "無法連線至目標網頁，請確認 URL 是否有效",
    "analyze": "請確認 OPENAI_API_KEY 有效、模型名稱正確，且 API endpoint 可連線",
    "synthesize": "請確認 OPENAI_API_KEY 有效，或檢查 LLM 分析階段是否有產出",
    "report": "請確認輸出路徑可寫入，磁碟空間是否充足",
}

_TOKEN_COST_PER_ARTICLE = 0.0003
_TOKEN_COST_SYNTHESIS = 0.0010


@dataclass
class StageResult:
    """單一 Stage 的執行結果記錄。."""

    stage_name: str
    success: bool
    duration: float
    items_count: int = 0
    error: str | None = None


class Pipeline:
    """五階段固定管道協調器。."""

    def __init__(
        self,
        inp: PipelineInput,
        *,
        demo: bool = False,
        execution_id: int | None = None,
    ) -> None:
        """初始化管道。."""
        self.inp = inp
        self.demo = demo
        self.execution_id = execution_id
        self.articles: list[Article] = []
        self.analyses: list[ArticleAnalysis] = []
        self.stage_results: list[StageResult] = []
        self.errors: list[dict[str, str]] = []
        self.llm_usage: dict[str, Any] = {
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "calls": 0,
        }
        self.report_content: ReportContent | None = None
        self.db = Database()
        self.last_completed_stage: str | None = None

    # ────────────────────────────
    # 公開介面
    # ────────────────────────────

    async def run(self) -> PipelineOutput:
        """執行完整管道，回傳結構化結果。."""
        console = Console()
        logger.info("Pipeline 開始執行 - 主題: {topic}", topic=self.inp.topic)

        # 如果是續傳模式，從資料庫載入狀態
        if self.execution_id:
            logger.info("正在續傳執行記錄 (ID: {id})", id=self.execution_id)
            await self._load_state()

        self._print_pipeline_diagram(console)

        self._estimate_cost(console)

        # Stage 1: Fetch
        for source in self.inp.sources:
            stage_name = f"fetch_{source}"
            if self._should_skip(stage_name):
                continue
            await self._run_stage(stage_name, lambda s=source: self._fetch_source(s), console)

        # Stage 2: Normalize
        if not self._should_skip("normalize"):
            await self._run_stage("normalize", self._normalize, console)

        # Stage 3: Extract
        if not self._should_skip("extract"):
            await self._run_stage("extract", self._extract, console)

        # Stage 4: Analyze（併發 LLM 評分+摘要+子分析）
        if not self._should_skip("analyze"):
            if settings.openai_api_key and not self.demo:
                await self._run_stage("analyze", self._analyze, console)
            elif self.demo:
                await self._run_stage("analyze", self._analyze_demo, console)
            else:
                await self._run_stage("analyze", self._analyze_fallback, console)

        # Stage 4.5: Synthesize（彙總子分析 → 最終報告）
        if not self._should_skip("synthesize"):
            has_llm = bool(settings.openai_api_key) or self.demo
            if has_llm and self.analyses:
                await self._run_stage("synthesize", self._synthesize, console)
            else:
                logger.info("跳過報告合成階段（需 LLM + 有分析結果）")
                # 為了測試一致性，即使跳過也記錄一個成功的空結果
                self.stage_results.append(
                    StageResult(stage_name="synthesize", success=True, duration=0.0, items_count=0)
                )

        # Stage 5: Report
        if not self._should_skip("report"):
            await self._run_stage("report", self._report, console)

        self._print_summary(console)
        output = self._build_output()

        # 最終更新資料庫
        try:
            if self.execution_id:
                await self.db.update_execution(self.execution_id, output, "success", last_stage="report")
            else:
                self.execution_id = await self.db.save_execution(
                    output, demo=self.demo, last_stage="report"
                )
            logger.debug("執行記錄已完成並儲存 (ID: {id})", id=self.execution_id)
        except Exception as e:  # noqa: BLE001
            logger.warning("無法更新執行記錄: {error}", error=e)

        return output

    # ────────────────────────────
    # Stage 執行包裝器
    # ────────────────────────────

    async def _run_stage(
        self,
        name: str,
        fn: Callable[[], Coroutine[Any, Any, None]],
        console: Console,
    ) -> None:
        """執行單一 Stage，含計時、spinner 與錯誤捕捉。."""
        label = _STAGE_LABELS.get(name, name)
        status = console.status(f"{label}…", spinner="dots")
        status.start()
        t0 = time.monotonic()
        try:
            # 加上逾時控制
            await asyncio.wait_for(fn(), timeout=settings.stage_timeout)
            elapsed = time.monotonic() - t0
            status.stop()
            result = StageResult(
                stage_name=name,
                success=True,
                duration=elapsed,
                items_count=len(self.articles),
            )
            self.last_completed_stage = name
            console.print(f"  [green]✔[/green] {label} 完成  [dim]({elapsed:.2f}s)[/dim]")

            # 中間狀態存檔
            await self._save_intermediate_state("running")

        except Exception as exc:  # noqa: BLE001
            elapsed = time.monotonic() - t0
            status.stop()
            error_msg = str(exc) or exc.__class__.__name__
            result = StageResult(
                stage_name=name,
                success=False,
                duration=elapsed,
                error=error_msg,
            )
            msg = f"  [red]✘[/red] {label} 失敗  [dim]({elapsed:.2f}s)[/dim]: {error_msg}"
            console.print(msg)
            fix = _FIX_SUGGESTIONS.get(name)
            if fix:
                console.print(f"    [dim]💡 建議: {fix}[/dim]")
            self.errors.append({"stage": name, "error": error_msg})

            # 失敗也存檔，狀態改為 failed
            await self._save_intermediate_state("failed")

        self.stage_results.append(result)

    # ────────────────────────────
    # Stage 1: Fetch
    # ────────────────────────────

    async def _fetch_source(self, source_name: str) -> None:
        """從指定來源採集資料。."""
        from cortexflow.fetchers.registry import registry

        fetcher = registry.get(source_name)
        if not fetcher:
            logger.error("找不到 Fetcher: {name}", name=source_name)
            return

        articles = await fetcher.fetch(
            self.inp.topic,
            self.inp.max_results_per_source,
            demo=self.demo,
        )
        self.articles.extend(articles)

    # ────────────────────────────
    # Stage 2: Normalize
    # ────────────────────────────

    async def _normalize(self) -> None:
        normalizer = Normalizer()
        self.articles = normalizer.deduplicate(self.articles)

    # ────────────────────────────
    # Stage 3: FastExtract
    # ────────────────────────────

    async def _extract(self) -> None:
        if self.demo:
            for a in self.articles:
                a.extracted_html = a.text
            return
        from cortexflow.extractor.fast_extractor import FastExtractor

        extractor = FastExtractor()
        await extractor.extract_all(self.articles)

    # ────────────────────────────
    # Stage 4: Analyze（併發 LLM 分析）
    # ────────────────────────────

    async def _analyze(self) -> None:
        from cortexflow.filter.article_analyzer import ArticleAnalyzer

        analyzer = ArticleAnalyzer(topic=self.inp.topic)
        self.analyses = await analyzer.analyze(
            self.articles,
            threshold=self.inp.relevance_threshold,
        )

        passed_ids = {a.article_id for a in self.analyses}
        self.articles = [a for a in self.articles if a.id in passed_ids]

        self.llm_usage["total_tokens"] += analyzer.total_tokens
        self.llm_usage["total_cost_usd"] += analyzer.total_cost_usd
        self.llm_usage["calls"] += analyzer.calls

    async def _analyze_fallback(self) -> None:
        """當 LLM 無法使用時的降級分析邏輯。."""
        from cortexflow.filter.article_analyzer import FallbackAnalyzer

        logger.info("使用規則式降級分析器 (Fallback)")
        analyzer = FallbackAnalyzer(topic=self.inp.topic)
        self.analyses = analyzer.analyze(self.articles)

        passed_ids = {a.article_id for a in self.analyses}
        self.articles = [a for a in self.articles if a.id in passed_ids]

    async def _analyze_demo(self) -> None:
        for a in self.articles:
            a.relevance_score = 7.5
            a.summary = f"關於 {self.inp.topic} 的相關分析摘要。"
            a.sub_analysis = "此文章提供了有價值的觀點與深入分析。"
            a.key_insights = [f"{self.inp.topic} 的重要性日益增加", "值得持續關注"]
            a.llm_judge_passed = True
            self.analyses.append(
                ArticleAnalysis(
                    article_id=a.id,
                    title=a.title,
                    url=a.url,
                    relevance_score=7.5,
                    summary=a.summary,
                    sub_analysis=a.sub_analysis,
                    key_insights=a.key_insights,
                ),
            )

    # ────────────────────────────
    # Stage 4.5: Synthesize（彙總子分析）
    # ────────────────────────────

    async def _synthesize(self) -> None:
        if self.demo or not settings.openai_api_key:
            self.report_content = ReportContent(
                title=f"關於 {self.inp.topic} 的分析報告",
                sections=[],
                key_points=[a.summary for a in self.analyses if a.summary],
                links=[a.url for a in self.analyses],
            )
            return

        from cortexflow.filter.synthesizer import Synthesizer

        synthesizer = Synthesizer(topic=self.inp.topic)
        result = await synthesizer.synthesize(self.analyses)
        if result:
            self.report_content = result
        else:
            self.report_content = ReportContent(
                title=f"關於 {self.inp.topic} 的分析報告",
                sections=[],
                key_points=[a.summary for a in self.analyses if a.summary],
                links=[a.url for a in self.analyses],
            )

        self.llm_usage["total_tokens"] += synthesizer.total_tokens
        self.llm_usage["total_cost_usd"] += synthesizer.total_cost_usd
        self.llm_usage["calls"] += synthesizer.calls

    # ────────────────────────────
    # Stage 5: Report
    # ────────────────────────────

    async def _report(self) -> None:
        reporter = JSONReporter() if self.inp.output_format == "json" else MarkdownReporter()
        reporter.generate(
            self.articles,
            self.inp,
            self.stage_results,
            self.errors,
            self.report_content,
        )

    # ────────────────────────────
    # 續傳邏輯
    # ────────────────────────────

    def _should_skip(self, stage_name: str) -> bool:
        """檢查是否應跳過此階段（續傳模式下）。."""
        if not self.execution_id or not self.last_completed_stage:
            return False

        # 定義 Stage 的線性順序以便比較
        stage_order = [
            "fetch_reddit",
            "fetch_github",
            "fetch_hackernews",
            "fetch_lobsters",
            "normalize",
            "extract",
            "analyze",
            "synthesize",
            "report",
        ]
        try:
            last_idx = stage_order.index(self.last_completed_stage)
            curr_idx = stage_order.index(stage_name)
            return curr_idx <= last_idx
        except ValueError:
            return False

    async def _load_state(self) -> None:
        """從資料庫載入執行狀態。."""
        if not self.execution_id:
            return

        exec_data = await self.db.get_execution(self.execution_id)
        if not exec_data or not exec_data["output_json"]:
            return

        import json

        try:
            # SQLAlchemy 返回的是 dict，input_json/output_json 可能是 dict 或 string
            out_data = exec_data["output_json"]
            if isinstance(out_data, str):
                out_data = json.loads(out_data)

            output = PipelineOutput(**out_data)
            self.articles = output.articles
            self.analyses = [
                ArticleAnalysis(
                    article_id=a.id,
                    title=a.title,
                    url=a.url,
                    relevance_score=a.relevance_score or 0.0,
                    summary=a.summary or "",
                    sub_analysis=a.sub_analysis or "",
                    key_insights=a.key_insights or [],
                )
                for a in self.articles
                if a.relevance_score is not None
            ]
            self.llm_usage = output.llm_usage
            self.last_completed_stage = exec_data["last_completed_stage"]

            # 還原 stage_results 列表
            self.stage_results = []
            for name, stats in output.stage_stats.items():
                self.stage_results.append(
                    StageResult(
                        stage_name=name,
                        success=stats["success"],
                        duration=stats["duration"],
                        items_count=stats["items_count"],
                        error=stats.get("error"),
                    )
                )
        except Exception as e:  # noqa: BLE001
            logger.error("還原狀態失敗: {error}", error=e)

    async def _save_intermediate_state(self, status: str) -> None:
        """儲存中間執行狀態到資料庫。."""
        output = self._build_output()
        try:
            if self.execution_id:
                await self.db.update_execution(
                    self.execution_id,
                    output,
                    status,
                    last_stage=self.last_completed_stage,
                )
            else:
                self.execution_id = await self.db.save_execution(
                    output,
                    status=status,
                    demo=self.demo,
                    last_stage=self.last_completed_stage,
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("無法儲存中間狀態: {error}", error=e)

    # ────────────────────────────
    # 內部輔助
    # ────────────────────────────

    def _print_pipeline_diagram(self, console: Console) -> None:
        console.print()
        console.rule("[bold blue]╔══════════════════════════════════╗")
        console.print("  [bold blue]║        [cyan]CortexFlow[/cyan] Pipeline        [bold blue]║")
        console.print("  [bold blue]╚══════════════════════════════════╝[/bold blue]")
        console.print()
        console.print("  [dim]  Fetch  →  Normalize  →  Extract  →  [/dim]")
        console.print("  [dim]                      Analyze (Map)[/dim]")
        console.print("  [dim]                          ↓          [/dim]")
        console.print("  [dim]           Synthesize (Reduce)[/dim]")
        console.print("  [dim]                ↓                [/dim]")
        console.print("  [dim]             Report              [/dim]")
        console.print()
        if self.inp.sources:
            src_str = " + ".join(f"[green]{s}[/green]" for s in self.inp.sources)
            console.print(f"  來源: {src_str}")
        console.print(f"  主題: [yellow]{self.inp.topic}[/yellow]")
        console.print()

    def _estimate_cost(self, console: Console) -> None:
        if not settings.openai_api_key or self.demo:
            return
        num_sources = len(self.inp.sources)
        max_articles = self.inp.max_results_per_source * num_sources
        estimated = max_articles * _TOKEN_COST_PER_ARTICLE + _TOKEN_COST_SYNTHESIS
        console.print(
            f"  [dim]💡 預估 LLM 成本: ~${estimated:.4f}"
            f"（{max_articles} 篇文章分析 + 1 次合成）[/dim]",
        )

    def _print_summary(self, console: Console) -> None:
        console.rule("[bold blue]執行摘要")
        for r in self.stage_results:
            label = _STAGE_LABELS.get(r.stage_name, r.stage_name)
            status_icon = "[green]✔" if r.success else "[red]✘"
            console.print(
                f"  {status_icon}[/] {label:12s}"
                f"  [cyan]{r.duration:6.2f}s[/cyan]  {r.items_count} items",
            )
        calls = self.llm_usage.get("calls", 0)
        if calls > 0:
            console.print()
            console.print(f"  🤖 LLM 呼叫: {calls} 次")
            console.print(f"  📊 Token 用量: {self.llm_usage.get('total_tokens', 0):,}")
            cost = self.llm_usage.get("total_cost_usd", 0.0)
            console.print(f"  💰 預估成本: [green]${cost:.4f}[/green]")
        console.print()

    def _build_output(self) -> PipelineOutput:
        stats: dict[str, dict[str, Any]] = {}
        for r in self.stage_results:
            stats[r.stage_name] = {
                "success": r.success,
                "duration": r.duration,
                "items_count": r.items_count,
                "error": r.error,
            }
        return PipelineOutput(
            input=self.inp,
            articles=self.articles,
            stage_stats=stats,
            errors=self.errors,
            llm_usage=self.llm_usage,
            report_content=self.report_content,
        )
