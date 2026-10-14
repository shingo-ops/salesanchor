/**
 * ReviewItemDrawer — 要確認の商品の確認スライド（原文 | Gemini | システム ＋ 下段「直す」）
 *
 * condition_review は null（入れると ConditionReviewPanel が API を呼ぶため）。
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { ReviewItemDrawer, type ReviewDrawerItem } from './ReviewItemDrawer'

const RAW_TEXT = Array.from({ length: 20 }, (_, index) =>
  index >= 11 && index <= 14
    ? `ポケモンカード 拡張パック BOX ${index - 10}箱 ${(index - 10) * 6500}円`
    : `サンプルの行 ${index + 1}`,
).join('\n')

const ITEM: ReviewDrawerItem = {
  extraction_item_id: 'story-item-1',
  source_message_id: 'story-msg-1',
  provider: 'Supplier A',
  raw_text: RAW_TEXT,
  gemini: { name: 'ポケモンカード 拡張パック BOX', quantity: '2', price: '13000', unit: '箱', state: '未開封', memo: '', span: 'L12-15' },
  system: { product_title: 'ポケモンカード 拡張パック BOX', unit: 'BOX', unit_resolved: 'YES', condition: 'New', work_name: 'ポケモンカード', product_id: 'PM-00001', status: 'on_sale' },
  condition_review: null,
  review_reason_details: [{ code: 'pid_unresolved', source: 'system', fix_stage: 'extraction' }],
  is_v102: true,
}

const meta: Meta<typeof ReviewItemDrawer> = {
  title: 'Features/ReviewItemDrawer',
  component: ReviewItemDrawer,
  parameters: { layout: 'fullscreen' },
}
export default meta

type Story = StoryObj<typeof ReviewItemDrawer>

export const Default: Story = {
  args: {
    item: ITEM,
    onClose: () => undefined,
    onRefresh: async () => undefined,
  },
}

/** バッジ有り（最大の4種）。見出し行の高さが変わらず、原文の枠と表の枠がそろうこと */
export const WithBadges: Story = {
  args: {
    item: { ...ITEM, review_issues: ['UNIT_UNRESOLVED', 'EXCLUDED', 'PRODUCT_MASTER_UNREGISTERED'] },
    onClose: () => undefined,
    onRefresh: async () => undefined,
  },
}

const LONG_RAW_TEXT = Array.from({ length: 80 }, (_, index) =>
  index >= 11 && index <= 14
    ? `ポケモンカード 拡張パック BOX ${index - 10}箱 ${(index - 10) * 6500}円`
    : `サンプルの長い行 ${index + 1} ${'あ'.repeat(index % 7 === 0 ? 60 : 8)}`,
).join('\n')

/** 長い原文。枠の下端が表の下端にそろい、原文は枠の中でスクロールすること */
export const LongSource: Story = {
  args: {
    item: { ...ITEM, raw_text: LONG_RAW_TEXT, review_issues: ['UNIT_UNRESOLVED'] },
    onClose: () => undefined,
    onRefresh: async () => undefined,
  },
}
