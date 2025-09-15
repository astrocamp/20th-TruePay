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
Alpine.start()