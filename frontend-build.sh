#!/bin/bash

# 前端資源建置腳本

echo "前端資源建置與管理"

case "$1" in
    build)
        echo "建置前端資源..."
        docker-compose exec web npm run build
        echo "前端資源建置完成"
        ;;
    watch)
        echo "啟動前端資源監控（開發模式）..."
        docker-compose exec web npm run watch
        ;;
    check)
        echo "檢查前端資源狀態..."
        echo "Static 目錄內容："
        docker-compose exec web ls -la /app/static/ 2>/dev/null || echo "static 目錄不存在"
        echo ""
        echo "編譯後的檔案："
        docker-compose exec web find /app/static -name "*.js" -o -name "*.css" 2>/dev/null || echo "找不到編譯後的檔案"
        echo ""
        echo "Django collectstatic 狀態："
        docker-compose exec web ls -la /app/staticfiles/ 2>/dev/null | head -10
        echo ""
        echo "靜態檔案服務測試："
        docker-compose exec web python manage.py findstatic scripts/app.js --verbosity=2 2>/dev/null || echo "無法找到 app.js"
        ;;
    clean)
        echo "清理前端編譯檔案..."
        docker-compose exec web rm -rf /app/static/scripts /app/static/styles 2>/dev/null
        echo "清理完成"
        ;;
    rebuild)
        echo "完整重建前端資源..."
        docker-compose exec web sh -c "rm -rf /app/static/scripts /app/static/styles && npm run build"
        echo "重建完成"
        ;;
    *)
        echo "前端資源管理腳本"
        echo "用法: $0 {build|watch|check|clean|rebuild}"
        echo ""
        echo "命令說明:"
        echo "  build   - 建置前端資源"
        echo "  watch   - 啟動開發模式監控"
        echo "  check   - 檢查編譯後的檔案狀態"
        echo "  clean   - 清理編譯檔案"
        echo "  rebuild - 完整重建前端資源"
        echo ""
        echo "範例:"
        echo "  ./frontend-build.sh build"
        echo "  ./frontend-build.sh check"
        exit 1
        ;;
esac