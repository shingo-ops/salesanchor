import type { Meta, StoryObj } from '@storybook/react-vite';
import { EmptyState } from './EmptyState';
import { Button } from './Button';
import { PAGE_ICONS, NAV_ICONS } from '../constants/icons';
import { ICON } from '../constants/iconSizes';

const meta = {
  title: 'Components/EmptyState',
  component: EmptyState,
  tags: ['autodocs'],
  args: {
    title: 'データがありません',
    size: 'default',
  },
} satisfies Meta<typeof EmptyState>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const WithIcon: Story = {
  args: {
    icon: <PAGE_ICONS.inboxEmpty size={ICON.xl} />,
    title: '受信箱は空です',
    description: '新しいメッセージが届くとここに表示されます。',
  },
};

export const WithAction: Story = {
  args: {
    icon: <NAV_ICONS.leads size={ICON.xl} />,
    title: 'リードがありません',
    description: '最初のリードを登録して営業活動を始めましょう。',
    action: <Button variant="primary">リードを追加</Button>,
  },
};

export const Compact: Story = {
  args: {
    icon: <NAV_ICONS.search size={ICON.lg} />,
    title: '検索結果なし',
    description: '検索条件を変えてお試しください。',
    size: 'compact',
  },
};

export const CompactMinimal: Story = {
  args: {
    title: 'データがありません',
    size: 'compact',
  },
};
