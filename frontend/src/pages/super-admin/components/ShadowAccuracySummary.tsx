/**
 * 解析精度管理（新方式）: 精度サマリータブ。
 * 数字は Card、仕入元別は DataTable。兆候の件数を押すと投稿照合タブがその兆候で絞り込まれる。
 */
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/Button";
import { Card } from "../../../components/Card";
import { DataTable, type DataTableColumn } from "../../../components/DataTable";
import {
  SIGNAL_CODES,
  type AccuracySummary,
  type SignalCode,
  type SupplierSummaryRow,
} from "./shadowAccuracyTypes";

interface Props {
  summary: AccuracySummary | null;
  loading: boolean;
  errorKey: string;
  onSelectSignal: (signal: SignalCode) => void;
}

function percent(value: number | null): string {
  return value == null ? "—" : `${Math.round(value * 100)}%`;
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Card variant="metric" density="compact">
      <div className="shadow-accuracy-metric-label">{label}</div>
      <div className="shadow-accuracy-metric-value">{value}</div>
    </Card>
  );
}

export function ShadowAccuracySummary({ summary, loading, errorKey, onSelectSignal }: Props) {
  const { t } = useTranslation();

  if (errorKey) {
    return <p role="alert" className="shadow-accuracy-error">{t(errorKey)}</p>;
  }
  if (loading && !summary) return <p role="status">{t("common.loading")}</p>;
  if (!summary) return null;

  const { totals } = summary;
  const supplierColumns: DataTableColumn<SupplierSummaryRow>[] = [
    { key: "supplier_name", header: t("shadowAccuracy.supplier"), renderCell: (r) => r.supplier_name || "—" },
    { key: "blocks", header: t("shadowAccuracy.metric.blocks"), renderCell: (r) => String(r.blocks) },
    {
      key: "needs_review_ratio",
      header: t("shadowAccuracy.metric.needsReviewRatio"),
      renderCell: (r) => percent(r.needs_review_ratio),
    },
    ...SIGNAL_CODES.map((code) => ({
      key: code,
      header: `${code} ${t(`shadowAccuracy.signal.short.${code}`)}`,
      renderCell: (r: SupplierSummaryRow) => String(r.signals[code]),
    })),
  ];

  return (
    <div className="shadow-accuracy-summary">
      {loading && <p role="status">{t("common.loading")}</p>}

      <div className="shadow-accuracy-metrics">
        <Metric label={t("shadowAccuracy.metric.blocks")} value={String(totals.blocks)} />
        <Metric
          label={t("shadowAccuracy.metric.autoConfirmed")}
          value={`${totals.auto_confirmed} (${percent(totals.auto_confirmed_ratio)})`}
        />
        <Metric label={t("shadowAccuracy.metric.matched")} value={String(totals.matched)} />
        <Metric label={t("shadowAccuracy.metric.ambiguous")} value={String(totals.ambiguous)} />
        <Metric label={t("shadowAccuracy.metric.unmatched")} value={String(totals.unmatched)} />
        <Metric label={t("shadowAccuracy.metric.priceFixed")} value={String(totals.price_fixed)} />
        <Metric label={t("shadowAccuracy.metric.quantityFixed")} value={String(totals.quantity_fixed)} />
        <Metric label={t("shadowAccuracy.metric.soldOut")} value={String(totals.sold_out)} />
        <Metric label={t("shadowAccuracy.metric.preOrder")} value={String(totals.pre_order)} />
      </div>

      <Card>
        <h3>{t("shadowAccuracy.conditions.title")}</h3>
        <DataTable
          columns={[
            {
              key: "condition",
              header: t("shadowAccuracy.conditions.condition"),
              renderCell: (r: AccuracySummary["conditions"][number]) => r.condition || "—",
            },
            {
              key: "blocks",
              header: t("shadowAccuracy.metric.blocks"),
              renderCell: (r: AccuracySummary["conditions"][number]) => String(r.blocks),
            },
          ]}
          data={summary.conditions}
          rowKey={(r) => r.condition ?? "none"}
          density="compact"
          emptyState={t("shadowAccuracy.empty")}
        />
      </Card>

      <Card>
        <h3>{t("shadowAccuracy.signal.title")}</h3>
        <p className="shadow-accuracy-note">{t("shadowAccuracy.signal.note")}</p>
        <ul className="shadow-accuracy-signals">
          {SIGNAL_CODES.map((code) => (
            <li key={code} className="shadow-accuracy-signal">
              <span className="shadow-accuracy-signal-name">
                {code} {t(`shadowAccuracy.signal.label.${code}`)}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onSelectSignal(code)}
                aria-label={t("shadowAccuracy.signal.openPosts", {
                  signal: `${code} ${t(`shadowAccuracy.signal.label.${code}`)}`,
                })}
              >
                {t("shadowAccuracy.signal.count", { count: summary.signals[code] })}
              </Button>
            </li>
          ))}
        </ul>
      </Card>

      <Card>
        <h3>{t("shadowAccuracy.bySupplier.title")}</h3>
        <DataTable
          columns={supplierColumns}
          data={summary.by_supplier}
          rowKey={(r) => String(r.supplier_id ?? "unknown")}
          emptyState={t("shadowAccuracy.empty")}
        />
      </Card>
    </div>
  );
}
