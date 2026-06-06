# CortexFlow

**情報 ETL Pipeline — 從社群雜訊到結構化情報的固定管道式概念驗證**

CortexFlow 是一個基於 Python 非同步架構開發的**固定管道式（Fixed Pipeline）情報過濾與自動化彙整概念驗證（PoC）**。與 gpt-researcher 等動態規劃型研究代理不同，CortexFlow 將情報處理流程定義為一組可預測、可除錯、可重現的固定階段（Stage），每個階段有明確的輸入/輸出合約與錯誤隔離邊界。

> **核心定位**：這不是一個會自己決定「下一步該做什麼」的研究 Agent。這是一個你定義好「去哪裡查、怎麼過濾、怎麼輸出」後，就會穩定執行的情報 ETL Pipeline。

---

## 設計哲學

### 不要 Agentic，要 Pipeline

| 維度 | 研究 Agent（如 gpt-researcher） | CortexFlow（固定管道） |
|------|-------------------------------|----------------------|
| 執行路徑 | LLM 動態決定下一步 | 預先定義的 5 個固定 Stage |
| 搜尋策略 | 自行產生查詢詞 | 使用者給定關鍵字 + 固定渠道參數 |
| 可重現性 | 低（每次執行結果不同） | 高（相同輸入 → 相同輸出） |
| 除錯難度 | 高（非確定性行為追蹤困難） | 低（每個 Stage 可獨立驗證與重播） |
| LLM 成本 | 極高（規劃 + 執行 + 總結全用） | 可控（僅 Stage 4 使用 LLM） |
| 錯誤隔離 | 差（任一環節失敗可能中斷整個流程） | 好（每個 Stage 獨立錯誤處理） |

### Map-Reduce 分析模式

Stage 4 採用 **Map-Reduce** 模式進行 LLM 分析：

```
Map 階段（併發）:    每篇文章獨立 LLM 分析 → 評分 + 摘要 + 子分析 + 洞察
Reduce 階段（單一）:  彙總所有子分析 → 結構化最終報告
```

這種設計的優勢：
- **併發執行**：所有文章同時進行 LLM 分析，不互相等待
- **單次呼叫**：每篇文章只需一次 LLM 呼叫（評分 + 摘要 + 子分析 + 洞察一次完成）
- **深度交叉**：Synthesizer 取得的是預分析過的摘要+洞察，而非原始文字，能產出更有深度的報告
- **成本可控**：N 篇文章只需 N+1 次 LLM 呼叫（N 次分析 + 1 次彙總）

---

## 系統架構：五階段固定管道

