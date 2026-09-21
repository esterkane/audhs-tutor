/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // API_PORT lets `make dev-sandbox` proxy to a second backend; ws:true carries the voice WebSocket.
  server: {
    proxy: { '/api': { target: `http://localhost:${process.env.API_PORT ?? 8000}`, ws: true } },
  },
  test: { environment: 'jsdom', setupFiles: ['./src/test/setup.ts'], css: false },
})
