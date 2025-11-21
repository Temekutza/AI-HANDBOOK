import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// Основная конфигурация Vite для React-приложения.
// Здесь настраивается proxy для перенаправления запросов /api на бэкенд.
export default defineConfig({
  plugins: [react()],
  server: {
    // В dev-режиме все вызовы fetch('/api/...') с фронта
    // будут отправляться на указанный здесь адрес бэкенда.
    proxy: {
      '/api': 'http://localhost:3000',
    },
  },
})
