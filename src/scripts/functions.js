// 統一的全域錯誤處理函數
function showGlobalError(message) {
  console.error('Global:', message);
  alert(message);
}

function showGlobalInfo(message) {
  console.log('Global:', message);
}

// 獲取 CSRF Token 的通用函數
function getCsrfToken() {
  // 優先從 cookie 獲取
  const cookieValue = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];
  
  if (cookieValue) {
    return cookieValue;
  }
  
  // 備案：從 DOM 獲取
  const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
  return csrfInput ? csrfInput.value : '';
}

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
        this.showError('讀取圖片時發生錯誤，請重新選擇');
        this.previewSrc = null;
      };
      
      reader.readAsDataURL(file);
    },
    
    isValidImageFile(file) {
      const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
      if (!validTypes.includes(file.type)) {
        this.showError('請選擇有效的圖片檔案 (JPG, PNG, GIF, WebP)');
        return false;
      }
      
      const maxSize = 5 * 1024 * 1024; // 5MB
      if (file.size > maxSize) {
        this.showError('圖片檔案大小不能超過 5MB');
        return false;
      }
      
      return true;
    },
    
    showError(message) {
      console.error('ImagePreview:', message);
      alert(message);
    }
  };
}

// 將函數掛載到全域供 Alpine.js 使用
window.createImagePreview = createImagePreview;




// 付款倒數計時功能
// Alpine.js 付款倒數計時組件
function createPaymentTimer(config = {}) {
  const initialDuration = config.duration || 5;
  return {
    countdown: initialDuration,
    initialDuration: initialDuration,
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
      this.countdown = this.initialDuration;
    },
    
    completeTimer() {
      this.pauseTimer();
      
      // 提交表單
      const form = document.getElementById(this.formId);
      if (form) {
        form.submit();
      } else {
        this.showError(`無法提交表單，找不到 ID 為 ${this.formId} 的表單`);
      }
    },
    
    destroy() {
      this.pauseTimer();
    },
    
    showError(message) {
      console.error('PaymentTimer:', message);
      alert(message);
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
      showGlobalError(`找不到 ID 為 ${formId} 的表單`);
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
      showGlobalError(`找不到 ID 為 ${targetId} 的輸入欄位`);
    }
  } else {
    showGlobalInfo('未提供商家電話資料');
  }
}

