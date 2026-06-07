# CortexFlow 部署指南

本文件介紹如何使用 Helm 在 Kubernetes 集群中部署 CortexFlow 系列服務。

## 前置作業

- 已安裝 **Helm 3.0+**。
- 已配置好 **Kubernetes 集群** (如 minikube, k3s, EKS 等)。
- (選用) 已安裝 **Traefik** 或其他 Ingress Controller（本 Chart 預設支援 Traefik）。

---

## 使用 Helm 安裝

我們建議使用 `helm upgrade --install` 指令，這可以確保在初次安裝與後續更新時使用一致的流程。

### 快速安裝指令

執行以下指令將 CortexFlow 部署到名為 `cortexflow` 的命名空間中：

```bash
helm upgrade --install contexflow ./helm/contexflow \
  --create-namespace \
  --namespace cortexflow
```

### 指令參數說明

- `upgrade --install`: 如果 release 不存在則安裝，如果已存在則進行更新。
- `contexflow`: 指定 Helm release 的名稱。
- `./helm/contexflow`: Chart 原始碼所在的目錄路徑。
- `--create-namespace`: 如果指定的 namespace 不存在，則自動建立。
- `--namespace cortexflow`: 指定部署的目標命名空間。

---

## 解除安裝 (Clean Uninstall)

若要完全移除部署的所有資源（包含資料庫中的暫存資料），請執行：

```bash
helm uninstall contexflow --namespace cortexflow
```

> **注意**：目前預設配置下的資料庫使用 `emptyDir` 儲存，解除安裝將導致所有資料遺失。在生產環境中，建議配置 Persistent Volume (PV)。

---

## 常用配置調整

你可以透過 `--set` 參數或自定義 `values.yaml` 來調整配置。

### 修改 API 埠號
```bash
--set api.service.port=8080
```

### 修改資料庫密碼
```bash
--set database.auth.password=your_secure_password
```

---

## 驗證部署狀態

安裝完成後，可以使用以下指令檢查 Pod 狀態：

```bash
kubectl get pods -n cortexflow
```

你應該會看到以下元件正在執行：
- `contexflow-api`
- `contexflow-worker`
- `contexflow-web`
- `contexflow-db` (PostgreSQL + pgvector)
