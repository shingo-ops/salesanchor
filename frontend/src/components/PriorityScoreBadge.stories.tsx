/**
 * PriorityScoreBadge — デザイントークンカタログ (ADR-107 / ADR-067)
 *
 * 顧客優先度スコアバッジの全表示状態確認。
 * ※ スコアは社内専用（顧客非公開）。
 *
 * 表示バリアント:
 *   - NoData: score=null → 「未評価」
 *   - ColdStart: is_cold_start=true → 「暫定」
 *   - Watching: tier=要観察
 *   - Promising: tier=有望
 *   - Top: tier=最有望
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import PriorityScoreBadge from './PriorityScoreBadge'
import type { CustomerScoreData } from './PriorityScoreBadge'

const meta: Meta<typeof PriorityScoreBadge> = {
  title: 'Components/PriorityScoreBadge',
  component: PriorityScoreBadge,
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof PriorityScoreBadge>

const baseScore: CustomerScoreData = {
  tier: '要観察',
  score: 0.25,
  confidence: 0.6,
  is_cold_start: false,
  sample_size: 12,
  signal_summary: {
    total_messages: 12,
    price_focus_count: 3,
    substance_talk_count: 1,
    self_disclosure_count: 0,
    early_purchase_signal_count: 0,
  },
}

export const NoData: Story = {
  name: '未評価 — score=null',
  args: { score: null },
}

export const ColdStart: Story = {
  name: '暫定 — is_cold_start=true（データ不足）',
  args: {
    score: {
      ...baseScore,
      is_cold_start: true,
      confidence: 0,
      sample_size: 2,
    },
  },
}

export const Watching: Story = {
  name: '要観察 — 低スコア',
  args: {
    score: { ...baseScore, tier: '要観察', score: 0.2, confidence: 0.7 },
  },
}

export const Promising: Story = {
  name: '有望 — 中スコア',
  args: {
    score: { ...baseScore, tier: '有望', score: 0.5, confidence: 0.8 },
  },
}

export const Top: Story = {
  name: '最有望 — 高スコア',
  args: {
    score: {
      ...baseScore,
      tier: '最有望',
      score: 0.82,
      confidence: 0.9,
      sample_size: 28,
      signal_summary: {
        ...baseScore.signal_summary,
        total_messages: 28,
        substance_talk_count: 5,
        self_disclosure_count: 4,
      },
    },
  },
}
