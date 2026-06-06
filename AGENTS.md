# CortexFlow — AGENTS.md

Single Python package. A fixed 5-stage async ETL pipeline (Fetch → Normalize → Extract → Analyze → Synthesize → Report). No web framework.

## Setup & commands
- **Install**: `uv sync`
- **Run**: `uv run cortexflow --topic "..." --sources reddit github`
- **Also**: `python -m cortexflow` / `python main.py` — all delegate to `cortexflow.cli:main`
- **Interactive**: `uv run cortexflow` (no args) → guided prompt for topic/sources/demo
- **Demo**: `--demo` — zero API keys needed, uses mock data for all stages
- **Tests**: `uv run pytest tests/ -q` — 47 tests, `pytest-asyncio` with `asyncio_mode=auto`
- **Lint**: `uv run ruff check cortexflow/ main.py`
- **Format**: `uv run ruff format cortexflow/ main.py`
- **Type check**: `uv run pyright` (basic mode, `pyproject.toml` config)

## Architecture
5 stages in `cortexflow/`:
| Stage | Dir | Key |
|-------|-----|-----|
| Fetch | `fetchers/` | `RedditFetcher` (3 fallbacks: JSON API → old.reddit → Demo), `GitHubFetcher` (trending scraper, no token needed) |
| Normalize | `normalizer/` | URL + content-fingerprint (first-100-char hash) dedup |
| Extract | `extractor/` | `FastExtractor`: `trafilatura` → `BeautifulSoup` fallback; Semaphore(10) |
| Analyze (Map) | `filter/article_analyzer.py` | per-article LLM via `langchain ChatOpenAI.with_structured_output`; Semaphore(5); threshold gates; content truncated to 6000 chars |
| Synthesize (Reduce) | `filter/synthesizer.py` | single LLM call merging top-10 `ArticleAnalysis` → `ReportContent` |
| Report | `reporter/` | `MarkdownReporter` (rich synthesis or fallback list mode), `JSONReporter` |

Orchestrator: `core/pipeline.py` — `Pipeline.run()` coordinates stages with Rich spinner, timing, and fix suggestions on failure.

## Entry points
- `cortexflow/cli.py` — real entrypoint (argparse + `_interactive_prompt` + `_check_environment`)
- `cortexflow/__main__.py` — `from cortexflow.cli import main` (no sys.path hack)
- `main.py` — same delegation; exists for convenience

## Data model (`core/schema.py`)
- `Article` — accumulates fields across stages (`extracted_html`, `relevance_score`, `summary`, `sub_analysis`, `key_insights`, `llm_judge_passed`)
- `ArticleAnalysis` — per-article LLM output (score + summary + sub_analysis + insights)
- `ReportContent` — final synthesis (title + sections + key_points + links)
- `PipelineInput` / `PipelineOutput` — run params (sources, threshold, output_path, etc.)

## Settings (`config/settings.py`)
- `pydantic-settings` loads from `.env` (gitignored)
- `OPENAI_API_KEY` — required for real LLM stages; missing → stages 4/4.5 skipped (degraded list report)
- `OPENAI_MODEL` (default `gpt-4o-mini`), `OPENAI_BASE_URL` (optional proxy)
- Sources need **no API keys** — Reddit has demo fallback, GitHub scrapes trending
- Token cost constants hardcoded in `article_analyzer.py:24-25` and `synthesizer.py:17-18`

## Key conventions
- **Error isolation**: per-article failures are caught individually; one bad article never breaks a stage
- `outputs/` is gitignored; default output `outputs/report.md`
- Environment check runs before real mode: validates Python version, package load, API key presence
- Interactive mode uses `types.SimpleNamespace` (not inner class) to avoid scoping bug
- `--help` / `-h` correctly shows argparse help; does not enter interactive prompt
