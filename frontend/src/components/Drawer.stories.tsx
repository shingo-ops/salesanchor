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
  parameters: { chromatic: { disable: true } },
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
  parameters: { chromatic: { disable: true } },
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

export const Closed: Story = {
  name: 'closed — 閉じた状態',
  parameters: { chromatic: { disable: true } },
  args: {
    open: false,
    onClose: () => {},
    title: 'Drawer（非表示）',
    children: 'コンテンツ',
  },
}
