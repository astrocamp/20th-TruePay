import jsQR from 'jsqr';

/**
 * Alpine.js QR 掃描組件
 * 純 Alpine.js 實現，不使用 document.addEventListener
 */

// 定義 Alpine.js 組件
document.addEventListener('alpine:init', () => {
    Alpine.data('qrScannerComponent', () => ({
        isScanning: false,
        errorMessage: '',
        video: null,
        canvas: null,
        context: null,
        stream: null,
        animationFrame: null,
        
        init() {
            console.log('🔧 QR 掃描組件初始化');
        },

        async startScan() {
            console.log('🎬 開始掃描');
            
            this.isScanning = true;
            this.errorMessage = '';

            // 獲取元素
            this.video = this.$el.querySelector('#qr-video');
            this.canvas = this.$el.querySelector('#qr-canvas');
            
            if (!this.video || !this.canvas) {
                this.errorMessage = '找不到視訊元素';
                this.isScanning = false;
                return;
            }

            // 設定 canvas
            this.context = this.canvas.getContext('2d');
            this.canvas.width = 640;
            this.canvas.height = 480;

            try {
                // 取得相機權限
                this.stream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        width: { ideal: 640 },
                        height: { ideal: 480 },
                        facingMode: 'environment'
                    }
                });

                this.video.srcObject = this.stream;
                await this.video.play();

                // 開始掃描循環
                this.scanFrame();

            } catch (error) {
                console.error('❌ 相機啟動失敗:', error);
                this.errorMessage = error.name === 'NotAllowedError' ? 
                    '請允許使用相機權限' : 
                    '無法啟動相機: ' + error.message;
                this.isScanning = false;
            }
        },

        stopScan() {
            console.log('⏹️ 停止掃描');
            
            this.isScanning = false;
            
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
        },

        scanFrame() {
            if (!this.isScanning) return;

            if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
                // 將影片畫面複製到 canvas
                this.context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
                
                // 獲取圖像數據
                const imageData = this.context.getImageData(0, 0, this.canvas.width, this.canvas.height);
                
                // 使用 jsQR 解析 QR code
                const qrResult = jsQR(imageData.data, imageData.width, imageData.height);
                
                if (qrResult) {
                    console.log('✅ 掃描到 QR code:', qrResult.data);
                    this.handleQRResult(qrResult.data);
                    return;
                }
            }

            // 繼續掃描下一框架
            this.animationFrame = requestAnimationFrame(() => this.scanFrame());
        },

        handleQRResult(data) {
            try {
                // 解析 QR code 資料
                const qrData = JSON.parse(data);
                
                if (qrData.type === 'ticket_voucher' && qrData.ticket_code) {
                    console.log('🎫 偵測到票券 QR code:', qrData.ticket_code);
                    
                    // 使用 Alpine.js $dispatch 觸發事件
                    this.$dispatch('qr-scanned', { 
                        ticketCode: qrData.ticket_code 
                    });
                    
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
        },

        retryScan() {
            this.errorMessage = '';
            this.startScan();
        }
    }));
});

console.log('🧩 純 Alpine.js QR 掃描組件已載入');