#!/bin/bash

# TruePay Docker 啟動腳本

# 建立 logs 目錄
mkdir -p logs

# 檢查 .env 檔案是否存在
if [ ! -f .env ]; then
    echo "找不到 .env 檔案！"
    echo "請複製 .env.docker.example 為 .env 並填入實際設定值"
    echo "   cp .env.docker.example .env"
    exit 1
fi

echo "啟動 TruePay Docker 服務..."

# 停止並移除現有容器
echo "停止現有容器..."
docker-compose down

# 詢問是否啟動 ngrok
echo ""
read -p "是否要啟動 ngrok 隧道服務？(y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -z "$NGROK_AUTHTOKEN" ]; then
        echo "警告：未設定 NGROK_AUTHTOKEN 環境變數"
        echo "請在 .env 檔案中添加: NGROK_AUTHTOKEN=your_token_here"
        echo "跳過 ngrok，直接啟動其他服務..."
        USE_NGROK=false
    else
        echo "步驟 1/3: 啟動 ngrok 隧道服務..."
        # 先啟動基礎服務（postgres 和 rabbitmq）
        docker-compose up -d postgres rabbitmq

        # 啟動 ngrok
        docker-compose --profile dev up -d ngrok

        echo "等待 ngrok 建立連接..."
        # 等待 ngrok 啟動並取得網址
        NGROK_URL=""
        RETRY_COUNT=0
        MAX_RETRIES=30

        while [ -z "$NGROK_URL" ] && [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
            sleep 2
            NGROK_URL=$(docker-compose logs ngrok 2>/dev/null | grep -o "https://[^[:space:]]*\.ngrok[^[:space:]]*\.app" | tail -1)
            RETRY_COUNT=$((RETRY_COUNT + 1))
            echo -n "."
        done
        echo ""

        if [ -n "$NGROK_URL" ]; then
            echo "步驟 2/3: 成功取得 ngrok 網址: $NGROK_URL"

            # 更新 .env 檔案
            echo "更新 .env 檔案中的 ALLOWED_HOSTS 和 NGROK_URL..."

            # 提取域名（移除 https://）
            NGROK_DOMAIN=$(echo $NGROK_URL | sed 's|https://||')

            # 備份原始 .env
            cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

            # 更新或添加 NGROK_URL
            if grep -q "^NGROK_URL=" .env; then
                sed -i "s|^NGROK_URL=.*|NGROK_URL=$NGROK_URL|" .env
            else
                echo "NGROK_URL=$NGROK_URL" >> .env
            fi

            # 更新 ALLOWED_HOSTS（如果存在）
            if grep -q "^ALLOWED_HOSTS=" .env; then
                # 檢查是否已包含 ngrok 域名
                if ! grep -q "$NGROK_DOMAIN" .env; then
                    sed -i "s|^ALLOWED_HOSTS=\(.*\)|ALLOWED_HOSTS=\1,$NGROK_DOMAIN|" .env
                fi
            else
                echo "ALLOWED_HOSTS=localhost,127.0.0.1,$NGROK_DOMAIN" >> .env
            fi

            echo "已更新 .env 檔案"
            USE_NGROK=true
        else
            echo "警告：無法取得 ngrok 網址，將繼續啟動其他服務"
            USE_NGROK=false
        fi
    fi
else
    USE_NGROK=false
fi

# 建立並啟動其他服務
echo "步驟 3/3: 啟動 TruePay 服務..."
docker-compose up --build -d

# 等待服務啟動
echo "等待服務啟動..."
sleep 10

# 檢查服務狀態
echo "服務狀態："
docker-compose ps

# 顯示有用的資訊
echo ""
echo "TruePay 服務已啟動！"
echo ""
echo "服務端點："
echo "   Web 應用程式:    http://localhost:8000"
echo "   RabbitMQ 管理:   http://localhost:15673 (guest/guest)"
echo "   Celery Flower:   http://localhost:5555 (使用 --profile monitoring 啟動)"
if docker-compose ps | grep -q ngrok; then
    echo "   ngrok 隧道:      查看上方顯示的網址或執行 'docker-compose logs ngrok'"
fi
echo ""
echo "日誌檔案："
echo "   Celery Worker:   ./logs/celery-worker.log"
echo "   Celery Beat:     ./logs/celery-beat.log"

if [ "$USE_NGROK" = "true" ]; then
    echo ""
    echo "ngrok 隧道資訊："
    echo "   外部網址:        $NGROK_URL"
    echo "   已自動更新到 .env 檔案"
    echo "   備份檔案:        .env.backup.*"
fi
echo ""
echo "常用命令："
echo "   查看日誌:        docker-compose logs -f [服務名]"
echo "   進入容器:        docker-compose exec [服務名] bash"
echo "   停止服務:        docker-compose down"
echo "   重新啟動:        docker-compose restart [服務名]"
echo "   啟動 Flower:     docker-compose --profile monitoring up -d celery-flower"
echo "   查看 ngrok 網址:  docker-compose logs ngrok"
echo "   啟動 ngrok:      docker-compose --profile dev up -d ngrok"
echo ""
echo "前端資源管理："
echo "   建置前端:        ./frontend-build.sh build"
echo "   檢查前端:        ./frontend-build.sh check"
echo "   重建前端:        ./frontend-build.sh rebuild"
echo ""
echo "Celery 任務監控："
echo "   docker-compose exec celery-worker python -m celery -A truepay inspect active"