"""CortexFlow CLI — 情報 ETL Pipeline 命令列入口。"""

from __future__ import annotations

import argparse
import asyncio

from rich.console import Console

from cortexflow.core.pipeline import Pipeline
from cortexflow.core.schema import PipelineInput


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="cortexflow",
        description="情報 ETL Pipeline — 從社群媒體與開發平台採集結構化情報",
    )
    parser.add_argument("--topic", required=True, help="研究主題")
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=["reddit", "github"],
        default=["reddit", "github"],
        help="來源渠道（預設: reddit github）",
    )
    parser.add_argument(
        "--output-format",
        choices=["markdown", "json"],
        default="markdown",
        help="輸出格式（預設: markdown）",
    )
    parser.add_argument(
        "--output",
        default="output_report.md",
        help="輸出檔案路徑（預設: output_report.md）",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=20,
        help="每渠道最大結果數（預設: 20）",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=5.0,
        help="LLM 相關性門檻 0-10（預設: 5）",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    console = Console()

    pipeline_input = PipelineInput(
        topic=args.topic,
        sources=args.sources,
        max_results_per_source=args.max_results,
        relevance_threshold=args.threshold,
        output_format=args.output_format,
        output_path=args.output,
    )

    console.print(
        f"[bold green]開始執行 Pipeline[/bold green] — 主題: [yellow]{args.topic}[/yellow]"
    )
    console.print(f"   來源: {', '.join(args.sources)}")
    console.print(f"   每渠道上限: {args.max_results}")
    console.print(f"   相關性門檻: {args.threshold}")
    console.print(f"   輸出格式: {args.output_format}")
    console.print(f"   輸出路徑: {args.output}")

    pipeline = Pipeline(pipeline_input)
    result = asyncio.run(pipeline.run())

    console.print(
        f"[bold green]執行完畢[/bold green] — 共採集 [cyan]{len(result.articles)}[/cyan] 篇文章"
    )


if __name__ == "__main__":
    main()
