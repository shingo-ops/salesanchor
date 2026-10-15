import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { DataTable } from './DataTable';
import type { DataTableColumn, SortDir } from './DataTable';
import { Badge } from './Badge';

// ── サンプルデータ ──────────────────────────────────────────────────────────
interface Lead {
  id: string;
  name: string;
  company: string;
  status: string;
  score: number;
}

const SAMPLE_LEADS: Lead[] = [
  { id: '1', name: '田中 一郎',   company: '株式会社A商事',   status: 'active',   score: 92 },
  { id: '2', name: '鈴木 花子',   company: 'B株式会社',       status: 'pending',  score: 75 },
  { id: '3', name: '佐藤 次郎',   company: 'Cコーポレーション', status: 'inactive', score: 40 },
  { id: '4', name: '伊藤 三郎',   company: 'D合同会社',       status: 'active',   score: 88 },
  { id: '5', name: '山田 美咲',   company: 'E株式会社',       status: 'pending',  score: 61 },
];

const STATUS_BADGE: Record<string, { variant: 'success' | 'warning' | 'neutral'; label: string }> = {
  active:   { variant: 'success', label: 'アクティブ' },
  pending:  { variant: 'warning', label: '保留中'     },
  inactive: { variant: 'neutral', label: '非アクティブ' },
};

const COLUMNS: DataTableColumn<Lead>[] = [
  { key: 'name',    header: '名前',     width: '160px', sortable: true },
  { key: 'company', header: '会社名',   sortable: true },
  {
    key: 'status',
    header: 'ステータス',
    width: '140px',
    renderCell: (row) => {
      const s = STATUS_BADGE[row.status] ?? { variant: 'neutral', label: row.status };
      return <Badge variant={s.variant} appearance="soft" size="sm">{s.label}</Badge>;
    },
  },
  { key: 'score', header: 'スコア', width: '80px', sortable: true },
];

// ── Meta ──────────────────────────────────────────────────────────────────────
const meta: Meta<typeof DataTable> = {
  title: 'Components/DataTable',
  component: DataTable,
  parameters: { layout: 'padded' },
};
export default meta;

type Story = StoryObj<typeof DataTable>;

// ── Stories ──────────────────────────────────────────────────────────────────

export const Default: Story = {
  render: () => (
    <DataTable<Lead>
      columns={COLUMNS}
      data={SAMPLE_LEADS}
      rowKey={(r) => r.id}
    />
  ),
};

export const WithSort: Story = {
  render: () => {
    const [sortKey, setSortKey] = useState<string>('name');
    const [sortDir, setSortDir] = useState<SortDir>('asc');

    const sorted = [...SAMPLE_LEADS].sort((a, b) => {
      const av = (a as unknown as Record<string, unknown>)[sortKey];
      const bv = (b as unknown as Record<string, unknown>)[sortKey];
      const cmp = String(av).localeCompare(String(bv), 'ja');
      return sortDir === 'asc' ? cmp : -cmp;
    });

    return (
      <DataTable<Lead>
        columns={COLUMNS}
        data={sorted}
        rowKey={(r) => r.id}
        sortKey={sortKey}
        sortDir={sortDir}
        onSort={(k, d) => { setSortKey(k); setSortDir(d); }}
      />
    );
  },
};

export const WithSelection: Story = {
  render: () => {
    const [selected, setSelected] = useState<Set<string>>(new Set(['1', '3']));

    return (
      <DataTable<Lead>
        columns={COLUMNS}
        data={SAMPLE_LEADS}
        rowKey={(r) => r.id}
        selectable
        selectedKeys={selected}
        onSelectChange={setSelected}
      />
    );
  },
};

export const DensityCompact: Story = {
  render: () => (
    <DataTable<Lead>
      columns={COLUMNS}
      data={SAMPLE_LEADS}
      rowKey={(r) => r.id}
      density="compact"
    />
  ),
};

export const DensityRelaxed: Story = {
  render: () => (
    <DataTable<Lead>
      columns={COLUMNS}
      data={SAMPLE_LEADS}
      rowKey={(r) => r.id}
      density="relaxed"
    />
  ),
};

