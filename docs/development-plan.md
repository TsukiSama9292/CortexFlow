# CortexFlow 產品開發路線圖

> 階段：Prototype → MVP → MMP → MLP
> 狀態：PoC ✅ 已完成

---

## 當前狀態總覽（PoC 已完成）

### ✅ 已實現
- 5 階段 Pipeline 端到端運作（Fetch → Normalize → Extract → Analyze → Synthesize → Report）
- 雙渠道資料採集（Reddit 三重 fallback + GitHub Trending）
- trafilatura 為主的內容提取器（取代 FireCrawl）
- Map-Reduce LLM 分析模式（併發評分+摘要+子分析 → 彙總合成）
- Stratechery 風格 Markdown 報告 + JSON 結構化輸出
- CLI 介面（`uv run cortexflow`）
- 完整的錯誤隔離與最佳努力策略
- 降級模式（無 LLM Key 仍可產出列表報告）

### 🔴 待清理問題
| 問題 | 嚴重性 | 說明 |
|------|--------|------|
| 死程式碼 | 中 | `extractor.py`、`firecrawl_client.py`、`fallback_parser.py`、`summarizer.py`、`llm_judge.py` 共 5 個未使用的檔案 |
| `sys.path` hack | 低 | `__main__.py` 使用 `sys.path.insert(0, ...)` 來 import `main.py` |
| 過時的註解 | 低 | `Article.extracted_html` 的 field description 仍提到 FireCrawl |
| 無測試覆蓋 | 高 | 雖有 pytest 依賴但無任何測試 |
| 無型態檢查 | 中 | 無 `mypy`/`pyright`/`ruff` 設定 |
| 無結構化日誌 | 中 | 僅靠 `rich.console` 輸出，無 logging 模組整合 |
| 硬編碼 Token 成本 | 低 | 使用 `gpt-4o-mini` 的固定費率，與實際設定的 `OPENAI_MODEL` 脫鉤 |
| Token 成本模型感知 | 中 | 不同模型價格不同，應動態查詢或設定 |
| 空 docs/ 目錄 | 低 | 目錄存在但無任何文件 |
| FireCrawl 設定殘留 | 低 | `settings.py` 仍保留 `firecrawl_api_key`、`firecrawl_api_url` 欄位 |

---

## 階段一：Prototype（原型製作）

### 核心目標：以 UX 展現產品願景，為競賽/募資簡報準備

本階段不追求功能完整，而是要讓任何人第一次使用時就感受到產品的價值與品質。

### 🎯 關鍵成果

#### 1.1 CLI 使用者體驗大升級
- [ ] **Rich 即時進度條**：每個 Stage 執行時顯示 spinner + 即時狀態更新
- [ ] **彩色結構化輸出**：階段標題、計時、錯誤訊息使用一致色彩系統
- [ ] **互動式模式**：`uv run cortexflow` 不加參數時進入互動式引導
- [ ] **精美的 Pipeline 視覺化**：啟動時以 ASCII 圖繪製 5 階段管線與當前位置
- [ ] **即時 Token 預估**：執行前先預估 LLM 成本並徵求確認

#### 1.2 程式碼品質清理（可展示性）
- [ ] **移除全部死程式碼**：刪除 5 個未使用的 legacy 檔案
- [ ] **重構 `__main__.py`**：消除 `sys.path` hack，改為標準 package 匯入
- [ ] **清理過時註解與欄位名稱**：消除 FireCrawl 相關的殘留文字
- [ ] **新增 `ruff` 與基本設定**：確保程式碼風格一致，適合公開展示
- [ ] **補上 module-level docstring**：所有模組至少有一行說明用途

#### 1.3 展示準備
- [ ] **Demo Mode 強化**：`--demo` 參數，不須任何 API Key 即可展示完整 Pipeline（含 LLM stage 使用模擬分析）
- [ ] **截圖/GIF 自動產生**：撰寫一鍵產生 CLI 執行 demo 錄製的腳本
- [ ] **README 更新**：加入實際執行截圖、GIF 展示、快速入門影片連結
- [ ] **產出範例報告庫**：`docs/samples/` 放入 3-5 份不同主題的實際輸出範例
- [ ] **簡報模板**：投影片大綱（包含 Pipeline 架構圖、Map-Reduce 流程、實際產出範例）

#### 1.4 設定與環境改善
- [ ] **啟動環境檢查**：執行前驗證必要套件、網路連線、API Key 格式
- [ ] **更好的錯誤訊息**：每個錯誤附帶「如何修復」的建議
- [ ] **移除 FireCrawl 殘留設定**：從 `settings.py` 與 `.env.example` 中移除未使用的欄位

### 📊 驗收標準
| 標準 | 說明 |
|------|------|
| 首次使用者體驗 | 從 `git clone` 到產出第一份報告 < 3 分鐘，無需閱讀文件 |
| 視覺品質 | CLI 輸出可直接截圖放入簡報，無需後製 |
| Demo 可執行性 | 在任何 Python 3.11+ 環境，`uv sync && uv run cortexflow --topic test --demo` 即可展示完整流程 |
| 程式碼可展示性 | 無死程式碼、風格一致、型態提示完整 |

### ⏱ 預估工時：2-3 週

---

## 階段二：MVP（最小可行性產品）

### 核心目標：讓真實使用者願意在實際工作中使用

### 🎯 關鍵成果

#### 2.1 測試與品質基礎建設
- [ ] **單元測試**：覆蓋 `Normalizer`、`errors`、`schema` 等純邏輯模組
- [ ] **整合測試**：Mock HTTP/LLM 的 Pipeline 端到端測試
- [ ] **Fixture 管理**：`conftest.py` 含測試用 Article 工廠、Mock LLM response
- [ ] **CI/CD**：GitHub Actions（PR 時自動跑 pytest + ruff + type check）
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
- [ ] **pyright / mypy strict mode**：整份 codebase 通過 strict type check
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
| **Prototype** | UX 展現產品願景 | 2-3 週 | 精美 CLI、Demo mode、程式碼清理 |
| **MVP** | 讓真實使用者用起來 | 4-6 週 | 測試、CI、新來源、可觀測性、執行記錄 |
| **MMP** | 具備商業推廣價值 | 6-8 週 | Docker、通知、成本優化、PDF/HTML 輸出 |
| **MLP** | 使用者愛不釋手 | 8-12 週 | Web Dashboard、生態系、智慧功能、社群 |

### 關鍵成功因素
1. **Prototype 階段不要急著加功能**：UX 打磨是競賽/募資的決勝點
2. **MVP 階段測試先行**：沒有測試的專案無法說服別人信賴
3. **MMP 階段專注成本**：LLM 成本是商業化最大的障礙
4. **MLP 階段重使用者反饋**：功能是做出來的，但可愛是被愛出來的
