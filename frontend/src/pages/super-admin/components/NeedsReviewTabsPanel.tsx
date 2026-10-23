/**
 * LINE解析ハブ「要確認」パネル（旧・要確認一覧ページから移設）
 *
 * タブ3種:
 *   - 本番の確認待ち: GET /api/v1/tcg/analysis-results?status_tab=NEEDS_REVIEW
 *   - 確認済み: 同じ API を status_tab=ACKED で読む（取り消しはドロワーから）
 *   - 投稿: GET /api/v1/tcg/v102/posts（V102PostsTab）
 * 認証: ハブ（AnalysisRulesPage）が is_super_admin を制御
 */
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { DataTable, type DataTableColumn } from "../../../components/DataTable";
import { Tabs, type TabItem } from "../../../components/Tabs";
import { Card } from "../../../components/Card";
import { Button } from "../../../components/Button";
import { SelectControl } from "../../../components/Select";
import { ContentToolbar } from "../../../components/ContentToolbar";
import { Stack } from "../../../components/Stack";
import { LoadingBlock } from "../../../components/loading";
import { useSuperAdmin } from "../../../hooks/useSuperAdmin";
import { useRealtimeRefresh } from "../../../hooks/useRealtimeRefresh";
import { TOPICS } from "../../../lib/realtime/topics";
import { api, ApiError } from "../../../lib/api";
import { reviewReasonLabel, reviewSourceLabel, type ReviewReasonDetail } from "../../../features/tcg-analysis-review/reviewReasonLabel";
import { formatDate } from "../../../features/tcg-analysis-review/formatDateTime";
import { ReviewItemDrawer } from "../../../features/tcg-analysis-review/ReviewItemDrawer";
import { V102PostsTab } from "../../../features/tcg-analysis-review/V102PostsTab";
import { ReviewCsvPanel } from "../../../features/tcg-review-csv/ReviewCsvPanel";
import { useReviewTiming } from "./useReviewTiming";

/** 確認済みタブの1ページの件数 */
const PAGE_SIZE = 20;
/** 要確認タブの件数の選択肢（先頭が既定） */
const PRODUCTION_PAGE_SIZES = [25, 50, 100] as const;
/** 要確認タブの「新しい投稿だけ」の窓（時間） */
const FRESH_WINDOW_HOURS = 24;

type TabKey = "production" | "acked" | "posts";

/** 一覧を読むタブと status_tab の対応（posts は別の画面なので載せない） */
const STATUS_TAB_OF: Record<Exclude<TabKey, "posts">, string> = {
  production: "NEEDS_REVIEW",
  acked: "ACKED",
};

interface NeedsReviewItem {
  extraction_item_id: string;
  source_message_id: string;
  provider: string;
  posted_at: string | null;
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

  // 要確認タブだけ: 24時間ボタン（既定 ON）と1ページの件数（既定 25）
  const [freshOnly, setFreshOnly] = useState(true);
  const [productionPageSize, setProductionPageSize] = useState<number>(PRODUCTION_PAGE_SIZES[0]);
  const pageSize = activeTab === "production" ? productionPageSize : PAGE_SIZE;

