import type { Meta, StoryObj } from '@storybook/react-vite';
import { TwoColumn } from './TwoColumn';

const meta = {
  title: 'Components/TwoColumn',
  component: TwoColumn,
  tags: ['autodocs'],
  args: {
    ratio: '1:2',
    gap: '3',
    align: 'start',
    children: [
      <div key="l">左の列</div>,
      <div key="r">右の列（左の2倍の幅）</div>,
    ],
  },
} satisfies Meta<typeof TwoColumn>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Equal: Story = { args: { ratio: '1:1' } };

export const CenterAligned: Story = { args: { align: 'center' } };
