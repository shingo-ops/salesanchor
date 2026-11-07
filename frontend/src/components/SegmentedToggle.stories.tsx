/**
 * SegmentedToggle — ストーリーカタログ
 * 状態: 3択 / 2択 / どれも選ばれていない / 押せない
 */
import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { SegmentedToggle, type SegmentedOption } from './SegmentedToggle';
import { SlashOutline, STATUS_ICONS } from '../constants/icons';

type Three = 'a' | 'b' | 'c';
type Two = 'a' | 'c';

const THREE: SegmentedOption<Three>[] = [
  { value: 'a', icon: STATUS_ICONS.error, label: 'Hidden', tone: 'danger' },
  { value: 'b', icon: SlashOutline, label: 'View only', tone: 'neutral' },
  { value: 'c', icon: STATUS_ICONS.check, label: 'Can edit', tone: 'success' },
];

const TWO: SegmentedOption<Two>[] = [
  { value: 'a', icon: STATUS_ICONS.error, label: 'Deny', tone: 'danger' },
  { value: 'c', icon: STATUS_ICONS.check, label: 'Allow', tone: 'success' },
];

const meta = {
  title: 'Components/SegmentedToggle',
  component: SegmentedToggle,
  tags: ['autodocs'],
  parameters: { layout: 'centered' },
  args: { options: THREE, value: 'b', onChange: () => {}, 'aria-label': 'Row' },
} satisfies Meta<typeof SegmentedToggle>;

export default meta;
type Story = StoryObj<typeof meta>;

function ThreeDemo({ initial, disabled }: { initial: Three | null; disabled?: boolean }) {
  const [value, setValue] = useState<Three | null>(initial);
  return (
    <SegmentedToggle options={THREE} value={value} onChange={setValue} aria-label="Row" disabled={disabled} />
  );
}

function TwoDemo() {
  const [value, setValue] = useState<Two | null>('a');
  return <SegmentedToggle options={TWO} value={value} onChange={setValue} aria-label="Row" />;
}

/** 3択（✕ ／ ✓） */
export const ThreeChoices: Story = { render: () => <ThreeDemo initial="b" /> };

/** 2択（✕ ✓） */
export const TwoChoices: Story = { render: () => <TwoDemo /> };

/** どれも選ばれていない（value=null） */
export const NoneSelected: Story = { render: () => <ThreeDemo initial={null} /> };

/** 全体が押せない */
export const Disabled: Story = { render: () => <ThreeDemo initial="c" disabled /> };
