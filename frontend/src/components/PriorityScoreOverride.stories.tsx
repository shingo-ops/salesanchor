/**
 * PriorityScoreOverride — デザイントークンカタログ (ADR-107 / ADR-067)
 *
 * 顧客優先度スコア人手上書きUI。
 *
 * ※ usePermissions() が /me/permissions を呼ぶため、Storybook 上では
 *   権限未取得（null返却）の状態になりコンポーネントが非表示になる。
 *   フォーム・スライダーの実見確認は実アプリ（tenant_admin 権限ユーザー）で行う。
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import PriorityScoreOverride from './PriorityScoreOverride'

const meta: Meta<typeof PriorityScoreOverride> = {
  title: 'Components/PriorityScoreOverride',
  component: PriorityScoreOverride,
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof PriorityScoreOverride>

export const Default: Story = {
  name: '権限あり（実アプリ確認推奨）',
  args: {
    leadId: 1,
    currentScore: {
      tier: '有望',
      score: 0.5,
      confidence: 0.75,
      is_cold_start: false,
      sample_size: 15,
      signal_summary: {
        total_messages: 15,
        price_focus_count: 2,
        substance_talk_count: 3,
        self_disclosure_count: 2,
        early_purchase_signal_count: 1,
      },
    },
    onUpdated: () => {},
  },
}
