/**
 * ItemComparison — 確認スライド・仕入先詳細の比較表（項目 | Gemini | システム | 採用元を1つの表に並べる）
 *
 * 幅 640・960 の入れ物は仕入先詳細を想定。1440・1024 は ReviewItemDrawer の story を viewport を変えて測る。
 */
import type { Decorator, Meta, StoryObj } from '@storybook/react-vite'
import { ItemComparison, type AnalysisReviewItem } from './ItemComparison'

const BASE: AnalysisReviewItem = {
  extraction_item_id: 'story-item-1',
  source_message_id: 'story-msg-1',
  provider: 'Supplier A',
  raw_text: '',
  gemini: { name: 'ポケモンカード 拡張パック BOX', quantity: '2', price: '13000', unit: '箱', state: '未開封', memo: '', span: 'L12-15' },
  system: { product_title: 'ポケモンカード 拡張パック BOX', unit: 'BOX', unit_resolved: 'YES', condition: 'New', work_name: 'ポケモンカード', product_id: 'PM-00001', status: 'on_sale' },
  review_issues: [],
}

const inBox = (width: number): Decorator => (Story) => (
  <div style={{ width }}><Story /></div>
)

const meta: Meta<typeof ItemComparison> = {
  title: 'Features/ItemComparison',
  component: ItemComparison,
  parameters: { layout: 'padded' },
  args: { item: BASE, readOnly: true, onJumpToSourceLine: () => undefined },
}
export default meta

type Story = StoryObj<typeof ItemComparison>

/** バッジ 0 件（バッジの div を出さない） */
export const Default: Story = {}

export const LongName: Story = {
  args: { item: { ...BASE, gemini: { ...BASE.gemini, name: 'ポケモンカードゲーム スカーレット&バイオレット 拡張パック 超電ブレイカー 未開封 シュリンク付き BOX 1カートン分 国内正規品' } } },
}

export const Unresolved: Story = {
  args: { item: { ...BASE, gemini: {}, system: {}, review_issues: ['UNIT_UNRESOLVED'] } },
}

export const NoMemo: Story = {
  args: { item: { ...BASE, gemini: { ...BASE.gemini, memo: '' }, system: { ...BASE.system, note: '' } } },
}

export const WithMemoNote: Story = {
  args: { item: { ...BASE, gemini: { ...BASE.gemini, memo: '角潰れあり' }, system: { ...BASE.system, note: '角潰れあり' } } },
}

export const ProductMasterUnregistered: Story = {
  args: { item: { ...BASE, review_issues: ['PRODUCT_MASTER_UNREGISTERED'] } },
}

export const Width640: Story = {
  decorators: [inBox(640)],
  args: { item: { ...BASE, review_issues: ['PRODUCT_MASTER_UNREGISTERED'] } },
}

export const Width960: Story = {
  decorators: [inBox(960)],
  args: { item: { ...BASE, review_issues: ['PRODUCT_MASTER_UNREGISTERED'] } },
}
