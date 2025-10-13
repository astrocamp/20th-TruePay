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

- **你的品牌，你作主**：支援子網域，打造獨一無二的品牌形象。
- **從銷售到驗證**：完整電子票券生命週期管理，提升營運效率。
- **交易最安心**：多平台安全支付整合，保障買賣雙方的每一筆交易。
- **絕佳顧客體驗**：方便的數位票券錢包，讓顧客輕鬆管理每一次購買。

**收款用 TruePay，筆筆都 PayTrue。**

<div align="center">
    <img src="https://test-django-images-marchung.s3.ap-northeast-1.amazonaws.com/TP/home.png" alt="TruePay Banner">
</div>

## Demo Day 影片

[![TruePay Demo](https://img.youtube.com/vi/8kIEo-F54Wg/maxresdefault.jpg)](https://www.youtube.com/watch?v=8kIEo-F54Wg)

**[🎬 點擊觀看完整影片](https://www.youtube.com/watch?v=8kIEo-F54Wg)**

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

### 商家功能

#### 商店管理
- **子網域支援**：每個商家都可以擁有專屬的子網域 (如 `yourstore.truepay.tw`)
- **商店模板**：多種精美模板可選，打造獨特品牌形象
- **商品管理**：完整的商品 CRUD 功能，支援圖片上傳、價格設定、庫存管理

#### 票券系統
- **電子票券生成**：自動產生具有防偽功能的 QR Code 票券
- **票券類型多樣**：支援活動門票、課程券、餐飲券等多種類型
- **有效期管理**：靈活設定票券有效期和使用條件

#### 核銷與驗證
- **QR Code 掃描**：內建掃描器，快速驗證票券真偽
- **核銷記錄**：完整的核銷歷史記錄和統計
- **防重複核銷**：確保每張票券只能使用一次

#### 金流整合
- **多元支付**：整合藍新金流及 LINE Pay
- **安全交易**：所有交易都經過加密處理，確保資金安全

#### 數據分析
- **銷售報表**：詳細的銷售數據和趨勢分析
- **圖表視覺化**：使用 Chart.js 提供直觀的數據展示

### 消費者功能

#### 帳戶系統
- **多元登入**：支援 Email 註冊登入和 Google 第三方登入
- **個人資料管理**：完整的個人資訊修改功能
- **密碼安全**：支援密碼修改和忘記密碼重設
- **二階段驗證**：整合 Google Authenticator，提供 TOTP 雙因子認證

#### 購物體驗
- **商品瀏覽**：清晰的商品展示和分類瀏覽
- **多元結帳**：支援信用卡、LINE Pay 等多種付款方式
- **訂單追蹤**：完整的訂單狀態追蹤和歷史記錄

#### 數位錢包
- **票券管理**：統一管理所有購買的電子票券
- **QR Code 展示**：安全的票券 QR Code 顯示功能
- **狀態追蹤**：票券使用狀態 (未使用/已使用/已過期) 一目了然
- **篩選功能**：支援按商家、狀態、日期等條件篩選票券

#### 安全防護
- **核銷前驗證**：高價值票券需要二階段驗證才能展示 QR Code
- **備用恢復碼**：提供 TOTP 備用恢復機制

### 系統功能

#### 多語言支援
- **國際化 (i18n)**：支援繁體中文、英文、日文
- **動態切換**：即時語言切換，無需重新登入
- **本地化內容**：所有介面元素都支援多語言

#### 一鍵嵌入
- **Widget 生成**：商家可以生成嵌入式購買按鈕
- **跨網站整合**：輕鬆整合到任何網站或部落格


## 安裝設定

1. **安裝依賴套件**

   ```bash
   # 使用 uv
   uv sync
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
| 洪政佑 | [Marc](https://github.com/marcpikachu/) | AWS S3圖片上傳、商家商品CRUD、票券QR code生成/核銷、二階段驗證功能 |
| 曾俊琳 | [ett-et](https://github.com/ett-et/) | Line pay金流串接、自動排程寄信功能、票券生成功能、一鍵嵌入功能 |
