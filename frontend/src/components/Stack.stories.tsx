import type { Meta, StoryObj } from '@storybook/react-vite';
import { Stack } from './Stack';

const meta = {
  title: 'Components/Stack',
  component: Stack,
  tags: ['autodocs'],
  args: {
    gap: '3',
    children: [
      <div key="a">1段目</div>,
      <div key="b">2段目</div>,
      <div key="c">3段目</div>,
    ],
  },
} satisfies Meta<typeof Stack>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Narrow: Story = { args: { gap: '1' } };

export const Wide: Story = { args: { gap: '6' } };
