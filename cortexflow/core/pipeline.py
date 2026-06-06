"""Pipeline Orchestrator — 依序執行 Stage 1→5 的核心協調器。

架構：
  Fetch → Normalize → FastExtract → Analyze(併發) → Synthesize → Report

Stage 4 (Analyze) 是 Map-Reduce 模式：
  - Map: 所有文章併發進行 LLM 分析（評分+摘要+子分析）
  - Reduce: 彙總所有子分析為最終報告
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

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

_STAGE_LABELS: dict[str, str] = {
    "fetch_reddit": "Reddit 採集",
    "fetch_github": "GitHub 採集",
    "normalize": "標準化去重",
    "extract": "內容提取",
    "analyze": "LLM 分析",
    "synthesize": "報告合成",
    "report": "報告輸出",
}

_FIX_SUGGESTIONS: dict[str, str] = {
    "fetch_reddit": "請確認網路連線正常，或使用 --demo 模式測試",
    "fetch_github": "請確認網路連線正常，或使用 --demo 模式測試",
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
    """單一 Stage 的執行結果記錄。"""

    stage_name: str
    success: bool
    duration: float
    items_count: int = 0
    error: str | None = None


class Pipeline:
    """五階段固定管道協調器。"""

    def __init__(self, inp: PipelineInput, demo: bool = False) -> None:
        self.inp = inp
        self.demo = demo
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
        console = Console()

        self._print_pipeline_diagram(console)

        self._estimate_cost(console)

        # Stage 1: Fetch
        if "reddit" in self.inp.sources:
            await self._run_stage("fetch_reddit", self._fetch_reddit, console)
        if "github" in self.inp.sources:
            await self._run_stage("fetch_github", self._fetch_github, console)

        # Stage 2: Normalize
        await self._run_stage("normalize", self._normalize, console)

        # Stage 3: Extract
        await self._run_stage("extract", self._extract, console)

        # Stage 4: Analyze（併發 LLM 評分+摘要+子分析）
        if settings.openai_api_key and not self.demo:
            await self._run_stage("analyze", self._analyze, console)
        elif self.demo:
            await self._run_stage("analyze", self._analyze_demo, console)
        else:
            console.print("  [yellow]⚠ 未設定 OPENAI_API_KEY，跳過 LLM 分析階段")

        # Stage 4.5: Synthesize（彙總子分析 → 最終報告）
        has_llm = bool(settings.openai_api_key) or self.demo
        if has_llm and self.analyses:
            await self._run_stage("synthesize", self._synthesize, console)
        else:
            console.print("  [yellow]⚠ 跳過報告合成階段（需 LLM + 有分析結果）")

        # Stage 5: Report
        await self._run_stage("report", self._report, console)

        self._print_summary(console)
        return self._build_output()

    # ────────────────────────────
    # Stage 執行包裝器
    # ────────────────────────────

    async def _run_stage(self, name: str, fn: Callable, console: Console) -> None:
        """執行單一 Stage，含計時、spinner 與錯誤捕捉。"""
        label = _STAGE_LABELS.get(name, name)
        status = console.status(f"{label}…", spinner="dots")
        status.start()
        t0 = time.monotonic()
        try:
            await fn()
            elapsed = time.monotonic() - t0
            status.stop()
            result = StageResult(
                stage_name=name,
                success=True,
                duration=elapsed,
                items_count=len(self.articles),
            )
            console.print(f"  [green]✔[/green] {label} 完成  [dim]({elapsed:.2f}s)[/dim]")
        except Exception as exc:
            elapsed = time.monotonic() - t0
            status.stop()
            result = StageResult(
                stage_name=name,
                success=False,
                duration=elapsed,
                error=str(exc),
            )
            msg = f"  [red]✘[/red] {label} 失敗  [dim]({elapsed:.2f}s)[/dim]: {exc}"
            console.print(msg)
            fix = _FIX_SUGGESTIONS.get(name)
            if fix:
                console.print(f"    [dim]💡 建議: {fix}[/dim]")
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
        if self.demo:
            self._fetch_demo_github()
            return
        from cortexflow.fetchers.github_fetcher import GitHubFetcher

        fetcher = GitHubFetcher()
        raw = await fetcher.fetch(self.inp.topic, self.inp.max_results_per_source)
        self.articles.extend(raw)

    def _fetch_demo_github(self) -> None:
        import hashlib

        repos = [
            ("cortexflow", "情報 ETL Pipeline — 從社群雜訊到結構化情報"),
            ("langchain-ai/langchain", "Building applications with LLMs through composability"),
            ("openai/openai-cookbook", "Examples and guides for using the OpenAI API"),
            ("pydantic/pydantic", "Data validation using Python type hints"),
            ("encode/httpx", "A next generation HTTP client for Python"),
        ]
        for name, desc in repos:
            uid = f"github-{name}"
            self.articles.append(
                Article(
                    id=hashlib.sha256(uid.encode()).hexdigest()[:16],
                    source="github",
                    source_id=name,
                    title=name,
                    text=desc,
                    author=name.split("/")[0] if "/" in name else "",
                    url=f"https://github.com/{name}",
                    score=100,
                )
            )

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
            self.articles, threshold=self.inp.relevance_threshold
        )

        passed_ids = {a.article_id for a in self.analyses}
        self.articles = [a for a in self.articles if a.id in passed_ids]

        self.llm_usage["total_tokens"] += analyzer.total_tokens
        self.llm_usage["total_cost_usd"] += analyzer.total_cost_usd
        self.llm_usage["calls"] += analyzer.calls

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
                )
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
        if self.inp.output_format == "json":
            reporter = JSONReporter()
        else:
            reporter = MarkdownReporter()
        reporter.generate(
            self.articles,
            self.inp,
            self.stage_results,
            self.errors,
            self.report_content,
        )

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
            f"（{max_articles} 篇文章分析 + 1 次合成）[/dim]"
        )

    def _print_summary(self, console: Console) -> None:
        console.rule("[bold blue]執行摘要")
        for r in self.stage_results:
            label = _STAGE_LABELS.get(r.stage_name, r.stage_name)
            status_icon = "[green]✔" if r.success else "[red]✘"
            console.print(
                f"  {status_icon}[/] {label:12s}"
                f"  [cyan]{r.duration:6.2f}s[/cyan]  {r.items_count} items"
            )
        if self.llm_usage["calls"] > 0:
            console.print()
            console.print(f"  🤖 LLM 呼叫: {self.llm_usage['calls']} 次")
            console.print(f"  📊 Token 用量: {self.llm_usage['total_tokens']:,}")
            console.print(f"  💰 預估成本: [green]${self.llm_usage['total_cost_usd']:.4f}[/green]")
        console.print()

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
