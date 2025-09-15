#!/bin/bash

# TruePay Docker 健康檢查腳本

echo "🔍 檢查 TruePay Docker 服務狀態..."
echo ""

# 檢查服務狀態
echo "📊 服務狀態："
docker-compose ps
echo ""

# 檢查 RabbitMQ 連線
echo "🐰 RabbitMQ 連線檢查："
docker-compose exec -T rabbitmq rabbitmq-diagnostics ping || echo "❌ RabbitMQ 連線失敗"
echo ""

# 檢查 PostgreSQL 連線
echo "🐘 PostgreSQL 連線檢查："
docker-compose exec -T postgres pg_isready -U ${DB_USER:-truepay} || echo "❌ PostgreSQL 連線失敗"
echo ""

# 檢查 Celery Worker 狀態
echo "⚙️  Celery Worker 狀態："
docker-compose exec -T celery-worker python -m celery -A truepay inspect ping || echo "❌ Celery Worker 無回應"
echo ""

# 檢查 Celery Beat 排程
echo "⏰ Celery Beat 排程檢查："
docker-compose exec -T celery-beat python -m celery -A truepay inspect scheduled || echo "❌ Celery Beat 無法檢查排程"
echo ""

# 檢查 Django 狀態
echo "🌐 Django 健康檢查："
docker-compose exec -T web python manage.py check --deploy || echo "❌ Django 健康檢查失敗"
echo ""

# 顯示最近的日誌
echo "📋 最近的服務日誌："
echo "--- Celery Worker 日誌 (最後 10 行) ---"
docker-compose exec -T celery-worker tail -n 10 /app/logs/celery-worker.log 2>/dev/null || echo "無法讀取 Celery Worker 日誌"
echo ""
echo "--- Celery Beat 日誌 (最後 10 行) ---"
docker-compose exec -T celery-beat tail -n 10 /app/logs/celery-beat.log 2>/dev/null || echo "無法讀取 Celery Beat 日誌"
echo ""

# 檢查票券任務是否正常執行
echo "🎫 票券任務執行檢查："
docker-compose exec -T celery-worker python -m celery -A truepay inspect active | grep -q "check_ticket_expiry" && echo "✅ 票券到期檢查任務執行中" || echo "⚠️  未發現票券到期檢查任務"

echo ""
echo "✅ 健康檢查完成！"