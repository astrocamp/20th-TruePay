class ImagePreview {
  constructor(config) {
    this.inputId = config.inputId;
    this.previewId = config.previewId;
    this.previewText = config.previewText || '圖片預覽：';
    this.altText = config.altText || '圖片預覽';
    this.imageClasses = config.imageClasses || 'w-32 h-32 object-cover rounded-lg border';
    this.containerClasses = config.containerClasses || 'mt-2';
    
    this.init();
  }

  init() {
    const inputElement = document.getElementById(this.inputId);
    if (!inputElement) {
      console.warn(`ImagePreview: 找不到 ID 為 ${this.inputId} 的輸入欄位`);
      return;
    }

    inputElement.addEventListener('change', (event) => {
      this.handleFileChange(event);
    });
  }

  handleFileChange(event) {
    const file = event.target.files[0];
    const existingPreview = document.getElementById(this.previewId);
    
    if (file && this.isValidImageFile(file)) {
      this.createOrUpdatePreview(file, existingPreview);
    } else if (existingPreview) {
      this.removePreview(existingPreview);
    }
  }

  isValidImageFile(file) {
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      alert('請選擇有效的圖片檔案 (JPG, PNG, GIF, WebP)');
      return false;
    }
    
    const maxSize = 5 * 1024 * 1024; // 5MB
    if (file.size > maxSize) {
      alert('圖片檔案大小不能超過 5MB');
      return false;
    }
    
    return true;
  }

  createOrUpdatePreview(file, existingPreview) {
    const reader = new FileReader();
    
    reader.onload = (e) => {
      if (existingPreview) {
        const img = existingPreview.querySelector('img');
        if (img) {
          img.src = e.target.result;
          return;
        }
      }
      
      this.createPreviewElement(e.target.result);
    };

    reader.onerror = () => {
      console.error('ImagePreview: 讀取檔案時發生錯誤');
      alert('讀取圖片時發生錯誤，請重新選擇');
    };

    reader.readAsDataURL(file);
  }

  createPreviewElement(imageSrc) {
    const inputElement = document.getElementById(this.inputId);
    const previewDiv = document.createElement('div');
    
    previewDiv.id = this.previewId;
    previewDiv.className = this.containerClasses;
    previewDiv.innerHTML = `
      <p class="text-sm text-gray-600 mb-2">${this.previewText}</p>
      <img class="${this.imageClasses}" src="${imageSrc}" alt="${this.altText}">
    `;
    
    inputElement.parentNode.appendChild(previewDiv);
  }

  removePreview(previewElement) {
    if (previewElement && previewElement.parentNode) {
      previewElement.parentNode.removeChild(previewElement);
    }
  }

  destroy() {
    const inputElement = document.getElementById(this.inputId);
    const previewElement = document.getElementById(this.previewId);
    
    if (inputElement) {
      inputElement.removeEventListener('change', this.handleFileChange);
    }
    
    if (previewElement) {
      this.removePreview(previewElement);
    }
  }
}

// 自動初始化圖片預覽功能
function initImagePreview() {
  document.addEventListener('DOMContentLoaded', function() {
    const imageInput = document.getElementById('image');
    if (!imageInput) return;

    // 檢查是否為編輯頁面（通過URL或表單action判斷）
    const isEditPage = window.location.pathname.includes('/edit/') || 
                      (document.querySelector('form[method="post"]') && 
                       document.querySelector('form[method="post"]').action.includes('edit'));

    if (isEditPage) {
      // 編輯頁面的圖片預覽
      new ImagePreview({
        inputId: 'image',
        previewId: 'new_image_preview',
        previewText: '新圖片預覽：',
        altText: '新圖片預覽'
      });
    } else {
      // 新增頁面的圖片預覽
      new ImagePreview({
        inputId: 'image',
        previewId: 'image_preview',
        previewText: '圖片預覽：',
        altText: '圖片預覽'
      });
    }
  });
}

// 自動執行初始化
initImagePreview();




