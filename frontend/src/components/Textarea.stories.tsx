/**
 * Textarea — デザイントークンカタログ (ADR-067 / Task 2C)
 *
 * 標準テキストエリアの全バリアント・状態確認。
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { Textarea, TextareaControl } from './Textarea'

const meta: Meta<typeof Textarea> = {
  title: 'Components/Textarea',
  component: Textarea,
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof Textarea>

export const Default: Story = {
  name: '通常状態',
  args: {
    label: 'Notes',
    placeholder: 'Enter notes...',
    helperText: 'Visible to all team members.',
  },
}

export const Required: Story = {
  name: '必須フィールド',
  args: {
    label: 'Description',
    placeholder: 'Describe the issue...',
    required: true,
  },
}

export const WithError: Story = {
  name: 'エラー状態',
  args: {
    label: 'Message',
    placeholder: 'Enter message...',
    error: 'Message is required.',
    required: true,
  },
}

export const Disabled: Story = {
  name: '無効状態',
  args: {
    label: 'Template body',
    defaultValue: 'This template is locked and cannot be edited.',
    disabled: true,
    helperText: 'Contact admin to edit.',
  },
}

export const WithRows: Story = {
  name: 'rows 指定 (rows=6)',
  args: {
    label: 'Detailed notes',
    placeholder: 'Enter detailed notes...',
    rows: 6,
    helperText: 'Up to 1000 characters.',
  },
}

export const Sizes: Story = {
  name: 'サイズ比較 (sm / md / lg)',
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      <Textarea label="Small" placeholder="sm textarea" size="sm" />
      <Textarea label="Medium (default)" placeholder="md textarea" size="md" />
      <Textarea label="Large" placeholder="lg textarea" size="lg" />
    </div>
  ),
}

export const ControlDefault: Story = {
  name: 'TextareaControl 通常（裸の本体）',
  render: () => <TextareaControl placeholder="Enter notes..." aria-label="Notes" />,
}

export const ControlSizes: Story = {
  name: 'TextareaControl サイズ比較 (sm / md / lg)',
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      <TextareaControl size="sm" placeholder="sm textarea" aria-label="Small" />
      <TextareaControl size="md" placeholder="md textarea" aria-label="Medium" />
      <TextareaControl size="lg" placeholder="lg textarea" aria-label="Large" />
    </div>
  ),
}

export const ControlDisabled: Story = {
  name: 'TextareaControl 無効状態',
  render: () => (
    <TextareaControl
      defaultValue="This template is locked and cannot be edited."
      disabled
      aria-label="Template body"
    />
  ),
}

export const ControlVariants: Story = {
  name: 'TextareaControl 種類 (karte / embedded / composer / schedule)',
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      <TextareaControl variant="karte" rows={3} placeholder="karte variant" aria-label="Karte" />
      <TextareaControl variant="embedded" rows={2} placeholder="embedded variant" aria-label="Embedded" />
      <TextareaControl variant="composer" rows={3} placeholder="composer variant" aria-label="Composer" />
      <TextareaControl variant="schedule" rows={4} placeholder="schedule variant" aria-label="Schedule" />
    </div>
  ),
}

export const ControlCode: Story = {
  name: 'TextareaControl 等幅 (textStyle=code)',
  render: () => (
    <TextareaControl
      textStyle="code"
      rows={4}
      defaultValue={'{ "prompt": "Extract the product name and price." }'}
      aria-label="Prompt"
    />
  ),
}
