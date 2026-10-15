/**
 * CheckboxControl — デザイントークンカタログ (design.md §AY-4a)
 *
 * チェック欄金型。未選択 / 選択 / indeterminate / disabled / sm / label で包んだ例。
 */
import { useState } from 'react'
import type { Meta, StoryObj } from '@storybook/react-vite'
import { CheckboxControl } from './CheckboxControl'

const meta: Meta<typeof CheckboxControl> = {
  title: 'Components/CheckboxControl',
  component: CheckboxControl,
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof CheckboxControl>

function Controlled({ initial, disabled, size }: { initial: boolean; disabled?: boolean; size?: 'md' | 'sm' }) {
  const [checked, setChecked] = useState(initial)
  return (
    <CheckboxControl
      checked={checked}
      onChange={(e) => setChecked(e.target.checked)}
      disabled={disabled}
      size={size}
      aria-label="Checkbox"
    />
  )
}

export const Unchecked: Story = {
  name: 'unchecked',
  render: () => <Controlled initial={false} />,
}

export const Checked: Story = {
  name: 'checked',
  render: () => <Controlled initial />,
}

export const Indeterminate: Story = {
  name: 'indeterminate',
  render: () => <CheckboxControl checked={false} indeterminate onChange={() => {}} aria-label="Indeterminate" />,
}

export const Disabled: Story = {
  name: 'disabled',
  render: () => (
    <div style={{ display: 'flex', gap: 'var(--space-4)' }}>
      <Controlled initial={false} disabled />
      <Controlled initial disabled />
    </div>
  ),
}

export const Small: Story = {
  name: 'sm',
  render: () => (
    <div style={{ display: 'flex', gap: 'var(--space-4)' }}>
      <Controlled initial={false} size="sm" />
      <Controlled initial size="sm" />
    </div>
  ),
}

export const WithLabel: Story = {
  name: 'with label',
  render: () => (
    <label style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-2)' }}>
      <Controlled initial />
      <span>Label</span>
    </label>
  ),
}

export const DataColor: Story = {
  name: 'dataColor',
  render: () => (
    <div style={{ display: 'flex', gap: 'var(--space-4)' }}>
      <CheckboxControl dataColor="#1a73e8" checked onChange={() => {}} aria-label="Data color blue" />
      <CheckboxControl dataColor="#e8710a" checked onChange={() => {}} aria-label="Data color orange" />
    </div>
  ),
}
