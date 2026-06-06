"""Summarizer — 對 Article 生成主題相關的簡潔中文摘要。

使用 LangChain ChatOpenAI + with_structured_output，
根據指定的研究主題產生 50～100 字的繁體中文摘要。
"""

from __future__ import annotations

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from cortexflow.config.settings import settings
from cortexflow.core.schema import Article


class Summary(BaseModel):
    """LLM 回傳的結構化摘要結果。"""
    summary: str = Field(
        ...,
        description="文章的繁體中文摘要，50～100 字",
    )


# Token 成本常數（gpt-4o-mini 定價）
_INPUT_TOKEN_COST = 0.15 / 1_000_000
_OUTPUT_TOKEN_COST = 0.60 / 1_000_000


class Summarizer:
    """情報摘要生成器。

    根據指定的研究主題，對 Article 生成 50～100 字的繁體中文摘要。
    使用 LangChain ChatOpenAI + with_structured_output(include_raw=True)
    同時取得摘要文字與原始回覆以追蹤 token 用量。
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
                "你是一個情報摘要專家。你的任務是根據研究主題，"
                "將文章濃縮成 50～100 字的繁體中文摘要。\n\n"
                "要求：\n"
                "- 只保留與研究主題相關的核心資訊\n"
                "- 摘要必須是繁體中文\n"
                "- 長度嚴格控制在 50～100 字之間\n"
                "- 使用客觀陳述句，不加評論或感想",
            ),
            (
                "human",
                "研究主題：{topic}\n\n"
                "文章標題：{title}\n\n"
                "文章內容：{content}",
            ),
        ])

        self._chain = self._prompt | self.llm.with_structured_output(
            Summary, include_raw=True
        )

        # ── 用量追蹤 ──
        self.total_tokens: int = 0
        self.total_cost_usd: float = 0.0
        self.calls: int = 0

    async def summarize(self, article: Article) -> str:
        """對一篇文章生成中文摘要。

        回傳 50～100 字的繁體中文摘要；
        若 LLM 呼叫失敗則回傳空字串，確保 Pipeline 不會中斷。
        """
        content = article.extracted_html or article.text or ""
        content = content[:8000]

        try:
            result = await self._chain.ainvoke({
                "topic": self.topic,
                "title": article.title or "",
                "content": content,
            })

            raw: AIMessage = result["raw"]
            parsed: Summary = result["parsed"]

            # 追蹤 token 用量與成本
            usage = raw.usage_metadata or {}
            in_tokens = usage.get("input_tokens", 0)
            out_tokens = usage.get("output_tokens", 0)
            self.total_tokens += in_tokens + out_tokens
            self.total_cost_usd += (
                in_tokens * _INPUT_TOKEN_COST + out_tokens * _OUTPUT_TOKEN_COST
            )
            self.calls += 1

            return parsed.summary

        except Exception:
            return ""
