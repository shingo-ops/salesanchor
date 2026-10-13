import { useState } from 'react'
import type { Meta, StoryObj } from '@storybook/react-vite'
import { AsyncCombobox, type AsyncComboboxOption } from './AsyncCombobox'
import { DataTable } from './DataTable'

const CATALOG: AsyncComboboxOption[] = [
  { value: 'p-1', label: 'Booster Box Alpha' },
  { value: 'p-2', label: 'Booster Box Beta' },
  { value: 'p-3', label: 'Starter Deck Alpha' },
  { value: 'p-4', label: 'Starter Deck Beta' },
  { value: 'p-5', label: 'Promo Pack Alpha' },
]

const loadFromCatalog = async (query: string): Promise<AsyncComboboxOption[]> =>
  CATALOG.filter((option) => option.label.toLowerCase().includes(query.toLowerCase()))

function Demo(props: { disabled?: boolean; load?: typeof loadFromCatalog }) {
  const [label, setLabel] = useState('')
  return (
    <AsyncCombobox
      id="async-combobox-story"
      ariaLabel="Product"
      value={label}
      placeholder="Type a product name"
      disabled={props.disabled}
      loadOptions={props.load ?? loadFromCatalog}
      onSelect={(option) => setLabel(option.label)}
      noResultsText="No results"
      loadingText="Loading..."
    />
  )
}

function InTable() {
  const rows = ['row-1', 'row-2', 'row-3']
  const [labels, setLabels] = useState<Record<string, string>>({})
  return (
    <DataTable
      columns={[
        { key: 'name', header: 'Row', renderCell: (row: string) => row },
        {
          key: 'product',
          header: 'Product',
          renderCell: (row: string) => (
            <AsyncCombobox
              id={`async-combobox-${row}`}
              ariaLabel="Product"
              value={labels[row] ?? ''}
              loadOptions={loadFromCatalog}
              onSelect={(option) => setLabels((current) => ({ ...current, [row]: option.label }))}
              noResultsText="No results"
              loadingText="Loading..."
            />
          ),
        },
      ]}
      data={rows}
      rowKey={(row: string) => row}
    />
  )
}

const meta: Meta<typeof AsyncCombobox> = {
  title: 'Components/AsyncCombobox',
  component: AsyncCombobox,
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}

export default meta

type Story = StoryObj<typeof AsyncCombobox>

export const Default: Story = {
  name: '初期表示',
  render: () => <Demo />,
}

export const NoResults: Story = {
  name: '候補なし',
  render: () => <Demo load={async () => []} />,
}

export const Loading: Story = {
  name: '読み込み中',
  render: () => <Demo load={() => new Promise(() => {})} />,
}

export const Disabled: Story = {
  name: '無効',
  render: () => <Demo disabled />,
}

export const InsideDataTable: Story = {
  name: '表のセル内（表の枠で切れない）',
  render: () => <InTable />,
}
