import Alpine from 'alpinejs'
import 'htmx.org';
import '../styles/app.css'

// 匯入QR掃描器（會自動初始化）
import './qrScanner.js';

window.Alpine = Alpine
Alpine.start()