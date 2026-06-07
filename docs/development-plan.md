# CortexFlow 產品開發路線圖

> 階段：Prototype ✅ → MVP ✅ → MMP → MLP

---

## 當前狀態總覽（MVP ✅ 已完成）

### ✅ 已完成核心里程碑

| 階段 | 核心成就 | 狀態 |
|------|---------|------|
| **Phase 1: PoC** | 驗證 5 階段 Pipeline 與 Reddit/GitHub 採集邏輯 | ✅ |
| **Phase 2: Prototype** | CLI UX 升級、Demo 模式、程式碼清理與品質規範 (Ruff/Pyright) | ✅ |
| **Phase 3: MVP** | 結構化日誌、SQLite 執行歷史、新來源 (HN/Lobsters)、續傳與重試機制 | ✅ |

### 🔴 剩餘待辦（規劃進入 MMP 階段）

| 問題 | 規劃階段 | 說明 |
|------|---------|------|
| 硬編碼 Token 成本 | **MMP** | `gpt-4o-mini` 固定費率，與 `OPENAI_MODEL` 脫鉤 |
| 模型感知計價 | **MMP** | 不同模型價格不同，應動態查詢 |
| LLM 快取機制 | **MMP** | 避免重複分析相同內容以節省成本 |

---

## 階段一：Prototype ✅（已完成）

本階段奠定了專案的視覺與品質基礎。

### 驗收結果
*   **視覺品質**: 具備豐富的 Rich 終端機回饋與進度條。
*   **代碼規範**: 通過 Ruff 與 Pyright (Basic) 檢查。

---

## 階段二：MVP（最小可行性產品）✅（已完成）

### 核心目標：讓真實使用者願意在實際工作中使用

### 🎯 關鍵成果

#### 2.1 測試與品質基礎建設
- [x] **單元測試擴充**：測項總數達到 **81 個**，覆蓋核心邏輯與邊界案例。
- [x] **整合測試**：Mock HTTP/LLM 的 Pipeline 端到端測試。
- [x] **CI/CD**：GitHub Actions 自動執行多版本 Python (3.11-3.13) 測試。
- [x] **pre-commit hook**：整合 Ruff, Pyright, Pytest，確保提交前品質。

#### 2.2 可觀測性
- [x] **結構化日誌**：整合 `loguru`，支援 `--verbose` 與 `--log-file`。
- [x] **執行記錄持久化**：SQLite 儲存每次執行的輸入/輸出/耗時/Token 用量。
- [x] **`history` 指令**：`uv run cortexflow --history` 以表格列出執行記錄。
- [x] **`replay` 指令**：`uv run cortexflow --replay <id>` 完全重現特定執行。

#### 2.3 新資料來源
- [x] **Hacker News Fetcher**：透過 Algolia Search API 採集。
- [x] **Lobsters Fetcher**：透過 JSON API 獲取熱門技術討論。
- [x] **插件化 Fetcher 機制**：`FetcherRegistry` 自動發現 `fetchers/` 下的所有來源。
- [x] **設定檔支援**：支援 `cortexflow.toml` 自定義預設參數。

#### 2.4 Pipeline 強化
- [x] **重試機制**：整合 `tenacity` 實作指數退避重試，應對網路與 API 波動。
- [x] **Stage 中斷續傳**：支援 `--resume <id>` 從失敗的 Stage 繼續執行。
- [x] **超時控制強化**：每個 Stage 具備獨立的超時保護。
- [x] **降級模式**：LLM 不可用時自動切換至 `FallbackAnalyzer` (規則式評分)。

#### 2.5 型態與靜態分析
- [x] **pyright strict mode**：全專案 100% 通過嚴格型態檢查。
- [x] **ruff 完整規則集**：導入業界標準的 Linter 與 Formatter。

### 📊 驗收標準

| 標準 | 說明 |
|------|------|
| 測試覆蓋率 | > 80 測項（已達成：81 測項），覆蓋所有關鍵路徑 |
| CI 通過率 | main/dev branch 均由 GitHub Actions 守護 |
| 執行重現性 | 支援 Replay 與 Resume，Pipeline 狀態可持久化 |

---

## 階段三：MMP（最小可銷售產品）— 下一階段

### 核心目標：具備商業推廣價值，可作為付費產品/服務

### 🎯 關鍵成果

#### 3.1 效能與成本最佳化
- [ ] **LLM Response 快取**：SQLite 快取分析結果，相同內容不重複扣費。
- [ ] **選擇性提取**：先評分再提取（僅對高相關性文章執行 Stage 3）。
- [ ] **批次 LLM 呼叫**：減少呼叫次數，優化長上下文模型效率。

#### 3.2 輸出格式擴充
- [ ] **PDF 報告**：支援產出專業排版的 PDF 文件。
- [ ] **HTML 報告**：產出具備自適應介面的網頁版報告。
- [ ] **報告主題系統**：提供不同風格的 Markdown/HTML 渲染模板。

#### 3.3 部署與維運
- [ ] **Docker 映像**：多階段建置，提供輕量化的執行環境。
- [ ] **Docker Compose**：整合持久化資料庫與排程執行器。

#### 3.4 商業功能
- [ ] **通知渠道**：Slack / Discord Webhook 通知。
- [ ] **排程執行**：支援內建 Cron 語法進行自動化追蹤。

---

## 階段四：MLP（最小可愛產品）

... (後續規劃維持不變)
