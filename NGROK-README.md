# Ngrok 自動化設定說明

## 功能概述

系統已優化為自動化的 ngrok 工作流程：

1. 先啟動 ngrok 取得外部網址
2. 自動更新 .env 檔案中的 `NGROK_URL` 和 `ALLOWED_HOSTS`
3. 然後啟動其他服務（web、celery、rabbitmq 等）

## 使用方式

### 方式 1: 使用優化後的啟動腳本（推薦）

```bash
./docker-start.sh
# 當詢問是否要啟動 ngrok 時，輸入 y
```

腳本會自動：
- 啟動 ngrok 並等待取得網址
- 更新 .env 檔案
- 啟動其他服務
- 顯示完整的服務資訊

### 方式 2: 使用 ngrok 管理腳本

```bash
# 啟動 ngrok（可選擇更新 .env）
./ngrok-manager.sh start

# 查看當前網址
./ngrok-manager.sh url

# 檢查狀態
./ngrok-manager.sh status

# 重置設定
./ngrok-manager.sh reset
```

## 自動更新的環境變數

執行後會在 .env 中自動添加/更新：

```env
NGROK_URL=https://xxxx-xx-xx-xxx-xx.ngrok-free.app
ALLOWED_HOSTS=localhost,127.0.0.1,xxxx-xx-xx-xxx-xx.ngrok-free.app
```

## 備份機制

每次更新 .env 時會自動建立備份：
- 格式：`.env.backup.YYYYMMDD_HHMMSS`
- 如需恢復，可複製備份檔案覆蓋 .env

## 前端資源問題

### 如果網頁缺少 CSS 或 JS
```bash
# 檢查前端資源狀態
./frontend-build.sh check

# 重新建置前端資源
./frontend-build.sh rebuild

# 或在容器內手動建置
docker-compose exec web npm run build
```

### 開發時前端資源監控
```bash
# 啟動前端資源監控（檔案變更時自動重建）
./frontend-build.sh watch
```

## 故障排除

### ngrok 無法啟動
1. 確認 `NGROK_AUTHTOKEN` 已在 .env 中設定
2. 檢查 ngrok 服務狀態：`docker-compose logs ngrok`

### 網址無法取得
- 腳本會等待最多 60 秒
- 如超時，會跳過更新繼續啟動其他服務

### 清理設定
```bash
# 重置所有 ngrok 相關設定
./ngrok-manager.sh reset
```

## 常用命令

```bash
# 查看 ngrok 日誌
docker-compose logs ngrok

# 重新啟動 ngrok
docker-compose restart ngrok

# 停止所有服務
docker-compose down
```

## 注意事項

- ngrok 免費版每次重啟會產生新的隨機網址
- 付費版可設定固定子域名
- 網址變更時系統會自動更新 .env 檔案