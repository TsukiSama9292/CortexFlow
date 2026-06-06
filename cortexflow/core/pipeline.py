"""Pipeline Orchestrator — 依序執行 Stage 1→5 的核心協調器。

架構：
  Fetch → Normalize → FastExtract → Analyze(併發) → Synthesize → Report

Stage 4 (Analyze) 是 Map-Reduce 模式：
  - Map: 所有文章併發進行 LLM 分析（評分+摘要+子分析）
  - Reduce: 彙總所有子分析為最終報告
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from rich.console import Console

from cortexflow.config.settings import settings
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

console = Console()


@dataclass
class StageResult:
    """單一 Stage 的執行結果記錄。"""
    stage_name: str
    success: bool
    duration: float
    items_count: int = 0
    error: str | None = None


class Pipeline:
    """五階段固定管道協調器。"""

    def __init__(self, inp: PipelineInput) -> None:
        self.inp = inp
        self.articles: list[Article] = []
        self.analyses: list[ArticleAnalysis] = []
        self.stage_results: list[StageResult] = []
        self.errors: list[dict] = []
        self.llm_usage: dict = {
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "calls": 0,
        }
        self.report_content: ReportContent | None = None

    # ────────────────────────────
    # 公開介面
    # ────────────────────────────

    async def run(self) -> PipelineOutput:
        """執行完整管道，回傳結構化結果。"""
        console.rule("[bold blue]CortexFlow Pipeline 開始")

        # Stage 1: Fetch
        if "reddit" in self.inp.sources:
            await self._run_stage("fetch_reddit", self._fetch_reddit)
        if "github" in self.inp.sources:
            await self._run_stage("fetch_github", self._fetch_github)

        # Stage 2: Normalize
        await self._run_stage("normalize", self._normalize)

        # Stage 3: FastExtract（trafilatura + BS4, 無 FireCrawl）
        await self._run_stage("extract", self._extract)

        # Stage 4: Analyze（併發 LLM 評分+摘要+子分析）
        if settings.openai_api_key:
            await self._run_stage("analyze", self._analyze)
        else:
            console.print("[yellow]⚠ 未設定 OPENAI_API_KEY，跳過 LLM 分析階段")

        # Stage 4.5: Synthesize（彙總子分析 → 最終報告）
        if settings.openai_api_key and self.analyses:
            await self._run_stage("synthesize", self._synthesize)
        else:
            console.print("[yellow]⚠ 跳過報告合成階段（需 LLM + 有分析結果）")

        # Stage 5: Report
        await self._run_stage("report", self._report)

        self._print_summary()
        return self._build_output()

    # ────────────────────────────
    # Stage 執行包裝器
    # ────────────────────────────

    async def _run_stage(self, name: str, fn: Callable) -> None:
        """執行單一 Stage，含計時與錯誤捕捉。"""
        t0 = time.monotonic()
        try:
            await fn()
            elapsed = time.monotonic() - t0
            result = StageResult(
                stage_name=name,
                success=True,
                duration=elapsed,
                items_count=len(self.articles),
            )
            console.print(f"[green]✔ {name} 完成 ({elapsed:.2f}s)")
        except Exception as exc:
            elapsed = time.monotonic() - t0
            result = StageResult(
                stage_name=name,
                success=False,
                duration=elapsed,
                error=str(exc),
            )
            console.print(f"[red]✘ {name} 失敗 ({elapsed:.2f}s): {exc}")
            self.errors.append({"stage": name, "error": str(exc)})
        self.stage_results.append(result)

    # ────────────────────────────
    # Stage 1: Fetch
    # ────────────────────────────

    async def _fetch_reddit(self) -> None:
        from cortexflow.fetchers.reddit_fetcher import RedditFetcher

        fetcher = RedditFetcher()
        raw = await fetcher.fetch(self.inp.topic, self.inp.max_results_per_source)
        self.articles.extend(raw)

    async def _fetch_github(self) -> None:
        from cortexflow.fetchers.github_fetcher import GitHubFetcher

        fetcher = GitHubFetcher()
        raw = await fetcher.fetch(self.inp.topic, self.inp.max_results_per_source)
        self.articles.extend(raw)

    # ────────────────────────────
    # Stage 2: Normalize
    # ────────────────────────────

    async def _normalize(self) -> None:
        normalizer = Normalizer()
        self.articles = normalizer.deduplicate(self.articles)

    # ────────────────────────────
    # Stage 3: FastExtract（取代 FireCrawl）
    # ────────────────────────────

    async def _extract(self) -> None:
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
            self.articles, threshold=self.inp.relevance_threshold
        )

        # 更新 articles 只保留通過的（確保後續 stage 一致）
        passed_ids = {a.article_id for a in self.analyses}
        self.articles = [a for a in self.articles if a.id in passed_ids]

        # 記錄 LLM 用量
        self.llm_usage["total_tokens"] += analyzer.total_tokens
        self.llm_usage["total_cost_usd"] += analyzer.total_cost_usd
        self.llm_usage["calls"] += analyzer.calls

    # ────────────────────────────
    # Stage 4.5: Synthesize（彙總子分析）
    # ────────────────────────────

    async def _synthesize(self) -> None:
        from cortexflow.filter.synthesizer import Synthesizer

        synthesizer = Synthesizer(topic=self.inp.topic)
        result = await synthesizer.synthesize(self.analyses)
        if result:
            self.report_content = result
            console.print(f"  報告合成: {result.title[:60]}...")
        else:
            console.print("  [yellow]⚠ 報告合成失敗")

        self.llm_usage["total_tokens"] += synthesizer.total_tokens
        self.llm_usage["total_cost_usd"] += synthesizer.total_cost_usd
        self.llm_usage["calls"] += synthesizer.calls

    # ────────────────────────────
    # Stage 5: Report
    # ────────────────────────────

    async def _report(self) -> None:
        if self.inp.output_format == "json":
            reporter = JSONReporter()
        else:
            reporter = MarkdownReporter()
        reporter.generate(
            self.articles, self.inp, self.stage_results, self.errors, self.report_content
        )

    # ────────────────────────────
    # 內部輔助
    # ────────────────────────────

    def _print_summary(self) -> None:
        console.rule("[bold blue]Pipeline 執行摘要")
        for r in self.stage_results:
            status = "[green]✔" if r.success else "[red]✘"
            console.print(f"  {status} {r.stage_name:20s}  {r.duration:6.2f}s  {r.items_count} items")
        if self.llm_usage["calls"] > 0:
            console.print(f"\n  LLM 呼叫: {self.llm_usage['calls']} 次")
            console.print(f"  Token 用量: {self.llm_usage['total_tokens']}")
            console.print(f"  預估成本: ${self.llm_usage['total_cost_usd']:.4f}")

    def _build_output(self) -> PipelineOutput:
        stats = {}
        for r in self.stage_results:
            stats[r.stage_name] = {
                "success": r.success,
                "duration_seconds": r.duration,
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
