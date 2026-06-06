# CortexFlow — AGENTS.md

## Project
Single Python package (not monorepo). A fixed 5-stage ETL pipeline for intelligence gathering (Fetch → Normalize → Extract → Analyze → Synthesize → Report). Async throughout, no web framework.

## Setup & commands
- **Install**: `uv sync` (uses `uv.lock`, not pip/poetry)
- **Run CLI**: `uv run cortexflow --topic "..." --sources github reddit`
- **Run as module**: `python -m cortexflow` (same CLI)
- **`cortexflow/__main__.py`** does a `sys.path.insert(0, ...)` then `from main import main` — the real entrypoint is `main.py` at repo root
- **Tests**: `pytest` + `pytest-asyncio` in dev deps, but **no tests/ directory exists yet**; no type checker configured
- **No CI/CD, no pre-commit, no Docker, no Makefile**

## Architecture
5 stages in `cortexflow/`:
| Stage | Dir | Key |
|-------|-----|-----|
| Fetch | `fetchers/` | `RedditFetcher` (3 fallback layers: API→old.reddit→Demo), `GitHubFetcher` (trending scraper) |
| Normalize | `normalizer/` | URL + content-fingerprint dedup |
| Extract | `extractor/` | `FastExtractor`: `trafilatura` → `BeautifulSoup` fallback; Semaphore(10) |
| Analyze (Map) | `filter/article_analyzer.py` | per-article LLM via `langchain ChatOpenAI.with_structured_output`; Semaphore(5); threshold gates |
| Synthesize (Reduce) | `filter/synthesizer.py` | single LLM call merging all `ArticleAnalysis` → `ReportContent` |
| Report | `reporter/` | `MarkdownReporter` (rich/simple modes), `JSONReporter` |

Pipeline orchestrator: `core/pipeline.py` — `Pipeline.run()` coordinates all stages.

## Data model
`cortexflow/core/schema.py` — Pydantic models:
- `Article` — accumulates fields across stages (`extracted_html`, `relevance_score`, `summary`, etc.)
- `ArticleAnalysis` — per-article LLM output
- `ReportContent` — final synthesis (sections, key_points, links)
- `PipelineInput` / `PipelineOutput` — run params and results

## Settings
`cortexflow/config/settings.py` — `pydantic-settings` loads from `.env`:
- **Required**: `OPENAI_API_KEY` (without it, Stage 4/4.5 are skipped — degraded mode)
- **Optional**: `OPENAI_MODEL` (default `gpt-4o-mini`), `OPENAI_BASE_URL` (proxy)
- Sources need **no API keys**: Reddit has Demo fallback, GitHub scrapes trending
- Token cost constants hardcoded in `article_analyzer.py:24-25` and `synthesizer.py:17-18`

## Key conventions
- LLM analysis uses `with_structured_output` (Pydantic schema) — single call per article gets score + summary + sub_analysis + insights
- Error isolation: per-article failures are caught individually; one bad article doesn't break the stage
- Content sent to LLM is truncated to 6000 chars (`article_analyzer.py:117`)
- Synthesizer processes top-10 analyses sorted by relevance score
- Report output dir is auto-created via `Path().mkdir(parents=True, exist_ok=True)`
