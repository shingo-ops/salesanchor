import { useEffect, type ReactNode } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { ThreeColumn } from './ThreeColumn';

function DarkFrame({ children }: { children: ReactNode }) {
  useEffect(() => {
    const previous = document.documentElement.classList.contains('force-dark');
    document.documentElement.classList.toggle('force-dark', true);
    return () => { document.documentElement.classList.toggle('force-dark', previous); };
  }, []);
  return <div style={{ background: 'var(--bg-primary)', padding: 'var(--space-4)' }}>{children}</div>;
}

const meta = {
  title: 'Components/ThreeColumn',
  component: ThreeColumn,
  tags: ['autodocs'],
  args: {
    gap: '4',
    align: 'start',
    children: [
      <div key="l">左の列</div>,
      <div key="c">中の列</div>,
      <div key="r">右の列</div>,
    ],
  },
} satisfies Meta<typeof ThreeColumn>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Stretch: Story = { args: { align: 'stretch' } };

export const Dark: Story = {
  decorators: [(Story) => <DarkFrame><Story /></DarkFrame>],
};

export const Narrow: Story = {
  globals: { viewport: { value: 'mobile1', isRotated: false } },
  parameters: { layout: 'padded' },
};