```
[使用者輸入主題 + 渠道設定 + 過濾規則]
        │
        ▼
┌─────────────────────────────────────────────┐
│ Stage 1: 資料採集層 (Fetch Layer)            │
│ 純非同步 I/O · 無 LLM · 渠道可插拔           │
│ 各渠道獨立執行，錯誤不互相影響                │
│                                             │
│  ├─ Reddit Fetcher                          │
│  │  策略：公開 JSON API → old.reddit → Demo │
│  │  特點：完全不需要 API 金鑰                │
│  │                                            │
│  ├─ GitHub Trending Fetcher                 │
│  │  策略：爬取 github.com/trending 頁面       │
│  │  特點：免 Token，支援語言過濾 + 主題篩選    │
│  │                                            │
│  └─ [擴充點] 自訂 Fetcher (RSS/Telegram等)   │
└───────────────────┬─────────────────────────┘
                    ▼
┌─────────────────────────────────────────────┐
│ Stage 2: 標準化層 (Normalize Layer)          │
│ 規則式處理 · 無 LLM                         │
│                                             │
│  ├─ URL 去重：相同 URL 只保留一篇            │
│  └─ Content Fingerprint 去重：前100字 hash  │
└───────────────────┬─────────────────────────┘
                    ▼
┌─────────────────────────────────────────────┐
│ Stage 3: 內容提取層 (Extract Layer)          │
│ 規則式提取 · 無 LLM · trafilatura 為主       │
│                                             │
│  ├─ trafilatura（主要）：本地 Markdown 提取   │
│  │  支援表格、連結格式化輸出                  │
│  │                                            │
│  └─ BeautifulSoup（備援）：當 trafilatura     │
│     無法提取時使用                            │
└───────────────────┬─────────────────────────┘
                    ▼
┌─────────────────────────────────────────────┐
│ Stage 4: LLM 分析層 (Analyze Layer)         │
│ Map-Reduce 模式 · 唯一使用 LLM 的階段        │
│                                             │
│  ┌─ Map（併發執行）───────────────────────┐  │
│  │  每篇文章一次 LLM 呼叫，同時完成：      │  │
│  │  1️⃣ 相關性評分 (0.0~10.0)             │  │
│  │  2️⃣ 繁體中文摘要 (50-100 字)          │  │
│  │  3️⃣ 深度子分析 (100-150 字)           │  │
│  │  4️⃣ 關鍵洞察 (2-3 條 bullet point)    │  │
│  │                                         │  │
│  │  未通過門檻的文章自動捨棄               │  │
│  └─────────────────────────────────────┘  │
│                                            │
│  ┌─ Reduce（單一呼叫）────────────────────┐  │
│  │  所有通過文章的子分析彙總為最終報告：    │  │
│  │  → 引人注目的主標題（含 emoji+關鍵數據）  │  │
│  │  → 3-5 個深度分析章節（Stratechery風格）  │  │
│  │  → 📌 重點總結 (3-6 條)                │  │
│  │  → 🔗 相關連結                         │  │
│  └─────────────────────────────────────┘  │
└───────────────────┬─────────────────────────┘
                    ▼
┌─────────────────────────────────────────────┐
│ Stage 5: 彙整輸出層 (Report Layer)          │
│ 模板化輸出 · 統計資訊 · 錯誤報告            │
│                                             │
│  ├─ Markdown 報告（豐富合成模式 / 簡潔列表） │
│  ├─ JSON 報告（含完整結構化資料）            │
│  └─ 執行摘要（各 Stage 耗時、LLM Token 用量）│
└───────────────────┬─────────────────────────┘
                    ▼
[輸出檔案 + 執行記錄]
```

---

## Pipeline 資料流詳解

### 資料模型演進

每一階段會逐步豐富 Article 物件的欄位：

```
原始 Article（Stage 1 產出）
  ├── id, source, source_id          # 識別
  ├── title, author, text, url       # 內容
  └── score, created_at              # 原始中繼

Stage 3 填充（FastExtractor）
  └── extracted_html  ←  trafilatura Markdown 全文

Stage 4 填充（ArticleAnalyzer）
  ├── relevance_score  ←  LLM 評分 (0-10)
  ├── summary          ←  LLM 摘要 (50-100 字)
  ├── sub_analysis     ←  LLM 深度子分析 (100-150 字)
  ├── key_insights     ←  LLM 關鍵洞察 (2-3 條)
  └── llm_judge_passed ← 是否通過門檻
```

### Stage 4 Map-Reduce 資料流

```
┌──────────┐   asyncio.gather（併發）   ┌──────────────┐
│ Article 1 │ ──────────────────────→ │ ArticleAnalysis │
│ Article 2 │ ──────────────────────→ │ (評分+摘要+洞察) │
│ Article 3 │ ──────────────────────→ │       ...       │
│ Article 4 │ ──────────────────────→ │       ...       │
└──────────┘                          └──────┬───────┘
                                             │
                                   （通過門檻者）
                                             ▼
                                   ┌──────────────────┐
                                   │   Synthesizer    │
                                   │  (Reduce: 1次呼叫)│
                                   │                  │
                                   │  交叉比對所有子分析 │
                                   │  產出最終結構化報告 │
                                   └──────┬───────────┘
                                          ▼
                                   ┌──────────────────┐
                                   │   ReportContent  │
                                   │  (title+sections+ │
                                   │   key_points+links)│
                                   └──────────────────┘
```

### 錯誤隔離策略

