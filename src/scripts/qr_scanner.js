import jsQR from 'jsqr';

/**
 * 商家端 QR 掃描功能
 * 使用瀏覽器原生 Camera API 和 jsQR 函式庫
 */
class QRScanner {
    constructor() {
        this.video = null;
        this.canvas = null;
        this.context = null;
        this.stream = null;
        this.scanning = false;
        this.animationFrame = null;
    }

    /**
     * 初始化掃描器
     */
    async init(videoElement, canvasElement) {
        this.video = videoElement;
        this.canvas = canvasElement;
        this.context = this.canvas.getContext('2d');

        // 設定 canvas 大小
        this.canvas.width = 640;
        this.canvas.height = 480;
    }

    /**
     * 開始掃描
     */
    async startScan() {
        try {
            console.log('🎥 啟動相機...');
            
            // 取得相機權限
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'environment' // 使用後置相機
                }
            });

            this.video.srcObject = this.stream;
            this.video.play();

            this.scanning = true;
            this.scanFrame();

            return { success: true };

        } catch (error) {
            console.error('❌ 相機啟動失敗:', error);
            return { 
                success: false, 
                error: error.name === 'NotAllowedError' ? 
                    '請允許使用相機權限' : 
                    '無法啟動相機: ' + error.message 
            };
        }
    }

    /**
     * 停止掃描
     */
    stopScan() {
        console.log('🛑 停止掃描');
        
        this.scanning = false;
        
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }

        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }

        if (this.video) {
            this.video.srcObject = null;
        }
    }

    /**
     * 掃描框架
     */
    scanFrame() {
        if (!this.scanning) return;

        if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
            // 將影片畫面複製到 canvas
            this.context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
            
            // 獲取圖像數據
            const imageData = this.context.getImageData(0, 0, this.canvas.width, this.canvas.height);
            
            // 使用 jsQR 解析 QR code
            const qrResult = jsQR(imageData.data, imageData.width, imageData.height);
            
            if (qrResult) {
                console.log('✅ 掃描到 QR code:', qrResult.data);
                this.onQRDetected(qrResult.data);
                return; // 找到 QR code，停止掃描
            }
        }

        // 繼續掃描下一框架
        this.animationFrame = requestAnimationFrame(() => this.scanFrame());
    }

    /**
     * QR code 被偵測到時的回調
     */
    onQRDetected(data) {
        try {
            // 解析 QR code 資料
            const qrData = JSON.parse(data);
            
            if (qrData.type === 'ticket_voucher' && qrData.ticket_code) {
                console.log('🎫 偵測到票券 QR code:', qrData.ticket_code);
                
                // 觸發自訂事件
                const event = new CustomEvent('qr-scanned', {
                    detail: { ticketCode: qrData.ticket_code }
                });
                document.dispatchEvent(event);
                
                this.stopScan();
            } else {
                console.warn('⚠️ 不是有效的票券 QR code');
                // 繼續掃描
                this.animationFrame = requestAnimationFrame(() => this.scanFrame());
            }
        } catch (error) {
            console.warn('⚠️ QR code 格式錯誤:', error);
            // 繼續掃描
            this.animationFrame = requestAnimationFrame(() => this.scanFrame());
        }
    }
}

// 全域 QR 掃描器實例
window.qrScanner = new QRScanner();

console.log('📷 QR 掃描器已載入');