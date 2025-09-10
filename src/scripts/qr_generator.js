import QRCode from 'qrcode';

/**
 * 生成票券QR code
 * @param {string} elementId - 要插入QR code的元素ID
 * @param {string} ticketCode - 票券代碼
 */
window.generateQR = function(elementId, ticketCode) {
    const element = document.getElementById(elementId);
    if (!element) {
        console.error('QR code container not found:', elementId);
        return;
    }
    
    // 清空現有內容
    element.innerHTML = '';
    
    // 構建QR code資料
    const qrData = {
        ticket_code: ticketCode,
        type: 'ticket_voucher',
        version: '1.0'
    };
    
    // 生成QR code
    QRCode.toCanvas(JSON.stringify(qrData), {
        width: 200,
        height: 200,
        margin: 2,
        color: {
            dark: '#000000',
            light: '#FFFFFF'
        }
    }, function (err, canvas) {
        if (err) {
            console.error('QR code generation failed:', err);
            element.innerHTML = '<p class="text-red-500 text-sm">QR code 生成失敗</p>';
            return;
        }
        
        // 添加樣式讓QR code置中
        canvas.style.display = 'block';
        canvas.style.margin = '0 auto';
        canvas.style.borderRadius = '8px';
        
        element.appendChild(canvas);
    });
};