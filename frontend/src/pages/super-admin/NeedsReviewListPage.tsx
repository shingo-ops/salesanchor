/**
 * /super-admin/needs-review — 要確認一覧
 *
 * GET /api/v1/tcg/analysis-results?status_tab=NEEDS_REVIEW
 * 認証: is_super_admin 必須
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { PageLayout } from "../../components/PageLayout";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { api, ApiError } from "../../lib/api";

const PAGE_SIZE = 20;

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

export default function NeedsReviewListPage() {
  const { t, i18n } = useTranslation();
  const { isSuperAdmin, loading: authLoading } = useSuperAdmin();
  const navigate = useNavigate();

  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<NeedsReviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorKey, setErrorKey] = useState("");

  useEffect(() => {
    if (authLoading || !isSuperAdmin) return;
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
  }, [authLoading, isSuperAdmin, offset]);

  if (authLoading) {
    return (
      <PageLayout navKey="nav.superAdminNeedsReview">
        {t("common.loading")}
      </PageLayout>
    );
  }
  if (!isSuperAdmin) {
    return (
      <PageLayout navKey="nav.superAdminNeedsReview">
        <p role="alert" style={{ color: "var(--color-error)" }}>
          {t("superAdmin.supplierQuality.superAdminOnly")}
        </p>
      </PageLayout>
    );
  }

  const columns: DataTableColumn<NeedsReviewItem>[] = [
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

  return (
    <PageLayout navKey="nav.superAdminNeedsReview">
      {loading && <p role="status">{t("common.loading")}</p>}
      {errorKey && <p role="alert" style={{ color: "var(--color-error)" }}>{t(errorKey)}</p>}
      {data && (
        <>
          <DataTable
            columns={columns}
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
        </>
      )}
    </PageLayout>
  );
}
