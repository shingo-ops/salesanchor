import React from 'react'
import ReactDOM from 'react-dom/client'
import './i18n' // i18next を App より先に初期化する（ADR-027）
import './index.css'
import './loading-animations.css'
import App from './App.tsx'
import { registerDevSession } from './lib/auth/devSessionSlot'

async function bootstrap() {
  // 開発サーバーだけ、開発用の偽ログインを登録する（本番の組み立てでは、この枝と devSession.ts は入らない）
  if (import.meta.env.DEV) {
    const { createDevSession } = await import('./lib/auth/devSession')
    registerDevSession(createDevSession())
  }
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  )
}

void bootstrap()
