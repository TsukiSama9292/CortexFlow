"""Stage 4.5: 報告合成器 — 將多篇子分析彙總為結構化分析報告。.

這是 Map-Reduce 中的 Reduce 步驟：
- Map（ArticleAnalyzer）：每篇文章獨立分析 → ArticleAnalysis
- Reduce（Synthesizer）：彙總所有 ArticleAnalysis → ReportContent
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from cortexflow.config.settings import settings
from cortexflow.core.schema import ArticleAnalysis, ReportContent

if TYPE_CHECKING:
    from langchain_core.messages import AIMessage

_INPUT_TOKEN_COST = 0.15 / 1_000_000
_OUTPUT_TOKEN_COST = 0.60 / 1_000_000


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

        self._prompt = ChatPromptTemplate.from_messages(  # pyright: ignore[reportUnknownMemberType]
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

        self._chain: Any = self._prompt | self.llm.with_structured_output(  # pyright: ignore[reportUnknownMemberType]
            ReportContent,
            include_raw=True,
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

        analyses_text = self._format_analyses(analyses)

        try:
            result = await self._chain.ainvoke(
                {
                    "topic": self.topic,
                    "analyses_text": analyses_text,
                },
            )

            raw = cast("AIMessage", result["raw"])
            parsed = cast("ReportContent", result["parsed"])

            usage = cast("dict[str, Any]", raw.usage_metadata or {})
            in_tokens = int(usage.get("input_tokens", 0))
            out_tokens = int(usage.get("output_tokens", 0))
            self.total_tokens += in_tokens + out_tokens
            self.total_cost_usd += in_tokens * _INPUT_TOKEN_COST + out_tokens * _OUTPUT_TOKEN_COST
            self.calls += 1

            return parsed

        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _format_analyses(analyses: list[ArticleAnalysis]) -> str:
        """將 ArticleAnalysis 列表格式化為 LLM 易讀的文字。."""
        parts: list[str] = []
        for i, a in enumerate(analyses[:10], 1):
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
