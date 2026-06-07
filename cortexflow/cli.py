"""CortexFlow CLI — 情報 ETL Pipeline 命令列入口。."""

from __future__ import annotations

import argparse
import asyncio
import sys
from importlib import metadata
from typing import Literal, cast

from rich.console import Console
from rich.prompt import Confirm, Prompt

from cortexflow.config.loader import get_pipeline_defaults, load_config
from cortexflow.core.db import Database
from cortexflow.core.logger import setup_logger
from cortexflow.core.pipeline import Pipeline
from cortexflow.core.schema import PipelineInput


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令列參數。."""
    # 載入設定檔預設值
    config = load_config()
    defaults = get_pipeline_defaults(config)

    parser = argparse.ArgumentParser(
        prog="cortexflow",
        description="情報 ETL Pipeline — 從社群媒體與開發平台採集結構化情報",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "範例:\\r"
            '  cortexflow --topic "AI Agent" --sources reddit github\\r'
            "  cortexflow --topic Rust --sources github --output-format json\\r"
            "  cortexflow --topic demo --demo"
        ),
    )
    parser.add_argument("--topic", help="研究主題（未提供時進入互動模式）")
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=["reddit", "github", "hackernews", "lobsters"],
        default=None,
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
        default="outputs/report.md",
        help="輸出檔案路徑（預設: outputs/report.md）",
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
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Demo 模式：使用模擬資料，不需任何 API Key",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="顯示詳細日誌")
    parser.add_argument("--log-file", help="日誌檔案路徑")
    parser.add_argument("--history", action="store_true", help="查看執行歷史記錄")
    parser.add_argument("--replay", type=int, help="從歷史記錄重現特定執行 (ID)")

    # 設定從檔案載入的預設值
    parser.set_defaults(**defaults)

    args = parser.parse_args(argv)

    if args.demo and not args.topic:
        args.topic = "demo"
    if args.sources is None:
        args.sources = ["reddit", "github"]

    return args


def _interactive_prompt(console: Console) -> argparse.Namespace:
    """互動式引導模式 — 逐步詢問使用者輸入。."""
    # 載入設定檔預設值
    config = load_config()
    defaults = get_pipeline_defaults(config)

    console.print()
    console.rule("[bold]🖐️ 歡迎使用 CortexFlow — 情報 ETL Pipeline[/bold]")
    console.print()
    console.print("  請輸入研究參數，或按 Ctrl+C 離開。")
    console.print()

    topic = Prompt.ask("  研究主題", default="AI Agent")

    default_sources_list = defaults.get("sources", ["reddit", "github"])
    default_sources = ", ".join(default_sources_list)
    sources_input = Prompt.ask("  來源渠道（逗號分隔）", default=default_sources)
    sources = [s.strip() for s in sources_input.split(",") if s.strip()]

    use_demo = not Confirm.ask("  使用真實資料", default=True)
    if use_demo:
        console.print("  [dim]💡 將使用模擬資料進行展示[/dim]")

    console.print()

    from types import SimpleNamespace

    ns = SimpleNamespace(
        topic=topic,
        sources=sources if sources else default_sources_list,
        output_format=defaults.get("output_format", "markdown"),
        output=defaults.get("output", "outputs/report.md"),
        max_results=defaults.get("max_results", 20),
        threshold=defaults.get("threshold", 5.0),
        demo=use_demo,
    )
    return cast("argparse.Namespace", ns)


def _check_environment(console: Console) -> bool:
    """執行前環境檢查，回傳是否為健康狀態。."""
    ok = True
    import importlib.util

    if importlib.util.find_spec("cortexflow") is None:
        console.print("  [red]✘ 無法載入 cortexflow 套件[/red]")
        console.print("    [dim]💡 建議: 執行 [bold]uv sync[/bold] 安裝相依套件[/dim]")
        ok = False

    from cortexflow.config.settings import settings

    has_llm = bool(settings.openai_api_key)
    if not has_llm:
        console.print("  [yellow]⚠ 未設定 OPENAI_API_KEY[/yellow] — LLM 分析階段將跳過")
        console.print(
            "    [dim]💡 建議: 在 .env 檔案中設定"
            " OPENAI_API_KEY，或使用 [bold]--demo[/bold] 模式測試[/dim]",
        )
    else:
        model = settings.openai_model or "gpt-4o-mini"
        if not settings.openai_base_url:
            console.print(
                "    [dim]💡 提示: 若使用 OpenAI 相容 API Proxy，請設定 OPENAI_BASE_URL[/dim]",
            )
        console.print(f"  [green]✔ LLM[/green] — {model}")

    if not settings.openai_base_url:
        console.print("  [green]✔ LLM Proxy[/green] — 直連 OpenAI（未設定代理）")
    else:
        console.print(f"  [green]✔ LLM Proxy[/green] — {settings.openai_base_url}")

    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    console.print(f"  [green]✔ Python[/green] — {py_ver}")

    try:
        ver = metadata.version("cortexflow")
        console.print(f"  [green]✔ CortexFlow[/green] — v{ver}")
    except metadata.PackageNotFoundError:
        pass

    return ok


def _show_history(console: Console) -> None:
    """顯示執行歷史記錄表格。."""
    db = Database()
    history = db.get_history()

    if not history:
        console.print("  [yellow]目前無執行記錄。[/yellow]")
        return

    from rich.table import Table

    table = Table(title="CortexFlow 執行歷史")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("主題", style="magenta")
    table.add_column("時間", style="green")
    table.add_column("狀態")
    table.add_column("耗時 (秒)", justify="right")
    table.add_column("Tokens", justify="right")

    for h in history:
        status_str = "[green]✅ 成功[/green]" if h["status"] == "success" else "[red]❌ 失敗[/red]"
        table.add_row(
            str(h["id"]),
            h["topic"],
            h["timestamp"],
            status_str,
            f"{h['duration_seconds']:.2f}",
            f"{h['total_tokens']:,}",
        )

    console.print(table)


async def _replay_execution(execution_id: int, console: Console) -> None:
    """從歷史記錄重現特定執行。."""
    db = Database()
    exec_data = db.get_execution(execution_id)

    if not exec_data:
        console.print(f"  [red]❌ 找不到 ID 為 {execution_id} 的執行記錄[/red]")
        return

    import json

    input_data = json.loads(exec_data["input_json"])
    console.print(f"  [bold]🔄 正在重現執行記錄 #{execution_id}[/bold]")
    console.print(f"  [dim]主題: {input_data['topic']}[/dim]\n")

    pipeline_input = PipelineInput(**input_data)
    use_demo = bool(exec_data.get("demo", 0))
    pipeline = Pipeline(pipeline_input, demo=use_demo)
    await pipeline.run()


def main(argv: list[str] | None = None) -> None:
    """CortexFlow 入口函式。."""
    console = Console()

    show_help = "--help" in sys.argv or "-h" in sys.argv
    if argv is None and not show_help and "--topic" not in sys.argv and "--demo" not in sys.argv:
        # 檢查是否有 history/replay 參數，有的話不進入互動模式
        if "--history" in sys.argv or "--replay" in sys.argv:
            args = parse_args(argv)
        else:
            args = _interactive_prompt(console)
    else:
        args = parse_args(argv)

    # 1. 配置日誌
    setup_logger(verbose=args.verbose, log_file=args.log_file)

    # 2. 處理特定指令
    if args.history:
        _show_history(console)
        return

    if args.replay:
        asyncio.run(_replay_execution(args.replay, console))
        return

    # 3. 執行 Pipeline
    if args.demo:
        console.print("[bold]🎮 Demo 模式[/bold] — 使用模擬資料\n")
    else:
        _check_environment(console)

    sources = cast(
        'list[Literal["reddit", "github", "hackernews", "lobsters"]]',
        args.sources or ["reddit", "github"],
    )

    pipeline_input = PipelineInput(
        topic=args.topic,
        sources=sources,
        max_results_per_source=args.max_results,
        relevance_threshold=args.threshold,
        output_format=args.output_format,
        output_path=args.output,
    )

    pipeline = Pipeline(pipeline_input, demo=args.demo)
    result = asyncio.run(pipeline.run())

    console.print(
        f"  [bold green]完成[/bold green] — 輸出: [cyan]{result.input.output_path}[/cyan]"
        f"  ({len(result.articles)} 篇文章)",
    )


if __name__ == "__main__":
    main()
