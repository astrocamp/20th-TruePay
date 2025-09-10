// QR掃描器組件
window.QRScannerComponent = {
    isScanning: false,
    hasCamera: false,
    errorMessage: '',
    scanResult: '',
    ticketCode: '',

    // 開始掃描
    startScan() {
        this.errorMessage = '';
        this.scanResult = '';
        this.isScanning = true;
        
        // 初始化QR掃描器
        initQRScanner('qr-video', 'qr-canvas', 
            (data) => this.onScanSuccess(data),
            (error) => this.onScanError(error)
        );
        
        startQRScanning()
            .then(() => {
                this.hasCamera = true;
            })
            .catch((error) => {
                this.onScanError('無法存取攝影機，請檢查權限設定');
            });
    },

    // 停止掃描
    stopScan() {
        this.isScanning = false;
        stopQRScanning();
    },

    // 掃描成功回調
    onScanSuccess(data) {
        this.scanResult = data;
        this.processQRData(data);
        this.stopScan();
    },

    // 掃描錯誤回調
    onScanError(error) {
        this.errorMessage = error;
        this.isScanning = false;
    },

    // 處理QR code資料
    processQRData(data) {
        try {
            const qrData = JSON.parse(data);
            if (qrData.type === 'ticket_voucher' && qrData.ticket_code) {
                // 自動填入票券代碼
                this.ticketCode = qrData.ticket_code;
                
                // 觸發父組件更新
                this.$dispatch('qr-scanned', { ticketCode: qrData.ticket_code });
                
                // 自動提交驗證表單
                this.$nextTick(() => {
                    const form = document.querySelector('form[hx-post*="validate_ticket"]');
                    if (form) {
                        htmx.trigger(form, 'submit');
                    }
                });
            } else {
                this.onScanError('無效的票券QR code格式');
            }
        } catch (e) {
            this.onScanError('QR code格式錯誤，請確認是否為有效的票券QR code');
        }
    },

    // 重新掃描
    retryScan() {
        this.errorMessage = '';
        this.startScan();
    },

    // 初始化
    init() {
        return {
            ...this,
            // Alpine生命週期
            init() {
                // 監聽標籤切換
                this.$watch('$store.currentTab', (tab) => {
                    if (tab === 'qr') {
                        this.$nextTick(() => this.startScan());
                    } else {
                        this.stopScan();
                    }
                });
            }
        }
    }
};