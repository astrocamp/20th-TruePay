import jsQR from 'jsqr';

export class QRScanner {
    constructor() {
        this.video = null;
        this.isScanning = false;
        this.stream = null;
    }
    init() {
        this.video = document.getElementById('qr-video');
        if (this.video) {
            this.startCamera();
            this.setupEventListeners();
        }
    }
    async startCamera() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                video: { facingMode: 'environment' } 
            });
            this.video.srcObject = this.stream;
            this.video.play();
            this.isScanning = true;
            this.updateScanStatus('正在掃描中...', 'scanning');
            requestAnimationFrame(() => this.scan());
        } catch (err) {
            console.error('Camera error:', err);
            this.updateScanStatus('無法開啟攝像頭', 'error');
            // 使用HTMX顯示攝像頭錯誤
            htmx.ajax('POST', '/merchant/restart-scan/', {
                target: '#scan-result',
                swap: 'innerHTML'
            });
        }
    }

    /**
     * 掃描QR Code
     */
    scan() {
        if (!this.isScanning || !window.jsQR) {
            requestAnimationFrame(() => this.scan());
            return;
        }

        if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            canvas.height = this.video.videoHeight;
            canvas.width = this.video.videoWidth;
            context.drawImage(this.video, 0, 0, canvas.width, canvas.height);
            
            const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
            const code = jsQR(imageData.data, imageData.width, imageData.height);
            
            if (code) {
                this.isScanning = false;
                this.updateScanStatus('掃描成功！驗證中...', 'validating');
                
                // 使用HTMX發送掃描結果到後端
                htmx.ajax('POST', '/merchant/validate-ticket/', {
                    values: { qr_data: code.data },
                    target: '#scan-result',
                    swap: 'innerHTML'
                });
                return;
            }
        }
        requestAnimationFrame(() => this.scan());
    }

    /**
     * 重新開始掃描
     */
    restartScanning() {
        this.isScanning = true;
        this.updateScanStatus('正在掃描中...', 'scanning');
    }

    /**
     * 更新掃描狀態顯示
     */
    updateScanStatus(message, type) {
        const statusEl = document.getElementById('scan-status');
        if (!statusEl) return;

        const icons = {
            ready: `<svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z"/></svg>`,
            scanning: `<svg class="w-4 h-4 mr-1 animate-pulse" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z"/></svg>`,
            validating: `<svg class="w-4 h-4 mr-1 animate-spin" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z"/></svg>`,
            error: `<svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"/></svg>`
        };
        
        const classes = {
            ready: 'bg-blue-100 text-[#0056B3]',
            scanning: 'bg-blue-100 text-[#0056B3]',
            validating: 'bg-yellow-100 text-yellow-700',
            error: 'bg-red-100 text-red-700'
        };
        
        statusEl.className = `inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${classes[type]}`;
        statusEl.innerHTML = `${icons[type]}${message}`;
    }

    /**
     * 設置事件監聽器
     */
    setupEventListeners() {
        // 監聽HTMX事件，當重新開始掃描時恢復掃描狀態
        document.body.addEventListener('htmx:afterRequest', (event) => {
            if (event.detail.pathInfo.requestPath.includes('restart-scan')) {
                this.restartScanning();
            }
        });

        // 頁面關閉時停止攝像頭
        window.addEventListener('beforeunload', () => {
            this.destroy();
        });
    }

    /**
     * 銷毀掃描器，釋放資源
     */
    destroy() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }
        this.isScanning = false;
    }
}

// 全局函數，供HTML模板使用
window.restartScanning = function() {
    if (window.qrScannerInstance) {
        window.qrScannerInstance.restartScanning();
    }
};

// 自動初始化（當頁面有QR掃描器時）
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('qr-video')) {
        window.qrScannerInstance = new QRScanner();
        window.qrScannerInstance.init();
    }
});

export default QRScanner;