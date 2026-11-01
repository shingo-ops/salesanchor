/**
 * ChatBubble — ストーリーカタログ
 * 状態: 受信 / 送信 / 送れなかった / 長い本文（折り返し）/ 時刻の行にボタンが入る形
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
