import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { configDefaults } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  cacheDir: process.env.AUDHS_VITE_CACHE_DIR ?? 'node_modules/.vite',
  optimizeDeps: { include: ['@xyflow/react', 'wavesurfer.js', 'wavesurfer.js/dist/plugins/spectrogram.js'] },
  plugins: [react(), tailwindcss()],
  // API_PORT lets `make dev-sandbox` proxy to a second backend; ws:true carries the voice WebSocket.
  server: {
    proxy: { '/api': { target: `http://127.0.0.1:${process.env.API_PORT ?? 8000}`, ws: true } },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    exclude: [...configDefaults.exclude, 'e2e/**'], // Playwright owns e2e/
  },
})
