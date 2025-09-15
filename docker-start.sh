#!/bin/bash

# TruePay Docker 啟動腳本

# 建立 logs 目錄
mkdir -p logs

# 檢查 .env 檔案是否存在
if [ ! -f .env ]; then
    echo "❌ 找不到 .env 檔案！"
    echo "📝 請複製 .env.docker.example 為 .env 並填入實際設定值"
    echo "   cp .env.docker.example .env"
    exit 1
fi

echo "🚀 啟動 TruePay Docker 服務..."

# 停止並移除現有容器
echo "🔄 停止現有容器..."
docker-compose down

# 建立並啟動服務
echo "🏗️  建立並啟動服務..."
docker-compose up --build -d

# 等待服務啟動
echo "⏳ 等待服務啟動..."
sleep 10

# 檢查服務狀態
echo "📊 服務狀態："
docker-compose ps

# 顯示有用的資訊
echo ""
echo "✅ TruePay 服務已啟動！"
echo ""
echo "🌐 服務端點："
echo "   Web 應用程式:    http://localhost:8000"
echo "   RabbitMQ 管理:   http://localhost:15672 (guest/guest)"
echo "   Celery Flower:   http://localhost:5555 (使用 --profile monitoring 啟動)"
echo ""
echo "📁 日誌檔案："
echo "   Celery Worker:   ./logs/celery-worker.log"
echo "   Celery Beat:     ./logs/celery-beat.log"
echo ""
echo "🔧 常用命令："
echo "   查看日誌:        docker-compose logs -f [服務名]"
echo "   進入容器:        docker-compose exec [服務名] bash"
echo "   停止服務:        docker-compose down"
echo "   重新啟動:        docker-compose restart [服務名]"
echo "   啟動 Flower:     docker-compose --profile monitoring up -d celery-flower"
echo ""
echo "📊 Celery 任務監控："
echo "   docker-compose exec celery-worker python -m celery -A truepay inspect active"