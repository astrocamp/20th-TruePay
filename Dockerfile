FROM python:3.13-slim

# 設定 UTF-8 環境變數
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONIOENCODING=utf-8

WORKDIR /app
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    locales \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && locale-gen zh_CN.UTF-8 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY package.json package-lock.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 8000
CMD ["uv", "run", "--", "python", "manage.py", "runserver", "0.0.0.0:8000"]
