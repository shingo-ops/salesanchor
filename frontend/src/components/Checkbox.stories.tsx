/**
 * Checkbox — デザイントークンカタログ (ADR-067 / design.md §3-6(a))
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { Checkbox } from './Checkbox'

const meta: Meta<typeof Checkbox> = {
  title: 'Components/Checkbox',
  component: Checkbox,
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof Checkbox>

export const Default: Story = {
  name: '通常状態',
  args: {
    label: 'Meta の新着メッセージ',
  },
}

export const Checked: Story = {
  name: 'チェック済み',
  args: {
    label: 'Meta の新着メッセージ',
    defaultChecked: true,
  },
}

export const WithDescription: Story = {
  name: '説明文つき',
  args: {
    label: 'TCG在庫配信エラー',
    description: '配信失敗時にこのサーバーへ通知します。',
  },
}

export const WithError: Story = {
  name: 'エラー状態',
  args: {
    label: '商談の担当アサイン',
    error: '少なくとも1つ選択してください。',
  },
}

export const Disabled: Story = {
  name: '無効状態',
  args: {
    label: '商談の担当アサイン',
    disabled: true,
    defaultChecked: true,
  },
}

export const Sizes: Story = {
  name: 'サイズ比較 (sm / md / lg)',
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      <Checkbox label="Small" size="sm" />
      <Checkbox label="Medium (default)" size="md" />
      <Checkbox label="Large" size="lg" />
    </div>
  ),
}

export const Group: Story = {
  name: '縦並びの複数選択例',
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
      <Checkbox label="商談の担当アサイン" defaultChecked />
      <Checkbox label="Meta の新着メッセージ" />
      <Checkbox label="TCG在庫配信エラー" />
    </div>
  ),
}
