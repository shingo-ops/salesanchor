import { useEffect, type ReactNode } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { SectionCard } from './SectionCard';
import { Button } from './Button';

function DarkFrame({ children }: { children: ReactNode }) {
  useEffect(() => {
    const previous = document.documentElement.classList.contains('force-dark');
    document.documentElement.classList.toggle('force-dark', true);
    return () => { document.documentElement.classList.toggle('force-dark', previous); };
  }, []);
  return <div style={{ background: 'var(--bg-primary)', padding: 'var(--space-4)' }}>{children}</div>;
}

const meta = {
  title: 'Components/SectionCard',
  component: SectionCard,
  tags: ['autodocs'],
  args: {
    title: '発送先',
    actions: <Button variant="secondary" size="sm">編集</Button>,
    children: <p>カードの中身</p>,
  },
} satisfies Meta<typeof SectionCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const WithoutActions: Story = { args: { actions: undefined } };

export const Dark: Story = {
  decorators: [(Story) => <DarkFrame><Story /></DarkFrame>],
};

export const Narrow: Story = {
  globals: { viewport: { value: 'mobile1', isRotated: false } },
  parameters: { layout: 'padded' },
};