// 付款倒數計時功能
class PaymentTimer {
  constructor(config) {
    this.duration = config.duration || 5;
    this.countdownElementId = config.countdownElementId || 'countdown';
    this.formId = config.formId || 'newebpay-form';
    this.onComplete = config.onComplete || this.defaultOnComplete.bind(this);
    this.onTick = config.onTick || this.defaultOnTick.bind(this);
    
    this.currentTime = this.duration;
    this.timer = null;
    this.isRunning = false;
    
    this.init();
  }

  init() {
    const countdownElement = document.getElementById(this.countdownElementId);
    if (!countdownElement) {
      console.warn(`PaymentTimer: 找不到 ID 為 ${this.countdownElementId} 的倒數顯示元素`);
      return;
    }

    const form = document.getElementById(this.formId);
    if (!form) {
      console.warn(`PaymentTimer: 找不到 ID 為 ${this.formId} 的表單`);
      return;
    }

    this.start();
  }

  start() {
    if (this.isRunning) return;
    
    this.isRunning = true;
    this.updateDisplay();
    
    this.timer = setInterval(() => {
      this.currentTime--;
      this.updateDisplay();
      this.onTick(this.currentTime);
      
      if (this.currentTime <= 0) {
        this.complete();
      }
    }, 1000);
  }

  pause() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
      this.isRunning = false;
    }
  }

  resume() {
    if (!this.isRunning && this.currentTime > 0) {
      this.start();
    }
  }

  reset() {
    this.pause();
    this.currentTime = this.duration;
    this.updateDisplay();
  }

  complete() {
    this.pause();
    this.onComplete();
  }

  updateDisplay() {
    const countdownElement = document.getElementById(this.countdownElementId);
    if (countdownElement) {
      countdownElement.textContent = this.currentTime;
    }
  }

  defaultOnTick(remainingTime) {
    // 可以在這裡加入每秒的額外處理邏輯
  }

  defaultOnComplete() {
    const form = document.getElementById(this.formId);
    if (form) {
      form.submit();
    } else {
      console.error(`PaymentTimer: 無法提交表單，找不到 ID 為 ${this.formId} 的表單`);
    }
  }

  destroy() {
    this.pause();
  }
}

// 自動初始化付款倒數計時功能
function initPaymentTimer() {
  document.addEventListener('DOMContentLoaded', function() {
    // 檢查是否有倒數顯示元素和表單
    if (document.getElementById('countdown') && document.getElementById('newebpay-form')) {
      new PaymentTimer({
        duration: 5,
        countdownElementId: 'countdown',
        formId: 'newebpay-form'
      });
    }
  });
}

// 自動執行初始化
initPaymentTimer();

// 統一的事件處理器
function handleConfirmDelete(element) {
  const formId = element.dataset.formId || 'deleteForm';
  const message = element.dataset.message || '確定要刪除這個商品嗎？此操作無法復原。';
  
  if (confirm(message)) {
    const form = document.getElementById(formId);
    if (form) {
      form.submit();
    } else {
      console.error(`找不到 ID 為 ${formId} 的表單`);
    }
  }
}

function handleUseMerchantPhone(element) {
  const targetId = element.dataset.target || 'phone_number';
  const merchantPhone = element.dataset.phone;
  
  if (merchantPhone) {
    const phoneInput = document.getElementById(targetId);
    if (phoneInput) {
      phoneInput.value = merchantPhone;
    } else {
      console.error(`找不到 ID 為 ${targetId} 的輸入欄位`);
    }
  } else {
    console.warn('未提供商家電話資料');
  }
}

function handlePaymentTimer(element) {
  const duration = parseInt(element.dataset.duration) || 5;
  const countdownElementId = element.dataset.countdownElement || 'countdown';
  const formId = element.dataset.formId || 'newebpay-form';
  
  new PaymentTimer({
    duration: duration,
    countdownElementId: countdownElementId,
    formId: formId
  });
}

function handleToggleMenu(element) {
  const menuId = element.dataset.menuId || 'mobile-menu';
  const brandId = element.dataset.brandId || 'nav-brand';
  
  const menu = document.getElementById(menuId);
  const brand = document.getElementById(brandId);
  
  if (menu && brand) {
    const isHidden = menu.classList.toggle('hidden');
    brand.classList.toggle('hidden', !isHidden);
    element.setAttribute('aria-expanded', String(!isHidden));
  }
}

