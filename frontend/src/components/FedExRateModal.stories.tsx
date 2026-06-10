/**
 * FedExRateModal — デザイントークンカタログ (ADR-067)
 *
 * FedEx ライブ見積もり比較モーダルのバリアント
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { FedExRateModal } from './FedExRateModal'

const meta: Meta<typeof FedExRateModal> = {
  title: 'Components/FedExRateModal',
  component: FedExRateModal,
  parameters: { layout: 'fullscreen' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof FedExRateModal>

export const Default: Story = {
  name: '初期表示（未取得）',
  args: {
    open: true,
    destinationCountryCode: 'US',
    weightKg: 1.5,
    onClose: () => {},
    onSelectRate: () => {},
  },
}

export const Closed: Story = {
  name: '非表示（closed）',
  args: {
    open: false,
    destinationCountryCode: 'US',
    weightKg: 1.5,
    onClose: () => {},
    onSelectRate: () => {},
  },
}
