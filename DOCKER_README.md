# TruePay Docker 部署指南

本指南說明如何使用 Docker 和 Docker Compose 來運行 TruePay 應用程式，包含 Celery + RabbitMQ + Celery Beat 的自動票券到期通知系統。

## 🚀 快速開始

### 1. 環境準備

確保你的系統已安裝：
- Docker
- Docker Compose

### 2. 設定環境變數

```bash
# 複製環境變數範例檔案
cp .env.docker.example .env

# 編輯 .env 檔案，填入你的實際設定值
nano .env
```

### 3. 啟動服務

```bash
# 使用啟動腳本（推薦）
./docker-start.sh

# 或手動啟動
docker-compose up --build -d
```

### 4. 檢查服務狀態

```bash
# 使用健康檢查腳本
./docker-check.sh

# 或手動檢查
docker-compose ps
```

## 📋 服務說明

### 核心服務

| 服務名稱 | 說明 | 端口 |
|---------|------|------|
| `web` | Django 網站應用程式 | 8000 |
| `postgres` | PostgreSQL 資料庫 | 5432 |
| `rabbitmq` | RabbitMQ 訊息佇列 | 5672, 15672 |
| `celery-worker` | Celery 工作進程 | - |
| `celery-beat` | Celery 排程器 | - |
| `celery-flower` | Celery 監控工具（可選） | 5555 |

### 票券自動任務

系統會自動執行以下任務：

1. **票券到期檢查** (`check_ticket_expiry`)
   - 執行頻率：每分鐘
   - 功能：檢查即將到期的票券並發送通知

2. **清理過期票券** (`cleanup_expired_tickets`)
   - 執行頻率：每小時
   - 功能：將過期票券狀態更新為 'expired'

3. **每日統計報表** (`send_daily_ticket_report`)
   - 執行頻率：每日 23:00
   - 功能：統計當日票券使用情況

## 🔧 常用操作

### 查看日誌

```bash
# 查看所有服務日誌
docker-compose logs -f

# 查看特定服務日誌
docker-compose logs -f celery-worker
docker-compose logs -f celery-beat
docker-compose logs -f web

# 查看 Celery 日誌檔案
docker-compose exec celery-worker tail -f /app/logs/celery-worker.log
docker-compose exec celery-beat tail -f /app/logs/celery-beat.log
```

### 執行 Django 命令

```bash
# 進入 Web 容器
docker-compose exec web bash

# 執行 Django 管理命令
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py collectstatic
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py setup_ticket_schedule
```

### Celery 管理

```bash
# 檢查 Celery Worker 狀態
docker-compose exec celery-worker python -m celery -A truepay inspect ping

# 檢查正在執行的任務
docker-compose exec celery-worker python -m celery -A truepay inspect active

# 檢查排程任務
docker-compose exec celery-beat python -m celery -A truepay inspect scheduled

# 重新啟動 Celery 服務
docker-compose restart celery-worker celery-beat
```

### 啟動監控工具

```bash
# 啟動 Celery Flower 監控（開發環境）
docker-compose -f docker-compose.dev.yml up -d celery-flower

# 或使用 profile 方式
docker-compose --profile monitoring up -d celery-flower
```

## 🔍 監控和除錯

### 存取點

- **Web 應用程式**: http://localhost:8000
- **RabbitMQ 管理介面**: http://localhost:15672 (guest/guest)
- **Celery Flower**: http://localhost:5555 (admin/flower123，僅開發環境)

### 健康檢查

```bash
# 使用內建健康檢查腳本
./docker-check.sh

# 手動檢查各服務
docker-compose exec postgres pg_isready
docker-compose exec rabbitmq rabbitmq-diagnostics ping
docker-compose exec web python manage.py check --deploy
```

### 效能監控

```bash
# 查看容器資源使用情況
docker stats

# 查看特定容器的資源使用
docker stats truepay_celery-worker_1
```

## 🛠️ 開發環境

針對開發需求，可以使用 `docker-compose.dev.yml`：

```bash
# 啟動開發環境（包含更多除錯功能）
docker-compose -f docker-compose.dev.yml up --build -d

# 包含以下額外功能：
# - Celery Worker 除錯模式
# - 預設啟動 Flower 監控
# - Redis 快取服務
# - 自動設定票券排程
```

## 🔄 維護操作

### 停止服務

```bash
# 使用停止腳本
./docker-stop.sh

# 或手動停止
docker-compose down
```

### 清理資料

```bash
# 移除容器和資料卷
docker-compose down -v

# 移除映像檔
docker-compose down --rmi all

# 完全清理
docker-compose down -v --rmi all --remove-orphans
```

### 備份資料

```bash
# 備份 PostgreSQL 資料庫
docker-compose exec postgres pg_dump -U truepay truepay > backup.sql

# 備份 RabbitMQ 設定
docker-compose exec rabbitmq rabbitmqctl export_definitions /tmp/rabbitmq.json
docker-compose cp rabbitmq:/tmp/rabbitmq.json ./rabbitmq-backup.json
```

## 🚨 疑難排解

### 常見問題

1. **Celery Worker 無法連線到 RabbitMQ**
   ```bash
   # 檢查 RabbitMQ 是否啟動
   docker-compose logs rabbitmq
   
   # 重新啟動 RabbitMQ
   docker-compose restart rabbitmq
   ```

2. **票券任務沒有執行**
   ```bash
   # 檢查 Celery Beat 是否運作
   docker-compose logs celery-beat
   
   # 手動設定排程
   docker-compose exec web python manage.py setup_ticket_schedule
   ```

3. **資料庫連線失敗**
   ```bash
   # 檢查 PostgreSQL 狀態
   docker-compose logs postgres
   
   # 檢查環境變數設定
   docker-compose exec web env | grep DB_
   ```

### 日誌位置

- Celery Worker: `./logs/celery-worker.log`
- Celery Beat: `./logs/celery-beat.log`
- Django: Docker logs (`docker-compose logs web`)
- RabbitMQ: Docker logs (`docker-compose logs rabbitmq`)

## 📈 生產環境部署

建議的生產環境調整：

1. 使用外部資料庫和 RabbitMQ 服務
2. 設定適當的資源限制
3. 使用 SSL/TLS 加密
4. 設定監控和告警
5. 定期備份資料

```yaml
# 生產環境範例設定
deploy:
  resources:
    limits:
      memory: 512M
    reservations:
      memory: 256M
```