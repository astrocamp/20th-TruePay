 嵌入商品系統實現完成！

  我已經成功實現了你要求的所有功能：

  ✅ 已完成的核心功能

  1. 公開商品展示
  - GET /embed/api/products/:id -
  取得商品資訊、價格、圖片、購買連結

  2. 登入狀態檢查
  - GET /embed/api/auth/session - 透過 Cookie
  判斷登入狀態和管理權限

  3. 管理 Token 驗證
  - POST /embed/api/auth/verify-token - 驗證 JWT 短效 Token    

  4. 商品更新
  - PATCH /embed/api/products/:id - 支援權限驗證的商品編輯     

  5. 管理連結生成
  - POST /embed/api/manage-token - 產生帶 JWT 的臨時管理       
  URL

  6. 嵌入方式
  - iframe 版本: <iframe src="https://yourdomain.com/embed/    
  embed/product/:id"></iframe>
  - script 版本: <div class="truepay-widget"
  data-id=":id"></div><script
  src="https://yourdomain.com/embed/embed.js"></script>        

  7. 編輯工具列
  - 當權限驗證通過時顯示編輯按鈕
  - 實時編輯商品資訊並更新 UI

  8. 文章轉商品
  - POST /embed/api/products/create-from-article -
  接收文章資料創建商品並回傳嵌入碼

  🏗️ 技術實現特點

  - 集中管理: JavaScript 和 CSS 使用專案的 static/
  目錄統一管理
  - 乾淨代碼: 模板不包含內聯樣式或腳本
  - 響應式設計: 使用 Tailwind CSS，支援各種設備
  - 安全權限: JWT Token 機制，30分鐘過期
  - 跨域支持: iframe 和 postMessage 通信
  - 實時編輯: Alpine.js 實現動態 UI 更新

  系統已通過 Django 檢查，可以開始使用了！