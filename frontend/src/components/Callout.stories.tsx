import type { Meta, StoryObj } from '@storybook/react-vite';
import { Callout } from './Callout';

const meta = {
  title: 'Components/Callout',
  component: Callout,
  tags: ['autodocs'],
  args: {
    title: 'タイトル',
    children: '本文がここに入ります。',
    variant: 'warning',
  },
} satisfies Meta<typeof Callout>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Warning: Story = {};

export const Info: Story = { args: { variant: 'info' } };

export const WithoutBody: Story = { args: { children: undefined } };