// Alpine.js 選單管理組件
function createMobileMenu() {
  return {
    isOpen: false,
    
    init() {
       // 初始狀態：手機版關閉選單，桌面版不受影響
      this.isOpen = false;
      
      // 視窗大小變化時，如果切換到桌面版就關閉手機版選單狀態
      this.$nextTick(() => {
        window.addEventListener('resize', () => {
          if (window.innerWidth >= 768) { // md breakpoint
            this.isOpen = false; // 重置手機版選單狀態
          }
        }, { passive: true });
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
    this._currentPath = null; // 快取路徑
    this.baseClasses = 'flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-[#F5F5F7]';
    this.activeClasses = 'text-[#0056B3] font-medium bg-blue-50';
    this.inactiveClasses = 'text-gray-700';
    this.logoutClasses = 'flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-[#F5F5F7] text-red-600';
  }
  
  get currentPath() {
    if (!this._currentPath) {
      this._currentPath = window.location.pathname;
    }
    return this._currentPath;
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
    productId: null,
    
    // 即時庫存驗證相關變數
    stockCheckLoading: false,
    stockWarningMessage: '',
    lastStockCheck: 0,
    stockCheckInterval: null,
    
    // 驗證相關變數
    needsVerification: config.needsVerification || false,
    isVerified: config.isVerified || false,
    verificationData: config.verificationData || { terms: false },
    
    init() {
      // 從頁面中提取價格和庫存資訊
      this.extractPriceAndStock();
      this.extractProductId();
      
      // 設置初始數量
      const quantityInput = this.$refs.quantityInput;
      if (quantityInput && quantityInput.value) {
        this.quantity = parseInt(quantityInput.value) || 1;
      }
      
      // 驗證並更新初始狀態
      this.validateQuantity();
      
      // 啟動定期庫存檢查（每30秒檢查一次）
      this.startPeriodicStockCheck();
    },
    
    destroy() {
      // 清理定時器
      if (this.stockCheckInterval) {
        clearInterval(this.stockCheckInterval);
      }
    },
    
    extractPriceAndStock() {
      this.extractPrice();
      this.extractStock();
    },
    
    extractPrice() {
      const priceElement = document.querySelector('[data-unit-price]');
      if (priceElement) {
        this.unitPrice = parseInt(priceElement.dataset.unitPrice) || 0;
      }
    },
    
    extractStock() {
      const stockElement = document.querySelector('[data-max-stock]');
      if (stockElement) {
        this.maxStock = parseInt(stockElement.dataset.maxStock) || 0;
        return;
      }
    },
    
    extractProductId() {
      const productElement = document.querySelector('[data-product-id]');
      if (productElement) {
        this.productId = productElement.dataset.productId;
      }
      
      // 如果找不到 data-product-id，嘗試從表單中提取
      const productInput = document.querySelector('input[name="product_id"]');
      if (productInput && productInput.value) {
        this.productId = productInput.value;
      }
    },
    
    // 啟動定期庫存檢查
    startPeriodicStockCheck() {
      if (!this.productId) return;
      
      // 立即執行一次檢查
      this.checkStockStatus();
      
      // 每30秒檢查一次
      this.stockCheckInterval = setInterval(() => {
        this.checkStockStatus();
      }, 30000);
    },
    
    // 檢查庫存狀態
    async checkStockStatus() {
      if (!this.productId || this.stockCheckLoading) return;
      
      // 避免過於頻繁的請求（至少間隔5秒）
      const now = Date.now();
      if (now - this.lastStockCheck < 5000) return;
      
      this.stockCheckLoading = true;
      this.lastStockCheck = now;
      
      try {
        const formData = new FormData();
        formData.append('product_id', this.productId);
        formData.append('quantity', this.quantity.toString());
        
        // 添加 CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfToken) {
          formData.append('csrfmiddlewaretoken', csrfToken.value);
        }
        
        const response = await fetch('/payments/api/check-stock/', {
          method: 'POST',
          body: formData
        });
        
        if (response.ok) {
          const data = await response.json();
          this.handleStockCheckResponse(data);
        } else {
          console.warn('庫存檢查請求失敗:', response.status);
        }
      } catch (error) {
        console.warn('庫存檢查發生錯誤:', error);
      } finally {
        this.stockCheckLoading = false;
      }
    },
    
    // 處理庫存檢查回應
    handleStockCheckResponse(data) {
      const oldMaxStock = this.maxStock;
      this.maxStock = data.max_available;
      
      // 清除之前的警告訊息
      this.stockWarningMessage = '';
      
      // 如果庫存發生變化，顯示通知
      if (oldMaxStock !== this.maxStock && oldMaxStock > 0) {
        if (data.is_sold_out) {
          this.stockWarningMessage = '很抱歉，商品已售完！頁面將自動更新。';
          this.autoRefreshPage();
        } else if (!data.is_available) {
          this.stockWarningMessage = `庫存已更新：目前僅剩 ${this.maxStock} 件`;
          this.quantity = Math.min(this.quantity, this.maxStock);
        } else if (data.is_low_stock) {
          this.stockWarningMessage = `注意：庫存偏低，僅剩 ${this.maxStock} 件`;
        }
      }
      
      // 如果當前選擇的數量超過庫存，自動調整
      if (this.quantity > this.maxStock) {
        this.quantity = Math.max(1, this.maxStock);
      }
      
      // 更新庫存顯示元素
      this.updateStockDisplay(data);
    },
    
    // 更新頁面中的庫存顯示
    updateStockDisplay(data) {
      const stockElements = document.querySelectorAll('[data-stock-display]');
      stockElements.forEach(element => {
        element.textContent = `${data.current_stock} 件`;
      });
      
      const stockStatusElements = document.querySelectorAll('[data-stock-status]');
      stockStatusElements.forEach(element => {
        element.innerHTML = '';
        if (data.is_sold_out) {
          element.innerHTML = '<span class="text-red-600 font-medium">（已售完）</span>';
        } else if (data.is_low_stock) {
          element.innerHTML = '<span class="text-orange-600 font-medium">（庫存不足）</span>';
        }
      });
    },
    
    // 自動重新整理頁面
    autoRefreshPage() {
      setTimeout(() => {
        window.location.reload();
      }, 3000);
    },
    
    // 手動觸發庫存檢查
    async refreshStock() {
      this.lastStockCheck = 0; // 重設檢查時間，強制執行
      await this.checkStockStatus();
    },
    
    // 原有的 extractStock 方法的其餘部分
    extractStockFromInput() {
      // 如果沒有 data 屬性，嘗試從輸入框的 max 屬性獲取
      const quantityInput = this.$refs.quantityInput;
      if (quantityInput) {
        this.maxStock = parseInt(quantityInput.getAttribute('max')) || 0;
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
        this.showError('複製失敗: ' + error.message);
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
          this.showError('舊版複製方法失敗');
        }
      } catch (err) {
        this.showError('複製失敗: ' + err.message);
      }
      
      document.body.removeChild(textArea);
    },
    
    showCopySuccess() {
      this.copyButtonText = '已複製！';
      setTimeout(() => {
        this.copyButtonText = '複製票券代碼';
      }, 2000);
    },
    
    showError(message) {
      console.error('TicketCopy:', message);
    }
  }));
});

