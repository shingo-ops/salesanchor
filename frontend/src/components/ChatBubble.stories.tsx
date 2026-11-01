import type { Meta, StoryObj } from '@storybook/react-vite';
import { ChatBubble } from './ChatBubble';

const meta = {
  title: 'Components/ChatBubble',
  component: ChatBubble,
  tags: ['autodocs'],
  args: {
    side: 'assistant',
    children: 'ここに返事が入ります。',
  },
} satisfies Meta<typeof ChatBubble>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Assistant: Story = {};

export const User: Story = { args: { side: 'user', children: 'ここに質問が入ります。' } };

export const Sending: Story = { args: { side: 'user', status: 'sending' } };

export const ErrorState: Story = { args: { side: 'assistant', status: 'error', children: '失敗しました。' } };
