# CortexFlow 產品開發路線圖

> 階段：PoC ✅ → Prototype ✅ → MVP ✅ → MMP → MLP

---

## 專案發展總覽（截至 2026/06/07）

目前 CortexFlow 已成功走過從 PoC 到 MVP 的完整路徑，建立了一套堅韌、可觀測且具備生產級質量的情報 ETL 核心。

### ✅ 已實現核心里程碑

| 階段 | 核心成就 | 狀態 |
|------|---------|------|
| **Phase 0: PoC** | 驗證 5 階段 Pipeline 與 Reddit/GitHub 採集邏輯 | ✅ |
| **Phase 1: Prototype** | CLI UX 升級、Demo 模式、代碼品質規範 (Ruff/Pyright) | ✅ |
| **Phase 2: MVP** | 結構化日誌、SQLite 執行歷史、新來源、續傳與重試機制、81 項測試 | ✅ |

---

## 階段零：概念驗證 (PoC) ✅（已完成）

### 🎯 已實現功能
- 5 階段 Pipeline 端到端運作（Fetch → Normalize → Extract → Analyze → Synthesize → Report）
- 雙渠道資料採集（Reddit 三重 fallback + GitHub Trending）
- trafilatura 為主的內容提取器（取代 FireCrawl）
- Map-Reduce LLM 分析模式（併發評分+摘要+子分析 → 彙總合成）
- Stratechery 風格 Markdown 報告 + JSON 結構化輸出
- CLI 介面（`uv run cortexflow`）
- 完整的錯誤隔離與最佳努力策略
- 降級模式（無 LLM Key 仍可產出列表報告）

---

## 階段一：Prototype（原型製作） ✅（已完成）

本階段奠定了專案的視覺與代碼質量基礎，讓產品從「可用」變為「專業」。

### 🎯 關鍵成果

#### 1.1 CLI 使用者體驗大升級
- [x] **Rich 即時進度條**：每個 Stage 執行時顯示 spinner + 即時狀態更新。
- [x] **彩色結構化輸出**：階段標題、計時、錯誤訊息使用一致色彩系統。
- [x] **互動式模式**：`uv run cortexflow` 不加參數時進入互動式引導。
- [x] **精美的 Pipeline 視覺化**：啟動時以 ASCII 圖繪製 5 階段管線與當前位置。
- [x] **即時 Token 預估**：執行前先預估 LLM 成本並徵求確認。

#### 1.2 程式碼品質清理
- [x] **移除全部死程式碼**：刪除 5 個未使用的 legacy 檔案 (`extractor.py`, `summarizer.py` 等)。
- [x] **重構 `__main__.py`**：消除 `sys.path` hack，改為標準 package 匯入。
- [x] **清理過時註解與欄位名稱**：消除與 FireCrawl 相關的殘留文字。
- [x] **導入 `ruff` 設定**：確保代碼格式與 Lint 符合最高規範。
- [x] **補上 module-level docstring**：提升代碼庫的可維護性。

#### 1.3 展示與環境準備
- [x] **強化 Demo Mode**：`--demo` 參數，模擬完整 LLM 分析流程。
- [x] **截圖/GIF 自動產生**：建立錄製腳本以利展示。
- [x] **README 全面改版**：加入架構圖、範例數據與快速入門指引。

---

## 階段二：MVP（最小可行性產品） ✅（已完成）

### 核心目標：讓真實使用者願意在實際工作中使用

### 🎯 關鍵成果

#### 2.1 測試與品質基礎建設
- [x] **單元測試擴充**：測項總數達到 **81 個**，覆蓋所有核心組件。
- [x] **整合測試**：Mock 環境下的 Pipeline 端到端驗證。
- [x] **CI/CD**：GitHub Actions 自動化多版本測試流程。
- [x] **pre-commit hook**：本地端強制執行品質檢查。

#### 2.2 可觀測性與持久化
- [x] **結構化日誌**：整合 `loguru`，支援 `--verbose` 與檔案日誌輸出。
- [x] **執行記錄持久化**：使用 SQLite 儲存每次 Pipeline 執行的詳細數據。
- [x] **`history` 與 `replay` 指令**：支援查詢歷史記錄與完全重現特定執行。

