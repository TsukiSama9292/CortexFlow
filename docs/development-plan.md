# CortexFlow 產品開發路線圖

> 階段：Prototype ✅ → MVP → MMP → MLP

---

## 當前狀態總覽（Prototype ✅ 已完成）

### ✅ Phase 0 → 1 完成項目

| 類別 | 項目 | 狀態 |
|------|------|------|
| **死程式碼清理** | 移除 5 個 legacy 檔案（extractor.py、firecrawl_client.py、fallback_parser.py、summarizer.py、llm_judge.py） | ✅ |
| **`__main__.py` 重構** | 消除 `sys.path.insert` hack，改為 `from cortexflow.cli import main` | ✅ |
| **過時註解清理** | `Article.extracted_html` field description 及 `fast_extractor.py` docstring 已清理 | ✅ |
| **FireCrawl 殘留設定** | `settings.py`、`.env.example`、`.env` 中全部移除 | ✅ |
| **Ruff 設定** | `pyproject.toml` 含 `[tool.ruff]`（line-length=100, quote-style=double, lint rules） | ✅ |
| **pyright 設定** | `pyproject.toml` 含 `[tool.pyright]`（typeCheckingMode=basic） | ✅ |
| **Module docstring** | 所有 Package `__init__.py` 補上說明 | ✅ |
| **測試覆蓋** | 47 測項（schema 19 + errors 11 + normalizer 9 + pipeline 8），`pytest -q` 全通過 | ✅ |
| **Rich 進度條** | 每個 Stage 執行時顯示 `console.status` spinner + 即時計時 | ✅ |
| **彩色輸出** | 一致色彩系統（✔ 綠 / ✘ 紅 / ⚠ 黃 / 💡 dim / 時間 cyan） | ✅ |
| **互動式模式** | `uv run cortexflow`（無參數）→ 逐步引導主題/來源/Demo 切換 | ✅ |
| **Pipeline 圖** | 啟動時顯示 5 階段 ASCII 管線圖（Map-Reduce 標示） | ✅ |
| **Token 預估** | 執行前依使用者設定估算 LLM 成本 | ✅ |
| **Demo Mode** | `--demo` 不需 API Key，Mock Reddit/GitHub 資料 + Mock LLM 分析 | ✅ |
| **環境檢查** | 啟動前檢查 Python 版本、套件載入、API Key、Proxy URL | ✅ |
| **錯誤修復建議** | 每階段失敗顯示 💡 建議，環境問題顯示具體修復指令 | ✅ |
| **錄製腳本** | `docs/demo-recording.sh` — 支援 `asciinema` 與純文字模式 | ✅ |
| **簡報模板** | `docs/presentation-template.md` — 10 頁投影片大綱 | ✅ |
| **範例報告庫** | `docs/samples/` 含 5 份不同主題報告 | ✅ |
| **README 更新** | Demo 模式說明、CLI 輸出範例、參數表格 | ✅ |
| **輸出目錄** | 預設輸出 `outputs/report.md`，`outputs/` 已加入 `.gitignore` | ✅ |

### 🔴 剩餘待辦（非 Prototype 範圍）

| 問題 | 規劃階段 | 說明 |
|------|---------|------|
| 無結構化日誌 | **MVP** | 僅靠 `rich.console`，無 logging 模組 |
| 硬編碼 Token 成本 | **MMP** | `gpt-4o-mini` 固定費率，與 `OPENAI_MODEL` 脫鉤 |
| 模型感知計價 | **MMP** | 不同模型價格不同，應動態查詢 |

---

## 階段一：Prototype ✅（已完成）

本階段耗時約 **1 週**（含 audit 補正），原始規劃 2-3 週。

### 驗收結果

| 標準 | 結果 |
|------|------|
| 首次使用者體驗 | `git clone && uv sync && uv run cortexflow --topic test --demo` → 1 分鐘產出報告 |
| 視覺品質 | CLI 輸出可直接截圖放入簡報 |
| Demo 可執行性 | 任一 Python 3.11+ 環境，無 API Key 即可展示 |
| 程式碼可展示性 | 零死程式碼、Ruff 零錯誤、型態提示完整 |

---

## 階段二：MVP（最小可行性產品）— 下一階段

