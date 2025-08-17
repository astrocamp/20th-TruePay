# TruePay 專案設置指南

## 系統需求

- macOS（推薦）或 Linux
- Python 3.8+
- PostgreSQL 15+

## 安裝步驟

### 1. 安裝 uv（Python 套件管理器）

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 Homebrew
brew install uv
```

### 2. 安裝 PostgreSQL

**macOS（推薦使用 Homebrew）：**
```bash
# 安裝 Homebrew（如果尚未安裝）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安裝 PostgreSQL 17
brew install postgresql@17

# 啟動 PostgreSQL 服務
brew services start postgresql@17
```

**Ubuntu/Debian：**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 3. 設置資料庫

```bash
# 創建專案資料庫
createdb truepay_db

# 如果遇到權限問題，可能需要先創建用戶（替換 your_username）
sudo -u postgres createuser --createdb your_username
createdb truepay_db
```

### 4. 複製專案並設置環境

```bash
# 複製專案
git clone <repository-url>
cd 20th-TruePay

# 複製環境變數範本
cp .env.example .env

# 編輯 .env 檔案設定你的資料庫資訊
nano .env
```

### 5. 環境變數設定

編輯 `.env` 檔案：

```bash
DB_NAME=truepay_db
DB_USER=your_username        # 替換為你的系統用戶名
DB_PASSWORD=                 # 如果有設密碼則填入
DB_HOST=localhost
DB_PORT=5432
```

### 6. 安裝 Python 依賴並執行遷移

```bash
# 安裝所有依賴
uv sync

# 執行資料庫遷移
uv run python manage.py migrate

# 創建超級用戶（可選）
uv run python manage.py createsuperuser
```

### 7. 啟動開發服務器

```bash
uv run python manage.py runserver
```

專案應該會在 `http://127.0.0.1:8000` 啟動。

## 常見問題解決

### PostgreSQL 連線問題

1. **確認 PostgreSQL 正在運行：**
   ```bash
   # macOS
   brew services list | grep postgresql
   
   # Linux
   sudo systemctl status postgresql
   ```

2. **檢查端口是否可用：**
   ```bash
   lsof -i :5432
   ```

3. **測試資料庫連線：**
   ```bash
   psql -h localhost -U your_username -d truepay_db
   ```

### 權限問題

如果遇到資料庫權限問題：

```bash
# macOS/Linux - 設定 PostgreSQL 用戶權限
sudo -u postgres psql
CREATE USER your_username WITH CREATEDB;
ALTER USER your_username CREATEDB;
```

### Python 依賴問題

如果 uv 無法使用，可以使用 pip：

```bash
# 創建虛擬環境
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# 或 .venv\Scripts\activate  # Windows

# 安裝依賴
pip install -r requirements.txt  # 如果有 requirements.txt
```

## 開發工具

### 執行測試
```bash
uv run python manage.py test
```

### 代碼檢查
```bash
uv run python manage.py check
```

### 收集靜態檔案（生產環境）
```bash
uv run python manage.py collectstatic
```

## 生產部署注意事項

1. 設定 `DEBUG=False`
2. 配置適當的 `ALLOWED_HOSTS`
3. 使用環境變數管理敏感資訊
4. 設定適當的資料庫連線池
5. 配置靜態檔案服務

## 支援

如有問題，請檢查：
1. Python 版本是否符合需求
2. PostgreSQL 是否正確安裝並運行
3. 環境變數是否正確設定
4. 資料庫權限是否充足

---

**注意：** 請勿將 `.env` 檔案提交到版本控制系統中，這個檔案包含敏感資訊。