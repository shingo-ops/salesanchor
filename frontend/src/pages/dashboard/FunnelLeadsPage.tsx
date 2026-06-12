/**
 * FunnelLeadsPage — リード流入分析 下層ページ（PR5）
 * /dashboard/leads
 * チャネル別: きっかけ × チャネル × リード数 × 転換率 × 成約率 × 平均単価 × 粗利
 */

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { PageLayout } from "../../components/PageLayout";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { getChannels, type ChannelRow } from "../../api/funnel";

interface ChannelRowWithId extends ChannelRow {
  id: number;
}

function fmtMoney(n: number): string {
  if (n >= 10_000) return `¥${Math.round(n / 10_000)}万`;
  return `¥${n.toLocaleString("ja-JP")}`;
}

export default function FunnelLeadsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [rows, setRows] = useState<ChannelRowWithId[]>([]);
  const [loading, setLoading] = useState(true);

  const currentMonth = (() => {
    const now = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Tokyo" }));
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  })();

  useEffect(() => {
    setLoading(true);
    getChannels(currentMonth)
      .then((res) => {
        setRows(res.rows.map((r, i) => ({ ...r, id: i + 1 })));
      })
      .finally(() => setLoading(false));
  }, [currentMonth]);

  const columns: DataTableColumn<ChannelRowWithId>[] = [
    {
      key: "initiative",
      header: t("funnel.colInitiative"),
      renderCell: (row) => (
        <span className={`fl-initiative-chip fl-initiative--${row.initiative}`}>
          {t(`initiative.${row.initiative}_short`)}
        </span>
      ),
    },
    {
      key: "channel",
      header: t("funnel.colChannel"),
      renderCell: (row) => row.channel,
    },
    {
      key: "leads",
      header: t("funnel.leads"),
      renderCell: (row) => `${row.leads}${t("funnel.unitDeal")}`,
    },
    {
      key: "conversion_rate",
      header: t("funnel.conversion"),
      renderCell: (row) => `${row.conversion_rate}%`,
    },
    {
      key: "win_rate",
      header: t("funnel.wonRate"),
      renderCell: (row) => `${row.win_rate}%`,
    },
    {
      key: "avg_order_value",
      header: t("funnel.colAvgOrderValue"),
      renderCell: (row) => fmtMoney(row.avg_order_value),
    },
    {
      key: "gross_margin",
      header: t("funnel.grossMargin"),
      renderCell: (row) => fmtMoney(row.gross_margin),
    },
  ];

  return (
    <PageLayout
      navKey="nav.dashboard"
      subtitleKey="funnel.leadsPageTitle"
      headerAction={
        <button
          type="button"
          className="fu-back-btn"
          onClick={() => navigate("/")}
          style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-1)", padding: "var(--space-2) var(--space-3)", border: "none", background: "var(--bg-primary)", color: "var(--text-secondary)", fontSize: "var(--font-sm)", borderRadius: "var(--radius-md)", cursor: "pointer" }}
        >
          ← {t("nav.dashboard")}
        </button>
      }
    >
      {loading ? (
        <div style={{ padding: "var(--space-6) 0", color: "var(--text-secondary)", fontSize: "var(--font-sm)" }}>
          {t("common.loading")}
        </div>
      ) : (
        <>
          <style>{`
            .fl-initiative-chip { display: inline-flex; align-items: center; padding: 2px var(--space-2); border-radius: var(--radius-badge); font-size: var(--font-xs); font-weight: var(--font-weight-semi); white-space: nowrap; }
            .fl-initiative--inbound { background: var(--accent-bg-subtle); color: var(--accent); }
            .fl-initiative--outbound { background: var(--success-bg); color: var(--success-text); }
          `}</style>
          <DataTable<ChannelRowWithId>
            columns={columns}
            data={rows}
            rowKey={(row) => String(row.id)}
            emptyState={<p style={{ textAlign: "center", color: "var(--text-muted)", fontSize: "var(--font-sm)" }}>{t("dashboard.noData")}</p>}
          />
        </>
      )}
    </PageLayout>
  );
}
