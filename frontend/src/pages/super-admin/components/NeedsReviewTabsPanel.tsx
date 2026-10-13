/**
 * LINE解析ハブ「要確認」パネル（旧・要確認一覧ページから移設）
 *
 * タブ2種:
 *   - 本番の確認待ち: GET /api/v1/tcg/analysis-results?status_tab=NEEDS_REVIEW
 *   - 投稿: GET /api/v1/tcg/v102/posts（V102PostsTab）
 * 認証: ハブ（AnalysisRulesPage）が is_super_admin を制御
 */
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { DataTable, type DataTableColumn } from "../../../components/DataTable";
import { Tabs, type TabItem } from "../../../components/Tabs";
import { Card } from "../../../components/Card";
import { useSuperAdmin } from "../../../hooks/useSuperAdmin";
import { api, ApiError } from "../../../lib/api";
import { reviewReasonLabel, reviewSourceLabel, type ReviewReasonDetail } from "../../../features/tcg-analysis-review/reviewReasonLabel";
import { formatDate } from "../../../features/tcg-analysis-review/formatDateTime";
import { ReviewRowActions } from "../../../features/tcg-analysis-review/ReviewRowActions";
import { ReviewItemDrawer } from "../../../features/tcg-analysis-review/ReviewItemDrawer";
import { V102PostsTab } from "../../../features/tcg-analysis-review/V102PostsTab";
import { ReviewCsvPanel } from "../../../features/tcg-review-csv/ReviewCsvPanel";

const PAGE_SIZE = 20;
const INLINE_FIX_COLUMN_WIDTH = "var(--review-inline-fix-col-w)";

type TabKey = "production" | "posts";

interface NeedsReviewItem {
  extraction_item_id: string;
  source_message_id: string;
  provider: string;
  raw_text: string;
  gemini: Record<string, string>;
  system: Record<string, string>;
  review_reason_details?: ReviewReasonDetail[];
  review_issues: string[];
  is_v102?: boolean;
  condition_review: {
    condition_id: string | null;
    review_version: string;
    needs_review: boolean;
    review_reasons: string;
    confirmed: boolean;
    classification: string;
  } | null;
}

interface NeedsReviewResponse {
  items: NeedsReviewItem[];
  total: number;
  item_total: number;
  offset: number;
  limit: number;
  providers: string[];
  works: { id: string; code: string; display_name: string; alt_name: string }[];
}

export default function NeedsReviewTabsPanel() {
  const { t, i18n } = useTranslation();
  const { isSuperAdmin, loading: authLoading } = useSuperAdmin();

  const [activeTab, setActiveTab] = useState<TabKey>("production");

  // --- 本番の確認待ち ---
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<NeedsReviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorKey, setErrorKey] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [drawerItem, setDrawerItem] = useState<NeedsReviewItem | null>(null);

  // 保存のあとの読み直し（reloadKey だけが変わったとき）は、表を消さずに取り直す
  const lastReloadKeyRef = useRef(reloadKey);

  useEffect(() => {
    if (authLoading || !isSuperAdmin || activeTab !== "production") return;
    let cancelled = false;
    const isReload = lastReloadKeyRef.current !== reloadKey;
    lastReloadKeyRef.current = reloadKey;
    setLoading(true);
    if (!isReload) setData(null);
    setErrorKey("");
    const params = new URLSearchParams({
      status_tab: "NEEDS_REVIEW",
      offset: String(offset),
      limit: String(PAGE_SIZE),
    });
    api
      .get<NeedsReviewResponse>(`/tcg/analysis-results?${params.toString()}`)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setErrorKey(
            error instanceof ApiError &&
              (error.status === 401 || error.status === 403)
              ? "superAdmin.supplierQuality.superAdminOnly"
              : "common.fetchError"
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [authLoading, isSuperAdmin, offset, activeTab, reloadKey]);

  const productionColumns: DataTableColumn<NeedsReviewItem>[] = [
    {
      key: "raw_product_name",
      header: t("needsReview.productName"),
      width: "var(--col-width-wide)",
      ellipsis: true,
      renderCell: (item) => item.gemini["name"] || item.system["product_title"] || "—",
    },
    {
      key: "provider",
      header: t("needsReview.supplier"),
      ellipsis: true,
      renderCell: (item) => item.provider,
    },
    {
      key: "review_source",
      header: t("needsReview.source"),
      ellipsis: true,
      renderCell: (item) => reviewSourceLabel(t, item.review_reason_details) ?? "—",
    },
    {
      key: "review_reasons",
      header: t("needsReview.reviewReasons"),
      width: "var(--col-width-medium)",
      ellipsis: true,
      renderCell: (item) => {
        const details = item.review_reason_details ?? [];
        if (details.length > 0) {
          return details.map((detail) => reviewReasonLabel(t, detail.code)).join(t("reviewReason.separator"));
        }
        const issues = item.review_issues ?? [];
        return issues
          .map((issue) => {
            if (issue === "PRODUCT_ID_UNRESOLVED") return t("needsReview.pidUnresolved");
            if (issue === "PRODUCT_MASTER_UNREGISTERED") return t("needsReview.multiCandidate");
            if (issue === "CONDITION_REVIEW_REQUIRED") return t("needsReview.noteUnmatched");
            return issue;
          })
          .join(", ") || "—";
      },
    },
    {
      key: "created_at",
      header: t("needsReview.createdAt"),
      ellipsis: true,
      renderCell: (item) => {
        const spanValue = item.gemini["span"];
        if (!spanValue) return "—";
        try {
          return formatDate(spanValue, i18n.language);
        } catch {
          return spanValue;
        }
      },
    },
    {
      key: "inline_fix",
      header: t("needsReview.inline.header"),
      width: INLINE_FIX_COLUMN_WIDTH,
      renderCell: (item) => (
        <ReviewRowActions item={item} onSaved={() => setReloadKey((k) => k + 1)} />
      ),
    },
  ];

  const tabItems: TabItem<TabKey>[] = [
    { key: "production", label: t("needsReview.tabs.production") },
    { key: "posts", label: t("needsReview.tabs.posts") },
  ];

  return (
    <>
      <Tabs items={tabItems} activeKey={activeTab} onChange={setActiveTab} />

      {activeTab === "production" && (
        <>
          <Card>
            <h3>{t("needsReview.csvTitle")}</h3>
            <ReviewCsvPanel onDone={() => setReloadKey((k) => k + 1)} />
          </Card>
          {loading && <p role="status">{t("common.loading")}</p>}
          {errorKey && <p role="alert" style={{ color: "var(--color-error)" }}>{t(errorKey)}</p>}
          {data && (
            <DataTable
              columns={productionColumns}
              data={data.items}
              rowKey={(item) => item.extraction_item_id}
              emptyState={t("needsReview.noItems")}
              onRowClick={setDrawerItem}
              page={Math.floor(offset / PAGE_SIZE) + 1}
              hasNextPage={offset + (data.items?.length ?? 0) < data.total}
              onPageChange={(page) => setOffset((page - 1) * PAGE_SIZE)}
            />
          )}
        </>
      )}

      {activeTab === "posts" && !authLoading && isSuperAdmin && <V102PostsTab />}

      {drawerItem && (
        <ReviewItemDrawer
          item={drawerItem}
          onClose={() => setDrawerItem(null)}
          onRefresh={async () => setReloadKey((k) => k + 1)}
        />
      )}
    </>
  );
}
