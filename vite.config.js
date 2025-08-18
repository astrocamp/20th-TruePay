import { defineConfig } from 'vite'
import { resolve } from "path"
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
    plugins: [tailwindcss()],
    build:{
        outDir: 'static',
        emptyOutDir: false,
        watch: {
            exclude: ['static/**', 'node_modules/**'],
            buildDelay: 100
        },
        rollupOptions:{
            input: {
                app: resolve(__dirname,'src/scripts/app.js')
            },
            output: {
                entryFileNames:"scripts/[name].js",
                chunkFileNames:"scripts/[name].js",
                assetFileNames:"styles/[name].[ext]"
            }
        }
    }
})
