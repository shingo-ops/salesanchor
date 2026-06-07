/**
 * MergeLeadModal — デザイントークンカタログ (ADR-067)
 *
 * リード統合モーダル（ADR-119 PR-E）
 * ※ マウント時にAPIでリード候補を取得するため、Storybook上ではローディング状態で表示される
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import MergeLeadModal from './MergeLeadModal'

const meta: Meta<typeof MergeLeadModal> = {
  title: 'Components/MergeLeadModal',
  component: MergeLeadModal,
  parameters: { layout: 'fullscreen' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof MergeLeadModal>

export const Open: Story = {
  name: 'モーダル表示',
  args: {
    open: true,
    source: { id: 42, lead_code: 'LD-00042', customer_name: 'テストユーザー（新規）' },
    onMerged: () => {},
    onCancel: () => {},
  },
}
