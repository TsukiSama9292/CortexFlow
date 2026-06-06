"""統一資料模型 — 跨渠道的標準化 Article Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Article(BaseModel):
    """經過標準化處理後的單一情報條目。"""

    # ── 識別 ──
    id: str = Field(description="全域唯一 ID（由 source + source_id 組成）")
    source: Literal["reddit", "github"] = Field(description="來源渠道")
    source_id: str = Field(description="在原始渠道中的 ID")

    # ── 內容 ──
    title: str = Field(default="", description="標題")
    author: str = Field(default="", description="作者/使用者名稱")
    text: str = Field(default="", description="原始內容文字")
    url: str = Field(default="", description="原文連結")
    score: int = Field(default=0, description="原始互動分數（likes/upvotes/stars）")
    created_at: datetime | None = Field(default=None, description="原始發佈時間")

    # ── 後設 ──
    fetched_at: datetime = Field(
        default_factory=datetime.now, description="系統採集時間"
    )

    # ── 擴充（Stage 3 填入） ──
    extracted_html: str | None = Field(default=None, description="FireCrawl 提取的 Markdown")

    # ── LLM 過濾結果（Stage 4 填入） ──
    relevance_score: float | None = Field(default=None, ge=0.0, le=10.0)
    summary: str | None = Field(default=None)
    sub_analysis: str | None = Field(default=None, description="深度子分析")
    key_insights: list[str] | None = Field(default=None, description="關鍵洞察")
    llm_judge_passed: bool | None = Field(default=None)


class ArticleAnalysis(BaseModel):
    """單篇文章的 LLM 分析結果 — 整合評分、摘要、子分析。"""

    article_id: str = Field(description="對應的 Article ID")
    title: str = Field(description="文章標題")
    url: str = Field(description="文章連結")
    relevance_score: float = Field(ge=0.0, le=10.0, description="相關性分數")
    summary: str = Field(description="繁體中文摘要（50-100 字）")
    sub_analysis: str = Field(description="深度子分析（100-150 字，分析此文章的獨特洞察）")
    key_insights: list[str] = Field(description="2-3 條關鍵洞察")


class ReportSection(BaseModel):
    """報告中的一個章節。"""
    emoji: str = Field(description="章節 emoji 圖示")
    title: str = Field(description="章節標題")
    content: str = Field(description="章節內文")


class ReportContent(BaseModel):
    """LLM 合成的完整報告結構。"""
    title: str = Field(description="報告主標題")
    sections: list[ReportSection] = Field(description="報告章節列表")
    key_points: list[str] = Field(description="📌 重點總結")
    links: list[str] = Field(description="相關連結列表")


class PipelineInput(BaseModel):
    """管道執行參數。"""

    topic: str = Field(description="研究主題")
    sources: list[Literal["reddit", "github"]] = Field(
        default=["reddit", "github"]
    )
    max_results_per_source: int = Field(default=20, ge=1, le=100)
    relevance_threshold: float = Field(default=5.0, ge=0.0, le=10.0)
    output_format: Literal["markdown", "json"] = Field(default="markdown")
    output_path: str = Field(default="output_report.md")


class PipelineOutput(BaseModel):
    """管道執行結果。"""

    input: PipelineInput
    articles: list[Article] = Field(default_factory=list)
    stage_stats: dict[str, dict] = Field(default_factory=dict)
    errors: list[dict] = Field(default_factory=list)
    llm_usage: dict = Field(default_factory=dict)
    report_content: ReportContent | None = Field(default=None)
