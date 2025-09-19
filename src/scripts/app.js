import Alpine from 'alpinejs'
import htmx from 'htmx.org';
import { Html5Qrcode } from 'html5-qrcode';
import '../styles/app.css'
import './functions.js'
import './chart.js'
import jsQR from 'jsqr'
import Chart from 'chart.js/auto' 

window.Alpine = Alpine
window.htmx = htmx
window.jsQR = jsQR
window.Html5Qrcode = Html5Qrcode
window.Chart = Chart

// 暴露 Alpine 組件到全域
// authenticatorGuide 函數在 functions.js 中定義，會自動暴露到全域

Alpine.start()