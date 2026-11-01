import type { Meta, StoryObj } from '@storybook/react-vite';
import { FloatingActionButton } from './FloatingActionButton';
import { LeadChatIcon } from '../constants/icons';

const meta = {
  title: 'Components/FloatingActionButton',
  component: FloatingActionButton,
  tags: ['autodocs'],
  args: {
    icon: <LeadChatIcon />,
    label: '相談する',
  },
} satisfies Meta<typeof FloatingActionButton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const WithBadge: Story = { args: { badge: 3 } };

export const AboveTabbar: Story = { args: { aboveTabbar: true } };
