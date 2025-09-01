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



// Alpine.js 組件註冊
document.addEventListener('alpine:init', () => {
  // 票券複製功能組件
  Alpine.data('ticketCopy', () => ({
    copyButtonText: '複製票券代碼',
    
    async copyTicketCode(ticketCode) {
      try {
        // 使用現代 Clipboard API
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(ticketCode);
          this.showCopySuccess();
        } else {
          // 降級到舊版方法
          this.fallbackCopyTextToClipboard(ticketCode);
        }
      } catch (error) {
        console.error('複製失敗:', error);
        this.fallbackCopyTextToClipboard(ticketCode);
      }
    },
    
    fallbackCopyTextToClipboard(text) {
      const textArea = document.createElement('textarea');
      textArea.value = text;
      
      // 避免捲動到底部
      textArea.style.top = '0';
      textArea.style.left = '0';
      textArea.style.position = 'fixed';
      textArea.style.opacity = '0';
      
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      
      try {
        const successful = document.execCommand('copy');
        if (successful) {
          this.showCopySuccess();
        } else {
          console.error('舊版複製方法失敗');
        }
      } catch (err) {
        console.error('複製失敗:', err);
      }
      
      document.body.removeChild(textArea);
    },
    
    showCopySuccess() {
      this.copyButtonText = '已複製！';
      setTimeout(() => {
        this.copyButtonText = '複製票券代碼';
      }, 2000);
    }
  }));
});

export { ImagePreview, PaymentTimer };