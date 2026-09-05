import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './context/AuthContext'
import { ToastProvider } from './context/ToastContext'
import { initTheme } from './hooks/useTheme'
import './index.css'

// Apply the stored theme before React mounts so there is no light-mode flash.
initTheme()

const container = document.getElementById('root')
if (!container) {
  throw new Error('Root element #root not found in index.html')
}

createRoot(container).render(
  <StrictMode>
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  </StrictMode>,
)

// Register the service worker so the app can be installed to the home screen.
// Only in a production build: during `vite dev` a worker would serve stale
// modules and make edits look like they did nothing.
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js').catch((error) => {
      // An install failure costs the home-screen icon, not the app itself.
      console.warn('Service worker registration failed:', error)
    })
  })
}
