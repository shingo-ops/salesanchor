import { useEffect, type ReactNode } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { TotalsBox } from './TotalsBox';

function DarkFrame({ children }: { children: ReactNode }) {
  useEffect(() => {
    const previous = document.documentElement.classList.contains('force-dark');
    document.documentElement.classList.toggle('force-dark', true);
    return () => { document.documentElement.classList.toggle('force-dark', previous); };
  }, []);
  return <div style={{ background: 'var(--bg-primary)', padding: 'var(--space-4)' }}>{children}</div>;
}

const meta = {
  title: 'Components/TotalsBox',
  component: TotalsBox,
  tags: ['autodocs'],
  args: {
    rows: [
      { key: 'subtotal', label: '小計', value: 'USD 1,200.00' },
      { key: 'shipping', label: '送料', value: 'USD 45.00' },
      { key: 'tax', label: '税または関税', value: 'USD 0.00' },
    ],
    total: { label: '合計', value: 'USD 1,245.00' },
  },
} satisfies Meta<typeof TotalsBox>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Dark: Story = {
  decorators: [(Story) => <DarkFrame><Story /></DarkFrame>],
};

export const Narrow: Story = {
  globals: { viewport: { value: 'mobile1', isRotated: false } },
  parameters: { layout: 'padded' },
};
