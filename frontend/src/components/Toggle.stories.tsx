/**
 * Toggle — デザイントークンカタログ (design.md §AY-3b)
 *
 * 切替スイッチ金型。OFF / ON / disabled。
 */
import { useState } from 'react'
import type { Meta, StoryObj } from '@storybook/react-vite'
import { Toggle } from './Toggle'

const meta: Meta<typeof Toggle> = {
  title: 'Components/Toggle',
  component: Toggle,
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof Toggle>

function Controlled({ initial, disabled }: { initial: boolean; disabled?: boolean }) {
  const [checked, setChecked] = useState(initial)
  return <Toggle checked={checked} onCheckedChange={setChecked} disabled={disabled} aria-label="Toggle" />
}

export const Off: Story = {
  name: 'OFF',
  render: () => <Controlled initial={false} />,
}

export const On: Story = {
  name: 'ON',
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
