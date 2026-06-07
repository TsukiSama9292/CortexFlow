"""Stage 4.5: 報告合成器 — 將多篇子分析彙總為結構化分析報告。.

這是 Map-Reduce 中的 Reduce 步驟：
- Map（ArticleAnalyzer）：每篇文章獨立分析 → ArticleAnalysis
- Reduce（Synthesizer）：彙總所有 ArticleAnalysis → ReportContent

支援分層聚合 (Hierarchical Reduction) 以處理大規模文章。
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from loguru import logger
from pydantic import BaseModel, Field, SecretStr
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from cortexflow.config.settings import settings
from cortexflow.core.schema import ArticleAnalysis, ReportContent

if TYPE_CHECKING:
    from langchain_core.messages import AIMessage
    from langchain_core.runnables import Runnable

_INPUT_TOKEN_COST = 0.15 / 1_000_000
_OUTPUT_TOKEN_COST = 0.60 / 1_000_000


class PartialAnalysis(BaseModel):
    """分層聚合中的中間分析結果。."""

    title: str = Field(description="該批次的彙總標題")
    key_points: list[str] = Field(description="該批次的關鍵洞察點")
    summary: str = Field(description="該批次的深度總結內文")
    links: list[str] = Field(description="原始連結列表")


class Synthesizer:
    """將多個 ArticleAnalysis 彙總為結構化分析報告。."""

    def __init__(self, topic: str) -> None:
        """初始化合成器。.

        Args:
            topic: 研究主題。
        """
        self.topic = topic

        # type: ignore[call-arg]
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=SecretStr(settings.openai_api_key) if settings.openai_api_key else None,
            base_url=settings.openai_base_url or None,
            temperature=0.3,
        )

        self.total_tokens: int = 0
        self.total_cost_usd: float = 0.0
        self.calls: int = 0

    async def synthesize(self, analyses: list[ArticleAnalysis]) -> ReportContent | None:
        """將多個 ArticleAnalysis 彙總為結構化報告。."""
        if not analyses:
            return None

        # 依相關性排序
        analyses = sorted(analyses, key=lambda a: a.relevance_score, reverse=True)

        # 如果文章數量過多，執行分層聚合
        if len(analyses) > 10:
            logger.info("檢測到大量文章 ({count} 篇)，啟動分層聚合模式", count=len(analyses))
            final_data = await self._hierarchical_reduce(analyses)
        else:
            final_data = await self._final_reduce(analyses)

        return final_data

    async def _hierarchical_reduce(self, analyses: list[ArticleAnalysis]) -> ReportContent | None:
        """分層聚合邏輯：將文章分批處理再彙整。."""
        batch_size = 8
        batches = [analyses[i : i + batch_size] for i in range(0, len(analyses), batch_size)]

        # Step 1: Map (併發處理各批次)
        tasks = [self._partial_reduce(batch) for batch in batches]
        partial_results = await asyncio.gather(*tasks)
        # pyright: ignore[reportUnknownArgumentType]
        partial_results = [r for r in partial_results if r is not None]

        if not partial_results:
            return None

        # Step 2: Final Reduce (彙整中間結果)
        # pyright: ignore[reportUnknownArgumentType]
        return await self._reduce_partials(partial_results)

    async def _partial_reduce(self, analyses: list[ArticleAnalysis]) -> PartialAnalysis | None:
        """將一小批次的文章轉換為中間分析結果。."""
        prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages(  # pyright: ignore[reportUnknownMemberType]
            [
                (
                    "system",
                    "你是一位專業分析師。請將這組文章分析結果彙整為一段中間摘要，"
                    "保留最關鍵的洞察與連結，供後續最終報告合成使用。",
                ),
                (
                    "human",
                    "主題：{topic}\n文章：\n{text}\n\n請產出 PartialAnalysis 結構。",
                ),
            ]
        )
        chain = prompt | self.llm.with_structured_output(  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
            PartialAnalysis, include_raw=True
        )
        text = self._format_analyses(analyses)

        result = await self._invoke_chain(chain, {"topic": self.topic, "text": text})  # pyright: ignore[reportUnknownArgumentType]
        return cast(PartialAnalysis, result) if result else None

    async def _reduce_partials(self, partials: list[PartialAnalysis]) -> ReportContent | None:
        """彙整多個中間分析結果為最終 ReportContent。."""
        prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages(  # pyright: ignore[reportUnknownMemberType]
            [
                (
                    "system",
                    "你是一位專業的科技情報分析師。請將多個「中間分析批次」"
                    "整合成一份具有深度洞察的最終結構化報告。\n"
                    "不要逐條列出，要跨批次比對趨勢。",
                ),
                (
                    "human",
                    "主題：{topic}\n中間分析數據：\n{text}\n\n請產出最終 ReportContent。",
                ),
            ]
        )
        chain = prompt | self.llm.with_structured_output(  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
            ReportContent, include_raw=True
        )

        text_parts: list[str] = []
        for i, p in enumerate(partials, 1):
            batch_text = (
                f"[批次 {i}] {p.title}\n"
                f"重點：{', '.join(p.key_points)}\n"
                f"內容：{p.summary}\n"
                f"連結：{', '.join(p.links)}"
            )
            text_parts.append(batch_text)  # pyright: ignore[reportUnknownMemberType]
        text = "\n---\n".join(text_parts)  # pyright: ignore[reportUnknownArgumentType]

        result = await self._invoke_chain(chain, {"topic": self.topic, "text": text})  # pyright: ignore[reportUnknownArgumentType]
        return cast("ReportContent", result) if result else None

    async def _final_reduce(self, analyses: list[ArticleAnalysis]) -> ReportContent | None:
        """原有的單次合成邏輯。."""
        prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages(  # pyright: ignore[reportUnknownMemberType]
            [
                (
                    "system",
                    "你是一位專業的科技情報分析師。你的任務是將多篇「已分析過」的文章"
                    "整合成一份具有深度洞察的結構化報告。\n\n"
                    "每篇文章已經過初步分析，包含：\n"
                    "- summary: 文章摘要\n"
                    "- sub_analysis: 深度子分析（獨特洞察）\n"
                    "- key_insights: 關鍵洞察\n"
                    "- relevance_score: 相關性分數\n"
                    "- url: 原始連結\n\n"
                    "報告要求：\n"
                    "- 使用繁體中文\n"
                    "- 報告風格類似 Stratechery / Platformer 等科技分析媒體\n"
                    "- 交叉比對、整合多篇文章的觀點，找出共通趨勢與矛盾\n"
                    "- 提出對開發者/團隊的具體建議\n"
                    "- 不要逐篇摘要，而是提煉跨文章的全局觀點",
                ),
                (
                    "human",
                    "研究主題：{topic}\n\n"
                    "以下是各篇文章的分析結果（依相關性排序）：\n"
                    "{analyses_text}\n\n"
                    "請產出結構化報告，包含：\n"
                    "1. 一個引人注目的主標題（含 emoji 和關鍵數據）\n"
                    "2. 3-5 個分析章節（每個含 emoji + 標題 + 深度內文）\n"
                    "3. 📌 重點總結（3-6 條 bullet point）\n"
                    "4. 🔗 相關連結",
                ),
            ],
        )
        chain = prompt | self.llm.with_structured_output(  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
            ReportContent, include_raw=True
        )
        text = self._format_analyses(analyses)

        result = await self._invoke_chain(chain, {"topic": self.topic, "analyses_text": text})  # pyright: ignore[reportUnknownArgumentType]
        return cast("ReportContent", result) if result else None

    async def _invoke_chain(
        self, chain: Runnable[dict[str, Any], Any], inputs: dict[str, Any]
    ) -> Any:  # noqa: ANN401
        """封裝 LLM 呼叫，含重試與 Token 統計。."""

        @retry(
            stop=stop_after_attempt(settings.max_retries),
            wait=wait_exponential(
                multiplier=1, min=settings.retry_min_wait, max=settings.retry_max_wait
            ),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )
        async def _invoke() -> Any:  # noqa: ANN401
            return await chain.ainvoke(inputs)

        try:
            res = await _invoke()
            raw = cast("AIMessage", res["raw"])
            parsed = res["parsed"]

            usage = cast(dict[str, Any], raw.usage_metadata or {})
            in_tokens = int(usage.get("input_tokens", 0))
            out_tokens = int(usage.get("output_tokens", 0))
            self.total_tokens += in_tokens + out_tokens
            self.total_cost_usd += in_tokens * _INPUT_TOKEN_COST + out_tokens * _OUTPUT_TOKEN_COST
            self.calls += 1

            return parsed
        except (ValueError, RuntimeError) as e:
            logger.warning("LLM 呼叫失敗: {error}", error=e)
            return None
        except Exception as e:  # noqa: BLE001
            logger.error("LLM 呼叫發生非預期錯誤: {error}", error=e)
            return None

    @staticmethod
    def _format_analyses(analyses: list[ArticleAnalysis]) -> str:
        """將 ArticleAnalysis 列表格式化為 LLM 易讀的文字。."""
        parts: list[str] = []
        for i, a in enumerate(analyses, 1):
            parts.append(
                f"[分析 {i}] ⭐ 相關性: {a.relevance_score}/10\n"
                f"標題: {a.title}\n"
                f"連結: {a.url}\n"
                f"摘要: {a.summary}\n"
                f"深度分析: {a.sub_analysis}\n"
                f"關鍵洞察:\n"
                + "\n".join(f"  - {insight}" for insight in (a.key_insights or []))
                + "\n",
            )
        return "\n---\n".join(parts)
