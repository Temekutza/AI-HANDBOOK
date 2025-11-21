import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// Точка входа в React-приложение: монтируем <App /> в элемент с id="root".
createRoot(document.getElementById('root')).render(
  <StrictMode>
    {/* StrictMode помогает отлавливать потенциальные проблемы в dev-режиме во время разработки. */}
    <App />
  </StrictMode>,
)
