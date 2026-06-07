/**
 * Card — デザイントークンカタログ (ADR-067 / Task 1C)
 *
 * 標準カード金型の全バリアント・密度確認。
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { Card } from './Card'

const meta: Meta<typeof Card> = {
  title: 'Components/Card',
  component: Card,
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof Card>

export const Container: Story = {
  name: 'container — 汎用コンテナ',
  args: {
    variant: 'container',
    children: (
      <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: 'var(--font-sm)' }}>
        padding: 24px (--comp-card-padding) / radius: 8px (--comp-card-radius)
      </p>
    ),
  },
}

export const Interactive: Story = {
  name: 'interactive — クリック可能カード',
  args: {
    variant: 'interactive',
    children: (
      <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: 'var(--font-sm)' }}>
        hover: shadow-md + translateY(-1px)
      </p>
    ),
  },
}

export const Metric: Story = {
  name: 'metric — 指標カード（上部アクセント）',
  args: {
    variant: 'metric',
    children: (
      <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: 'var(--font-sm)' }}>
        border-top: 3px solid var(--accent)
      </p>
    ),
  },
}

export const Compact: Story = {
  name: 'compact 密度 — 16px padding',
  args: {
    variant: 'container',
    density: 'compact',
    children: (
      <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: 'var(--font-sm)' }}>
        padding: 16px (--comp-card-padding-compact)
      </p>
    ),
  },
}

export const GridLayout: Story = {
  name: 'グリッドレイアウト (gap 検証)',
  render: () => (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--comp-card-gap)' }}>
      {['Card A', 'Card B', 'Card C'].map((label) => (
        <Card key={label} variant="container">
          <p style={{ margin: 0, fontWeight: 'var(--font-weight-semi)', color: 'var(--text-primary)' }}>{label}</p>
          <p style={{ margin: '4px 0 0', fontSize: 'var(--font-xs)', color: 'var(--text-secondary)' }}>
            gap: var(--comp-card-gap) = 24px
          </p>
        </Card>
      ))}
    </div>
  ),
}