| Stage | 錯誤處理策略 |
|-------|-------------|
| Stage 1 | 單一渠道失敗不影響其他渠道；Reddit 有 3 層 fallback（API → old.reddit → Demo） |
| Stage 2 | 格式不符的資料直接捨棄並記錄 |
| Stage 3 | 單一 URL 提取失敗不影響其他文章（trafilatura → BS4 雙層策略） |
| Stage 4 | 單篇文章 LLM 分析失敗則跳過該篇（回傳 None），不影響其他文章；採用 `asyncio.Semaphore(5)` 控制併發數避免 API 限流 |
| Stage 5 | 部分資料缺失仍可產出部分報告；有 synthesis 則輸出豐富模式，否則降級為列表模式 |

---

## 各 Stage 原始碼詳解

### Stage 1: Fetch Layer
**位置**: `cortexflow/fetchers/`

**RedditFetcher** (`reddit_fetcher.py`):
- 使用 Reddit 公開 JSON API（不需 OAuth 憑證）
- 三重 fallback 策略：`www.reddit.com` → `old.reddit.com` → 內建 Demo 模式
- Demo 模式根據 topic 產生 12 篇模擬貼文（確保無 API 時仍可測試完整流程）

**GitHubFetcher** (`github_fetcher.py`):
- 爬取 `github.com/trending?since=weekly` 頁面
- 支援語言偵測：若 topic 是程式語言名稱（如 "rust"、"python"），自動加語言過濾
- 使用 BeautifulSoup 解析 HTML，擷取專案名稱、描述、語言、星星數
- 主題過濾：比對名稱/描述中是否包含 topic 關鍵字

### Stage 2: Normalize Layer
**位置**: `cortexflow/normalizer/normalizer.py`

- URL 去重：以 `article.url` 為鍵，確保相同 URL 只保留一篇
- Content fingerprint 去重：取文章前 100 字的 hash，防止不同 URL 但內容相同的重複

### Stage 3: Extract Layer
**位置**: `cortexflow/extractor/fast_extractor.py`

**FastExtractor**（取代原本的 FireCrawl Client）:

```python
class FastExtractor:
    async def _try_trafilatura(self, url: str) -> str | None:
        # 1. trafilatura.fetch_url() 下載 HTML
        # 2. trafilatura.extract(output_format="markdown") 轉為 Markdown
        # 保留表格、連結，只回傳 >50 chars 的有效內容

    async def _try_beautifulsoup(self, url: str) -> str | None:
        # 當 trafilatura 失敗時的備援
        # 1. httpx 下載 HTML
        # 2. BeautifulSoup 依序嘗試 article/main/.content 等 selector
```

使用 `asyncio.Semaphore(10)` 控制最大 10 篇併發提取。

### Stage 4: Analyze Layer
**位置**: `cortexflow/filter/article_analyzer.py`（Map） + `synthesizer.py`（Reduce）

**ArticleAnalyzer** — per-article LLM 分析（併發執行）：

```python
class ArticleAnalyzer:
    async def analyze(self, articles, threshold=5.0) -> list[ArticleAnalysis]:
        sem = asyncio.Semaphore(5)  # 控制併發數
        
        async def _analyze_one(article) -> ArticleAnalysis | None:
            async with sem:
                return await self._rate_and_analyze(article, threshold)
        
        tasks = [_analyze_one(a) for a in articles]
        results = await asyncio.gather(*tasks)
        # 過濾 None（未通過門檻或失敗的）
        return [r for r in results if r is not None]
```

每次 LLM 呼叫使用 `with_structured_output` 同時取得 4 項輸出：
- `relevance_score`（0-10）
- `summary`（繁體中文摘要）
- `sub_analysis`（深度子分析）
- `key_insights`（2-3 條洞察）

**Synthesizer** — 彙總分析（單次呼叫）：

接收所有 `ArticleAnalysis`，依相關性排序後，由 LLM 產出 `ReportContent`（標題 + 章節 + 重點 + 連結）。

### Stage 5: Report Layer
**位置**: `cortexflow/reporter/`

**MarkdownReporter** (`markdown_reporter.py`):
- 豐富模式（有 synthesis）：以合成的 `ReportContent` 產生 Stratchery 風格報告
- 簡潔模式（無 synthesis）：條列式文章列表 + 執行統計表格

