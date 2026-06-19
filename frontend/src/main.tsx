import React from 'react'
import ReactDOM from 'react-dom/client'
import './i18n' // i18next を App より先に初期化する（ADR-027）
import './index.css'
import './loading-animations.css'
import App from './App.tsx'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
