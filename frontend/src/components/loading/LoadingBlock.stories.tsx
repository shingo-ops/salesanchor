import type { Meta, StoryObj } from '@storybook/react-vite';
import { LoadingBlock } from './LoadingBlock';

const meta = {
  title: 'Components/LoadingBlock',
  component: LoadingBlock,
  tags: ['autodocs'],
} satisfies Meta<typeof LoadingBlock>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Small: Story = { args: { size: 'sm' } };

export const Inline: Story = { args: { inline: true } };

export const CustomLabel: Story = { args: { label: 'Loading orders...' } };
