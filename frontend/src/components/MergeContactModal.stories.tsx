/**
 * MergeContactModal — デザイントークンカタログ (ADR-067)
 *
 * 担当者統合モーダル（ADR-098 SA-04）
 * ※ API 通信を含むため Storybook 上では実際の統合処理は行われない
 *   2段階確認 UI のレイアウト・スタイル確認が目的
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import MergeContactModal from './MergeContactModal'

const meta: Meta<typeof MergeContactModal> = {
  title: 'Components/MergeContactModal',
  component: MergeContactModal,
  parameters: { layout: 'centered' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof MergeContactModal>

export const Open: Story = {
  name: '担当者選択ステップ',
  args: {
    open: true,
    companyId: 1,
    source: {
      id: 5,
      contact_code: 'C005',
      display_name: '田中太郎',
      surname: '田中',
      given_name: '太郎',
    },
    onMerged: () => {},
    onCancel: () => {},
  },
}

export const Closed: Story = {
  name: '非表示状態',
  args: {
    open: false,
    companyId: 1,
    source: {
      id: 5,
      contact_code: 'C005',
      display_name: '田中太郎',
      surname: '田中',
      given_name: '太郎',
    },
    onMerged: () => {},
    onCancel: () => {},
  },
}