**JSONReporter** (`json_reporter.py`):
- 輸出完整結構化 JSON，含 meta、stage_stats、articles、report_content

---

## 安裝與設定

### 前提條件

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)（套件管理工具）
- OpenAI 相容 API（LLM 階段必備）

### 安裝步驟

```bash
# 1. 複製專案
git clone https://github.com/yourusername/CortexFlow.git
cd CortexFlow

# 2. 建立虛擬環境並安裝依賴
uv sync

# 3. 建立環境變數檔
cp .env.example .env
# 編輯 .env 填入對應憑證
```

### 環境變數設定

```env
# ─── LLM 設定（必要） ───
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini          # 或透過 proxy 使用其他模型
OPENAI_BASE_URL=                  # 可選：OpenAI 相容 API proxy 位址

# ─── 渠道憑證（全部選用，不設也有對應運作模式） ───
# Reddit: 不設可用 Demo 模式
# GitHub: 不設可用 Trending 爬蟲
```

**無 API Key 也可正常運作**：
- **Reddit**：公開 JSON API → `old.reddit.com` → Demo 模擬資料
- **GitHub**：Trending 爬蟲（免 Token）
- 唯一必須的是 LLM API Key（若無則跳過 Stage 4，輸出簡潔列表報告）

---

## CLI 使用方式

```bash
# 基本用法：指定主題與目標渠道
uv run cortexflow \
  --topic "AI Coding Agents 2026" \
  --sources github

# 同時使用 Reddit + GitHub
uv run cortexflow \
  --topic "Rust 在嵌入式系統的應用" \
  --sources reddit github

# 指定輸出格式與路徑
uv run cortexflow \
  --topic "oMLX Apple Silicon" \
  --sources github \
  --output-format json \
  --output ./reports/omlx.json

# 設定 LLM 過濾門檻（0-10，越高越嚴格）
uv run cortexflow \
  --topic "Vibe Coding" \
  --sources reddit github \
  --threshold 6 \
  --max-results 10
```

### CLI 參數說明

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `--topic` | （必要） | 研究主題關鍵字 |
| `--sources` | `reddit github` | 來源渠道，可選 reddit、github |
| `--output-format` | `markdown` | 輸出格式，可選 markdown、json |
| `--output` | `output_report.md` | 輸出檔案路徑 |
| `--max-results` | `20` | 每渠道最大結果數 |
| `--threshold` | `5.0` | LLM 相關性門檻（0-10） |

---

## 專案結構

```
CortexFlow/
├── main.py                          # CLI 入口點（argparse）
├── pyproject.toml                   # 套件設定與依賴管理
├── .env.example                     # 環境變數範本
│
├── cortexflow/
│   ├── __init__.py
│   ├── __main__.py                  # python -m cortexflow 入口
│   │
│   ├── core/                        # 核心元件
│   │   ├── pipeline.py              # Pipeline 協調器（5 階段順序執行）
│   │   ├── schema.py                # 統一資料模型（Pydantic）
│   │   │   ├── Article              # 原始文章
│   │   │   ├── ArticleAnalysis      # LLM 分析結果
│   │   │   ├── ReportContent        # 合成報告結構
│   │   │   ├── PipelineInput        # Pipeline 輸入參數
│   │   │   └── PipelineOutput       # Pipeline 執行結果
│   │   └── errors.py                # 階段錯誤類型（StageError family）
│   │
│   ├── config/
│   │   └── settings.py              # 設定管理（pydantic-settings）
│   │
│   ├── fetchers/                    # Stage 1: 資料採集
│   │   ├── base.py                  # BaseFetcher 抽象類別
│   │   ├── reddit_fetcher.py        # Reddit（公開 JSON API + Demo）
│   │   └── github_fetcher.py        # GitHub Trending 爬蟲
│   │
│   ├── normalizer/                  # Stage 2: 標準化
│   │   └── normalizer.py            # URL + Content Fingerprint 去重
│   │
│   ├── extractor/                   # Stage 3: 內容提取
│   │   └── fast_extractor.py        # FastExtractor（trafilatura + BS4 fallback）
│   │
│   ├── filter/                      # Stage 4: LLM 分析（Map-Reduce）
│   │   ├── article_analyzer.py      # Map: 每篇文章併發分析（評分+摘要+子分析）
│   │   └── synthesizer.py           # Reduce: 彙總子分析為最終報告
│   │
│   └── reporter/                    # Stage 5: 彙整輸出
│       ├── markdown_reporter.py     # Markdown 輸出（豐富/簡潔模式）
│       └── json_reporter.py         # JSON 結構化輸出
│
└── docs/                            # 文件與報告範例
```

