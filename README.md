# CortexFlow

**情報 ETL Pipeline — 從社群雜訊到結構化情報的 Monorepo 工程化系統**

CortexFlow 是一個基於 Turborepo 管理的工程化情報系統。它採用 Control/Data Plane 分離架構，將複雜的情報處理流程（Fetch → Normalize → Extract → Analyze → Report）封裝為可擴展的微服務群，並透過 LLM 進行 Map-Reduce 模式的情報合成。

---

## 🏗️ 系統架構 (Monorepo)

本專案採用 **Turborepo** 管理，結構如下：

- **`apps/`** (應用程式層)
    - `api/`: Control Plane，負責任務調度與 API 提供。
    - `worker/`: Data Plane，執行實際的 ETL Pipeline 任務。
    - `web/`: Next.js 前端管理後台。
    - `cli/`: 互動式命令列工具。
- **`packages/`** (共享套件層)
    - `core/`: 核心邏輯、資料模型 (Pydantic)、資料庫 (SQLAlchemy/Alembic) 與 Pipeline 引擎。
- **`docker/`**: 包含開發與生產環境的 Docker 配置。
- **`helm/`**: K8s 生產環境部署 Chart。

---

## 🚀 快速上手 (開發環境)

本專案使用 `npm` 作為 Monorepo 管理員，並透過 `docker compose` 啟動基礎設施。

### 1. 環境初始化

啟動必要的開發環境基礎設施（PostgreSQL + Traefik）：
```bash
npm run init
```

### 2. 啟動開發模式
啟動所有應用程式的開發伺服器：
```bash
npm run dev
```

### 3. 常用開發指令
Turborepo 會自動處理任務相依性與快取：
- **測試**：`npm test`
- **檢查**：`npm run lint`
- **建置**：`npm run build`
- **型態檢查**：`npm run type-check`

---

## 🐳 Docker 與容器化

### 本地整合測試 (Full Stack)
啟動包含 API、Worker、Web 與 DB 的完整環境：
```bash
docker compose -f docker/contexflow/docker-compose.yml up -d
```
存取路徑：
- Web UI: [http://localhost](http://localhost)
- API Docs: [http://api.localhost/docs](http://api.localhost/docs)

### 建置與推送鏡像
```bash
npm run docker:build
npm run docker:push
```

---

## ☸️ Kubernetes 部署 (Helm)

我們提供生產級的 Helm Chart 部署方案：
```bash
# 安裝或更新
helm upgrade --install contexflow ./helm/contexflow --create-namespace --namespace cortexflow
```
詳細部署資訊請參考 [部署指南](docs/deployment.md)。

---

## 📜 核心開發方法

1.  **非同步優先**：核心邏輯使用 `asyncio` 以確保 I/O 效率。
2.  **型態安全**：全面使用 Pydantic v2 與 Pyright 嚴格模式。
3.  **任務隔離**：API (Control Plane) 與 Worker (Data Plane) 透過資料庫任務隊列通訊。
4.  **快取加速**：利用 Turborepo 的遠端快取機制優化 CI/CD 流程。

---

## 授權規範

本專案基於 **MIT License** 開源。