#### 2.3 擴充性與新來源
- [x] **Hacker News Fetcher**：Hacker News 熱門討論抓取。
- [x] **Lobsters Fetcher**：Lobste.rs 技術社群採集。
- [x] **插件化 Fetcher 機制**：`FetcherRegistry` 支援動態發現新採集器。
- [x] **設定檔支援**：`cortexflow.toml` 預設參數自定義。

#### 2.4 Pipeline 韌性強化
- [x] **重試機制**：整合 `tenacity` 實作指數退避重試。
- [x] **Stage 中斷續傳**：支援從失敗點恢復執行的 `--resume` 功能。
- [x] **超時控制**：全階段 `asyncio.wait_for` 保護。
- [x] **Fallback Analyzer**：LLM 故障時自動降級至規則式分析。

---

## 階段三：MMP（最小可銷售產品）— 下一階段

### 核心目標：商業化部屬與工程化開發環境

### 🎯 關鍵成果

#### 3.1 商業級開發架構 (Monorepo)
- [ ] **Turborepo 深度整合**：
    - 建立 Monorepo 結構，加速建置與測試。
    - 在根目錄配置任務管線，將 `uv run pytest` 與 `next build` 納入網格相依性。
- [ ] **Control Plane / Data Plane 解耦設計**：
    - 將 API 調度中心與 ETL 執行節點分離，Data Plane 支援水平擴展。
    - 實作心跳機制 (Heartbeat)，若 Worker 異常中斷需自動釋放任務。

#### 3.2 工業級部屬方案 (Infrastructure as Code)
- [ ] **Traefik 邊緣路由器導入**：動態路由分流與自動化 SSL 管理。
- [ ] **生產級 Docker 生態**：Multi-stage Builds 與極簡化 Docker Compose 佈署。
- [ ] **Helm Chart 雲端發佈**：支援 K8s 企業級集群部署。

#### 3.3 商業數據基石 (ORM & Migration)
- [ ] **SQLAlchemy ORM 遷移**：從 SQLite 升級至企業級 PostgreSQL。
- [ ] **Alembic Migration**：建立嚴謹的資料庫遷移版本控制。
- [ ] **PostgreSQL 事務性任務佇列 (DB-as-a-Queue)**：
    - 利用 `FOR UPDATE SKIP LOCKED` 實作高效任務分發，移除 Redis 依賴。
    - 針對狀態與時間戳建立複合索引，並確保耗時操作位於事務外部。

#### 3.4 商業化與通知整合 (Marketability)
- [ ] **多渠道通知系統**：支援 Slack, Discord, Telegram 即時推送報告摘要。
- [ ] **進階採集防護 (Proxy Management)**：
    - 實作代理伺服器池 (Proxy Pool) 與動態 User-Agent 切換，防止被目標網站阻擋。
- [ ] **分層聚合機制 (Hierarchical Reduction)**：
    - 針對大規模採集（>50 篇文章），實作分批分析與二次合成，避免 LLM 上下文視窗溢出。
- [ ] **進階去重演算法**：
    - 導入 LSH (Locality Sensitive Hashing) 如 MinHash，應對微調重複內容。

#### 3.5 前端管理後台 (`apps/web`)
- [ ] **Next.js 官方網站**：視覺化 Dashboard、歷史情報檢索、Token 成本統計。

---

## 階段四：MLP（最小可愛產品）

### 核心目標：極致使用者體驗與社群生態

### 🎯 關鍵成果
- [ ] **即時串流 progress**：Web 端動態展示執行細節。
- [ ] **Fetcher 插件市集**：支援社群貢獻採集器。
- [ ] **一鍵分享與嵌入**：開放情報連結分享功能。

---

## 總結：階段時程與資源

| 階段 | 核心主題 | 預計工時 | 關鍵交付 |
|------|---------|---------|---------|
| **PoC** | 概念驗證 | ✅ **1 週** | 驗證邏輯思路無誤 |
| **Prototype** | 產品願景 | ✅ **1 週** | 精美 CLI、Demo mode |
| **MVP** | 真實工作可用 | ✅ **4 週** | 81 測項、新來源、執行記錄 |
| **MMP** | 商業部屬與工程化 | 8-10 週 | Turborepo, Helm Chart, Docker, ORM/Migration |
| **MLP** | 使用者愛不釋手 | 10-12 週 | 即時串流、市集生態、一鍵分享 |
