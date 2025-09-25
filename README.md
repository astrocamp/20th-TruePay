# TruePay

<div align="center">
    <img src="https://test-django-images-marchung.s3.ap-northeast-1.amazonaws.com/TP/logo.png" alt="TruePay Logo">
</div>

[![Django](https://img.shields.io/badge/Django-5.2-green.svg)](https://djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://postgresql.org/)
[![Alpine.js](https://img.shields.io/badge/Alpine.js-3.14-8BC0D0.svg)](https://alpinejs.dev/)
[![Chart.js](https://img.shields.io/badge/Chart.js-4.5-FF6384.svg)](https://www.chartjs.org/)
[![TailwindCSS](https://img.shields.io/badge/Tailwind-4.1-06B6D4.svg)](https://tailwindcss.com/)
[![Celery](https://img.shields.io/badge/Celery-5.3-green.svg)](https://celeryproject.org/)
[![RabbitMQ](https://img.shields.io/badge/RabbitMQ-3.12-orange.svg)](https://www.rabbitmq.com/)
[![DaisyUI](https://img.shields.io/badge/DaisyUI-5.0-5A0EF8.svg)](https://daisyui.com/)
[![HTMX](https://img.shields.io/badge/HTMX-2.0-3366CC.svg)](https://htmx.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docker.com/)

## 簡介

**厭倦了繁瑣的開店流程與不安全的交易？**

**[TruePay](https://truepay.tw/) 整合了商店建立、票券販售與信任支付，為你的事業開啟無限可能。無論是課程、活動、或入場券，都能在這裡找到最完美的銷售方式。**

• **你的品牌，你作主**：支援子網域，打造獨一無二的品牌形象。
• **從銷售到驗證**：完整電子票券生命週期管理，提升營運效率。
• **交易最安心**：多平台安全支付整合，保障買賣雙方的每一筆交易。
• **絕佳顧客體驗**：方便的數位票券錢包，讓顧客輕鬆管理每一次購買。

**收款用 TruePay，筆筆都 PayTrue。**

<div align="center">
    <img src="https://test-django-images-marchung.s3.ap-northeast-1.amazonaws.com/TP/home.png" alt="TruePay Banner">
</div>

## 技術架構

### 前端技術

- **JavaScript**: Alpine.js, Chart.js, HTMX
- **CSS Framework**: TailwindCSS

### 後端技術

- **LANGUAGE**: Python
- **Framework**: Django 5.2.5
- **Database**: PostgreSQL
- **Task Queue**: Celery, RabbitMQ
- **Storage**: AWS S3


### 部署與基礎設施

- **Containerization**: Docker
- **雲端服務**: AWS EC2
- **Email**: Resend

## 功能簡介

(這裡放功能流程)

## 安裝設定

1. **安裝依賴套件**

   ```bash
   # 使用 pip
   pip install -r requirements.txt
   # 或使用 uv
   uv pip install -r requirements.txt
   ```

2. **設定環境變數**

   ```bash
   cp .env.example .env
   # 編輯 .env 檔案，填入必要的設定
   ```

3. **資料庫遷移**

   ```bash
   make migrate
   # 或
   uv run python manage.py migrate
   ```

4. **運行開發伺服器**
   ```bash
   make runserver
   # 或
   uv run python manage.py runserver
   ```

## 團隊成員

| 成員名稱 | GitHub | 負責內容 |
|----------|--------|----------|
| 張文琳 | [WenLin](https://github.com/WENLIN-CHANG/) | 藍新金流串接、第三方登入功能、消費者會員系統、商家報表分析功能 |
| 魏綸廷 | [LunTing](https://github.com/LunTing-Wei/) | 商家子網域功能、AWS EC2部署、資料庫欄位設計、網站視覺/商家模板設計 |
| 洪政佑 | [Mark](https://github.com/marcpikachu/) | 圖片上傳功能、商家建立商品CRUD、票券QR code生成/核銷、二階段驗證功能 |
| 曾俊琳 | [ett-et](https://github.com/ett-et/) | Line pay金流串接、自動排程寄信功能、票券生成功能、一鍵嵌入功能 |