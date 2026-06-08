import type { Meta, StoryObj } from '@storybook/react-vite';
import { Badge } from './Badge';

const meta = {
  title: 'Components/Badge',
  component: Badge,
  tags: ['autodocs'],
  args: {
    children: 'ラベル',
    variant: 'neutral',
    appearance: 'soft',
    size: 'md',
  },
} satisfies Meta<typeof Badge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const AllVariantsSoft: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
      <Badge variant="neutral"  appearance="soft">neutral</Badge>
      <Badge variant="info"     appearance="soft">info</Badge>
      <Badge variant="success"  appearance="soft">success</Badge>
      <Badge variant="warning"  appearance="soft">warning</Badge>
      <Badge variant="danger"   appearance="soft">danger</Badge>
    </div>
  ),
};

export const AllVariantsSolid: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
      <Badge variant="neutral"  appearance="solid">neutral</Badge>
      <Badge variant="info"     appearance="solid">info</Badge>
      <Badge variant="success"  appearance="solid">success</Badge>
      <Badge variant="warning"  appearance="solid">warning</Badge>
      <Badge variant="danger"   appearance="solid">danger</Badge>
    </div>
  ),
};

export const Sizes: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
      <Badge variant="success" size="sm">sm</Badge>
      <Badge variant="success" size="md">md</Badge>
    </div>
  ),
};

export const WithDot: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
      <Badge variant="success" dot>対応済み</Badge>
      <Badge variant="warning" dot>保留中</Badge>
      <Badge variant="danger"  dot>要対応</Badge>
      <Badge variant="info"    dot>処理中</Badge>
    </div>
  ),
};
