/**
 * LINE解析ハブ「要確認」パネル（旧・要確認一覧ページから移設）
 *
 * タブ3種（design.md PR-D）:
 *   - 本番の確認待ち: GET /api/v1/tcg/analysis-results?status_tab=NEEDS_REVIEW
 *   - 試運転の確認待ち: GET /api/v1/tcg/shadow-results
 *   - 詰まり: GET /api/v1/tcg/shadow-results/bottlenecks
 * 認証: ハブ（AnalysisRulesPage）が is_super_admin を制御
 */
import { useEffect, useState } from "react";
import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { DataTable, type DataTableColumn } from "../../../components/DataTable";
import { Tabs, type TabItem } from "../../../components/Tabs";
import { Modal } from "../../../components/Modal";
import { Select } from "../../../components/Select";
import { TextField } from "../../../components/TextField";
import { Button } from "../../../components/Button";
import { Card } from "../../../components/Card";
import { useSuperAdmin } from "../../../hooks/useSuperAdmin";
import { api, ApiError } from "../../../lib/api";

const PAGE_SIZE = 20;

type TabKey = "production" | "shadow" | "bottlenecks";

interface NeedsReviewItem {
  extraction_item_id: string;
  source_message_id: string;
  provider: string;
  raw_text: string;
  gemini: Record<string, string>;
  system: Record<string, string>;
  review_issues: string[];
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

interface ShadowCandidate {
  product_id: number;
  product_name: string | null;
}

interface ShadowReviewItemEntry {
  item: string | null;
  reason: string | null;
  candidates: ShadowCandidate[];
}

interface ShadowResultItem {
  id: string;
  block_text: string;
  raw_product_name: string | null;
  raw_price: string | null;
  raw_unit: string | null;
  raw_quantity: string | null;
  raw_state: string | null;
  raw_ship: string | null;
  match_status: "matched" | "ambiguous" | "unmatched";
  product_id: number | null;
  work_id: number | null;
  needs_review: boolean;
  review_items: ShadowReviewItemEntry[];
  supplier_id: number | null;
  supplier_name: string | null;
  created_at: string | null;
}

interface ShadowResultsResponse {
  items: ShadowResultItem[];
  total: number;
  offset: number;
  limit: number;
}

interface BottleneckBySupplier {
  supplier_id: number | null;
  supplier_name: string | null;
  total: number;
  matched: number;
  needs_review_count: number;
  matched_ratio: number | null;
}

interface BottleneckByItem {
  supplier_id: number | null;
  supplier_name: string | null;
  item: string | null;
  count: number;
}

interface BottlenecksResponse {
  days: number;
  by_supplier: BottleneckBySupplier[];
  by_item: BottleneckByItem[];
}

interface KeywordPreviewResponse {
  checked: number;
  transitions: Record<string, number>;
}

function formatDate(isoString: string, locale: string): string {
  return new Intl.DateTimeFormat(locale.startsWith("ja") ? "ja-JP" : "en-GB", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(new Date(isoString));
}

function formatPriceQtyReason(reason: string, t: TFunction): string {
  return reason
    .split(",")
    .filter(Boolean)
    .map((code) => t(`shadowReview.priceQtyReason.${code}`, { defaultValue: code }))
    .join(", ");
}

export default function NeedsReviewTabsPanel() {
  const { t, i18n } = useTranslation();
  const { isSuperAdmin, loading: authLoading } = useSuperAdmin();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<TabKey>("production");

  // --- 本番の確認待ち ---
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<NeedsReviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorKey, setErrorKey] = useState("");

  useEffect(() => {
    if (authLoading || !isSuperAdmin || activeTab !== "production") return;
    let cancelled = false;
    setLoading(true);
    setData(null);
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
  }, [authLoading, isSuperAdmin, offset, activeTab]);

  // --- 試運転の確認待ち ---
  const [shadowOffset, setShadowOffset] = useState(0);
  const [shadowData, setShadowData] = useState<ShadowResultsResponse | null>(null);
  const [shadowLoading, setShadowLoading] = useState(false);
  const [shadowErrorKey, setShadowErrorKey] = useState("");
  const [shadowReloadKey, setShadowReloadKey] = useState(0);

  useEffect(() => {
    if (authLoading || !isSuperAdmin || activeTab !== "shadow") return;
    let cancelled = false;
    setShadowLoading(true);
    setShadowErrorKey("");
    const params = new URLSearchParams({
      needs_review: "true",
      offset: String(shadowOffset),
      limit: String(PAGE_SIZE),
    });
    api
      .get<ShadowResultsResponse>(`/tcg/shadow-results?${params.toString()}`)
      .then((result) => {
        if (!cancelled) setShadowData(result);
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setShadowErrorKey(
            error instanceof ApiError && (error.status === 401 || error.status === 403)
              ? "superAdmin.supplierQuality.superAdminOnly"
              : "common.fetchError"
          );
        }
      })
      .finally(() => {
        if (!cancelled) setShadowLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [authLoading, isSuperAdmin, activeTab, shadowOffset, shadowReloadKey]);

  // --- 詰まり ---
  const [bottleneckDays, setBottleneckDays] = useState<7 | 30>(7);
  const [bottleneckData, setBottleneckData] = useState<BottlenecksResponse | null>(null);
  const [bottleneckLoading, setBottleneckLoading] = useState(false);
  const [bottleneckErrorKey, setBottleneckErrorKey] = useState("");

  useEffect(() => {
    if (authLoading || !isSuperAdmin || activeTab !== "bottlenecks") return;
    let cancelled = false;
    setBottleneckLoading(true);
    setBottleneckErrorKey("");
    api
      .get<BottlenecksResponse>(`/tcg/shadow-results/bottlenecks?days=${bottleneckDays}`)
      .then((result) => {
        if (!cancelled) setBottleneckData(result);
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setBottleneckErrorKey(
            error instanceof ApiError && (error.status === 401 || error.status === 403)
              ? "superAdmin.supplierQuality.superAdminOnly"
              : "common.fetchError"
          );
        }
      })
      .finally(() => {
        if (!cancelled) setBottleneckLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [authLoading, isSuperAdmin, activeTab, bottleneckDays]);

  // --- モーダル（試運転の確認待ち：候補選択・ワード登録） ---
  const [selectedItem, setSelectedItem] = useState<ShadowResultItem | null>(null);
  const [selectedProductId, setSelectedProductId] = useState<number | null>(null);
  const [keywordKind, setKeywordKind] = useState<"search" | "exclude">("search");
  const [keywordValue, setKeywordValue] = useState("");
  const [previewResult, setPreviewResult] = useState<KeywordPreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [registerMessageKey, setRegisterMessageKey] = useState("");

  const openShadowModal = (item: ShadowResultItem) => {
    const productCandidates =
      item.review_items.find((r) => r.item === "product")?.candidates ?? [];
    setSelectedItem(item);
    setSelectedProductId(item.product_id ?? productCandidates[0]?.product_id ?? null);
    setKeywordKind("search");
    setKeywordValue(item.block_text);
    setPreviewResult(null);
    setRegisterMessageKey("");
  };

  const closeShadowModal = () => {
    setSelectedItem(null);
  };

  const handleCheckImpact = async () => {
    if (!selectedProductId || !keywordValue.trim()) return;
    setPreviewLoading(true);
    setRegisterMessageKey("");
    try {
      const result = await api.post<KeywordPreviewResponse>(
        "/tcg/shadow-results/keyword-preview",
        { product_id: selectedProductId, kind: keywordKind, keyword: keywordValue }
      );
      setPreviewResult(result);
    } catch {
      setRegisterMessageKey("common.fetchError");
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleRegister = async () => {
    if (!selectedProductId || !keywordValue.trim()) return;
    setRegistering(true);
    setRegisterMessageKey("");
    try {
      const endpoint =
        keywordKind === "search"
          ? `/tcg/products/${selectedProductId}/search-keywords`
          : `/tcg/products/${selectedProductId}/exclude-keywords`;
      const result = await api.post<{ ok: boolean; code?: string }>(endpoint, {
        new_keyword: keywordValue,
      });
      if (result.ok) {
        setRegisterMessageKey("shadowReview.registerSuccess");
        setShadowReloadKey((k) => k + 1);
      } else if (result.code === "KEYWORD_ALREADY_EXISTS") {
        setRegisterMessageKey("shadowReview.keywordAlreadyExists");
      } else {
        setRegisterMessageKey("shadowReview.registerFailed");
      }
    } catch {
      setRegisterMessageKey("shadowReview.registerFailed");
    } finally {
      setRegistering(false);
    }
  };

  const productionColumns: DataTableColumn<NeedsReviewItem>[] = [
    {
      key: "raw_product_name",
      header: t("needsReview.productName"),
      renderCell: (item) => item.gemini["name"] || item.system["product_title"] || "—",
    },
    {
      key: "provider",
      header: t("needsReview.supplier"),
      renderCell: (item) => item.provider,
    },
    {
      key: "review_reasons",
      header: t("needsReview.reviewReasons"),
      renderCell: (item) => {
        if (item.condition_review?.review_reasons) {
          return item.condition_review.review_reasons;
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
  ];

  const shadowColumns: DataTableColumn<ShadowResultItem>[] = [
    {
      key: "supplier_name",
      header: t("shadowReview.supplier"),
      renderCell: (item) => item.supplier_name || "—",
    },
    {
      key: "block_text",
      header: t("shadowReview.excerpt"),
      renderCell: (item) => (item.block_text.length > 60
        ? `${item.block_text.slice(0, 60)}…`
        : item.block_text),
    },
    {
      key: "stopped_item",
      header: t("shadowReview.stoppedItem"),
      renderCell: (item) =>
        item.review_items
          .map((r) => t(`shadowReview.itemLabel.${r.item}`, { defaultValue: r.item }))
          .join(", ") || "—",
    },
    {
      key: "candidates",
      header: t("shadowReview.candidates"),
      renderCell: (item) =>
        item.review_items
          .flatMap((r) => r.candidates.map((c) => c.product_name || String(c.product_id)))
          .join(", ") || "—",
    },
    {
      key: "reason",
      header: t("shadowReview.reason"),
      renderCell: (item) =>
        item.review_items
          .map((r) => (r.item === "price_qty" ? formatPriceQtyReason(r.reason ?? "", t) : r.reason))
          .filter(Boolean)
          .join(" / ") || "—",
    },
    {
      key: "created_at",
      header: t("shadowReview.createdAt"),
      renderCell: (item) => {
        if (!item.created_at) return "—";
        try {
          return formatDate(item.created_at, i18n.language);
        } catch {
          return item.created_at;
        }
      },
    },
  ];

  const bySupplierColumns: DataTableColumn<BottleneckBySupplier>[] = [
    { key: "supplier_name", header: t("shadowReview.supplier"), renderCell: (r) => r.supplier_name || "—" },
    { key: "needs_review_count", header: t("shadowReview.needsReviewCount"), renderCell: (r) => String(r.needs_review_count) },
    { key: "total", header: t("shadowReview.totalCount"), renderCell: (r) => String(r.total) },
    {
      key: "matched_ratio",
      header: t("shadowReview.matchedRatio"),
      renderCell: (r) => (r.matched_ratio == null ? "—" : `${Math.round(r.matched_ratio * 100)}%`),
    },
  ];

  const byItemColumns: DataTableColumn<BottleneckByItem>[] = [
    { key: "supplier_name", header: t("shadowReview.supplier"), renderCell: (r) => r.supplier_name || "—" },
    { key: "item", header: t("shadowReview.byItem"), renderCell: (r) => r.item || "—" },
    { key: "count", header: t("shadowReview.totalCount"), renderCell: (r) => String(r.count) },
  ];

  const tabItems: TabItem<TabKey>[] = [
    { key: "production", label: t("needsReview.tabs.production") },
    { key: "shadow", label: t("needsReview.tabs.shadow") },
    { key: "bottlenecks", label: t("needsReview.tabs.bottlenecks") },
  ];

  const productCandidates =
    selectedItem?.review_items.find((r) => r.item === "product")?.candidates ?? [];

  return (
    <>
      <Tabs items={tabItems} activeKey={activeTab} onChange={setActiveTab} />

      {activeTab === "production" && (
        <>
          {loading && <p role="status">{t("common.loading")}</p>}
          {errorKey && <p role="alert" style={{ color: "var(--color-error)" }}>{t(errorKey)}</p>}
          {data && (
            <DataTable
              columns={productionColumns}
              data={data.items}
              rowKey={(item) => item.extraction_item_id}
              emptyState={t("needsReview.noItems")}
              onRowClick={(item) =>
                navigate(`/super-admin/inbound/${item.source_message_id}/review`)
              }
              page={Math.floor(offset / PAGE_SIZE) + 1}
              hasNextPage={offset + (data.items?.length ?? 0) < data.total}
              onPageChange={(page) => setOffset((page - 1) * PAGE_SIZE)}
            />
          )}
        </>
      )}

      {activeTab === "shadow" && (
        <>
          {shadowLoading && <p role="status">{t("common.loading")}</p>}
          {shadowErrorKey && (
            <p role="alert" style={{ color: "var(--color-error)" }}>{t(shadowErrorKey)}</p>
          )}
          {shadowData && (
            <DataTable
              columns={shadowColumns}
              data={shadowData.items}
              rowKey={(item) => item.id}
              emptyState={t("shadowReview.noItems")}
              onRowClick={openShadowModal}
              page={Math.floor(shadowOffset / PAGE_SIZE) + 1}
              hasNextPage={shadowOffset + (shadowData.items?.length ?? 0) < shadowData.total}
              onPageChange={(page) => setShadowOffset((page - 1) * PAGE_SIZE)}
            />
          )}
        </>
      )}

      {activeTab === "bottlenecks" && (
        <>
          <Select
            label={t("shadowReview.bottleneckDaysLabel")}
            value={String(bottleneckDays)}
            onChange={(e) => setBottleneckDays(Number(e.target.value) === 30 ? 30 : 7)}
            options={[
              { value: "7", label: t("shadowReview.bottleneckDays7") },
              { value: "30", label: t("shadowReview.bottleneckDays30") },
            ]}
          />
          {bottleneckLoading && <p role="status">{t("common.loading")}</p>}
          {bottleneckErrorKey && (
            <p role="alert" style={{ color: "var(--color-error)" }}>{t(bottleneckErrorKey)}</p>
          )}
          {bottleneckData && (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
              <Card>
                <h3>{t("shadowReview.bySupplier")}</h3>
                <DataTable
                  columns={bySupplierColumns}
                  data={bottleneckData.by_supplier}
                  rowKey={(r) => String(r.supplier_id ?? "unknown")}
                  emptyState={t("shadowReview.noItems")}
                />
              </Card>
              <Card>
                <h3>{t("shadowReview.byItem")}</h3>
                <DataTable
                  columns={byItemColumns}
                  data={bottleneckData.by_item}
                  rowKey={(r) => `${r.supplier_id ?? "unknown"}-${r.item ?? "unknown"}`}
                  emptyState={t("shadowReview.noItems")}
                />
              </Card>
            </div>
          )}
        </>
      )}

      {selectedItem && (
        <Modal open onClose={closeShadowModal} title={t("shadowReview.modalTitle")} size="lg">
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            <div>
              <strong>{t("shadowReview.blockText")}</strong>
              <p>{selectedItem.block_text}</p>
            </div>

            {productCandidates.length > 0 && (
              <div>
                <strong>{t("shadowReview.candidateList")}</strong>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
                  {productCandidates.map((c) => (
                    <Button
                      key={c.product_id}
                      variant={selectedProductId === c.product_id ? "primary" : "outline"}
                      size="sm"
                      onClick={() => setSelectedProductId(c.product_id)}
                    >
                      {c.product_name || c.product_id}
                    </Button>
                  ))}
                </div>
              </div>
            )}

            <Select
              label={t("shadowReview.keywordKind")}
              value={keywordKind}
              onChange={(e) => setKeywordKind(e.target.value === "exclude" ? "exclude" : "search")}
              options={[
                { value: "search", label: t("shadowReview.keywordKindSearch") },
                { value: "exclude", label: t("shadowReview.keywordKindExclude") },
              ]}
            />

            <TextField
              label={t("shadowReview.keywordInput")}
              value={keywordValue}
              onChange={(e) => setKeywordValue(e.target.value)}
              fullWidth
            />

            <div style={{ display: "flex", gap: "var(--space-2)" }}>
              <Button
                variant="secondary"
                onClick={() => void handleCheckImpact()}
                disabled={previewLoading || !selectedProductId}
                loading={previewLoading}
              >
                {t("shadowReview.checkImpact")}
              </Button>
              <Button
                variant="primary"
                onClick={() => void handleRegister()}
                disabled={registering || !previewResult || !selectedProductId}
                loading={registering}
              >
                {t("shadowReview.register")}
              </Button>
            </div>

            {previewResult && (
              <p>{t("shadowReview.previewChecked", { count: previewResult.checked })}</p>
            )}
            {registerMessageKey && <p>{t(registerMessageKey)}</p>}
          </div>
        </Modal>
      )}
    </>
  );
}
