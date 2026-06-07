# CortexFlow

**情報 ETL Pipeline — 從社群雜訊到結構化情報的固定管道式系統**

CortexFlow 是一個基於 Python 非同步架構開發的**固定管道式（Fixed Pipeline）情報過濾與自動化彙整系統**。與動態規劃型研究代理不同，CortexFlow 將處理流程定義為一組可預測、可重現的固定階段（Stage），具備強大的錯誤隔離、重試機制與執行記錄持久化功能。

---

## 核心定位：堅韌的情報 ETL

*   **固定管道**：Fetch → Normalize → Extract → Analyze → Report，流程清晰可除錯。
*   **多源採集**：支援 Reddit, GitHub, Hacker News, Lobste.rs 等多元渠道。
*   **Map-Reduce 分析**：併發執行 LLM 文章分析，最後單次彙總合成深度報告。
*   **高可觀測性**：整合結構化日誌 (Loguru) 與 SQLite 執行歷史追蹤。
*   **生產級韌性**：實作指數退避重試、全階段超時保護與**中斷續傳 (--resume)**。

---

## 系統架構

```
[使用者輸入] → [cortexflow.toml]
        │
        ▼
┌─────────────────────────────────────────────┐
│ Stage 1: 資料採集層 (Fetch Layer)            │
│  ├─ Reddit, GitHub Trending                 │
│  ├─ Hacker News, Lobste.rs                  │
│  └─ [擴充點] 插件化 FetcherRegistry          │
└───────────────────┬─────────────────────────┘
                    ▼
┌─────────────────────────────────────────────┐
│ Stage 2: 標準化層 (Normalize Layer)          │
│  └─ URL 去重 + 內容指紋 (Fingerprint) 去重   │
└───────────────────┬─────────────────────────┘
                    ▼
┌─────────────────────────────────────────────┐
│ Stage 3: 內容提取層 (Extract Layer)          │
│  └─ trafilatura + BeautifulSoup 備援         │
└───────────────────┬─────────────────────────┘
                    ▼
┌─────────────────────────────────────────────┐
│ Stage 4: LLM 分析層 (Analyze Layer)         │
│  ├─ Map: 併發評分、摘要、深度分析            │
│  ├─ Reduce: 全局觀點合成與交叉比對           │
│  └─ Fallback: 規則式降級分析器               │
└───────────────────┬─────────────────────────┘
                    ▼
┌─────────────────────────────────────────────┐
│ Stage 5: 彙整輸出層 (Report Layer)          │
│  ├─ Markdown (豐富模式/列表模式)             │
│  └─ JSON (完整結構化資料)                    │
└───────────────────┬─────────────────────────┘
                    ▼
[SQLite 執行歷史] ── [輸出報告報告]
```

---

## CLI 使用方式

```bash
# 基本用法
uv run cortexflow --topic "Rust 併發編程"

# 指定多個來源並進入詳細模式
uv run cortexflow --topic "AI Agent" --sources github hackernews -v

# 從失敗點續傳執行
uv run cortexflow --resume 42

# 查看歷史記錄列表
uv run cortexflow --history

# 重新執行歷史任務
uv run cortexflow --replay 1
```

### 參數說明

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `--topic` | (必要) | 研究主題關鍵字 |
| `--sources` | reddit github | 來源渠道 (reddit, github, hackernews, lobsters) |
| `--output-format`| markdown | 輸出格式 (markdown, json) |
| `--threshold` | 5.0 | LLM 相關性門檻 (0-10) |
| `--demo` | - | Demo 模式：不需 API Key，使用模擬資料 |
| `--verbose`, `-v` | - | 顯示詳細偵錯日誌 |
| `--history` | - | 以表格列出 SQLite 中的執行紀錄 |
| `--resume <id>` | - | 從指定 ID 的失敗點繼續執行 |
| `--replay <id>` | - | 以相同設定重新執行歷史任務 |

---

## 專案結構

*   `cortexflow/core/`: 核心協調器 (`pipeline.py`)、資料庫 (`db.py`)、日誌 (`logger.py`) 與資料模型。
*   `cortexflow/fetchers/`: 各類資料來源採集器與註冊中心。
*   `cortexflow/config/`: 設定管理與 `cortexflow.toml` 載入邏輯。
*   `cortexflow/filter/`: LLM 分析、報告合成與降級分析器。
*   `tests/`: 包含 80+ 個測項的完整測試套件。

---

## 開發路線圖 (Roadmap)

### Phase 1: PoC & Prototype ✅
- ✅ 5 階段 Pipeline 核心實作
- ✅ Reddit/GitHub Trending 採集
- ✅ Rich CLI 視覺化介面

### Phase 2: MVP ✅ (目前版本)
- ✅ **可觀測性**: Loguru 結構化日誌 + SQLite 持久化
- ✅ **新來源**: Hacker News 與 Lobste.rs
- ✅ **韌性**: 指數退避重試、Stage 超時、中斷續傳
- ✅ **品質**: 100% Pyright Strict、Ruff、80+ Pytest 測項、CI/CD

### Phase 3: MMP (進行中)
- [ ] LLM Response 快取
- [ ] HTML/PDF 報告格式
- [ ] Docker 化與排程執行器

---

## 授權規範

本專案基於 **MIT License** 開源。
