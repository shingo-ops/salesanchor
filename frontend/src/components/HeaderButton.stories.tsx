/**
 * HeaderButton — デザイントークンカタログ (ADR-067 / ADR-069)
 *
 * ページヘッダーアクション用ボタンの全バリアント確認。
 * CombinedInHeader が受信箱（InboxPage）の基準パターン。
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { HeaderButton } from './HeaderButton'

const meta: Meta<typeof HeaderButton> = {
  title: 'Components/HeaderButton',
  component: HeaderButton,
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof HeaderButton>

export const GhostVariant: Story = {
  name: 'ghost — テキストボタン（ナビゲーション用）',
  args: {
    variant: 'ghost',
    children: 'テンプレート',
  },
}

export const PrimaryVariant: Story = {
  name: 'primary — テキストボタン（新規作成用）',
  args: {
    variant: 'primary',
    children: '新規作成',
  },
}

export const SecondaryVariant: Story = {
  name: 'secondary — テキストボタン（インポート等）',
  args: {
    variant: 'secondary',
    children: 'インポート',
  },
}

export const IconVariant: Story = {
  name: 'icon — アイコンボタン（--size-icon-btn: 36px）',
  args: {
    variant: 'icon',
    'aria-label': '設定',
    'data-tooltip': '設定',
    children: (
      // PAGE_ICONS.settingsSolid 相当のSVG（Storybookデモ用）
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"
          stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
        />
        <path
          d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"
          stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
        />
      </svg>
    ),
  },
}

/** 受信箱（InboxPage）の基準パターン — .page-header-actions 内でのレイアウト確認 */
export const CombinedInHeader: Story = {
  name: '複合 — .page-header-actions 内（受信箱の基準パターン）',
  render: () => (
    <div className="page-header-actions">
      <HeaderButton variant="ghost">テンプレート</HeaderButton>
      <HeaderButton variant="ghost">FAQ</HeaderButton>
      <HeaderButton
        variant="icon"
        aria-label="設定"
        data-tooltip="設定"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"
            stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
          />
          <path
            d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"
            stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
          />
        </svg>
      </HeaderButton>
    </div>
  ),
}
