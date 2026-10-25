/**
 * Drawer — 右スライドパネルカタログ
 *
 * onOpenFullPage prop で「フルページで開く↗」ボタンの表示/非表示を切り替え。
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { useState } from 'react'
import { Drawer } from './Drawer'

const meta: Meta<typeof Drawer> = {
  title: 'Components/Drawer',
  component: Drawer,
  parameters: {
    layout: 'fullscreen',
    docs: { disable: true },
  },
  tags: [],
}
export default meta

type Story = StoryObj<typeof Drawer>

export const Default: Story = {
  name: 'open — 基本表示',
  render: () => {
    const [open, setOpen] = useState(false)
    return (
      <div style={{ height: '100vh', background: 'var(--bg-canvas)', padding: '2rem' }}>
        <button onClick={() => setOpen(true)}>Drawer を開く</button>
        <Drawer
          open={open}
          onClose={() => setOpen(false)}
          title="仕入先を編集"
        >
          <p>コンテンツエリア</p>
        </Drawer>
      </div>
    )
  },
}

export const WithFullPage: Story = {
  name: 'with fullpage — フルページボタン付き',
  render: () => {
    const [open, setOpen] = useState(false)
    return (
      <div style={{ height: '100vh', background: 'var(--bg-canvas)', padding: '2rem' }}>
        <button onClick={() => setOpen(true)}>Drawer を開く</button>
        <Drawer
          open={open}
          onClose={() => setOpen(false)}
          title="仕入先を編集"
          onOpenFullPage={() => alert('フルページへ遷移')}
        >
          <p>コンテンツエリア（↗ボタンでフルページ展開）</p>
        </Drawer>
      </div>
    )
  },
}

export const Wide: Story = {
  name: 'wide — 広幅（1100px・スマホは全幅）',
  render: () => {
    const [open, setOpen] = useState(false)
    return (
      <div style={{ height: '100vh', background: 'var(--bg-canvas)', padding: '2rem' }}>
        <button onClick={() => setOpen(true)}>Drawer を開く</button>
        <Drawer
          open={open}
          onClose={() => setOpen(false)}
          title="広幅のドロワー"
          size="wide"
        >
          <p>size="wide" で幅が 1100px になる（画面が狭いときは画面幅）</p>
        </Drawer>
      </div>
    )
  },
}

export const WithBack: Story = {
  name: 'with back — ← 戻るボタン付き（design.md 4-1）',
  render: () => {
    const [open, setOpen] = useState(false)
    const [sub, setSub] = useState(false)
    return (
      <div style={{ height: '100vh', background: 'var(--bg-canvas)', padding: '2rem' }}>
        <button onClick={() => { setSub(false); setOpen(true) }}>Drawer を開く</button>
        <Drawer
          open={open}
          onClose={() => setOpen(false)}
          title={sub ? '提供者' : '絞り込み'}
          onBack={sub ? () => setSub(false) : undefined}
          backLabel="戻る"
        >
          {sub
            ? <p>提供者だけの選択画面（← で一覧に戻る）</p>
            : <button onClick={() => setSub(true)}>提供者 ›</button>}
        </Drawer>
      </div>
    )
  },
}

export const Closed: Story = {
  name: 'closed — 閉じた状態',
  args: {
    open: false,
    onClose: () => {},
    title: 'Drawer（非表示）',
    children: 'コンテンツ',
  },
}
