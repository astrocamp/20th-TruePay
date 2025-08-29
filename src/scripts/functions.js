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

// 刪除確認對話框功能
class ConfirmDialog {
  constructor(config) {
    this.buttonSelector = config.buttonSelector || '[onclick*="confirmDelete"]';
    this.formId = config.formId || 'deleteForm';
    this.message = config.message || '確定要刪除這個商品嗎？此操作無法復原。';
    this.customConfirmHandler = config.customConfirmHandler;
    
    this.init();
  }

  init() {
    // 移除所有按鈕的 onclick 屬性，改用事件監聽
    document.addEventListener('DOMContentLoaded', () => {
      this.setupDeleteButtons();
    });
  }

  setupDeleteButtons() {
    // 找到所有刪除按鈕
    const deleteButtons = document.querySelectorAll(this.buttonSelector);
    
    deleteButtons.forEach(button => {
      // 移除 onclick 屬性，避免衝突
      button.removeAttribute('onclick');
      
      // 新增事件監聽器
      button.addEventListener('click', (event) => {
        event.preventDefault();
        this.showConfirmDialog();
      });
    });
  }

  showConfirmDialog() {
    if (confirm(this.message)) {
      if (this.customConfirmHandler) {
        this.customConfirmHandler();
      } else {
        this.submitDeleteForm();
      }
    }
  }

  submitDeleteForm() {
    const form = document.getElementById(this.formId);
    if (form) {
      form.submit();
    } else {
      console.error(`ConfirmDialog: 找不到 ID 為 ${this.formId} 的表單`);
    }
  }

  destroy() {
    const deleteButtons = document.querySelectorAll(this.buttonSelector);
    deleteButtons.forEach(button => {
      button.removeEventListener('click', this.showConfirmDialog);
    });
  }
}

// 舊的 ConfirmDialog 初始化已移除，改用統一的事件委託系統


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
});

// 響應式選單功能
class ResponsiveMenu {
  constructor(config) {
    this.toggleBtnId = config.toggleBtnId || 'menu-toggle';
    this.mobileMenuId = config.mobileMenuId || 'mobile-menu';
    this.navBrandId = config.navBrandId || 'nav-brand';
    this.breakpoint = config.breakpoint || 768;
    
    this.toggleBtn = null;
    this.mobileMenu = null;
    this.navBrand = null;
    this.isInitialized = false;
    
    this.init();
  }

  init() {
    // 等待 DOM 載入完成
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.setup());
    } else {
      this.setup();
    }
  }

  setup() {
    // 取得 DOM 元素
    this.toggleBtn = document.getElementById(this.toggleBtnId);
    this.mobileMenu = document.getElementById(this.mobileMenuId);
    this.navBrand = document.getElementById(this.navBrandId);

    // 如果找不到必要元素，不初始化
    if (!this.toggleBtn || !this.mobileMenu || !this.navBrand) {
      return;
    }

    this.bindEvents();
    this.isInitialized = true;
  }

  bindEvents() {
    // 漢堡按鈕點擊事件
    this.toggleBtn.addEventListener('click', (e) => {
      e.preventDefault();
      this.toggleMenu();
    });

    // 選單內連結點擊自動關閉
    this.mobileMenu.addEventListener('click', (e) => {
      const link = e.target.closest('a');
      if (link) {
        this.closeMenu();
      }
    });

    // 視窗大小變化處理
    window.addEventListener('resize', () => {
      if (window.innerWidth >= this.breakpoint) {
        this.closeMenu();
      }
    });
  }

  toggleMenu() {
    const isHidden = this.mobileMenu.classList.toggle('hidden');
    this.navBrand.classList.toggle('hidden', !isHidden);
    this.toggleBtn.setAttribute('aria-expanded', String(!isHidden));
  }

  closeMenu() {
    if (!this.mobileMenu.classList.contains('hidden')) {
      this.mobileMenu.classList.add('hidden');
      this.navBrand.classList.remove('hidden');
      this.toggleBtn.setAttribute('aria-expanded', 'false');
    }
  }

  destroy() {
    if (!this.isInitialized) return;

    if (this.toggleBtn) {
      this.toggleBtn.removeEventListener('click', this.toggleMenu);
    }
    
    if (this.mobileMenu) {
      this.mobileMenu.removeEventListener('click', this.closeMenu);
    }
    
    window.removeEventListener('resize', this.closeMenu);
    this.isInitialized = false;
  }
}

// 自動初始化響應式選單功能
function initResponsiveMenu() {
  // 只在有相關元素的頁面初始化
  if (document.getElementById('menu-toggle') && 
      document.getElementById('mobile-menu') && 
      document.getElementById('nav-brand')) {
    new ResponsiveMenu({
      toggleBtnId: 'menu-toggle',
      mobileMenuId: 'mobile-menu',
      navBrandId: 'nav-brand',
      breakpoint: 768
    });
  }
}

// 自動執行初始化
initResponsiveMenu();

export { ImagePreview, ConfirmDialog, PaymentTimer, ResponsiveMenu };