/**
 * LINE解析ハブ「解析精度管理（新方式）」パネル
 *
 * タブ2種（design.md §3-2）:
 *   - 精度サマリー: GET /api/v1/tcg/shadow-accuracy/summary
 *   - 投稿照合:     GET /api/v1/tcg/shadow-accuracy/posts（+ /posts/{job_id}）
 * 見るだけの画面（データは変えない）。認証はハブ（AnalysisRulesPage）が is_super_admin を制御。
 * 誤りの兆候は「誤りの候補」であり、誤りそのものではない（定義: backend shadow_accuracy_signals.py）。
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Select } from "../../../components/Select";
import { Tabs, type TabItem } from "../../../components/Tabs";
import { api } from "../../../lib/api";
import { errorKeyOf } from "./shadowAccuracyErrors";
import { ShadowAccuracyPosts } from "./ShadowAccuracyPosts";
import { ShadowAccuracySummary } from "./ShadowAccuracySummary";
import {
  PERIOD_DAYS,
  type AccuracySummary,
  type PeriodDays,
  type PostFilters,
  type SignalCode,
} from "./shadowAccuracyTypes";
import "./ShadowAccuracyPanel.css";

type TabKey = "summary" | "posts";

const DEFAULT_DAYS: PeriodDays = 7;

export function ShadowAccuracyPanel() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<TabKey>("summary");
  const [days, setDays] = useState<PeriodDays>(DEFAULT_DAYS);
  const [supplierId, setSupplierId] = useState("");
  const [filters, setFilters] = useState<PostFilters>({ needsReview: "", signal: "" });
  // 仕入元の選択肢は「仕入元で絞っていない」サマリーから集める（絞り込み後も消えないよう保持する）
  const [supplierOptions, setSupplierOptions] = useState<{ value: string; label: string }[]>([]);

  const [summary, setSummary] = useState<AccuracySummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorKey, setErrorKey] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErrorKey("");
    const params = new URLSearchParams({ days: String(days) });
    if (supplierId) params.set("supplier_id", supplierId);
    api
      .get<AccuracySummary>(`/tcg/shadow-accuracy/summary?${params.toString()}`)
      .then((result) => {
        if (cancelled) return;
        setSummary(result);
        if (!supplierId) {
          setSupplierOptions(
            result.by_supplier
              .filter((row) => row.supplier_id != null)
              .map((row) => ({
                value: String(row.supplier_id),
                label: row.supplier_name ?? String(row.supplier_id),
              })),
          );
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) setErrorKey(errorKeyOf(error));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [days, supplierId]);

  const openPostsWithSignal = useCallback((signal: SignalCode) => {
    setFilters({ needsReview: "", signal });
    setActiveTab("posts");
  }, []);

  const tabItems: TabItem<TabKey>[] = [
    { key: "summary", label: t("shadowAccuracy.tabs.summary") },
    { key: "posts", label: t("shadowAccuracy.tabs.posts") },
  ];

  return (
    <div className="shadow-accuracy">
      <div className="shadow-accuracy-filters">
        <Select
          label={t("shadowAccuracy.filter.period")}
          value={String(days)}
          onChange={(e) => setDays(Number(e.target.value) as PeriodDays)}
          options={PERIOD_DAYS.map((d) => ({
            value: String(d),
            label: t(`shadowAccuracy.period.${d}`),
          }))}
        />
        <Select
          label={t("shadowAccuracy.filter.supplier")}
          value={supplierId}
          onChange={(e) => setSupplierId(e.target.value)}
          options={[{ value: "", label: t("shadowAccuracy.filter.allSuppliers") }, ...supplierOptions]}
        />
      </div>

      <Tabs items={tabItems} activeKey={activeTab} onChange={setActiveTab} />

      {activeTab === "summary" && (
        <ShadowAccuracySummary
          summary={summary}
          loading={loading}
          errorKey={errorKey}
          onSelectSignal={openPostsWithSignal}
        />
      )}
      {activeTab === "posts" && (
        <ShadowAccuracyPosts
          days={days}
          supplierId={supplierId}
          filters={filters}
          onFiltersChange={setFilters}
        />
      )}
    </div>
  );
}

export default ShadowAccuracyPanel;
