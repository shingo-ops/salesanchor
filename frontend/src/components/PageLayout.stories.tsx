/**
 * PageLayout — デザイントークンカタログ (ADR-067)
 *
 * 全ページ共通のタイトル・サブタイトルレイアウト標準パターン
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { Button } from './Button'
import { PageLayout } from './PageLayout'

const meta: Meta<typeof PageLayout> = {
  title: 'Components/PageLayout',
  component: PageLayout,
  parameters: { layout: 'fullscreen' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof PageLayout>

export const TitleOnly: Story = {
  name: 'タイトルのみ',
  args: {
    navKey: 'nav.dashboard',
    children: <div style={{ padding: 'var(--space-4)' }}>コンテンツエリア</div>,
  },
}

export const WithSubtitle: Story = {
  name: 'タイトル + サブタイトル',
  args: {
    navKey: 'nav.leadChat',
    subtitleKey: 'inbox.subtitle',
    children: <div style={{ padding: 'var(--space-4)' }}>コンテンツエリア</div>,
  },
}

export const WithHeaderAction: Story = {
  name: 'ヘッダーアクションボタン付き',
  args: {
    navKey: 'nav.companies',
    headerAction: (
      <Button variant="primary" size="md">+ 新規追加</Button>
    ),
    children: <div style={{ padding: 'var(--space-4)' }}>コンテンツエリア</div>,
  },
}

export const WithAll: Story = {
  name: 'フル構成（サブタイトル + アクション）',
  args: {
    navKey: 'nav.orders',
    subtitleKey: 'orders.subtitle',
    headerAction: (
      <Button variant="primary" size="md">+ 受注追加</Button>
    ),
    children: <div style={{ padding: 'var(--space-4)' }}>コンテンツエリア</div>,
  },
}

export const SlimHeaderOnMobile: Story = {
  name: 'スマホでヘッダーを圧縮（slimHeaderOnMobile）',
  args: {
    navKey: 'nav.leadChat',
    subtitleKey: 'inbox.subtitle',
    slimHeaderOnMobile: true,
    headerAction: (
      <Button variant="primary" size="md">テンプレート</Button>
    ),
    children: (
      <div style={{ padding: 'var(--space-4)' }}>
        画面幅を767px以下にすると、タイトルと説明文が画面から外れ、操作ボタンだけが残る。
        上部バーに同じタイトルが出ているページで、限られた高さを本文に回すために使う。
        タイトルは読み上げには残る。PC・タブレットの見た目は変わらない。
      </div>
    ),
  },
}
