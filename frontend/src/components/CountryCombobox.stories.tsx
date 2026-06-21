import { useEffect } from 'react'
import type { Meta, StoryObj } from '@storybook/react-vite'
import { CountryCombobox } from './CountryCombobox'
import { api } from '../lib/api'

const MOCK_COUNTRIES = [
  { code: 'JP', name: 'Japan', dial_code: '+81', is_active: true },
  { code: 'US', name: 'United States', dial_code: '+1', is_active: true },
  { code: 'SG', name: 'Singapore', dial_code: '+65', is_active: true },
]

function CountryComboboxStory(props: StoryObj<typeof CountryCombobox>['args']) {
  const originalGet = api.get
  api.get = async () => MOCK_COUNTRIES as any

  useEffect(() => () => {
    api.get = originalGet
  }, [originalGet])

  return <CountryCombobox {...props} />
}

const meta: Meta<typeof CountryCombobox> = {
  title: 'Components/CountryCombobox',
  component: CountryCombobox,
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}

export default meta

type Story = StoryObj<typeof CountryCombobox>

export const Default: Story = {
  name: '初期表示',
  args: {
    id: 'country-combobox-story',
    value: 'JP',
    placeholder: '国を選択',
    onChange: () => {},
    onCommit: () => {},
  },
  render: (args) => <CountryComboboxStory {...args} />,
}
