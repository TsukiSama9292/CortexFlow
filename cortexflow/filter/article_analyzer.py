"""ArticleAnalyzer — 對單篇文章進行一次性 LLM 分析。.

整合三個任務到一次 LLM 呼叫：
1. 評分（Judge）：主題相關性 0.0~10.0
2. 摘要（Summarize）：繁體中文摘要 50-100 字
3. 子分析（Sub-Analyze）：深度洞察分析
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr
from rich.console import Console

from cortexflow.config.settings import settings
from cortexflow.core.schema import Article, ArticleAnalysis

if TYPE_CHECKING:
    from langchain_core.messages import AIMessage

console = Console()

_INPUT_TOKEN_COST = 0.15 / 1_000_000
_OUTPUT_TOKEN_COST = 0.60 / 1_000_000


class _RawAnalysis(BaseModel):
    """LLM 回傳的原始結構化分析結果。."""

    relevance_score: float = Field(ge=0.0, le=10.0, description="文章與主題的相關性分數")
    summary: str = Field(description="繁體中文摘要（50-100 字，客觀陳述）")
    sub_analysis: str = Field(description="深度子分析（100-150 字，分析此文章的獨特洞察與意義）")
    key_insights: list[str] = Field(description="2-3 條從此文章中提煉出的關鍵洞察")


class ArticleAnalyzer:
    """對 Articles 進行一次性 LLM 分析（併發執行）。."""

    def __init__(self, topic: str) -> None:
        """初始化分析器。.

        Args:
            topic: 研究主題。
        """
        self.topic = topic

        # type: ignore[call-arg]
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=SecretStr(settings.openai_api_key) if settings.openai_api_key else None,
            base_url=settings.openai_base_url or None,
            temperature=0.0,
        )

        self._prompt = ChatPromptTemplate.from_messages(  # pyright: ignore[reportUnknownMemberType]
            [
                (
                    "system",
                    "你是一個專業的情報分析師。針對一篇文章，你需要完成三項任務：\n\n"
                    "1️⃣ **相關性評分**（0.0~10.0）：\n"
                    "   - 10.0：完全相關，直接討論主題核心\n"
                    "   - 7.0~9.0：高度相關，深入探討相關面向\n"
                    "   - 4.0~6.0：部分相關，僅提及或間接關聯\n"
                    "   - 1.0~3.0：低度相關\n"
                    "   - 0.0：完全不相關\n\n"
                    "2️⃣ **繁體中文摘要**（50~100 字）：濃縮文章核心資訊\n\n"
                    "3️⃣ **深度子分析**（100~150 字）：分析此文章對研究主題的獨特洞察、"
                    "作者觀點、數據意義等\n\n"
                    "4️⃣ **關鍵洞察**：2-3 條從文章中提煉的具體洞察",
                ),
                (
                    "human",
                    "研究主題：{topic}\n\n"
                    "文章標題：{title}\n"
                    "文章來源：{source}\n"
                    "社群分數：{score}\n"
                    "原文連結：{url}\n\n"
                    "文章內容：\n{content}",
                ),
            ],
        )

        self._chain: Any = (
            self._prompt | self.llm.with_structured_output(_RawAnalysis, include_raw=True)
        )  # pyright: ignore[reportUnknownMemberType]

        # ── 用量追蹤 ──
        self.total_tokens: int = 0
        self.total_cost_usd: float = 0.0
        self.calls: int = 0

    async def analyze(
        self, articles: list[Article], threshold: float = 5.0,
    ) -> list[ArticleAnalysis]:
        """對所有文章進行併發 LLM 分析。.

        每篇文章獨立呼叫 LLM（併發執行），只保留通過 threshold 的結果。
        """
        if not articles:
            return []

        sem = asyncio.Semaphore(5)  # 控制併發數

        async def _analyze_one(article: Article) -> ArticleAnalysis | None:
            async with sem:
                return await self._rate_and_analyze(article, threshold)

        tasks = [_analyze_one(a) for a in articles]
        results = await asyncio.gather(*tasks)

        # 過濾 None（未通過 threshold 或失敗的）
        passed = [r for r in results if r is not None]
        skipped = len(results) - len(passed)
        console.print(f"  LLM 分析: {len(passed)} 通過, {skipped} 低於門檻/失敗")
        return passed

    async def _rate_and_analyze(self, article: Article, threshold: float) -> ArticleAnalysis | None:
        """對單篇文章進行一次 LLM 呼叫（評分＋摘要＋子分析）。."""
        content = article.extracted_html or article.text or ""
        content = content[:6000]

        try:
            result = await self._chain.ainvoke(
                {
                    "topic": self.topic,
                    "title": article.title or "",
                    "source": article.source or "",
                    "score": str(article.score or 0),
                    "url": article.url or "",
                    "content": content,
                },
            )

            raw = cast("AIMessage", result["raw"])
            parsed = cast("_RawAnalysis", result["parsed"])

            # 追蹤用量
            usage = cast("dict[str, Any]", raw.usage_metadata or {})
            in_tokens = int(usage.get("input_tokens", 0))
            out_tokens = int(usage.get("output_tokens", 0))
            self.total_tokens += in_tokens + out_tokens
            self.total_cost_usd += in_tokens * _INPUT_TOKEN_COST + out_tokens * _OUTPUT_TOKEN_COST
            self.calls += 1

            # 檢查是否通過門檻
            score = max(0.0, min(10.0, float(parsed.relevance_score)))
            if score < threshold:
                return None

            # 更新 Article 物件
            article.relevance_score = score
            article.summary = parsed.summary
            article.sub_analysis = parsed.sub_analysis
            article.key_insights = parsed.key_insights
            article.llm_judge_passed = True

            return ArticleAnalysis(
                article_id=article.id,
                title=article.title,
                url=article.url,
                relevance_score=score,
                summary=parsed.summary,
                sub_analysis=parsed.sub_analysis,
                key_insights=parsed.key_insights,
            )

        except Exception:  # noqa: BLE001
            return None
