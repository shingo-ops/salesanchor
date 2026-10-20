import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { Tabs } from './Tabs';
import type { TabItem } from './Tabs';
import { SelectControl } from './Select';
import { DataTable } from './DataTable';

const meta = {
  title: 'Components/Tabs',
  component: Tabs,
  tags: ['autodocs'],
  args: {
    // render 関数で useState に上書きされるため no-op で OK
    onChange: () => {},
  },
} satisfies Meta<typeof Tabs>;

export default meta;
type Story = StoryObj<typeof meta>;

/* ─ 共通データ ─────────────────────────────────────────────────────────── */

const THREE_TABS: TabItem<string>[] = [
  { key: 'deal',    label: '商談'    },
  { key: 'company', label: '会社'    },
  { key: 'contact', label: '担当者' },
];

const SIX_TABS: TabItem<string>[] = [
  { key: 'all',      label: 'すべて',     count: 128 },
  { key: 'lead',     label: 'リード',     count: 42  },
  { key: 'deal',     label: '商談',       count: 21  },
  { key: 'existing', label: '既存顧客',   count: 35  },
  { key: 'followup', label: 'フォロー',   count: 18  },
  { key: 'archive',  label: 'アーカイブ', count: 12  },
];

/* ─ ストーリー ────────────────────────────────────────────────────────── */

/** underline / md（right-panel-tab 系・既定） */
export const UnderlineMd: Story = {
  render: (args) => {
    const [active, setActive] = useState('deal');
    return <Tabs {...args} activeKey={active} onChange={setActive} />;
  },
  args: {
    items: THREE_TABS,
    activeKey: 'deal',
    variant: 'underline',
    size: 'md',
  },
};

/** underline / sm（KartePanel 向け） */
export const UnderlineSm: Story = {
  render: (args) => {
    const [active, setActive] = useState('deal');
    return <Tabs {...args} activeKey={active} onChange={setActive} />;
  },
  args: {
    items: THREE_TABS,
    activeKey: 'deal',
    variant: 'underline',
    size: 'sm',
  },
};

/** pill / md（inbox-full-tab-bar 系） */
export const PillMd: Story = {
  render: (args) => {
    const [active, setActive] = useState('all');
    return <Tabs {...args} activeKey={active} onChange={setActive} />;
  },
  args: {
    items: SIX_TABS,
    activeKey: 'all',
    variant: 'pill',
    size: 'md',
  },
};

/** 件数バッジ付き underline */
export const WithCounts: Story = {
  render: (args) => {
    const [active, setActive] = useState('all');
    return <Tabs {...args} activeKey={active} onChange={setActive} />;
  },
  args: {
    items: SIX_TABS,
    activeKey: 'all',
    variant: 'underline',
    size: 'md',
  },
};

/** disabled 状態 */
export const WithDisabled: Story = {
  render: (args) => {
    const [active, setActive] = useState('deal');
    return <Tabs {...args} activeKey={active} onChange={setActive} />;
  },
  args: {
    items: [
      { key: 'deal',    label: '商談'           },
      { key: 'company', label: '会社'            },
      { key: 'contact', label: '担当者 (未対応)', disabled: true },
    ],
    activeKey: 'deal',
    variant: 'underline',
    size: 'md',
  },
};

/** 横スクロール（6タブ / 375px幅相当） */
export const ScrollablePill: Story = {
  render: (args) => {
    const [active, setActive] = useState('all');
    return (
      <div style={{ width: 320, overflow: 'hidden' }}>
        <Tabs {...args} activeKey={active} onChange={setActive} />
      </div>
    );
  },
  args: {
    items: SIX_TABS,
    activeKey: 'all',
    variant: 'pill',
    size: 'md',
  },
};

/** 表にくっつけた形（在庫表・閲覧ページ）。extra=「その他」プルダウン、end=注記、DataTable attachedTop */
export const AttachedToTable: Story = {
  name: 'その他プルダウンと注記つき・表にくっつけた',
  render: (args) => {
    const [active, setActive] = useState('pokemon');
    const [other, setOther] = useState('');
    const activeKey = other !== '' ? '' : active;
    return (
      <div data-testid="attached-demo">
        <Tabs
          {...args}
          activeKey={activeKey}
          onChange={(k) => { setOther(''); setActive(k); }}
          extra={
            <SelectControl
              variant="tab"
              aria-label="その他"
              data-testid="attached-other"
              value={other}
              onChange={(e) => setOther(e.target.value)}
              options={[
                { value: '', label: 'その他' },
                { value: 'hololive', label: 'ホロライブ' },
              ]}
            />
          }
          end={<p data-testid="attached-note" style={{ margin: 0 }}>注記</p>}
        />
        <DataTable
          attachedTop
          columns={[{ key: 'name', header: '商品名', renderCell: (r: { id: string; name: string }) => r.name }]}
          data={[{ id: '1', name: 'サンプル' }]}
          rowKey={(r) => r.id}
        />
      </div>
    );
  },
  args: {
    items: [
      { key: 'all', label: 'すべて' },
      { key: 'pokemon', label: 'ポケモン' },
      { key: 'one_piece', label: 'ワンピース' },
    ],
    activeKey: 'pokemon',
    variant: 'underline',
    size: 'md',
  },
};
