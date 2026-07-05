import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, HashRouter } from 'react-router'
import { Toaster } from 'sonner'
import './index.css'
import App from './App.tsx'

const Router = import.meta.env.VITE_ROUTER_MODE === 'hash' ? HashRouter : BrowserRouter

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Router>
      <App />
      <Toaster position="top-right" theme="dark" richColors />
    </Router>
  </StrictMode>,
)
