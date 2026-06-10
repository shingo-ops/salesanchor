/**
 * 精度サマリータブ — 仕入元ごとの v_supplier_parse_stats ビューを表示する。
 *
 * ADR SA-06: 解析ログ永続化 + ドリフト検知
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";

interface Supplier {
  id: number;
  name: string;
}

interface ParseStatRow {
  supplier_id: number;
  supplier_name: string | null;
  day: string;
  total_lines: number;
  parsed_count: number;
  excluded_count: number;
  unparsed_count: number;
  exclude_rate_pct: number | null;
  avg_confidence: number | null;
}

const EXCLUDE_RATE_THRESHOLD = 30;
const CONFIDENCE_THRESHOLD = 0.5;

const numCell = (n: number) => (
  <span style={{ display: "block", textAlign: "right" }}>{n.toLocaleString()}</span>
);

function rowClassName(row: ParseStatRow): string {
  if ((row.exclude_rate_pct ?? 0) > EXCLUDE_RATE_THRESHOLD) return "comp-table__row--danger";
  if (row.avg_confidence !== null && row.avg_confidence < CONFIDENCE_THRESHOLD) return "comp-table__row--warning";
  return "";
}

export default function SupplierParseStatsTab() {
  const { t } = useTranslation();
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [rows, setRows] = useState<ParseStatRow[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api
      .get<Supplier[]>("/super-admin/suppliers?is_active=true&per_page=500")
      .then(setSuppliers)
      .catch((e) =>
        setError(e instanceof Error ? e.message : t("common.fetchError"))
      );
  }, [t]);

  const loadStats = useCallback(async () => {
    if (selectedId === null) return;
    setLoading(true);
    setError("");
    try {
      const data = await api.get<ParseStatRow[]>(
        `/super-admin/suppliers/${selectedId}/parse-stats?days=30`
      );
      setRows(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  }, [selectedId, t]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  const f = "supplier.parseStats";

  const columns: DataTableColumn<ParseStatRow>[] = [
    { key: "day",            header: t(`${f}.columns.day`) },
    { key: "total_lines",    header: t(`${f}.columns.totalLines`),    renderCell: (r) => numCell(r.total_lines) },
    { key: "parsed_count",   header: t(`${f}.columns.parsedCount`),   renderCell: (r) => numCell(r.parsed_count) },
    { key: "excluded_count", header: t(`${f}.columns.excludedCount`), renderCell: (r) => numCell(r.excluded_count) },
    { key: "unparsed_count", header: t(`${f}.columns.unparsedCount`), renderCell: (r) => numCell(r.unparsed_count) },
    {
      key: "exclude_rate_pct",
      header: t(`${f}.columns.excludeRate`),
      renderCell: (r) => (
        <span style={{ display: "block", textAlign: "right" }}>
          {r.exclude_rate_pct !== null ? `${r.exclude_rate_pct.toFixed(1)}%` : "-"}
        </span>
      ),
    },
    {
      key: "avg_confidence",
      header: t(`${f}.columns.avgConfidence`),
      renderCell: (r) => (
        <span style={{ display: "block", textAlign: "right" }}>
          {r.avg_confidence !== null ? r.avg_confidence.toFixed(3) : "-"}
        </span>
      ),
    },
  ];

  return (
    <div className="supplier-parse-stats-tab">
      {error && <div className="error-message">{error}</div>}

      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", margin: "var(--space-2) 0 var(--space-4)" }}>
        <label htmlFor="parse-stats-supplier-select">{t(`${f}.selectSupplier`)}</label>
        <select
          id="parse-stats-supplier-select"
          value={selectedId ?? ""}
          onChange={(e) => setSelectedId(e.target.value ? Number(e.target.value) : null)}
          style={{ minWidth: "16rem" }}
          data-testid="parse-stats-supplier-select"
        >
          <option value="">{t(`${f}.selectPlaceholder`)}</option>
          {suppliers.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
      </div>

      {loading && <div>{t("common.loading")}</div>}

      {!loading && selectedId !== null && (
        <DataTable<ParseStatRow>
          columns={columns}
          data={rows}
          rowKey={(r) => r.day}
          emptyState={t(`${f}.noData`)}
          rowClassName={rowClassName}
        />
      )}

      {!loading && rows.length > 0 && (
        <div style={{ display: "flex", gap: "var(--space-4)", marginTop: "var(--space-3)", fontSize: "var(--text-sm)", color: "var(--text-secondary)" }}>
          <span style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-1)" }}>
            <span style={{ width: "1rem", height: "1rem", background: "var(--danger-bg)", border: "1px solid var(--border-light)", display: "inline-block" }} />
            {t(`${f}.legend.highExclude`)}
          </span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-1)" }}>
            <span style={{ width: "1rem", height: "1rem", background: "var(--warning-bg)", border: "1px solid var(--border-light)", display: "inline-block" }} />
            {t(`${f}.legend.lowConfidence`)}
          </span>
        </div>
      )}
    </div>
  );
}