// 自動關閉選單的輔助函數
function closeMenu(menuId = 'mobile-menu', brandId = 'nav-brand', toggleBtnId = 'menu-toggle') {
  const menu = document.getElementById(menuId);
  const brand = document.getElementById(brandId);
  const toggleBtn = document.getElementById(toggleBtnId);
  
  if (menu && brand && toggleBtn && !menu.classList.contains('hidden')) {
    menu.classList.add('hidden');
    brand.classList.remove('hidden');
    toggleBtn.setAttribute('aria-expanded', 'false');
  }
}

// 統一的事件委託系統
function initEventDelegation() {
  document.addEventListener('click', function(event) {
    const element = event.target;
    const action = element.dataset.action;
    
    if (!action) return;
    
    switch (action) {
      case 'confirm-delete':
        event.preventDefault();
        handleConfirmDelete(element);
        break;
        
      case 'use-merchant-phone':
        event.preventDefault();
        handleUseMerchantPhone(element);
        break;
        
      case 'start-payment-timer':
        event.preventDefault();
        handlePaymentTimer(element);
        break;
        
      case 'toggle-menu':
        event.preventDefault();
        handleToggleMenu(element);
        break;
        
      default:
        // 未知的 action，不處理
        break;
    }
  });
}

// 初始化事件委託系統
document.addEventListener('DOMContentLoaded', function() {
  initEventDelegation();
  
  // 設置額外的選單相關事件監聽器
  setupMenuEventListeners();
});

// 設置選單相關的事件監聽器
function setupMenuEventListeners() {
  // 視窗大小變化時自動關閉手機選單
  window.addEventListener('resize', function() {
    if (window.innerWidth >= 768) { // md breakpoint
      closeMenu();
    }
  });
  
  // 手機選單內連結點擊時自動關閉選單
  const mobileMenu = document.getElementById('mobile-menu');
  if (mobileMenu) {
    mobileMenu.addEventListener('click', function(event) {
      const link = event.target.closest('a');
      if (link) {
        closeMenu();
      }
    });
  }
}



// 導航管理器 - 統一處理導航連結的樣式和無障礙性
class NavigationManager {
  constructor() {
    this.currentPath = window.location.pathname;
    this.baseClasses = 'flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-[#F5F5F7]';
    this.activeClasses = 'text-[#0056B3] font-medium bg-blue-50';
    this.inactiveClasses = 'text-gray-700';
    this.logoutClasses = 'flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-[#F5F5F7] text-red-600';
  }

  isActive(element) {
    if (!element || !element.getAttribute) return false;
    const href = element.getAttribute('href');
    if (!href) return false;
    return this.currentPath === href.replace(/\?.*$/, '');
  }

  navLinkBinding(element) {
    const isActiveState = this.isActive(element);
    const finalClasses = `${this.baseClasses} ${isActiveState ? this.activeClasses : this.inactiveClasses}`;
    
    return {
      class: finalClasses,
      'aria-current': isActiveState ? 'page' : null
    };
  }

  navLinkBindingWithOpacity(element) {
    const binding = this.navLinkBinding(element);
    return {
      ...binding,
      class: binding.class + ' opacity-50'
    };
  }

  logoutLinkBinding() {
    return {
      class: this.logoutClasses
    };
  }

  // 為 Alpine.js 提供全域可用的函數
  static createAlpineData() {
    const manager = new NavigationManager();
    
    return {
      currentPath: manager.currentPath,
      isActive: (element) => manager.isActive(element),
      navLinkBinding: (element) => manager.navLinkBinding(element),
      navLinkBindingWithOpacity: (element) => manager.navLinkBindingWithOpacity(element),
      logoutLinkBinding: () => manager.logoutLinkBinding()
    };
  }
}

// 將 NavigationManager 掛載到全域，供 Alpine.js 使用
window.NavigationManager = NavigationManager;

// 金流設定表單驗證
class PaymentSettingsValidator {
  constructor() {
    this.init();
  }

