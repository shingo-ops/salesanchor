/**
 * ListRow — 一覧の1行金型カタログ
 *
 * card-mobile-molds.md §1 で定めた6状態を並べる。
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { ListRow } from './ListRow'
import { Check } from '../constants/icons'

const meta: Meta<typeof ListRow> = {
  title: 'Components/ListRow',
  component: ListRow,
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof ListRow>

function DemoAvatar({ initial }: { initial: string }) {
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        borderRadius: '50%',
        background: 'var(--bg-hover)',
        color: 'var(--text-primary)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 'var(--font-base)',
        fontWeight: 'var(--font-weight-bold)',
      }}
    >
      {initial}
    </div>
  )
}

function UnreadBadge({ count }: { count: number }) {
  return (
    <span
      style={{
        background: 'var(--accent)',
        color: 'var(--on-accent)',
        borderRadius: 'var(--radius-xl)',
        padding: 'var(--space-1px) var(--space-6px)',
        fontSize: 'var(--font-2xs)',
        fontWeight: 'var(--font-weight-bold)',
      }}
    >
      {count}
    </span>
  )
}

export const WithAvatarUnread: Story = {
  name: '1. 画像あり・未読あり（受信箱の既定）',
  args: {
    avatar: <DemoAvatar initial="田" />,
    title: '田中 様',
    titleAside: '14:32',
    subtitle: 'ご注文ありがとうございます。発送は明日の予定です。',
    subtitleAside: <UnreadBadge count={3} />,
  },
}

export const WithAvatarRead: Story = {
  name: '2. 画像あり・未読なし',
  args: {
    avatar: <DemoAvatar initial="佐" />,
    title: '佐藤商事',
    titleAside: '昨日',
    subtitle: 'ありがとうございます。また次回もよろしくお願いします。',
  },
}

export const WithoutAvatar: Story = {
  name: '3. 画像なし（在庫表などで使う形）',
  args: {
    title: '腕時計 ROLEX Submariner',
    titleAside: '#SKU-10234',
    subtitle: '在庫: 2点 / 保管場所: A-12',
  },
}

export const WithSubtitleIcon: Story = {
  name: '4. 2行目に種類の印あり',
  args: {
    avatar: <DemoAvatar initial="鈴" />,
    title: '鈴木 一郎',
    titleAside: '10:05',
    subtitleIcon: <Check size={14} aria-hidden="true" />,
    subtitle: '既読になりました',
  },
}

export const Selected: Story = {
  name: '5. 選択中',
  args: {
    avatar: <DemoAvatar initial="高" />,
    title: '高橋 花子',
    titleAside: '09:48',
    subtitle: '来週の打ち合わせの件、承知いたしました。',
    selected: true,
  },
}

export const Truncated: Story = {
  name: '6. 文字が長くて切れる場合',
  args: {
    avatar: <DemoAvatar initial="長" />,
    title: '株式会社グローバルトレーディングインターナショナル 営業部 担当者',
    titleAside: '2026/10/11',
    subtitle: 'お見積りの件、添付資料をご確認のうえご返信いただけますと幸いです。よろしくお願いいたします。',
    subtitleAside: <UnreadBadge count={12} />,
  },
}
