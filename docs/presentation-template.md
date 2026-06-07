# CortexFlow 簡報模板

> 適用於競賽／募資／技術分享的 10 分鐘簡報大綱

---

## Slide 1: 封面

**CortexFlow**
情報 ETL Pipeline — 從社群雜訊到結構化情報

```
你的名字／團隊名稱
日期
```

---

## Slide 2: 問題陳述

**情報超載，決策癱瘓**

- 開發者每天面對 Reddit、GitHub、Hacker News 等大量資訊源
- 手動過濾耗時費力，遺漏關鍵情報
- 現有方案過度依賴 LLM Agent（成本高、不可預測、難除錯）

> 「不是資訊不夠，而是有用的資訊被淹沒了」

---

## Slide 3: 解決方案 — CortexFlow

**固定管道式情報 ETL Pipeline**

```
  Fetch  →  Normalize  →  Extract  →
                  Analyze (Map)
                      ↓
         Synthesize (Reduce)
              ↓
           Report
```

- **5 個固定階段**：可預測、可重現、可除錯
- **Map-Reduce LLM 分析**：N 篇文章 = N+1 次 LLM 呼叫
- **錯誤隔離**：任一階段失敗不影響整個流程

---

## Slide 4: 核心架構 — Map-Reduce LLM 分析

```
  ┌──────────┐   asyncio.gather（併發）   ┌──────────────┐
  │ Article 1 │ ──────────────────────→ │ ArticleAnalysis │
  │ Article 2 │ ──────────────────────→ │ (評分+摘要+洞察) │
  │ Article 3 │ ──────────────────────→ │       ...       │
  └──────────┘                          └──────┬───────┘
                                                │
                                       （通過門檻者）
                                                ▼
                                      ┌──────────────────┐
                                      │   Synthesizer    │
                                      │  (Reduce: 1次呼叫)│
                                      └──────┬───────────┘
                                             ▼
                                      ┌──────────────────┐
                                      │   ReportContent  │
                                      │  (title+sections+ │
                                      │   key_points+links)│
                                      └──────────────────┘
```

**為什麼是 Map-Reduce？**
- 併發執行：所有文章同時分析，不互相等待
- 單次呼叫：每篇文章只需一次 LLM 呼叫
- 深度交叉：Synthesizer 取得預分析過的摘要，產出更有深度的報告
- 成本可控：N 篇文章只需 N+1 次 LLM 呼叫

---

## Slide 5: 技術亮點

| 特性 | 說明 |
|------|------|
| **零 API Key 設計** | Reddit 有 3 層 fallback（API → old.reddit → Demo），GitHub 用 Trending 爬蟲 |
| **降級模式** | 無 LLM Key 仍可運作，輸出結構化列表報告 |
| **錯誤隔離** | 單一文章失敗不影響整體流程 |
| **成本透明** | 執行前預估 Token 成本，無隱藏費用 |
| **非同步架構** | asyncio + Semaphore 控制併發，高效利用 API 配額 |

---

## Slide 6: 實際輸出範例

**主題：AI Coding Agents 2026**

```
✔ GitHub 採集 完成  (1.73s)
✔ 標準化去重 完成  (0.00s)
✔ 內容提取 完成  (2.07s)
✔ LLM 分析 完成  (31.57s)
✔ 報告合成 完成  (55.69s)
✔ 報告輸出 完成  (0.00s)

LLM 呼叫: 5 次
Token 用量: 11,464
預估成本: $0.0031
```

產出報告結構：
- 🚀 引人注目的主標題（含關鍵數據）
- 3-5 個深度分析章節（Stratechery 風格）
- 📌 重點總結
- 🔗 相關連結

---

## Slide 7: Demo 展示

**即時展示 CortexFlow Pipeline**

```bash
# Demo 模式 — 不需任何 API Key
uv sync && uv run cortexflow \
  --topic "AI Agent" \
  --sources github \
  --demo
```

展示重點：
1. Pipeline 視覺化啟動畫面
2. 各階段即時 spinner + 計時
3. 執行摘要與成本統計
4. 產出報告預覽

---

## Slide 8: 開發路線圖

```
現在（Prototype）          下一階段（MVP）           未來（MLP）
╔══════════════╗         ╔══════════════╗        ╔══════════════╗
║ 精美 CLI UX  ║  ──→   ║ 測試覆蓋 70% ║  ──→  ║ Web Dashboard║
║ Demo 模式    ║         ║ CI/CD       ║        ║ 生態系市集   ║
║ 程式碼品質   ║         ║ Hacker News  ║        ║ 趨勢偵測     ║
║ 47 項測試    ║         ║ 執行記錄     ║        ║ 一鍵分享     ║
╚══════════════╝         ╚══════════════╝        ╚══════════════╝
```

---

## Slide 9: 商業價值

| 面向 | 價值 |
|------|------|
| **節省時間** | 從每週數小時手動過濾 → 一鍵產出結構化報告 |
| **降低 LLM 成本** | Map-Reduce 設計比 Agent 方案節省 5-10 倍成本 |
| **決策品質** | 跨來源交叉比對，不再遺漏關鍵情報 |
| **自由度** | 不需要任何付費 API Key 即可使用核心功能 |

---

## Slide 10: 結尾

**CortexFlow**
情報 ETL Pipeline

- GitHub: [你的 repo 連結]
- 一鍵體驗：`uv sync && uv run cortexflow --topic test --demo`

**Q&A**

---

> 此簡報模板使用 Markdown 格式，可用以下工具轉換為投影片：
> - [Marp](https://marp.app/) — Markdown → HTML/PDF 投影片
> - [Slidev](https://sli.dev/) — 互動式 Markdown 簡報
> - [Pandoc](https://pandoc.org/) — Markdown → PPTX