  // --- 本番の確認待ち ---
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<NeedsReviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorKey, setErrorKey] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  // スライドは「どの件か」(id) だけ持ち、表示する中身は一覧の最新データから引き直す。
  // 一覧から外れた（要確認でなくなった・ページ外）ときは最後に見た内容を残す
  const [drawerItemId, setDrawerItemId] = useState<string | null>(null);
  const lastDrawerItemRef = useRef<NeedsReviewItem | null>(null);

  // 保存のあとの読み直し（reloadKey だけが変わったとき）は、表を消さずに取り直す
  const lastReloadKeyRef = useRef(reloadKey);

  // ADR-1016: 他の人・裏の処理で要確認が変わったら、保存後と同じ読み直しを 1 回走らせる
  useRealtimeRefresh([TOPICS.tcgReview], () => setReloadKey((k) => k + 1));

  // 便0: 要確認タブの一覧が最初に描かれるまでの計時（mount ごとに1回だけ送る）
  const { recordListMs, abandon: abandonTiming } = useReviewTiming({
    shown: activeTab === "production" && data !== null,
    rows: data?.items.length ?? 0,
    pageSize: productionPageSize,
  });

  useEffect(() => {
    if (authLoading || !isSuperAdmin || activeTab === "posts") return;
    let cancelled = false;
    const isReload = lastReloadKeyRef.current !== reloadKey;
    lastReloadKeyRef.current = reloadKey;
    setLoading(true);
    if (!isReload) setData(null);
    setErrorKey("");
    const params = new URLSearchParams({
      status_tab: STATUS_TAB_OF[activeTab],
      offset: String(offset),
      limit: String(pageSize),
    });
    if (activeTab === "production") {
      params.set("order", "posted_desc");
      if (freshOnly) params.set("posted_within_hours", String(FRESH_WINDOW_HOURS));
    }
    const startedAt = performance.now();
    api
      .get<NeedsReviewResponse>(`/tcg/analysis-results?${params.toString()}`)
      .then((result) => {
        if (!cancelled) {
          setData(result);
          recordListMs(performance.now() - startedAt);
        }
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
  }, [authLoading, isSuperAdmin, offset, activeTab, reloadKey, recordListMs, freshOnly, pageSize]);

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
        // 要確認タブは投稿日時、確認済みタブは今のまま（gemini.span）
        const dateValue = activeTab === "production" ? item.posted_at : item.gemini["span"];
        if (!dateValue) return "—";
        try {
          return formatDate(dateValue, i18n.language);
        } catch {
          return dateValue;
        }
      },
    },
  ];

  const latestDrawerItem = drawerItemId ? data?.items.find((i) => i.extraction_item_id === drawerItemId) ?? null : null;
  if (latestDrawerItem) lastDrawerItemRef.current = latestDrawerItem;
  if (!drawerItemId) lastDrawerItemRef.current = null;
  const drawerItem = drawerItemId ? latestDrawerItem ?? lastDrawerItemRef.current : null;
  const drawerRemoved = drawerItemId !== null && latestDrawerItem === null;

  // タブを替えたら、前のタブの行・ページ・ドロワーを持ち越さない
  const changeTab = (tab: TabKey) => {
    if (tab === activeTab) return;
    abandonTiming();
    setActiveTab(tab);
    setOffset(0);
    setDrawerItemId(null);
    setData(null);
  };

  const tabItems: TabItem<TabKey>[] = [
    { key: "production", label: t("needsReview.tabs.production") },
    { key: "acked", label: t("needsReview.tabs.acked") },
    { key: "posts", label: t("needsReview.tabs.posts") },
  ];

  return (
    <>
      <Tabs items={tabItems} activeKey={activeTab} onChange={changeTab} />

      {activeTab !== "posts" && (
        <>
          {activeTab === "production" && (
            <Card>
              <h3>{t("needsReview.csvTitle")}</h3>
              <ReviewCsvPanel onDone={() => setReloadKey((k) => k + 1)} />
            </Card>
          )}
          {activeTab === "production" && (
            <ContentToolbar
              left={
                <Stack direction="row" gap="2">
                  <Button
                    variant={freshOnly ? "primary" : "secondary"}
                    size="sm"
                    layoutClassName="field-h-md"
                    type="button"
                    data-testid="needs-review-fresh-toggle"
                    aria-pressed={freshOnly}
                    onClick={() => {
                      setFreshOnly((v) => !v);
                      setOffset(0);
                    }}
                  >
                    {t("needsReview.freshOnly", { hours: FRESH_WINDOW_HOURS })}
                  </Button>
                  <SelectControl
                    size="sm"
                    className="field-h-md"
                    data-testid="needs-review-page-size"
                    aria-label={t("needsReview.pageSize")}
                    value={String(productionPageSize)}
                    onChange={(e) => {
                      setProductionPageSize(Number(e.target.value));
                      setOffset(0);
                    }}
                    options={PRODUCTION_PAGE_SIZES.map((n) => ({
                      value: String(n),
                      label: t("needsReview.pageSizeOption", { n }),
                    }))}
                  />
                </Stack>
              }
            />
          )}
          {loading && <LoadingBlock />}
          {errorKey && <p role="alert" style={{ color: "var(--color-error)" }}>{t(errorKey)}</p>}
          {data && (
            <DataTable
              columns={productionColumns}
              data={data.items}
              rowKey={(item) => item.extraction_item_id}
              emptyState={t(activeTab === "acked" ? "needsReview.ackedEmpty" : "needsReview.noItems")}
              onRowClick={(item) => setDrawerItemId(item.extraction_item_id)}
              page={Math.floor(offset / pageSize) + 1}
              hasNextPage={offset + (data.items?.length ?? 0) < data.total}
              onPageChange={(page) => setOffset((page - 1) * pageSize)}
            />
          )}
        </>
      )}

      {activeTab === "posts" && !authLoading && isSuperAdmin && <V102PostsTab />}

      {drawerItem && (
        <ReviewItemDrawer
          item={drawerItem}
          removedFromList={drawerRemoved && activeTab === "production"}
          ackedView={activeTab === "acked"}
          onClose={() => setDrawerItemId(null)}
          onRefresh={async () => setReloadKey((k) => k + 1)}
        />
      )}
    </>
  );
}
