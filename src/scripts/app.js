import Alpine from 'alpinejs'
import htmx from 'htmx.org';
import { Html5Qrcode } from 'html5-qrcode';
import '../styles/app.css'
import './functions.js'
import jsQR from 'jsqr'

window.Alpine = Alpine
window.htmx = htmx
window.jsQR = jsQR
window.Html5Qrcode = Html5Qrcode
Alpine.start()