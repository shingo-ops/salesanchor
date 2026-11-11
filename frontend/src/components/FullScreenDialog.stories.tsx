/**
 * FullScreenDialog — 窓いっぱいの入れ物のカタログ（ADR-144）
 *
 * 用途: 小窓に収まらない編集（予定の「その他のオプション」が最初の利用先）。
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { useState } from 'react'
import { Button } from './Button'
import { FullScreenDialog } from './FullScreenDialog'
import { TextFieldControl } from './TextField'

const meta: Meta<typeof FullScreenDialog> = {
  title: 'Components/FullScreenDialog',
  component: FullScreenDialog,
  parameters: {
    layout: 'fullscreen',
    docs: { disable: true },
  },
  tags: [],
}
export default meta

type Story = StoryObj<typeof FullScreenDialog>

export const Default: Story = {
  name: 'open — 窓いっぱいの編集（× で閉じる）',
  render: () => {
    const [open, setOpen] = useState(false)
    return (
      <div style={{ height: '100vh', background: 'var(--bg-canvas)', padding: 'var(--space-6)' }}>
        <Button variant="secondary" onClick={() => setOpen(true)}>開く</Button>
        <FullScreenDialog
          open={open}
          onClose={() => setOpen(false)}
          ariaLabel="予定の編集"
          closeLabel="閉じる"
          title={<TextFieldControl variant="schedule-title" aria-label="題名" placeholder="題名を追加" />}
          actions={<Button variant="primary" onClick={() => setOpen(false)}>保存</Button>}
        >
          <p>ここに編集の項目が並びます。</p>
          <p>× か Esc で閉じます。</p>
        </FullScreenDialog>
      </div>
    )
  },
}
