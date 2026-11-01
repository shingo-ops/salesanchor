/**
 * ChatBubble — ストーリーカタログ
 * 状態: 受信 / 送信 / 送れなかった / 長い本文（折り返し）/ 時刻の行にボタンが入る形
 *       / panel（秘書のチャット）: AI / 利用者 / 送信中 / エラー / 広い吹き出し
 */
import type { Meta, StoryObj } from '@storybook/react-vite';
import { ChatBubble } from './ChatBubble';

const meta = {
  title: 'Components/ChatBubble',
  component: ChatBubble,
  tags: ['autodocs'],
  parameters: { layout: 'centered' },
  args: {
    direction: 'inbound',
    time: '5 min ago',
    children: 'Hello, is this item still available?',
  },
} satisfies Meta<typeof ChatBubble>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Inbound: Story = {};

export const Outbound: Story = { args: { direction: 'outbound', children: 'Yes, it is available.' } };

export const Failed: Story = {
  args: { direction: 'outbound', failed: true, role: 'alert', children: 'This message could not be sent.' },
};

export const LongText: Story = {
  args: {
    children:
      'This is a very long message that should wrap onto several lines inside the bubble without overflowing the container around it, even when a long-unbroken-token-like-this-one-appears-in-the-text.',
  },
};

export const TimeWithButton: Story = {
  args: {
    time: (
      <>
        5 min ago
        <button type="button" aria-label="Translate">
          T
        </button>
      </>
    ),
  },
};

export const PanelAssistant: Story = {
  args: { layout: 'panel', direction: 'inbound', time: undefined, children: 'ここに返事が入ります。' },
};

export const PanelUser: Story = {
  args: { layout: 'panel', direction: 'outbound', time: undefined, children: 'ここに質問が入ります。' },
};

export const PanelSending: Story = {
  args: { layout: 'panel', direction: 'outbound', pending: true, time: undefined },
};

export const PanelError: Story = {
  args: { layout: 'panel', direction: 'inbound', failed: true, time: undefined, children: '失敗しました。' },
};

export const PanelWide: Story = {
  args: {
    layout: 'panel',
    direction: 'inbound',
    wide: true,
    time: undefined,
    children: 'A wide bubble for a draft form.',
  },
};
