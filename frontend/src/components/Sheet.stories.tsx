/**
 * Sheet — 下から出るシートのカタログ
 *
 * 用途: スマホで「選んで閉じる」操作に使う（受信箱の絞り込みが最初の利用先）。
 * Drawer（右から出る）との違いは出る向きと重ね順だけで、a11y の作りは同じ。
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { useState } from 'react'
import { Sheet } from './Sheet'

const meta: Meta<typeof Sheet> = {
  title: 'Components/Sheet',
  component: Sheet,
  parameters: {
    layout: 'fullscreen',
    docs: { disable: true },
  },
  tags: [],
}
export default meta

type Story = StoryObj<typeof Sheet>

export const Default: Story = {
  name: 'open — 基本表示（選んで閉じる）',
  render: () => {
    const [open, setOpen] = useState(false)
    const [picked, setPicked] = useState<string | null>(null)
    const options = ['すべて', 'リード', '商談中', '既存顧客']
    return (
      <div style={{ height: '100vh', background: 'var(--bg-canvas)', padding: '2rem' }}>
        <button onClick={() => setOpen(true)}>Sheet を開く</button>
        <p>選んだもの: {picked ?? '（まだ無い）'}</p>
        <Sheet open={open} onClose={() => setOpen(false)} title="絞り込み">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {options.map((o) => (
              <button
                key={o}
                onClick={() => { setPicked(o); setOpen(false) }}
                style={{ minHeight: 'var(--size-icon-btn-lg)' }}
              >
                {o}
              </button>
            ))}
          </div>
        </Sheet>
      </div>
    )
  },
}

export const WithFooter: Story = {
  name: 'footer あり — 操作ボタンを下に置く',
  render: () => {
    const [open, setOpen] = useState(true)
    return (
      <div style={{ height: '100vh', background: 'var(--bg-canvas)', padding: '2rem' }}>
        <button onClick={() => setOpen(true)}>Sheet を開く</button>
        <Sheet
          open={open}
          onClose={() => setOpen(false)}
          title="絞り込み"
          footer={<button onClick={() => setOpen(false)}>閉じる</button>}
        >
          <p>中身が少ないときはシートも低くなる。</p>
        </Sheet>
      </div>
    )
  },
}

export const LongContent: Story = {
  name: '中身が多い — 80dvh を上限に内側でスクロール',
  render: () => {
    const [open, setOpen] = useState(true)
    return (
      <div style={{ height: '100vh', background: 'var(--bg-canvas)', padding: '2rem' }}>
        <button onClick={() => setOpen(true)}>Sheet を開く</button>
        <Sheet open={open} onClose={() => setOpen(false)} title="項目が多い場合">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {Array.from({ length: 30 }, (_, i) => (
              <button key={i} style={{ minHeight: 'var(--size-icon-btn-lg)' }}>項目 {i + 1}</button>
            ))}
          </div>
        </Sheet>
      </div>
    )
  },
}
