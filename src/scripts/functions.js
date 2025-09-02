// Alpine.js 圖片預覽組件
function createImagePreview() {
  return {
    previewSrc: null,
    previewText: '圖片預覽：',
    imageClasses: 'w-32 h-32 object-cover rounded-lg border',
    
    init() {
      // 根據頁面類型調整預覽文字
      const isEditPage = window.location.pathname.includes('/edit/') || 
                        (document.querySelector('form[method="post"]') && 
                         document.querySelector('form[method="post"]').action.includes('edit'));
      
      if (isEditPage) {
        this.previewText = '新圖片預覽：';
      }
    },
    
    handleFileChange(event) {
      const file = event.target.files[0];
      
      if (!file) {
        this.previewSrc = null;
        return;
      }
      
      if (!this.isValidImageFile(file)) {
        this.previewSrc = null;
        event.target.value = '';
        return;
      }
      
      const reader = new FileReader();
      reader.onload = (e) => {
        this.previewSrc = e.target.result;
      };
      
      reader.onerror = () => {
        console.error('ImagePreview: 讀取檔案時發生錯誤');
        alert('讀取圖片時發生錯誤，請重新選擇');
        this.previewSrc = null;
      };
      
      reader.readAsDataURL(file);
    },
    
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
  };
}

// 將函數掛載到全域供 Alpine.js 使用
window.createImagePreview = createImagePreview;




// 付款倒數計時功能
// Alpine.js 付款倒數計時組件
function createPaymentTimer(config = {}) {
  return {
    countdown: config.duration || 5,
    formId: config.formId || 'newebpay-form',
    timer: null,
    isRunning: false,
    
    init() {
      // 自動開始計時
      this.startTimer();
    },
    
    startTimer() {
      if (this.isRunning) return;
      
      this.isRunning = true;
      this.timer = setInterval(() => {
        this.countdown--;
        
        if (this.countdown <= 0) {
          this.completeTimer();
        }
      }, 1000);
    },
    
    pauseTimer() {
      if (this.timer) {
        clearInterval(this.timer);
        this.timer = null;
        this.isRunning = false;
      }
    },
    
    resumeTimer() {
      if (!this.isRunning && this.countdown > 0) {
        this.startTimer();
      }
    },
    
    resetTimer() {
      this.pauseTimer();
      this.countdown = config.duration || 5;
    },
    
    completeTimer() {
      this.pauseTimer();
      
      // 提交表單
      const form = document.getElementById(this.formId);
      if (form) {
        form.submit();
      } else {
        console.error(`PaymentTimer: 無法提交表單，找不到 ID 為 ${this.formId} 的表單`);
      }
    },
    
    destroy() {
      this.pauseTimer();
    }
  };
}

// 將函數掛載到全域供 Alpine.js 使用
window.createPaymentTimer = createPaymentTimer;

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

// Alpine.js 選單管理組件
function createMobileMenu() {
  return {
    isOpen: false,
    
    init() {
      // 視窗大小變化時自動關閉選單
      this.$nextTick(() => {
        window.addEventListener('resize', () => {
          if (window.innerWidth >= 768) { // md breakpoint
            this.isOpen = false;
          }
        });
      });
    },
    
    toggle() {
      this.isOpen = !this.isOpen;
    },
    
    close() {
      this.isOpen = false;
    },
    
    // 當點擊選單內連結時自動關閉
    handleLinkClick(event) {
      const link = event.target.closest('a');
      if (link) {
        this.close();
      }
    }
  };
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

// 將選單組件掛載到全域供 Alpine.js 使用
window.createMobileMenu = createMobileMenu;



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

// Alpine.js 數量管理組件
function createQuantityManager(config = {}) {
  return {
    quantity: 1,
    unitPrice: 0,
    maxStock: 0,
    
    init() {
      // 從頁面中提取價格和庫存資訊
      this.extractPriceAndStock();
      
      // 設置初始數量
      const quantityInput = this.$refs.quantityInput;
      if (quantityInput && quantityInput.value) {
        this.quantity = parseInt(quantityInput.value) || 1;
      }
      
      // 驗證並更新初始狀態
      this.validateQuantity();
    },
    
    extractPriceAndStock() {
      // 從頁面中提取單價
      const priceElement = document.querySelector('[data-unit-price]');
      if (priceElement) {
        this.unitPrice = parseInt(priceElement.dataset.unitPrice) || 0;
      }
      
      // 從頁面中提取最大庫存
      const stockElement = document.querySelector('[data-max-stock]');
      if (stockElement) {
        this.maxStock = parseInt(stockElement.dataset.maxStock) || 0;
      }
      
      // 如果沒有 data 屬性，嘗試從輸入框的 max 屬性獲取
      if (this.maxStock === 0) {
        const quantityInput = this.$refs.quantityInput;
        if (quantityInput) {
          this.maxStock = parseInt(quantityInput.getAttribute('max')) || 0;
        }
      }
    },
    
    decrease() {
      if (this.quantity > 1) {
        this.quantity--;
        this.validateQuantity();
      }
    },
    
    increase() {
      if (this.quantity < this.maxStock) {
        this.quantity++;
        this.validateQuantity();
      }
    },
    
    validateQuantity() {
      // 確保數量在有效範圍內
      if (this.quantity < 1) this.quantity = 1;
      if (this.quantity > this.maxStock) this.quantity = this.maxStock;
    },
    
    // 計算總價
    get totalPrice() {
      return this.unitPrice * this.quantity;
    },
    
    // 格式化價格顯示
    get formattedTotalPrice() {
      return `NT$ ${this.totalPrice.toLocaleString()}`;
    },
    
    // 按鈕狀態
    get canDecrease() {
      return this.quantity > 1;
    },
    
    get canIncrease() {
      return this.quantity < this.maxStock;
    },
    
    // 公開方法：設置單價
    setUnitPrice(price) {
      this.unitPrice = price;
    },
    
    // 公開方法：設置最大庫存
    setMaxStock(stock) {
      this.maxStock = stock;
      this.validateQuantity();
    }
  };
}

// 將函數掛載到全域供 Alpine.js 使用
window.createQuantityManager = createQuantityManager;

// 導出 Alpine.js 組件創建函數和 NavigationManager
export { 
  createImagePreview,
  createPaymentTimer, 
  createMobileMenu,
  createQuantityManager,
  NavigationManager
};