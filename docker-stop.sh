#!/bin/bash

# TruePay Docker 停止腳本

echo "🛑 停止 TruePay Docker 服務..."

# 停止並移除容器
docker-compose down

# 顯示清理選項
echo ""
echo "🧹 清理選項："
echo "   移除所有資料:    docker-compose down -v"
echo "   移除映像檔:      docker-compose down --rmi all"
echo "   完全清理:        docker-compose down -v --rmi all --remove-orphans"

echo "✅ 服務已停止！"