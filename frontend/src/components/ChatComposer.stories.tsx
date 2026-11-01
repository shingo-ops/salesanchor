/**
 * ChatComposer — ストーリーカタログ
 * 状態: 空 / 文字あり / 添付なし / trailing あり / 送信が押せない
 */
import type { Meta, StoryObj } from '@storybook/react-vite';
import { ChatComposer } from './ChatComposer';
import { INBOX_ACTION_ICONS } from '../constants/icons';

const meta = {
  title: 'Components/ChatComposer',
  component: ChatComposer,
  tags: ['autodocs'],
  parameters: { layout: 'padded' },
  args: {
    leading: <div style={{ width: 36, height: 36 }}>Me</div>,
    input: <input aria-label="Message" placeholder="Type a message" style={{ flex: 1, border: 'none', background: 'transparent' }} />,
    attach: { icon: INBOX_ACTION_ICONS.attach, label: 'Attach image', onClick: () => {} },
    send: { icon: INBOX_ACTION_ICONS.send, label: 'Send', title: 'Send', onClick: () => {} },
  },
} satisfies Meta<typeof ChatComposer>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Empty: Story = {};

export const WithText: Story = {
  args: {
    input: <input aria-label="Message" defaultValue="hello" style={{ flex: 1, border: 'none', background: 'transparent' }} />,
  },
};

export const NoAttach: Story = { args: { attach: undefined } };

export const WithTrailing: Story = {
  args: { trailing: <button type="button">EN</button> },
};

export const SendDisabled: Story = {
  args: { send: { icon: INBOX_ACTION_ICONS.send, label: 'Send', title: 'Send', onClick: () => {}, disabled: true } },
};
