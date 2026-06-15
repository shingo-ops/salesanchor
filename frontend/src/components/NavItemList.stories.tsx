/**
 * NavItemList — 共通 nav item 描画コンポーネント (ADR-137)
 *
 * DesktopShell / MobileShell が共通利用する純粋描画コンポーネント。
 * MemoryRouter 必須。
 */
import type { Meta, StoryObj } from '@storybook/react-vite';
import { MemoryRouter } from 'react-router-dom';
import { NavItemList } from './NavItemList';
import type { ResolvedNavItem } from './NavItemList';
import { NAV_ICONS } from '../constants/icons';
import { ICON } from '../constants/iconSizes';

const SAMPLE_ITEMS: ResolvedNavItem[] = [
  {
    key: 'dashboard',
    labelKey: 'nav.dashboard',
    icon: <NAV_ICONS.dashboard size={ICON.base} />,
    path: '/',
  },
  {
    key: 'leads',
    labelKey: 'nav.leads',
    icon: <NAV_ICONS.leads size={ICON.base} />,
    path: '/leads',
    unread: true,
  },
  {
    key: 'more',
    labelKey: 'nav.more',
    icon: <NAV_ICONS.more size={ICON.base} />,
    path: '/more',
    children: [
      { key: 'faq', labelKey: 'nav.faq', icon: <NAV_ICONS.help size={ICON.base} />, path: '/faq' },
      { key: 'settings', labelKey: 'nav.settings', icon: <NAV_ICONS.settings size={ICON.base} />, path: '/settings' },
    ],
  },
];

const meta: Meta<typeof NavItemList> = {
  title: 'Components/NavItemList',
  component: NavItemList,
  decorators: [
    (Story) => (
      <MemoryRouter>
        <div style={{ padding: 'var(--space-4)', background: 'var(--bg-sidebar, var(--bg-primary))', width: '240px' }}>
          <Story />
        </div>
      </MemoryRouter>
    ),
  ],
  tags: ['autodocs'],
  args: {
    items: SAMPLE_ITEMS,
    onNavClick: () => {},
    variant: 'desktop',
    unreadCount: 3,
  },
};
export default meta;

type Story = StoryObj<typeof meta>;

export const Desktop: Story = {
  name: 'Desktop variant',
  args: { variant: 'desktop' },
};

export const Mobile: Story = {
  name: 'Mobile variant',
  args: { variant: 'mobile' },
};

export const NoUnread: Story = {
  name: '未読なし',
  args: { unreadCount: 0 },
};
