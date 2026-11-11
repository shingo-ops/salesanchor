/**
 * EditorPage — 窓いっぱいの編集画面のカタログ（ADR-144・ADR-1074）
 *
 * 用途: 予定の編集（作る・直す）。左に寄せた題名・日時の段（lead）・絵の列つきの札。
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { useState } from 'react'
import { Button } from './Button'
import { EditorPage, EditorPageRow } from './EditorPage'
import { TextareaControl } from './Textarea'
import { TextFieldControl } from './TextField'

const meta: Meta<typeof EditorPage> = {
  title: 'Components/EditorPage',
  component: EditorPage,
  parameters: {
    layout: 'fullscreen',
    docs: { disable: true },
  },
  tags: [],
}
export default meta

type Story = StoryObj<typeof EditorPage>

export const Default: Story = {
  name: 'open — 予定の編集',
  render: () => {
    const [open, setOpen] = useState(false)
    return (
      <div style={{ height: '100vh', background: 'var(--bg-canvas)', padding: 'var(--space-6)' }}>
        <Button variant="secondary" onClick={() => setOpen(true)}>開く</Button>
        <EditorPage
          open={open}
          onClose={() => setOpen(false)}
          ariaLabel="予定の編集"
          closeLabel="閉じる"
          title={<TextFieldControl variant="editor-title" aria-label="題名" placeholder="題名を追加" />}
          saveLabel="保存"
          onSave={() => setOpen(false)}
          cardTitle="予定の詳細"
          lead={
            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <TextFieldControl variant="editor-filled" type="date" aria-label="開始日" />
              <TextFieldControl variant="editor-filled" type="date" aria-label="終了日" />
            </div>
          }
        >
          <EditorPageRow icon={<span aria-hidden="true">場</span>}>
            <TextFieldControl variant="editor-filled" aria-label="場所" placeholder="場所を追加" />
          </EditorPageRow>
          <EditorPageRow icon={<span aria-hidden="true">説</span>}>
            <TextareaControl variant="editor-filled" rows={4} aria-label="説明" placeholder="説明を追加" />
          </EditorPageRow>
        </EditorPage>
      </div>
    )
  },
}
