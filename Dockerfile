FROM python:3.13-slim

# 設定 UTF-8 環境變數
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONIOENCODING=utf-8 \
    PYTHONPATH=/app \
    DJANGO_SETTINGS_MODULE=truepay.settings \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    postgresql-client \
    gcc \
    curl \
    locales \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && locale-gen zh_CN.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

# 安裝 uv
RUN pip install uv


# 複製 Python 依賴檔案
COPY pyproject.toml uv.lock ./

# 安裝 Python 依賴
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"

# 複製前端依賴檔案
COPY package.json package-lock.json ./

# 安裝前端依賴
RUN npm install

# 複製應用程式代碼
COPY . .

# 建立必要目錄
RUN mkdir -p /app/logs /app/static

# 建置前端資源
RUN npm run build

# 開放 8000 port
EXPOSE 8000

# 健康檢查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python manage.py check --deploy || exit 1

# 預設命令（可被 docker-compose 覆蓋）
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]