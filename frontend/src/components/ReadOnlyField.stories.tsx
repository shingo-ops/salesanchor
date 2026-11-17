import { useEffect, type ReactNode } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { ReadOnlyField } from './ReadOnlyField';

function DarkFrame({ children }: { children: ReactNode }) {
  useEffect(() => {
    const previous = document.documentElement.classList.contains('force-dark');
    document.documentElement.classList.toggle('force-dark', true);
    return () => { document.documentElement.classList.toggle('force-dark', previous); };
  }, []);
  return <div style={{ background: 'var(--bg-primary)', padding: 'var(--space-4)' }}>{children}</div>;
}

const meta = {
  title: 'Components/ReadOnlyField',
  component: ReadOnlyField,
  tags: ['autodocs'],
  args: {
    label: '受取人',
    value: 'Taro Yamada',
  },
} satisfies Meta<typeof ReadOnlyField>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Empty: Story = { args: { value: '' } };

export const MultiLine: Story = { args: { label: '住所1', value: '1-2-3 Shibuya\nShibuya-ku' } };

export const Dark: Story = {
  decorators: [(Story) => <DarkFrame><Story /></DarkFrame>],
};

export const DarkEmpty: Story = {
  args: { value: null },
  decorators: [(Story) => <DarkFrame><Story /></DarkFrame>],
};

export const Narrow: Story = {
  globals: { viewport: { value: 'mobile1', isRotated: false } },
  parameters: { layout: 'padded' },
};
