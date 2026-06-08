import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { SubMenu } from './SubMenu';
import type { SubMenuGroup } from './SubMenu';

const meta = {
  title: 'Components/SubMenu',
  component: SubMenu,
  tags: ['autodocs'],
  args: {
    // render 関数で useState に上書きされるため no-op で OK
    onChange: () => {},
    activeKey: 'leads',
  },
} satisfies Meta<typeof SubMenu>;

export default meta;
type Story = StoryObj<typeof meta>;

/* ─ 共通データ ─────────────────────────────────────────────────────────── */

const CRM_GROUPS: SubMenuGroup<string>[] = [
  {
    title: 'CRM',
    items: [
      { key: 'leads',     label: 'リード',     badge: 42 },
      { key: 'companies', label: '会社',       badge: 15 },
      { key: 'contacts',  label: '担当者',     badge: 8  },
    ],
  },
  {
    title: '分析',
    items: [
      { key: 'analytics', label: 'アナリティクス' },
      { key: 'reports',   label: 'レポート', disabled: true },
    ],
  },
];

const FLAT_ITEMS: SubMenuGroup<string>[] = [
  {
    items: [
      { key: 'dashboard', label: 'ダッシュボード', badge: 3  },
      { key: 'inbox',     label: '受信箱',         badge: 12 },
      { key: 'orders',    label: '受注管理'        },
      { key: 'schedule',  label: 'スケジュール'    },
      { key: 'settings',  label: '設定', disabled: true },
    ],
  },
];

/* ─ ストーリー ────────────────────────────────────────────────────────── */

/** grouped / 件数バッジ・disabled 含む（hub-subnav 系・標準） */
export const GroupedWithBadge: Story = {
  render: (args) => {
    const [active, setActive] = useState('leads');
    return <SubMenu {...args} activeKey={active} onChange={setActive} />;
  },
  args: {
    variant: 'grouped',
    groups: CRM_GROUPS,
    activeKey: 'leads',
  },
};

/** flat / 件数バッジ・disabled 含む */
export const FlatWithBadge: Story = {
  render: (args) => {
    const [active, setActive] = useState('dashboard');
    return <SubMenu {...args} activeKey={active} onChange={setActive} />;
  },
  args: {
    variant: 'flat',
    groups: FLAT_ITEMS,
    activeKey: 'dashboard',
  },
};

/** grouped / 見出しなしグループ */
export const GroupedNoTitle: Story = {
  render: (args) => {
    const [active, setActive] = useState('leads');
    return <SubMenu {...args} activeKey={active} onChange={setActive} />;
  },
  args: {
    variant: 'grouped',
    groups: [
      { items: CRM_GROUPS[0].items },
      { items: CRM_GROUPS[1].items },
    ],
    activeKey: 'leads',
  },
};