  init() {
    // 在 DOM 載入後初始化
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.attachFormHandler());
    } else {
      this.attachFormHandler();
    }
  }

  attachFormHandler() {
    const form = document.querySelector('form[data-form="payment-settings"]');
    if (form) {
      form.addEventListener('submit', (e) => this.validateForm(e));
    }
  }

  validateForm(event) {
    const merchantId = document.getElementById('newebpay_merchant_id')?.value.trim() || '';
    const hashKey = document.getElementById('newebpay_hash_key')?.value.trim() || '';
    const hashIv = document.getElementById('newebpay_hash_iv')?.value.trim() || '';
    
    const channelId = document.getElementById('linepay_channel_id')?.value.trim() || '';
    const channelSecret = document.getElementById('linepay_channel_secret')?.value.trim() || '';
    
    // 檢查是否至少完成一組設定
    const hasNewebpay = merchantId && hashKey && hashIv;
    const hasLinepay = channelId && channelSecret;
    
    if (!hasNewebpay && !hasLinepay) {
      event.preventDefault();
      this.showAlert('請至少完成一組金流設定（藍新金流或 LINE Pay）');
      return false;
    }
    
    // 如果部分填寫藍新金流，要求完整填寫
    if ((merchantId || hashKey || hashIv) && !hasNewebpay) {
      event.preventDefault();
      this.showAlert('請完整填寫藍新金流的所有欄位，或清空所有欄位');
      return false;
    }
    
    // 如果部分填寫 LINE Pay，要求完整填寫
    if ((channelId || channelSecret) && !hasLinepay) {
      event.preventDefault();
      this.showAlert('請完整填寫 LINE Pay 的所有欄位，或清空所有欄位');
      return false;
    }

    return true;
  }

  showAlert(message) {
    // 可以替換為更好看的通知系統
    alert(message);
  }
}

// 自動初始化金流設定驗證器
new PaymentSettingsValidator();

// 購買數量管理器
class PurchaseQuantityManager {
  constructor() {
    this.quantityInput = null;
    this.decreaseBtn = null;
    this.increaseBtn = null;
    this.totalPriceElement = null;
    this.paymentButtons = {};
    this.unitPrice = 0;
    this.maxStock = 0;
    
    this.init();
  }