### 核心目標：讓真實使用者願意在實際工作中使用

### 🎯 關鍵成果

#### 2.1 測試與品質基礎建設
- [ ] **單元測試擴充**：覆蓋 fetchers、extractor、reporter 模組（目標 > 80 測項）
- [ ] **整合測試**：Mock HTTP/LLM 的 Pipeline 端到端測試
- [ ] **CI/CD**：GitHub Actions（PR 時自動跑 pytest + ruff + pyright）
- [ ] **pre-commit hook**：提交前自動檢查格式與型態

#### 2.2 可觀測性
- [ ] **結構化日誌**：整合 `loguru` 或標準 `logging`，支援 `--verbose` / `--log-file`
- [ ] **執行記錄持久化**：SQLite 儲存每次 Pipeline 執行的輸入/輸出/耗時/Token 用量
- [ ] **`history` 指令**：`uv run cortexflow --history` 列出近期執行記錄
- [ ] **`replay` 指令**：`uv run cortexflow --replay <id>` 從歷史記錄重現特定執行

#### 2.3 新資料來源
- [ ] **Hacker News Fetcher**：Algolia Search API 搜尋 + 文章內容提取
- [ ] **Lobsters Fetcher**：API 撈取熱門/最新文章
- [ ] **插件化 Fetcher 機制**：定義 Fetcher 註冊介面，`cortexflow/fetchers/plugins/` 自動發現
- [ ] **設定檔支援**：`cortexflow.yml` / `cortexflow.toml` 指定來源組合與參數

#### 2.4 Pipeline 強化
- [ ] **重試機制**：可設定的 retry policy（次數、backoff），特別是 LLM 呼叫
- [ ] **Stage 中斷續傳**：支援 `--resume` 從失敗 stage 繼續執行
- [ ] **超時控制強化**：每個 Stage 有獨立的 timeout 設定
- [ ] **更好的降級模式**：當 LLM 失敗時，使用規則式關鍵字評分作為降級

#### 2.5 型態與靜態分析
- [ ] **pyright strict mode**：整份 codebase 通過 strict type check
- [ ] **ruff 完整規則集**：導入所有相關 linter rules

### 📊 驗收標準

| 標準 | 說明 |
|------|------|
| 測試覆蓋率 | > 70%（關鍵路徑：Pipeline orchestration、LLM 分析、資料去重） |
| CI 通過率 | main branch 永遠保持綠燈 |
| 新來源上線 | 從寫 Fetcher 到 PR 合併 < 1 天（因有 plugins 機制） |
| 執行重現性 | 任一 Pipeline 執行都可透過 ID 完整重現 |

### ⏱ 預估工時：4-6 週

---

## 階段三：MMP（最小可銷售產品）

### 核心目標：具備商業推廣價值，可作為付費產品/服務

### 🎯 關鍵成果

#### 3.1 效能與成本最佳化
- [ ] **LLM Response 快取**：相同 article content 不重複呼叫 LLM（SQLite 快取）
- [ ] **選擇性提取**：僅對可能通過門檻的文章進行內容提取（先評分再提取）
- [ ] **批次 LLM 呼叫**：將多篇文章合併為單次 LLM 呼叫（適用於上下文視窗大的模型）
- [ ] **模型感知 Token 計價**：根據 `OPENAI_MODEL` 自動查詢或設定對應價格

#### 3.2 輸出格式擴充
- [ ] **PDF 報告**：基於 Markdown → PDF（weasyprint / pandoc）
- [ ] **HTML 報告**：自適應網頁版報告（可嵌入 iframe）
- [ ] **CSV 匯出**：結構化資料輸出，便於試算表分析
- [ ] **報告主題系統**：可更換的 CSS 主題（dark / light / corporate）

#### 3.3 部署與維運
- [ ] **Docker 映像**：多階段建置，`docker run cortexflow --topic ...`
- [ ] **Docker Compose**：+ 排程器（如 celery beat）定期執行
- [ ] **Helm Chart**：K8s 部署（選用，視目標客戶需求）

#### 3.4 商業功能
- [ ] **通知渠道**：Slack webhook、Discord webhook、Email（smtplib）
- [ ] **排程執行**：內建 cron 語法，`--schedule "0 9 * * 1"` 每週一早上九點執行
- [ ] **用量統計與報表**：每月 Token 用量、執行次數、熱門主題分析

