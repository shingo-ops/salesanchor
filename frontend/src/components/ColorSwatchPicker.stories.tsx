/**
 * ColorSwatchPicker — デザイントークンカタログ（ADR-1081・ADR-144）
 *
 * 色見本から 1 つ選ぶ金型。デフォルト（null）＋予定の色の例。
 */
import { useState } from 'react'
import type { Meta, StoryObj } from '@storybook/react-vite'
import { ColorSwatchPicker, type ColorSwatchOption } from './ColorSwatchPicker'

const meta: Meta<typeof ColorSwatchPicker> = {
  title: 'Components/ColorSwatchPicker',
  component: ColorSwatchPicker,
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof ColorSwatchPicker>

const OPTIONS: ColorSwatchOption[] = [
  { value: null, label: 'Default', color: 'var(--accent)' },
  { value: 'tomato', label: 'Tomato', color: 'var(--event-color-tomato)' },
  { value: 'banana', label: 'Banana', color: 'var(--event-color-banana)' },
  { value: 'basil', label: 'Basil', color: 'var(--event-color-basil)' },
  { value: 'cobalt', label: 'Cobalt', color: 'var(--event-color-cobalt)' },
  { value: 'grape', label: 'Grape', color: 'var(--event-color-grape)' },
]

function Controlled({ initial }: { initial: string | null }) {
  const [value, setValue] = useState<string | null>(initial)
  return (
    <ColorSwatchPicker label="Event color" name="story-color" options={OPTIONS} value={value} onChange={setValue} />
  )
}

export const Default: Story = {
  name: 'default',
  render: () => <Controlled initial={null} />,
}

export const Selected: Story = {
  name: 'selected',
  render: () => <Controlled initial="tomato" />,
}