  init() {
    // 在 DOM 載入後初始化
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.setupElements());
    } else {
      this.setupElements();
    }
  }

  setupElements() {
    // 獲取 DOM 元素
    this.quantityInput = document.getElementById('quantity');
    this.decreaseBtn = document.getElementById('decrease-quantity');
    this.increaseBtn = document.getElementById('increase-quantity');
    this.totalPriceElement = document.getElementById('total-price');
    
    // 檢查是否在付款頁面
    if (!this.quantityInput) {
      return; // 不在付款頁面，不需要初始化
    }
    
    // 獲取價格和庫存資訊
    this.extractPriceAndStock();
    
    // 設置付款按鈕相關元素
    this.setupPaymentElements();
    
    // 綁定事件監聽器
    this.attachEventListeners();
    
    // 初始化驗證
    this.validateQuantity();
  }

  extractPriceAndStock() {
    // 從頁面中提取單價和最大庫存
    const priceElement = document.querySelector('[data-unit-price]');
    const stockElement = document.querySelector('[data-max-stock]');
    
    if (priceElement) {
      this.unitPrice = parseInt(priceElement.dataset.unitPrice) || 0;
    }
    
    if (stockElement) {
      this.maxStock = parseInt(stockElement.dataset.maxStock) || 0;
    }
    
    // 如果沒有 data 屬性，嘗試從輸入框的 max 屬性獲取
    if (this.maxStock === 0 && this.quantityInput) {
      this.maxStock = parseInt(this.quantityInput.getAttribute('max')) || 0;
    }
  }

  setupPaymentElements() {
    // 藍新金流相關元素
    this.paymentButtons.newebpay = {
      amt: document.getElementById('newebpay-amt'),
      quantity: document.getElementById('newebpay-quantity'),
      price: document.getElementById('newebpay-price')
    };
    
    // LINE Pay 相關元素
    this.paymentButtons.linepay = {
      quantity: document.getElementById('linepay-quantity'),
      price: document.getElementById('linepay-price')
    };
  }

  attachEventListeners() {
    // 數量輸入框事件
    if (this.quantityInput) {
      this.quantityInput.addEventListener('input', () => this.validateQuantity());
      this.quantityInput.addEventListener('change', () => this.validateQuantity());
    }
    
    // 減少按鈕
    if (this.decreaseBtn) {
      this.decreaseBtn.addEventListener('click', () => this.decreaseQuantity());
    }
    
    // 增加按鈕
    if (this.increaseBtn) {
      this.increaseBtn.addEventListener('click', () => this.increaseQuantity());
    }
  }

  decreaseQuantity() {
    const currentQuantity = parseInt(this.quantityInput.value) || 1;
    if (currentQuantity > 1) {
      this.quantityInput.value = currentQuantity - 1;
      this.validateQuantity();
    }
  }

  increaseQuantity() {
    const currentQuantity = parseInt(this.quantityInput.value) || 1;
    if (currentQuantity < this.maxStock) {
      this.quantityInput.value = currentQuantity + 1;
      this.validateQuantity();
    }
  }

  validateQuantity() {
    let quantity = parseInt(this.quantityInput.value) || 1;
    
    // 確保數量在有效範圍內
    if (quantity < 1) quantity = 1;
    if (quantity > this.maxStock) quantity = this.maxStock;
    
    // 更新輸入框值
    this.quantityInput.value = quantity;
    
    // 更新價格顯示
    this.updatePrice(quantity);
    
    // 更新按鈕狀態
    this.updateButtonStates(quantity);
    
    // 更新付款表單
    this.updatePaymentForms(quantity);
  }

  updatePrice(quantity) {
    const totalPrice = this.unitPrice * quantity;
    
    if (this.totalPriceElement) {
      this.totalPriceElement.textContent = `NT$ ${totalPrice.toLocaleString()}`;
    }
  }

  updateButtonStates(quantity) {
    // 更新減少按鈕狀態
    if (this.decreaseBtn) {
      this.decreaseBtn.disabled = quantity <= 1;
      this.decreaseBtn.classList.toggle('opacity-50', quantity <= 1);
      this.decreaseBtn.classList.toggle('cursor-not-allowed', quantity <= 1);
    }
    
    // 更新增加按鈕狀態
    if (this.increaseBtn) {
      this.increaseBtn.disabled = quantity >= this.maxStock;
      this.increaseBtn.classList.toggle('opacity-50', quantity >= this.maxStock);
      this.increaseBtn.classList.toggle('cursor-not-allowed', quantity >= this.maxStock);
    }
  }

  updatePaymentForms(quantity) {
    const totalPrice = this.unitPrice * quantity;
    
    // 更新藍新金流表單
    const newebpay = this.paymentButtons.newebpay;
    if (newebpay.amt) newebpay.amt.value = totalPrice;
    if (newebpay.quantity) newebpay.quantity.value = quantity;
    if (newebpay.price) newebpay.price.textContent = `NT$ ${totalPrice.toLocaleString()}`;
    
    // 更新 LINE Pay 表單
    const linepay = this.paymentButtons.linepay;
    if (linepay.quantity) linepay.quantity.value = quantity;
    if (linepay.price) linepay.price.textContent = `NT$ ${totalPrice.toLocaleString()}`;
  }

  // 公開方法：設置單價（用於動態設置）
  setUnitPrice(price) {
    this.unitPrice = price;
    this.validateQuantity();
  }

  // 公開方法：設置最大庫存（用於動態設置）
  setMaxStock(stock) {
    this.maxStock = stock;
    if (this.quantityInput) {
      this.quantityInput.setAttribute('max', stock);
    }
    this.validateQuantity();
  }

  // 公開方法：獲取當前數量
  getCurrentQuantity() {
    return parseInt(this.quantityInput?.value) || 1;
  }

  // 公開方法：獲取總價
  getTotalPrice() {
    return this.unitPrice * this.getCurrentQuantity();
  }
}

// 自動初始化購買數量管理器
const purchaseQuantityManager = new PurchaseQuantityManager();

// 將管理器掛載到全域，供其他腳本使用
window.PurchaseQuantityManager = purchaseQuantityManager;

export { ImagePreview, PaymentTimer, NavigationManager, PaymentSettingsValidator, PurchaseQuantityManager };