// Alpine.js 票券掃描管理組件
function createTicketScanManager() {
  return {
    isLoading: false,
    
    async restartScan(restartUrl, csrfToken) {
      if (this.isLoading) return;
      
      this.isLoading = true;
      
      try {
        const response = await fetch(restartUrl, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/x-www-form-urlencoded',
          }
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const html = await response.text();
        
        const scanResultElement = document.getElementById('scan-result');
        if (scanResultElement) {
          scanResultElement.innerHTML = html;
        } else {
          console.error('TicketScanManager: 找不到 scan-result 元素');
          return;
        }
        
        this.resetScanState();
        
        window.dispatchEvent(new CustomEvent('restart-scanning'));
        
      } catch (error) {
        console.error('TicketScanManager: 重啟掃描失敗', error);
        alert('重新掃描失敗，請重新整理頁面後再試');
      } finally {
        this.isLoading = false;
      }
    },
    
    resetScanState() {
      const ticketInput = document.querySelector('input[name=ticket_code]');
      if (ticketInput) {
        ticketInput.value = '';
        ticketInput.focus();
      }
    },
    
    get restartButtonClass() {
      const baseClasses = 'w-full py-4 px-6 rounded-xl font-medium text-lg transition-all focus:ring-4';
      const loadingClasses = 'opacity-50 cursor-not-allowed';
      const normalClasses = 'hover:bg-opacity-90';
      
      return this.isLoading ? 
        `${baseClasses} ${loadingClasses}` : 
        `${baseClasses} ${normalClasses}`;
    },
    
    get restartButtonText() {
      return this.isLoading ? '處理中...' : null;
    }
  };
}

// 將函數掛載到全域供 Alpine.js 使用
window.createTicketScanManager = createTicketScanManager;
window.createQuantityManager = createQuantityManager;

// Alpine.js TOTP 備用代碼管理組件
function createBackupCodes(backupTokens) {
    // 如果沒有直接傳入備用代碼，從 JSON script 元素讀取
    if (!backupTokens) {
        const backupTokensScript = document.getElementById('backup-tokens-data');
        if (backupTokensScript) {
            try {
                backupTokens = JSON.parse(backupTokensScript.textContent);
            } catch (error) {
                console.error('解析備用代碼資料失敗:', error);
                backupTokens = [];
            }
        }
    }
    
    return {
        backupTokens: backupTokens || [],
        copied: false,
        confirmed: false,
        
        async copyAllCodes() {
            const codesText = this.backupTokens.join('\n');
            
            try {
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    await navigator.clipboard.writeText(codesText);
                    this.showCopySuccess();
                } else {
                    this.fallbackCopyTextToClipboard(codesText);
                }
            } catch (error) {
                this.fallbackCopyTextToClipboard(codesText);
            }
        },
        
        fallbackCopyTextToClipboard(text) {
            const textArea = document.createElement('textarea');
            textArea.value = text;
            
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
                }
            } catch (err) {
                console.error('複製失敗:', err.message);
            }
            
            document.body.removeChild(textArea);
        },
        
        showCopySuccess() {
            this.copied = true;
            setTimeout(() => {
                this.copied = false;
            }, 2000);
        },
        
        downloadCodes() {
            const codesText = this.backupTokens.join('\n');
            const content = `TruePay 二階段驗證備用恢復代碼
生成時間：${new Date().toLocaleString()}

${codesText}

重要提醒：
- 每個代碼只能使用一次
- 請妥善保管，遺失後無法復原
- 可在個人設定中重新生成`;
            
            const blob = new Blob([content], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'truepay-backup-codes.txt';
            a.click();
            URL.revokeObjectURL(url);
        },
        
        goToDashboard(nextUrl, dashboardUrl) {
            if (this.confirmed) {
                window.location.href = nextUrl || dashboardUrl;
            }
        }
    };
}

// 將函數掛載到全域供 Alpine.js 使用
window.createBackupCodes = createBackupCodes;

