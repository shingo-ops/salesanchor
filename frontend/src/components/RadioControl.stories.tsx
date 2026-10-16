/**
 * RadioControl — デザイントークンカタログ (design.md §AY-5)
 *
 * ラジオボタン金型（単独の欄）。未選択 / 選択 / disabled / label で包んだ例。
 */
import { useState } from 'react'
import type { Meta, StoryObj } from '@storybook/react-vite'
import { RadioControl } from './RadioControl'

const meta: Meta<typeof RadioControl> = {
  title: 'Components/RadioControl',
  component: RadioControl,
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof RadioControl>

function Controlled({ initial, disabled }: { initial: boolean; disabled?: boolean }) {
  const [checked, setChecked] = useState(initial)
  return (
    <RadioControl
      checked={checked}
      onChange={(e) => setChecked(e.target.checked)}
      disabled={disabled}
      aria-label="Radio"
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

export const Disabled: Story = {
  name: 'disabled',
  render: () => (
    <div style={{ display: 'flex', gap: 'var(--space-4)' }}>
      <Controlled initial={false} disabled />
      <Controlled initial disabled />
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
