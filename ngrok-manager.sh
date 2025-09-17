#!/bin/bash

# ngrok 管理腳本

case "$1" in
    start)
        echo "啟動 ngrok 隧道服務..."
        if [ -z "$NGROK_AUTHTOKEN" ]; then
            echo "錯誤：未設定 NGROK_AUTHTOKEN 環境變數"
            echo "請在 .env 檔案中添加: NGROK_AUTHTOKEN=your_token_here"
            exit 1
        fi

        docker-compose --profile dev up -d ngrok
        echo "等待 ngrok 建立連接..."

        # 等待並取得網址
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
            echo "成功取得 ngrok 網址: $NGROK_URL"

            # 詢問是否要更新 .env
            read -p "是否要自動更新 .env 檔案？(y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                # 提取域名
                NGROK_DOMAIN=$(echo $NGROK_URL | sed 's|https://||')

                # 備份 .env
                cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

                # 更新 NGROK_URL
                if grep -q "^NGROK_URL=" .env; then
                    sed -i "s|^NGROK_URL=.*|NGROK_URL=$NGROK_URL|" .env
                else
                    echo "NGROK_URL=$NGROK_URL" >> .env
                fi

                # 更新 ALLOWED_HOSTS
                if grep -q "^ALLOWED_HOSTS=" .env; then
                    if ! grep -q "$NGROK_DOMAIN" .env; then
                        sed -i "s|^ALLOWED_HOSTS=\(.*\)|ALLOWED_HOSTS=\1,$NGROK_DOMAIN|" .env
                    fi
                else
                    echo "ALLOWED_HOSTS=localhost,127.0.0.1,$NGROK_DOMAIN" >> .env
                fi

                echo "已更新 .env 檔案"
            fi
        else
            echo "無法取得 ngrok 網址，請檢查 ngrok 服務狀態"
        fi
        ;;
    stop)
        echo "停止 ngrok 隧道服務..."
        docker-compose stop ngrok
        docker-compose rm -f ngrok
        ;;
    url)
        echo "當前 ngrok 隧道網址："
        docker-compose logs ngrok | grep -o "https://.*\.ngrok.*\.app" | tail -1 || echo "ngrok 未啟動或尚未建立連接"
        ;;
    logs)
        echo "ngrok 日誌："
        docker-compose logs -f ngrok
        ;;
    status)
        if docker-compose ps | grep -q ngrok; then
            echo "ngrok 狀態: 運行中"
            echo "網址: $(docker-compose logs ngrok | grep -o 'https://.*\.ngrok.*\.app' | tail -1)"
        else
            echo "ngrok 狀態: 未運行"
        fi
        ;;
    reset)
        echo "重置 ngrok 設定..."
        docker-compose stop ngrok 2>/dev/null
        docker-compose rm -f ngrok 2>/dev/null

        # 備份 .env
        cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

        # 移除 ngrok 相關設定
        sed -i '/^NGROK_URL=/d' .env
        sed -i 's/,[^,]*\.ngrok[^,]*\.app//g' .env
        sed -i 's/ALLOWED_HOSTS=,/ALLOWED_HOSTS=/' .env

        echo "已重置 ngrok 設定並停止服務"
        ;;
    *)
        echo "ngrok 管理腳本"
        echo "用法: $0 {start|stop|url|logs|status|reset}"
        echo ""
        echo "命令說明:"
        echo "  start   - 啟動 ngrok 隧道服務並可選更新 .env"
        echo "  stop    - 停止 ngrok 隧道服務"
        echo "  url     - 顯示當前隧道網址"
        echo "  logs    - 持續顯示 ngrok 日誌"
        echo "  status  - 檢查 ngrok 運行狀態"
        echo "  reset   - 停止服務並清理 .env 中的 ngrok 設定"
        echo ""
        echo "範例:"
        echo "  ./ngrok-manager.sh start"
        echo "  ./ngrok-manager.sh url"
        echo "  ./ngrok-manager.sh reset"
        exit 1
        ;;
esac