#### 3.5 API 服務模式（選用）
- [ ] **FastAPI 伺服器**：提供 REST API 觸發 Pipeline
- [ ] **SSE 即時推送**：Pipeline 執行進度透過 Server-Sent Events 推送
- [ ] **簡易 Web Dashboard**：執行歷史、報告瀏覽、手動觸發

### 📊 驗收標準

| 標準 | 說明 |
|------|------|
| 成本效益 | 與 Phase 1 相比，相同資訊量成本降低 > 50%（透過快取 + 選擇性提取） |
| 輸出多樣性 | 支援至少 4 種輸出格式（Markdown/JSON/PDF/HTML） |
| Docker 部署 | `docker compose up` 一鍵啟動，含排程器 |
| 商業通路 | Slack/Discord/Email 三種通知管道就緒 |

### ⏱ 預估工時：6-8 週

---

## 階段四：MLP（最小可愛產品）

### 核心目標：使用者愛不釋手，建立情感連結與忠誠度

### 🎯 關鍵成果

#### 4.1 極致使用者體驗
- [ ] **即時串流 Pipeline**：每個 Stage 的輸出即時串流到終端機，如 `kubectl` 般流暢
- [ ] **Web Dashboard**：即時 Pipeline 視覺化、報告預覽、歷史趨勢圖
- [ ] **一鍵分享**：產出報告可一鍵產生公開分享連結（內建輕量 server）
- [ ] **報告訂閱**：使用者可訂閱特定主題，有新報告時自動推送
- [ ] **主題推薦**：基於歷史執行記錄，推薦相關研究主題

#### 4.2 進階 LLM 整合
- [ ] **多模型策略**：評分用快速/便宜模型，合成用強大/昂貴模型
- [ ] **自訂分析 Prompt**：使用者可撰寫自訂的分析指令
- [ ] **反饋迴圈**：使用者可對報告評分，回饋用於改善 LLM prompt
- [ ] **報告協作編輯**：產出後可在 Web UI 上手動編輯調整

#### 4.3 社群與生態系
- [ ] **Fetcher 市集**：社群貢獻的 Fetcher 可透過簡單指令安裝
- [ ] **報告模板市集**：使用者可分享自訂的報告主題與模板
- [ ] **公開報告畫廊**：`gallery.cortexflow.dev` 展示社群最佳報告
- [ ] **API 用戶端函式庫**：Python / TypeScript SDK 供開發者整合

#### 4.4 智慧功能
- [ ] **趨勢偵測**：跨多次執行的主題趨勢分析（哪些主題討論度上升/下降）
- [ ] **異常預警**：當某主題突然爆量時自動通知
- [ ] **來源品質評分**：基於歷史資料評估各來源的可靠度與相關性

### 📊 驗收標準

| 標準 | 說明 |
|------|------|
| 使用者留存 | 使用者一週後回訪率 > 60% |
| 分享率 | > 30% 的報告被使用者主動分享 |
| 社群貢獻 | 至少有 5 個第三方 Fetcher 或主題貢獻 |
| NPS | 淨推薦值 > 50 |

### ⏱ 預估工時：8-12 週

---

## 總結：階段時程與資源

| 階段 | 核心主題 | 預計工時 | 關鍵交付 |
|------|---------|---------|---------|
| **Prototype** | UX 展現產品願景 | ✅ **1 週**（已完工） | 精美 CLI、Demo mode、47 tests、程式碼清理 |
| **MVP** | 讓真實使用者用起來 | 4-6 週 | 測試擴充、CI、新來源、結構化日誌、執行記錄 |
| **MMP** | 具備商業推廣價值 | 6-8 週 | Docker、通知、成本優化、PDF/HTML 輸出 |
| **MLP** | 使用者愛不釋手 | 8-12 週 | Web Dashboard、生態系、智慧功能、社群 |

### 關鍵成功因素
1. **MVP 階段測試先行**：Prototype 已建立 47 測項基礎，MVP 應衝到 > 80% 覆蓋
2. **MMP 階段專注成本**：LLM 成本是商業化最大的障礙
3. **MLP 階段重使用者反饋**：功能是做出來的，但可愛是被愛出來的
