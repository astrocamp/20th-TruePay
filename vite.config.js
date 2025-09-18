import { defineConfig } from 'vite'
import { resolve } from "path"
import tailwindcss from '@tailwindcss/vite'
import { copyFileSync } from 'fs'

export default defineConfig({
    plugins: [
        tailwindcss(),
        {
            name: 'copy-favicon',
            writeBundle() {
                copyFileSync('src/favicon.ico', 'static/favicon.ico')
            }
        }
    ],
    build: {
        outDir: 'static',
        emptyOutDir: false,
        rollupOptions: {
            input: {
                app: resolve(__dirname, 'src/scripts/app.js')
            },
            output: {
                entryFileNames: "scripts/[name].js",
                chunkFileNames: "scripts/[name].js",
                assetFileNames: "styles/[name].[ext]"
            }
        }
    }
})