---

## 執行範例與實測數據

以下為實際執行 `--topic "AI Coding Agents 2026" --sources github` 的結果：

### Pipeline 執行摘要

```
✔ fetch_github    1.73s   4 items    (GitHub Trending 爬取)
✔ normalize       0.00s   4 items    (去重)
✔ extract         2.07s   4 items    (trafilatura Markdown 提取)
✔ analyze        31.57s   4 items    (4 篇併發 LLM 分析)
✔ synthesize     55.69s   1 items    (1 次 LLM 彙總合成)
✔ report          0.00s   1 items    (輸出報告)

LLM 呼叫: 5 次
Token 用量: 11,464
預估成本: $0.0031
```

### 輸出報告結構範例

```markdown
# 🚀 AI Coding Agents 2026：從「代碼生成器」演進為「自主工程組織」

────────────────

## 🛠️ 深度系統整合：消除 AI 與執行環境的「摩擦力」

[分析內容：跨文章交叉比對的深度洞察...]

────────────────

## 🏗️ 從單體模型到「Agent 集群」：軟體工程設計模式的轉移

[分析內容...]

────────────────

## 📚 領域專家模組化：將 SOP 轉化為 AI 可執行的「技能集」

[分析內容...]

────────────────

## 📉 效能槓桿：Token 經濟學與狀態持久化

[分析內容...]

────────────────

## 📌 這件事的意義

- **權限升級**：AI Agent 將從 Web 介面全面移向終端機與 IDE 核心
- **架構轉型**：開發模式將從「Prompt Engineering」轉向「Agent Organization Design」
- **知識標準化**：領域專家經驗被模組化為結構化技能集
- **成本優化**：錨點編輯與狀態持久化降低 Token 成本

────────────────

## 🔗 相關連結

- **oh-my-pi**:https://github.com/can1357/oh-my-pi
- **Claude Code**:https://github.com/anthropics/claude-code
- **Harness**:https://github.com/revfactory/harness

---

*這篇報告由 AI 從多方資料源協助整理與編輯，方便閱讀與討論；
若想看完整脈絡、原始說法與更多細節，仍建議以原文內容為主。*
```

---

## 開發路線圖 (Roadmap)

### Phase 1 — PoC ✅（已完成）
- ✅ 核心管道協調器實作（Fetch → Normalize → Extract → Analyze → Synthesize → Report）
- ✅ 雙渠道 Fetcher（Reddit + GitHub Trending，全免 API Key）
- ✅ trafilatura 為主的內容提取器（取代 FireCrawl）
- ✅ Map-Reduce LLM 分析（併發評分+摘要+子分析 → 彙總合成）
- ✅ Stratechery 風格 Markdown 報告 + JSON 輸出
- ✅ CLI 介面（argparse + uv run cortexflow）
- ✅ 完整的錯誤隔離與最佳努力策略

### Phase 2 — 穩定性與可觀測性
- [ ] 執行記錄持久化（SQLite）
- [ ] Token 用量統計與成本估算儀表板
- [ ] 各 Stage 獨立重跑能力
- [ ] 部分失敗報告機制

### Phase 3 — 生產力提升
- [ ] 自訂 Fetcher 插件機制
- [ ] 排程觸發（定時執行）
- [ ] Webhook / Slack / Discord 通知輸出
- [ ] 更多來源渠道（Hacker News、Lobsters、技術部落格 RSS）

---

## 授權規範

本專案基於 **MIT License** 開源。
