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
    // eslint-disable-next-line react-hooks/rules-of-hooks
    const [sortKey, setSortKey] = useState<string>('name');
    // eslint-disable-next-line react-hooks/rules-of-hooks
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
    // eslint-disable-next-line react-hooks/rules-of-hooks
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
