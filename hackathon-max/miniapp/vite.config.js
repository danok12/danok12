import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base: './' — мини-приложение раздаётся API по пути /app/,
// поэтому все ссылки на ресурсы должны быть относительными.
export default defineConfig({
  plugins: [react()],
  base: './',
  build: { outDir: 'dist', emptyOutDir: true, sourcemap: false },
  server: { port: 5173, proxy: { '/api': 'http://localhost:8080' } },
})
