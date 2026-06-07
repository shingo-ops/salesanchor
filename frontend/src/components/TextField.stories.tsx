/**
 * TextField — デザイントークンカタログ (ADR-067 / Task 2C)
 *
 * 標準テキスト入力の全バリアント・状態確認。
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { TextField } from './TextField'

const meta: Meta<typeof TextField> = {
  title: 'Components/TextField',
  component: TextField,
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof TextField>

export const Default: Story = {
  name: '通常状態',
  args: {
    label: 'Company name',
    placeholder: 'Enter company name',
    helperText: 'Used across all documents.',
  },
}

export const Required: Story = {
  name: '必須フィールド',
  args: {
    label: 'Email',
    type: 'email',
    placeholder: 'you@example.com',
    required: true,
  },
}

export const WithError: Story = {
  name: 'エラー状態',
  args: {
    label: 'Email',
    type: 'email',
    placeholder: 'you@example.com',
    error: 'Invalid email address.',
    required: true,
    defaultValue: 'bad-email',
  },
}

export const Disabled: Story = {
  name: '無効状態',
  args: {
    label: 'Account ID',
    defaultValue: 'ACC-00123',
    disabled: true,
    helperText: 'Cannot be changed.',
  },
}

export const Sizes: Story = {
  name: 'サイズ比較 (sm / md / lg)',
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      <TextField label="Small" placeholder="sm input" size="sm" />
      <TextField label="Medium (default)" placeholder="md input" size="md" />
      <TextField label="Large" placeholder="lg input" size="lg" />
    </div>
  ),
}

export const FullWidth: Story = {
  name: '幅100% (fullWidth)',
  render: () => (
    <div style={{ width: 400 }}>
      <TextField label="Full width field" placeholder="Stretches to container" fullWidth />
    </div>
  ),
}

export const Password: Story = {
  name: 'password type',
  args: {
    label: 'Password',
    type: 'password',
    placeholder: 'Enter password',
    required: true,
  },
}