// Alpine.js QR Code 掃描器組件
function createQrScanner(config) {
    return {
        status: '點擊下方按鈕以啟動相機進行掃描',
        isScanning: false,
        html5QrCode: null,
        validationUrl: config.validationUrl,

        init() {
            // 初始化完成，準備掃描
            console.log('QR Scanner initialized');
        },

        startScanner() {
            if (this.isScanning) return;

            // #qr-reader 元素必須存在
            const qrReaderEl = document.getElementById("qr-reader");
            if (!qrReaderEl) {
                this.status = '錯誤：找不到 ID 為 qr-reader 的掃描器顯示元件。';
                return;
            }

            try {
                this.html5QrCode = new Html5Qrcode("qr-reader");
                this.isScanning = true;
                this.status = '正在啟動相機...';

                this.html5QrCode.start(
                    { facingMode: "environment" },
                    { fps: 10, qrbox: { width: 250, height: 250 } },
                    (decodedText) => this.onScanSuccess(decodedText),
                    () => {} // onScanFailure: do nothing
                ).catch(() => {
                    this.status = '無法啟動相機，請檢查瀏覽器權限。';
                    this.isScanning = false;
                });
            } catch (e) {
                this.status = '啟動掃描器時發生錯誤。';
                this.isScanning = false;
            }
        },

        stopScanner() {
            if (this.html5QrCode && this.isScanning) {
                this.html5QrCode.stop()
                    .then(() => {
                        this.isScanning = false;
                        this.status = '點擊下方按鈕以啟動相機進行掃描';
                    })
                    .catch((err) => {
                        console.error("QR Scanner failed to stop.", err);
                        this.isScanning = false; // 強制重設狀態
                    });
            }
        },

        onScanSuccess(decodedText) {
            const ticketCode = this.parseTicketCode(decodedText);
            this.status = `掃描成功！正在驗證 ${ticketCode}...`;
            
            this.stopScanner();

            // 使用 htmx 提交驗證
            htmx.ajax('POST', this.validationUrl, {
                target: '#scan-result',
                swap: 'innerHTML',
                values: {
                    'ticket_code': ticketCode,
                    'method': 'qr',
                    'csrfmiddlewaretoken': getCsrfToken()
                }
            });
        },

        parseTicketCode(rawText) {
            try {
                // 優先嘗試 JSON 解析
                const cleanedText = rawText.trim();
                const data = JSON.parse(cleanedText);
                if (data && data.ticket_code) {
                    return data.ticket_code;
                }
            } catch {
                // 若 JSON 解析失敗，則使用正規表示式作為備案
                const match = rawText.match(/"ticket_code"\s*:\s*"(.*?)"/);
                if (match && match[1]) {
                    return match[1];
                }
            }
            // 如果兩種方法都失敗，回傳原始文字
            return rawText;
        }
    };
}

// 將新的掃描器組件掛載到全域
window.createQrScanner = createQrScanner;

// URL 參數處理工具函數
function handleRefreshParameter() {
    // 自動重新整理庫存狀態的功能
    if (window.location.search.includes('refresh=1')) {
        // 移除 URL 中的 refresh 參數，避免無限重新整理
        const url = new URL(window.location);
        url.searchParams.delete('refresh');
        window.history.replaceState({}, document.title, url.pathname + url.search);
    }
}

// 當頁面載入時自動執行 refresh 參數處理
document.addEventListener('DOMContentLoaded', handleRefreshParameter);

// 將函數掛載到全域
window.handleRefreshParameter = handleRefreshParameter;

// Alpine.js 核銷前TOTP驗證組件
function createTotpVerifyRedemption() {
    return {
        totpCode: '',
        
        handleInput() {
            // 只允許數字輸入
            this.totpCode = this.totpCode.replace(/\D/g, '');
            
            // 自動提交當輸入滿6位數
            if (this.totpCode.length === 6) {
                // 延遲一點讓用戶看到完整輸入
                setTimeout(() => {
                    this.submitForm();
                }, 300);
            }
        },
        
        submitForm() {
            if (this.totpCode.length === 6) {
                document.querySelector('form').submit();
            }
        },
        
        cancelVerification() {
            if (confirm('確定要取消驗證嗎？您將無法查看票券 QR Code。')) {
                // 使用相對路徑返回票券錢包
                window.location.href = '/customers/ticket-wallet/';
            }
        }
    };
}

// 將核銷前驗證函數掛載到全域供 Alpine.js 使用
window.createTotpVerifyRedemption = createTotpVerifyRedemption;

// 導出 Alpine.js 組件創建函數和 NavigationManager
export { 
  createImagePreview,
  createPaymentTimer, 
  createMobileMenu,
  createQuantityManager,
  createTicketScanManager,
  createBackupCodes,
  createQrScanner,
  createTotpVerifyRedemption, // 新增核銷前TOTP驗證組件
  NavigationManager
};
