import jsQR from 'jsqr';

/**
 * QR Code掃描器類
 */
class QRScanner {
    constructor() {
        this.video = null;
        this.canvas = null;
        this.context = null;
        this.isScanning = false;
        this.stream = null;
        this.onScanCallback = null;
        this.onErrorCallback = null;
    }

    /**
     * 初始化掃描器
     * @param {HTMLVideoElement} videoElement - 影片元素
     * @param {HTMLCanvasElement} canvasElement - 畫布元素
     * @param {Function} onScan - 掃描成功回調
     * @param {Function} onError - 錯誤回調
     */
    init(videoElement, canvasElement, onScan, onError) {
        this.video = videoElement;
        this.canvas = canvasElement;
        this.context = this.canvas.getContext('2d');
        this.onScanCallback = onScan;
        this.onErrorCallback = onError;
        
        // 設置畫布尺寸
        this.canvas.width = 300;
        this.canvas.height = 300;
    }

    /**
     * 開始掃描
     */
    async startScanning() {
        if (this.isScanning) return;

        try {
            // 請求攝影機權限
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'environment', // 後置攝影機
                    width: { ideal: 300 },
                    height: { ideal: 300 }
                }
            });

            this.video.srcObject = this.stream;
            this.video.play();
            this.isScanning = true;

            // 等待影片準備就緒
            this.video.addEventListener('loadedmetadata', () => {
                this.scanFrame();
            });

        } catch (error) {
            console.error('Cannot access camera:', error);
            if (this.onErrorCallback) {
                this.onErrorCallback('無法存取攝影機，請確認權限設定');
            }
        }
    }

    /**
     * 停止掃描
     */
    stopScanning() {
        this.isScanning = false;
        
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }

        if (this.video) {
            this.video.srcObject = null;
        }
    }

    /**
     * 掃描幀
     */
    scanFrame() {
        if (!this.isScanning || !this.video || this.video.readyState !== this.video.HAVE_ENOUGH_DATA) {
            if (this.isScanning) {
                requestAnimationFrame(() => this.scanFrame());
            }
            return;
        }

        // 將影片畫面繪製到畫布
        this.context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        
        // 獲取影像資料
        const imageData = this.context.getImageData(0, 0, this.canvas.width, this.canvas.height);
        
        // 使用jsQR解析QR code
        const qrCode = jsQR(imageData.data, imageData.width, imageData.height);
        
        if (qrCode) {
            // 成功掃描到QR code
            if (this.onScanCallback) {
                this.onScanCallback(qrCode.data);
            }
        } else {
            // 繼續掃描下一幀
            requestAnimationFrame(() => this.scanFrame());
        }
    }
}

// 全局QR掃描器實例
window.qrScanner = new QRScanner();

/**
 * 初始化QR掃描功能
 * @param {string} videoId - 影片元素ID
 * @param {string} canvasId - 畫布元素ID
 * @param {Function} onScan - 掃描成功回調
 * @param {Function} onError - 錯誤回調
 */
window.initQRScanner = function(videoId, canvasId, onScan, onError) {
    const video = document.getElementById(videoId);
    const canvas = document.getElementById(canvasId);
    
    if (!video || !canvas) {
        console.error('Video or canvas element not found');
        return;
    }
    
    window.qrScanner.init(video, canvas, onScan, onError);
};

/**
 * 開始QR掃描
 */
window.startQRScanning = function() {
    return window.qrScanner.startScanning();
};

/**
 * 停止QR掃描
 */
window.stopQRScanning = function() {
    window.qrScanner.stopScanning();
};