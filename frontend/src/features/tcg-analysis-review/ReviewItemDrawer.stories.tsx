/**
 * ReviewItemDrawer — 要確認の商品の確認スライド（原文 | Gemini | システム ＋ 下段「直す」）
 *
 * condition_review は null（入れると ConditionReviewPanel が API を呼ぶため）。
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import type { Decorator } from '@storybook/react-vite'
import { useEffect, useRef } from 'react'
import { userEvent, within } from 'storybook/test'
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

// ── 直しウィザード（API は window.fetch を差し替えて返す） ─────────────────────

const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } })

function mockApi(duplicates: Array<{ product_id: string; japanese_title: string }>): Decorator {
  const install = (original: typeof window.fetch): typeof window.fetch =>
    (async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.includes('/tcg/products/registration-form')) {
        return json({
          item: { extraction_item_id: 'story-item-1', source_message_id: 'story-msg-1', raw_name: 'ポケモンカード 拡張パック BOX' },
          lookups: {
            product_kind_id: [{ id: '1', name: 'カード' }],
            work_id: [{ id: '2', name: 'ポケモンカード' }],
            manufacturer_id: [{ id: '3', name: 'ポケモン' }],
            product_category_id: [{ id: '4', name: '拡張パック' }],
          },
        })
      }
      if (url.includes('/tcg/products/check-duplicates')) return json({ candidates: duplicates })
      if (url.includes('/tcg/products/search')) {
        return json({ candidates: [{ product_uuid: 'uuid-1', product_id: '1', japanese_title: 'ポケモンカード 拡張パック BOX' }] })
      }
      return original(input, init)
    }) as typeof window.fetch
  return (Story) => (
    <MockFetch install={install}>
      <Story />
    </MockFetch>
  )
}

/** fetch を差し替えて描画し、外れたら元に戻す（差し替えはレンダー前に必要なので描画中に行う） */
function MockFetch({ install, children }: { install: (original: typeof window.fetch) => typeof window.fetch; children: React.ReactNode }) {
  const originalRef = useRef<typeof window.fetch | null>(null)
  if (originalRef.current === null) {
    originalRef.current = window.fetch
    window.fetch = install(originalRef.current)
  }
  useEffect(() => {
    const original = originalRef.current
    return () => {
      if (original) window.fetch = original
      originalRef.current = null
    }
  }, [])
  return <>{children}</>
}

const WIZARD_ARGS = {
  item: { ...ITEM, review_issues: ['PRODUCT_ID_UNRESOLVED', 'PRODUCT_MASTER_UNREGISTERED'] },
  onClose: () => undefined,
  onRefresh: async () => undefined,
}

/** 行を選ぶ前: 赤字の理由、比較表の「修正」列（押して直す）、「直したい行を表から押してください」 */
export const BeforeRowSelected: Story = { args: WIZARD_ARGS, decorators: [mockApi([])] }

/** 商品IDの行を押した後: 質問（何を直しますか）が出ること */
export const WizardQuestion: Story = {
  args: WIZARD_ARGS,
  decorators: [mockApi([])],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement.ownerDocument.body)
    await userEvent.click(await canvas.findByRole('row', { name: /Product ID|商品ID/ }))
  },
}

const CONDITION_ARGS = {
  item: {
    ...ITEM,
    system: { ...ITEM.system, condition: 'Empty box', condition_basis: 'MANUAL_CONDITION_REVIEW', pid_basis: 'MANUAL' },
    condition_review: { condition_id: '5', review_version: 'a'.repeat(64), needs_review: true, review_reasons: 'empty_box_ambiguous', confirmed: false, classification: 'ambiguous' },
    review_reason_details: [{ code: 'condition_unknown', source: 'system' as const, fix_stage: 'extraction' as const }],
  },
  onClose: () => undefined,
  onRefresh: async () => undefined,
}

/** 状態の行を押した後: 状態を選ぶ欄が直接出る。「修正」列に人が決めた商品名と状態（空箱）が出る */
export const ConditionRowSelected: Story = {
  args: CONDITION_ARGS,
  decorators: [mockApi([])],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement.ownerDocument.body)
    await userEvent.click(await canvas.findByRole('row', { name: /State|Condition|状態/ }))
  },
}

/** 商品IDの行を押し、選択肢1（既存の商品に付け替える）を選んだ後 */
export const WizardReassignSelected: Story = {
  args: WIZARD_ARGS,
  decorators: [mockApi([])],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement.ownerDocument.body)
    await userEvent.click(await canvas.findByRole('row', { name: /Product ID|商品ID/ }))
    await userEvent.click(await canvas.findByRole('radio', { name: /Reassign to an existing product|既存の商品/ }))
  },
}

async function fillRegisterForm(canvasElement: HTMLElement) {
  const canvas = within(canvasElement.ownerDocument.body)
  await userEvent.click(await canvas.findByRole('row', { name: /Product ID|商品ID/ }))
  await userEvent.click(await canvas.findByRole('radio', { name: /Register as a new product|新しい商品/ }))
  const pairs: Array<[RegExp, string, string]> = [
    [/Product type|商品種別/, 'カ', 'カード'],
    [/Title \/ series|作品/, 'ポ', 'ポケモンカード'],
    [/Manufacturer|メーカー/, 'ポ', 'ポケモン'],
    [/Category|カテゴリ/, '拡', '拡張パック'],
  ]
  for (const [label, typed, option] of pairs) {
    const input = await canvas.findByRole('combobox', { name: label })
    await userEvent.type(input, typed)
    await userEvent.click(await canvas.findByRole('option', { name: option }))
  }
}

/** 選択肢2（新しい商品を登録する）の入力フォーム */
export const WizardRegisterForm: Story = {
  args: WIZARD_ARGS,
  decorators: [mockApi([])],
  play: async ({ canvasElement }) => {
    await fillRegisterForm(canvasElement)
  },
}

/** 似た商品があるときの質問（同じ商品はこの中にありますか） */
export const WizardDuplicateQuestion: Story = {
  args: WIZARD_ARGS,
  decorators: [mockApi([{ product_id: '7', japanese_title: 'ポケモンカード 拡張パック BOX 旧版' }])],
  play: async ({ canvasElement }) => {
    await fillRegisterForm(canvasElement)
    const canvas = within(canvasElement.ownerDocument.body)
    await userEvent.click(await canvas.findByRole('button', { name: /Check for similar products|似た商品/ }))
  },
}
