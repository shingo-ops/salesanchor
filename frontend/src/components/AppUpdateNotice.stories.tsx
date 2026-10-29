import type { Meta, StoryObj } from '@storybook/react-vite';
import { AppUpdateNoticeView } from './AppUpdateNotice';

const meta = {
  title: 'Components/AppUpdateNotice',
  component: AppUpdateNoticeView,
  tags: ['autodocs'],
  args: {
    message: 'A new version is available',
    reloadLabel: 'Reload',
    onReload: () => undefined,
  },
} satisfies Meta<typeof AppUpdateNoticeView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