interface LongRow {
  id: string
  name: string
  reason: string
  note: string
}

const LONG_ROWS: LongRow[] = [
  {
    id: '1',
    name: 'ポケモンカードゲーム スカーレット&バイオレット 拡張パック 超電ブレイカー BOX シュリンク付き 未開封 日本語版',
    reason: '商品IDが決まらない、数量が読み取れない、価格の桁が不自然',
    note: '短い',
  },
  { id: '2', name: '短い商品名', reason: '理由', note: '短い' },
  {
    id: '3',
    name: 'ONE PIECEカードゲーム 新時代の主役 ブースターパック OP-05 カートン 12BOX入り',
    reason: '状態が決まらない、出どころが複数ある',
    note: '短い',
  },
]

const LONG_COLUMNS: DataTableColumn<LongRow>[] = [
  { key: 'name', header: '商品名', width: 'var(--col-width-wide)', ellipsis: true },
  { key: 'reason', header: '理由', width: 'var(--col-width-medium)', ellipsis: true },
  { key: 'note', header: '備考' },
]

/** ellipsis 列: 長い文字は1行（44px）に収まり末尾が …。マウスを当てると全文（title） */
export const Ellipsis: Story = {
  render: () => (
    <DataTable<LongRow>
      columns={LONG_COLUMNS}
      data={LONG_ROWS}
      rowKey={(r) => r.id}
    />
  ),
}

export const EmptyState: Story = {
  render: () => (
    <DataTable<Lead>
      columns={COLUMNS}
      data={[]}
      rowKey={(r) => r.id}
      emptyState={<span>該当するデータがありません</span>}
    />
  ),
};

// ── 便1: 見出し固定・縮小・カード表示 ───────────────────────────────────────
interface WideRow {
  id: string
  name: string
  price: number
  a: string
  b: string
  c: string
  d: string
}

const WIDE_ROWS: WideRow[] = Array.from({ length: 30 }, (_, i) => ({
  id: String(i + 1),
  name: `商品サンプル ${i + 1}`,
  price: 1000 * (i + 1),
  a: '横に長い列のサンプル文字列',
  b: '横に長い列のサンプル文字列',
  c: '横に長い列のサンプル文字列',
  d: '横に長い列のサンプル文字列',
}))

const WIDE_COLUMNS: DataTableColumn<WideRow>[] = [
  { key: 'name', header: '商品名', width: '200px', stickyLeft: true, mobileOrder: 1 },
  { key: 'price', header: '価格', width: '120px', align: 'right', mobileOrder: 2 },
  { key: 'a', header: '列A', width: '240px' },
  { key: 'b', header: '列B', width: '240px', mobileHidden: true },
  { key: 'c', header: '列C', width: '240px', mobileLabel: 'C' },
  { key: 'd', header: '列D', width: '240px' },
]

/** 見出し固定＋先頭列固定（縦横にスクロールしても見出しと商品名が残る） */
export const StickyHeader: Story = {
  render: () => (
    <DataTable<WideRow>
      columns={WIDE_COLUMNS}
      data={WIDE_ROWS}
      rowKey={(r) => r.id}
      stickyHeader
      selectable
    />
  ),
}

/** 枠の幅に合わせて表を縮める（768px 以上） */
export const FitToWidth: Story = {
  render: () => (
    <DataTable<WideRow>
      columns={WIDE_COLUMNS}
      data={WIDE_ROWS}
      rowKey={(r) => r.id}
      stickyHeader
      fitToWidth
    />
  ),
}

/** スマホ幅（767px 以下）でカード表示。Storybook の画面幅を狭めて確認する */
export const MobileCards: Story = {
  render: () => (
    <DataTable<WideRow>
      columns={WIDE_COLUMNS}
      data={WIDE_ROWS.slice(0, 5)}
      rowKey={(r) => r.id}
      mobileCards
      rowTestId={(r) => `row-${r.id}`}
    />
  ),
}
