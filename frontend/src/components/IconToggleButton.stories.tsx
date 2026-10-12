/**
 * IconToggleButton — ストーリーカタログ
 * 状態: 未押下 / 押下 / 件数つき / サイズ / 無効 / バッジ（他者のみ・自分あり）
 */
import { useState, type ComponentProps } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { IconToggleButton } from './IconToggleButton';
import { INBOX_ACTION_ICONS } from '../constants/icons';

const meta = {
  title: 'Components/IconToggleButton',
  component: IconToggleButton,
  tags: ['autodocs'],
  parameters: { layout: 'centered' },
  args: {
    pressed: false,
    onClick: () => {},
    iconOff: INBOX_ACTION_ICONS.heart,
    iconOn: INBOX_ACTION_ICONS.heartFilled,
    'aria-label': 'Toggle',
    size: 'sm',
  },
} satisfies Meta<typeof IconToggleButton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Off: Story = {};

export const On: Story = { args: { pressed: true } };

export const WithCount: Story = { args: { pressed: true, count: 3 } };

/** badge: 他者だけがハートを付けた状態（赤の塗り＋件数・枠なし） */
export const BadgeOthersOnly: Story = { args: { variant: 'badge', pressed: false, count: 2 } };

/** badge: 自分も付けた状態（赤の塗り＋件数・枠と背景で区別） */
export const BadgeMine: Story = { args: { variant: 'badge', pressed: true, count: 3 } };

export const Disabled: Story = { args: { disabled: true } };

export const Sizes: Story = {
  render: (args) => (
    <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
      <IconToggleButton {...args} size="sm" />
      <IconToggleButton {...args} size="md" />
    </div>
  ),
};

/** クリックで押下状態が切り替わる例（呼び出し側が state を持つ） */
function InteractiveDemo(args: ComponentProps<typeof IconToggleButton>) {
  const [pressed, setPressed] = useState(false);
  return (
    <IconToggleButton
      {...args}
      pressed={pressed}
      count={pressed ? 1 : 0}
      onClick={() => setPressed((p) => !p)}
    />
  );
}

export const Interactive: Story = {
  render: (args) => <InteractiveDemo {...args} />,
};
