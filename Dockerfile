# 使用 Python 3.13 官方映像
FROM python:3.13-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 升級 pip
RUN pip install --upgrade pip

# 複製 requirements.txt
COPY requirements.txt ./

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY . .

# 建立日誌目錄
RUN mkdir -p /app/logs

# 設定環境變數
ENV PYTHONPATH=/app
ENV DJANGO_SETTINGS_MODULE=truepay.settings
ENV PYTHONUNBUFFERED=1

# 開放 8000 port
EXPOSE 8000

# 健康檢查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python manage.py check --deploy || exit 1

# 預設命令（可被 docker-compose 覆蓋）
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]