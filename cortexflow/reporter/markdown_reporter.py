"""Markdown Reporter — 將情報結果輸出為結構化 Markdown 報告。

支援兩種模式：
1. 豐富報告模式（有 synthesis）：LLM 合成的分析報告，類似科技分析媒體風格
2. 簡潔列表模式（無 synthesis）：傳統條列式文章列表
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from cortexflow.core.schema import Article, PipelineInput, ReportContent

if TYPE_CHECKING:
    from cortexflow.core.pipeline import StageResult


class MarkdownReporter:
    """以 Markdown 格式輸出情報報告。"""

    TEXT_TRUNCATE_CHARS: int = 500

    def generate(
        self,
        articles: list[Article],
        inp: PipelineInput,
        stage_results: list[StageResult],
        errors: list[dict],
        report_content: ReportContent | None = None,
    ) -> None:
        """產生 Markdown 報告並寫入 inp.output_path。"""
        if report_content:
            report = self._build_rich(report_content)
        else:
            report = self._build_simple(articles, inp, stage_results, errors)
        output = Path(inp.output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")

    # ──────────────────────────────
    # 豐富報告模式（有 synthesis）
    # ──────────────────────────────

    def _build_rich(self, rc: ReportContent) -> str:
        lines: list[str] = []

        # 1. 主標題
        lines.append(f"# {rc.title}")
        lines.append("")

        # 2. 分格線
        lines.append("────────────────")
        lines.append("")

        # 3. 各章節
        for section in rc.sections:
            lines.append(f"## {section.emoji} {section.title}")
            lines.append("")
            lines.append(section.content)
            lines.append("")
            lines.append("────────────────")
            lines.append("")

        # 4. 重點總結
        lines.append("## 📌 這件事的意義")
        lines.append("")
        for point in rc.key_points:
            lines.append(f"- {point}")
        lines.append("")
        lines.append("────────────────")
        lines.append("")

        # 5. 相關連結
        lines.append("## 🔗 相關連結")
        lines.append("")
        for link in rc.links:
            if ":" in link:
                name, url = link.split(":", 1)
                lines.append(f"- **{name.strip()}**:{url.strip()}")
            else:
                lines.append(f"- {link}")
        lines.append("")

        # 6. 補充說明
        lines.append("---")
        lines.append("")
        lines.append(
            "*這篇報告由 AI 從多方資料源協助整理與編輯，方便閱讀與討論；"
            "若想看完整脈絡、原始說法與更多細節，仍建議以原文內容為主。*"
        )
        lines.append("")

        return "\n".join(lines)

    # ──────────────────────────────
    # 簡潔列表模式（無 synthesis）
    # ──────────────────────────────

    def _build_simple(
        self,
        articles: list[Article],
        inp: PipelineInput,
        stage_results: list[StageResult],
        errors: list[dict],
    ) -> str:
        lines: list[str] = []

        # 1. 標題
        lines.append(f"# 情報報告: {inp.topic}")
        lines.append("")

        # 2. 中繼資訊
        lines.append("## 基本資訊")
        lines.append("")
        lines.append(f"- **主題**: {inp.topic}")
        lines.append(f"- **來源渠道**: {', '.join(inp.sources)}")
        lines.append(f"- **報告產生時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- **文章總數**: {len(articles)}")
        lines.append("")

        # 3. 執行統計表格
        lines.append("## Stage 執行統計")
        lines.append("")
        lines.append("| Stage | 狀態 | 耗時 (秒) | 處理數量 |")
        lines.append("|-------|------|-----------|----------|")
        for sr in stage_results:
            status = "✅ 成功" if sr.success else "❌ 失敗"
            error_suffix = f" ({sr.error})" if sr.error else ""
            lines.append(
                f"| {sr.stage_name} | {status}{error_suffix} | {sr.duration:.2f} | {sr.items_count} |"
            )
        lines.append("")

        # 4. 文章列表
        passed_articles = [a for a in articles if a.llm_judge_passed is not False]

        if not passed_articles:
            lines.append("## 文章列表")
            lines.append("")
            lines.append("_無符合條件的文章。_")
            lines.append("")
        else:
            lines.append(f"## 文章列表（共 {len(passed_articles)} 篇）")
            lines.append("")
            for idx, article in enumerate(passed_articles, start=1):
                title = article.title.strip() if article.title.strip() else "無標題"
                lines.append(f"## {idx}. {title}")
                lines.append("")
                lines.append(f"- **來源**: {article.source}")
                lines.append(f"- **作者**: {article.author or '未知'}")
                lines.append(f"- **分數**: {article.score}")
                lines.append(f"- **連結**: {article.url}")
                if article.created_at:
                    lines.append(
                        f"- **發佈時間**: {article.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                if article.relevance_score is not None:
                    lines.append(f"- **相關性分數**: {article.relevance_score:.2f}")
                lines.append("")
                if article.summary:
                    lines.append("**摘要**:")
                    lines.append("")
                    lines.append(article.summary)
                    lines.append("")
                if article.text:
                    truncated = article.text[: self.TEXT_TRUNCATE_CHARS]
                    if len(article.text) > self.TEXT_TRUNCATE_CHARS:
                        truncated += "...（內容截斷）"
                    lines.append("**原文內容**:")
                    lines.append("")
                    lines.append("```text")
                    lines.append(truncated)
                    lines.append("```")
                    lines.append("")

        # 5. 錯誤附錄
        if errors:
            lines.append("---")
            lines.append("")
            lines.append("## 錯誤記錄")
            lines.append("")
            lines.append("| Stage | 錯誤訊息 |")
            lines.append("|-------|----------|")
            for err in errors:
                stage = err.get("stage", "?")
                msg = err.get("error", "?")
                lines.append(f"| {stage} | {msg} |")
            lines.append("")

        return "\n".join(lines)
