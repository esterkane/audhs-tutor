import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { configDefaults } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
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
