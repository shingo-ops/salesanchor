/**
 * Radio — デザイントークンカタログ (ADR-067 / design.md §AY-5)
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { Radio } from './Radio'

const meta: Meta<typeof Radio> = {
  title: 'Components/Radio',
  component: Radio,
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof Radio>

export const Default: Story = {
  name: '通常状態',
  args: {
    label: 'Meta の新着メッセージ',
    name: 'story-default',
  },
}

export const Checked: Story = {
  name: '選択済み',
  args: {
    label: 'Meta の新着メッセージ',
    name: 'story-checked',
    defaultChecked: true,
  },
}

export const WithDescription: Story = {
  name: '説明文つき',
  args: {
    label: 'TCG在庫配信エラー',
    name: 'story-description',
    description: '配信失敗時にこのサーバーへ通知します。',
  },
}

export const WithError: Story = {
  name: 'エラー状態',
  args: {
    label: '商談の担当アサイン',
    name: 'story-error',
    error: '少なくとも1つ選択してください。',
  },
}

export const Disabled: Story = {
  name: '無効状態',
  args: {
    label: '商談の担当アサイン',
    name: 'story-disabled',
    disabled: true,
    defaultChecked: true,
  },
}

export const Sizes: Story = {
  name: 'サイズ比較 (sm / md / lg)',
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      <Radio label="Small" size="sm" name="story-size" />
      <Radio label="Medium (default)" size="md" name="story-size" />
      <Radio label="Large" size="lg" name="story-size" />
    </div>
  ),
}

export const Group: Story = {
  name: '縦並びの択一例',
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
      <Radio label="商談の担当アサイン" name="story-group" defaultChecked />
      <Radio label="Meta の新着メッセージ" name="story-group" />
      <Radio label="TCG在庫配信エラー" name="story-group" />
    </div>
  ),
}
