"""LLM Judge — 對 Article 進行主題相關性評分。

使用 LangChain ChatOpenAI + with_structured_output，
根據指定的研究主題評分 0.0~10.0。
"""

from __future__ import annotations

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from cortexflow.config.settings import settings
from cortexflow.core.schema import Article


class RelevanceScore(BaseModel):
    """LLM 回傳的結構化評分結果。"""
    score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="文章與主題的相關性分數，0.0 為完全不相關，10.0 為完全相關",
    )
    reasoning: str = Field(
        ...,
        description="評分理由（簡短說明，20 字以內）",
    )


# Token 成本常數（gpt-4o-mini 定價）
_INPUT_TOKEN_COST = 0.15 / 1_000_000  # $0.15 / 1M input tokens
_OUTPUT_TOKEN_COST = 0.60 / 1_000_000  # $0.60 / 1M output tokens


class LLMJudge:
    """情報相關性評審。

    根據指定的研究主題，對 Article 進行 0.0~10.0 的相關性評分。
    使用 LangChain ChatOpenAI + with_structured_output(include_raw=True)
    同時取得結構化物件與原始回覆以追蹤 token 用量。
    """

    def __init__(self, topic: str) -> None:
        self.topic = topic

        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or None,
            temperature=0.0,
            max_tokens=256,
        )

        self._prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "你是一個情報相關性評審專家。你的任務是根據指定的研究主題，"
                "判斷一篇文章是否與該主題相關，並給出 0.0 到 10.0 的分數。\n\n"
                "評分標準：\n"
                "- 10.0：完全相關，直接討論主題核心內容\n"
                "- 7.0～9.0：高度相關，深入探討主題的相關面向\n"
                "- 4.0～6.0：部分相關，僅提及或間接關聯\n"
                "- 1.0～3.0：低度相關，僅少量關聯或泛泛而談\n"
                "- 0.0：完全不相關\n\n"
                "請根據文章實際內容客觀打分，避免預設偏見。",
            ),
            (
                "human",
                "研究主題：{topic}\n\n"
                "文章標題：{title}\n\n"
                "文章內容：{content}",
            ),
        ])

        # include_raw=True 讓我們能同時取得原始 AIMessage（含 token 用量）
        # 與解析後的 RelevanceScore 物件
        self._chain = self._prompt | self.llm.with_structured_output(
            RelevanceScore, include_raw=True
        )

        # ── 用量追蹤 ──
        self.total_tokens: int = 0
        self.total_cost_usd: float = 0.0
        self.calls: int = 0

    async def rate(self, article: Article) -> float:
        """對一篇文章進行相關性評分。

        回傳 0.0~10.0 的分數；若 LLM 呼叫失敗則回傳 5.0（中性分數），
        確保 Pipeline 不會因單一文章異常而中斷。
        """
        # 組合內容：優先使用 extracted_html（FireCrawl 提取版，更完整），
        # 若無則退回使用原始 text
        content = article.extracted_html or article.text or ""
        # 截斷以避免超出模型 token 限制
        content = content[:8000]

        try:
            result = await self._chain.ainvoke({
                "topic": self.topic,
                "title": article.title or "",
                "content": content,
            })

            raw: AIMessage = result["raw"]
            parsed: RelevanceScore = result["parsed"]

            # 追蹤 token 用量與成本
            usage = raw.usage_metadata or {}
            in_tokens = usage.get("input_tokens", 0)
            out_tokens = usage.get("output_tokens", 0)
            self.total_tokens += in_tokens + out_tokens
            self.total_cost_usd += (
                in_tokens * _INPUT_TOKEN_COST + out_tokens * _OUTPUT_TOKEN_COST
            )
            self.calls += 1

            return max(0.0, min(10.0, float(parsed.score)))

        except Exception:
            # 任何 LLM 相關異常（網路、格式、解析等）都回傳中性分數
            return 5.0
