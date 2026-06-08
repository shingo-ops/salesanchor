/**
 * Button — デザイントークンカタログ (ADR-067 / Task 1C)
 *
 * 標準ボタン金型の全バリアント・サイズ・状態確認。
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { Button } from './Button'

const meta: Meta<typeof Button> = {
  title: 'Components/Button',
  component: Button,
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof Button>

export const Primary: Story = {
  name: 'primary — 主要アクション',
  args: { variant: 'primary', children: 'ボタン' },
}

export const Secondary: Story = {
  name: 'secondary — 補助アクション',
  args: { variant: 'secondary', children: 'ボタン' },
}

export const Ghost: Story = {
  name: 'ghost — テキスト系',
  args: { variant: 'ghost', children: 'ボタン' },
}

export const Danger: Story = {
  name: 'danger — 破壊的操作',
  args: { variant: 'danger', children: '削除' },
}

export const Sizes: Story = {
  name: 'サイズ比較 (sm / md / lg)',
  render: () => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
      <Button variant="primary" size="sm">Small</Button>
      <Button variant="primary" size="md">Medium</Button>
      <Button variant="primary" size="lg">Large</Button>
    </div>
  ),
}

export const Disabled: Story = {
  name: '無効状態',
  render: () => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
      <Button variant="primary" disabled>Primary</Button>
      <Button variant="secondary" disabled>Secondary</Button>
      <Button variant="ghost" disabled>Ghost</Button>
      <Button variant="danger" disabled>Danger</Button>
    </div>
  ),
}

export const Loading: Story = {
  name: 'ローディング状態',
  render: () => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
      <Button variant="primary" loading>保存中...</Button>
      <Button variant="secondary" loading>読み込み中</Button>
    </div>
  ),
}

export const FullWidth: Story = {
  name: '幅100% (fullWidth)',
  render: () => (
    <div style={{ width: 320 }}>
      <Button variant="primary" fullWidth>幅いっぱいのボタン</Button>
    </div>
  ),
}

export const Outline: Story = {
  name: 'outline — 透過枠線（色背景用）',
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
      <p style={{ fontSize: 'var(--font-xs)', color: 'var(--text-muted)', margin: 0 }}>
        白背景（secondary と似た見た目・意図的）
      </p>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
        <Button variant="outline" size="sm">Small</Button>
        <Button variant="outline" size="md">Medium</Button>
        <Button variant="outline" size="lg">Large</Button>
      </div>
      <p style={{ fontSize: 'var(--font-xs)', color: 'var(--text-muted)', margin: 0, marginTop: 'var(--space-2)' }}>
        色背景（透過背景が機能する用途）
      </p>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 'var(--space-3)',
        background: 'var(--accent-bg-subtle)',
        padding: 'var(--space-3) var(--space-4)',
        borderRadius: 'var(--radius-md)',
      }}>
        <Button variant="outline" size="sm">Small</Button>
        <Button variant="outline" size="md">Medium</Button>
        <Button variant="outline" size="lg">Large</Button>
      </div>
    </div>
  ),
}
