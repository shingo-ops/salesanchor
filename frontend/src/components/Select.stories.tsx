/**
 * Select — デザイントークンカタログ (ADR-067 / Task 2C)
 *
 * 標準セレクトの全バリアント・状態確認。
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { Select } from './Select'
import type { SelectOption } from './Select'

const STATUS_OPTIONS: SelectOption[] = [
  { value: 'active', label: 'Active' },
  { value: 'pending', label: 'Pending' },
  { value: 'closed', label: 'Closed' },
  { value: 'archived', label: 'Archived', disabled: true },
]

const meta: Meta<typeof Select> = {
  title: 'Components/Select',
  component: Select,
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof Select>

export const Default: Story = {
  name: '通常状態',
  args: {
    label: 'Status',
    options: STATUS_OPTIONS,
    placeholder: '-- Select status --',
    helperText: 'Choose the current deal status.',
  },
}

export const Required: Story = {
  name: '必須フィールド',
  args: {
    label: 'Category',
    options: STATUS_OPTIONS,
    placeholder: '-- Select --',
    required: true,
  },
}

export const WithError: Story = {
  name: 'エラー状態',
  args: {
    label: 'Region',
    options: STATUS_OPTIONS,
    error: 'Please select a valid option.',
    required: true,
  },
}

export const Disabled: Story = {
  name: '無効状態',
  args: {
    label: 'Currency',
    options: [{ value: 'jpy', label: 'JPY — Japanese Yen' }],
    defaultValue: 'jpy',
    disabled: true,
    helperText: 'Fixed for this account.',
  },
}

export const Sizes: Story = {
  name: 'サイズ比較 (sm / md / lg)',
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      <Select label="Small" options={STATUS_OPTIONS} size="sm" />
      <Select label="Medium (default)" options={STATUS_OPTIONS} size="md" />
      <Select label="Large" options={STATUS_OPTIONS} size="lg" />
    </div>
  ),
}
