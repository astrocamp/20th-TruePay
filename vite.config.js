import { defineConfig } from 'vite'
import { resolve } from "path"
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
    plugins: [tailwindcss()],
    build:{
        outDir: 'static',
        emptyOutDir: false,
        rollupOptions:{
            input: {
                app: resolve(__dirname,'src/scripts/app.js'),
                qr: resolve(__dirname,'src/scripts/qr_generator.js'),
                scanner: resolve(__dirname,'src/scripts/qr_scanner.js'),
                qr_component: resolve(__dirname,'src/scripts/qr_scanner_component.js')
            },
            output: {
                entryFileNames:"scripts/[name].js",
                chunkFileNames:"scripts/[name].js",
                assetFileNames:"styles/[name].[ext]"
            }
        }
    }
})
