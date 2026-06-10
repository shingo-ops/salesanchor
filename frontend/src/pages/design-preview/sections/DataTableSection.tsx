/**
 * §9 データテーブル (DataTable)
 * ソート・行選択・density 3種・空状態・onRowClick・ページ送りの目視確認。
 */
import { useState } from "react";
import { DataTable } from "../../../components/DataTable";
import type { DataTableColumn, SortDir } from "../../../components/DataTable";
import { Badge } from "../../../components/Badge";
import { SectionHeader } from "./_shared";

interface DemoLead {
  id: string;
  name: string;
  company: string;
  status: string;
  score: number;
}

const DEMO_LEADS: DemoLead[] = [
  { id: "1", name: "田中 一郎",   company: "株式会社A商事",     status: "対応済み", score: 92 },
  { id: "2", name: "鈴木 花子",   company: "B株式会社",         status: "保留中",   score: 75 },
  { id: "3", name: "佐藤 次郎",   company: "Cコーポレーション", status: "未対応",   score: 40 },
  { id: "4", name: "伊藤 三郎",   company: "D合同会社",         status: "対応済み", score: 88 },
  { id: "5", name: "山田 美咲",   company: "E株式会社",         status: "保留中",   score: 61 },
];

const STATUS_VARIANT: Record<string, "success" | "warning" | "danger" | "neutral"> = {
  "対応済み": "success",
  "保留中":   "warning",
  "未対応":   "danger",
};

const DEMO_COLUMNS: DataTableColumn<DemoLead>[] = [
  { key: "name",    header: "名前",     width: "140px", sortable: true },
  { key: "company", header: "会社名",   sortable: true },
  {
    key: "status",
    header: "ステータス",
    width: "120px",
    renderCell: (row) => (
      <Badge variant={STATUS_VARIANT[row.status] ?? "neutral"} appearance="soft" size="sm">
        {row.status}
      </Badge>
    ),
  },
  { key: "score", header: "スコア", width: "72px", sortable: true },
];

const DEMO_PAGE_SIZE = 2;

export function DataTableSection() {
  const [sortKey,  setSortKey]  = useState<string>("name");
  const [sortDir,  setSortDir]  = useState<SortDir>("asc");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [density,  setDensity]  = useState<"compact" | "default" | "relaxed">("default");

  // step-2: onRowClick
  const [lastClicked, setLastClicked] = useState<DemoLead | null>(null);

  // step-2: 制御型ページ送り
  const [demoPage, setDemoPage] = useState(1);
  const demoPageData = DEMO_LEADS.slice((demoPage - 1) * DEMO_PAGE_SIZE, demoPage * DEMO_PAGE_SIZE);
  const demoHasNext = demoPage * DEMO_PAGE_SIZE < DEMO_LEADS.length;

  const sorted = [...DEMO_LEADS].sort((a, b) => {
    const av = (a as unknown as Record<string, unknown>)[sortKey];
    const bv = (b as unknown as Record<string, unknown>)[sortKey];
    const cmp = String(av).localeCompare(String(bv), "ja");
    return sortDir === "asc" ? cmp : -cmp;
  });

  return (
    <section className="dp-section">
      <SectionHeader
        title="9. データテーブル (DataTable)"
        desc="ソート・行選択・density 3種・空状態の目視確認。"
      />

      {/* density 切り替え */}
      <div className="dp-row">
        <span className="dp-row-label">density</span>
        <div className="dp-row-items">
          {(["compact", "default", "relaxed"] as const).map((d) => (
            <button
              key={d}
              type="button"
              className={`dp-band-btn${density === d ? " dp-band-btn--active" : ""}`}
              onClick={() => setDensity(d)}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      {/* テーブル本体 */}
      <DataTable<DemoLead>
        columns={DEMO_COLUMNS}
        data={sorted}
        rowKey={(r) => r.id}
        sortKey={sortKey}
        sortDir={sortDir}
        onSort={(k, d) => { setSortKey(k); setSortDir(d); }}
        selectable
        selectedKeys={selected}
        onSelectChange={setSelected}
        density={density}
        emptyState={<span>データがありません</span>}
      />

      {/* 空状態 */}
      <div className="dp-row">
        <span className="dp-row-label">empty</span>
        <div className="dp-row-items dp-row-items--full">
          <DataTable<DemoLead>
            columns={DEMO_COLUMNS}
            data={[]}
            rowKey={(r) => r.id}
            emptyState={<span>該当するデータがありません</span>}
          />
        </div>
      </div>

      {/* step-2: onRowClick */}
      <div className="dp-row">
        <span className="dp-row-label">onRowClick</span>
        <div className="dp-row-items dp-row-items--full">
          <p style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-2)" }}>
            最後にクリック:{" "}
            <strong>{lastClicked ? lastClicked.name : "（なし）"}</strong>
          </p>
          <DataTable<DemoLead>
            columns={DEMO_COLUMNS}
            data={DEMO_LEADS}
            rowKey={(r) => r.id}
            onRowClick={(row) => setLastClicked(row)}
          />
        </div>
      </div>

      {/* step-2: 制御型ページ送り */}
      <div className="dp-row">
        <span className="dp-row-label">pagination</span>
        <div className="dp-row-items dp-row-items--full">
          <DataTable<DemoLead>
            columns={DEMO_COLUMNS}
            data={demoPageData}
            rowKey={(r) => r.id}
            page={demoPage}
            hasNextPage={demoHasNext}
            onPageChange={setDemoPage}
            prevPageLabel="前へ"
            nextPageLabel="次へ"
            pageInfo={`${demoPage} / ${Math.ceil(DEMO_LEADS.length / DEMO_PAGE_SIZE)}`}
          />
        </div>
      </div>
    </section>
  );
}
