# CortexFlow — 情報 ETL Pipeline

CortexFlow 是一個基於 Python 非同步架構開發的**固定管道式（Fixed Pipeline）情報過濾與自動化彙整系統**。它將情報處理流程定義為 5 個可預測、可重現的階段，並在分析階段採用 Map-Reduce 模式利用 LLM 進行深度合成。

## 核心架構：五階段管道

1.  **Fetch Layer (採集層)**: 從 Reddit、GitHub 等來源異步獲取原始資料。支援免 API Key 的爬蟲與 Demo 模式。
2.  **Normalize Layer (標準化層)**: 執行 URL 去重與內容指紋 (Content Fingerprint) 去重。
3.  **Extract Layer (提取層)**: 使用 `trafilatura` 與 `BeautifulSoup` 將網頁內容轉換為乾淨的 Markdown 格式。
4.  **Analyze Layer (分析層)**: 
    - **Map**: 對每篇文章進行併發 LLM 分析（相關性評分、摘要、洞察）。
    - **Reduce**: 彙總所有子分析結果，由 LLM 合成為結構化報告。
5.  **Report Layer (彙整層)**: 產出 Stratechery 風格的 Markdown 報告或結構化 JSON 檔案。

## 技術棧

- **語言**: Python 3.11+ (Asyncio)
- **套件管理**: [uv](https://docs.astral.sh/uv/)
- **資料模型**: Pydantic v2
- **設定管理**: Pydantic Settings
- **LLM 框架**: LangChain OpenAI
- **內容提取**: trafilatura, BeautifulSoup4
- **CLI 視覺化**: Rich

## 快速上手

### 安裝與設定

```bash
# 安裝依賴
uv sync

# 設定環境變數
cp .env.example .env
# 編輯 .env 填入 OPENAI_API_KEY
```

### 常用命令

- **執行 Pipeline**: `uv run cortexflow --topic "AI Agents"`
- **Demo 模式 (免 API Key)**: `uv run cortexflow --topic "AI Agents" --demo`
- **執行測試**: `pytest`
- **程式碼檢查**: `ruff check .`
- **程式碼格式化**: `ruff format .`
- **型態檢查**: `pyright`

## 開發慣例

- **非同步優先**: 核心邏輯應盡可能使用 `async/await` 以確保 I/O 效率。
- **型態安全**: 使用 Pydantic 模型進行資料驗證。所有新功能應符合 `cortexflow/core/schema.py` 定義的介面。
- **錯誤隔離**: 每個 Stage 應有獨立的錯誤處理機制，確保單一文章或單一渠道失敗不會中斷整個 Pipeline。
- **Map-Reduce 分析**: LLM 分析必須遵循 Map（併發分析）與 Reduce（單次合成）的模式，以平衡速度與連貫性。
- **文件規範**: 程式碼應包含 Google 風格的 Docstrings，並保持 `README.md` 同步更新。

## 專案結構

- `cortexflow/core/`: 管道協調器 (`pipeline.py`) 與資料模型 (`schema.py`)。
- `cortexflow/fetchers/`: 資料來源適配器。
- `cortexflow/filter/`: LLM 分析與合成邏輯。
- `cortexflow/extractor/`: 網頁內容提取器。
- `cortexflow/reporter/`: 報告生成器。
- `tests/`: 單元與整合測試。
