import { useState } from 'react'
import type { Meta, StoryObj } from '@storybook/react-vite'
import { ChoiceCardGroup, type ChoiceCardOption } from './ChoiceCardGroup'

type Choice = 'reassign' | 'register' | 'condition' | 'keep'

const OPTIONS: ChoiceCardOption<Choice>[] = [
  { value: 'reassign', label: 'Reassign to an existing product', description: 'Search and pick a product' },
  { value: 'register', label: 'Register as a new product', description: 'Add to the product master and reassign this row' },
  { value: 'condition', label: 'Fix the condition', description: 'Confirm or correct the condition' },
  { value: 'keep', label: 'Keep as is', description: 'Mark reasons as checked' },
]

function Demo({ initial, options }: { initial: Choice | null; options: ChoiceCardOption<Choice>[] }) {
  const [value, setValue] = useState<Choice | null>(initial)
  return <ChoiceCardGroup legend="What do you want to fix?" name="story-choice" options={options} value={value} onChange={setValue} />
}

const meta = {
  title: 'Components/ChoiceCardGroup',
  component: ChoiceCardGroup,
  tags: ['autodocs'],
} satisfies Meta<typeof ChoiceCardGroup>

export default meta
type Story = StoryObj<typeof meta>

const noop = () => undefined

export const FourChoicesUnselected: Story = {
  args: { legend: 'What do you want to fix?', name: 'story-choice', options: OPTIONS, value: null, onChange: noop },
  render: () => <Demo initial={null} options={OPTIONS} />,
}

export const Selected: Story = {
  args: { legend: 'What do you want to fix?', name: 'story-choice', options: OPTIONS, value: 'register', onChange: noop },
  render: () => <Demo initial="register" options={OPTIONS} />,
}

export const WithDisabled: Story = {
  args: { legend: 'What do you want to fix?', name: 'story-choice', options: OPTIONS, value: null, onChange: noop },
  render: () => <Demo initial={null} options={OPTIONS.map((o) => (o.value === 'condition' || o.value === 'keep' ? { ...o, disabled: true } : o))} />,
}

export const WithoutDescription: Story = {
  args: { legend: 'What do you want to fix?', name: 'story-choice', options: OPTIONS, value: null, onChange: noop },
  render: () => <Demo initial={null} options={OPTIONS.map(({ description: _description, ...rest }) => rest)} />,
}
