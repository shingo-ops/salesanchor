/**
 * 要確認ページの「投稿」タブ（設計 §13-5 の 2）。
 * GET /api/v1/tcg/v102/posts の一覧。行を押すと書き写しを直す Modal を開く。
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Callout } from "../../components/Callout";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { EmptyState } from "../../components/EmptyState";
import { api } from "../../lib/api";
import { formatDate } from "./formatDateTime";
import { reviewReasonLabel } from "./reviewReasonLabel";
import { V102PostEditModal } from "./V102PostEditModal";
import type { V102PostListResponse, V102PostSummary } from "./v102PostTypes";

const PAGE_SIZE = 20;

export function V102PostsTab() {
  const { t, i18n } = useTranslation();
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<V102PostListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setHasError(false);
    const params = new URLSearchParams({ offset: String(offset), limit: String(PAGE_SIZE) });
    api
      .get<V102PostListResponse>(`/tcg/v102/posts?${params.toString()}`)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch(() => {
        if (!cancelled) setHasError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [offset, reloadKey]);

  const columns: DataTableColumn<V102PostSummary>[] = [
    { key: "provider", header: t("v102Posts.columns.supplier"), renderCell: (post) => post.provider },
    {
      key: "line_posted_at",
      header: t("v102Posts.columns.postedAt"),
      renderCell: (post) => (post.line_posted_at ? formatDate(post.line_posted_at, i18n.language) : "—"),
    },
    {
      key: "reasons",
      header: t("v102Posts.columns.postReasons"),
      renderCell: (post) =>
        post.job_review_reason_details.map((d) => reviewReasonLabel(t, d.code)).join(t("reviewReason.separator")) || "—",
    },
    {
      key: "counts",
      header: t("v102Posts.columns.counts"),
      renderCell: (post) => `${post.extraction_item_count} / ${post.item_count}`,
    },
  ];

  return (
    <>
      {loading && <p role="status">{t("common.loading")}</p>}
      {hasError && <Callout variant="warning" title={t("common.fetchError")} />}
      {data && data.items.length === 0 && <EmptyState size="compact" title={t("v102Posts.empty")} />}
      {data && data.items.length > 0 && (
        <DataTable
          columns={columns}
          data={data.items}
          rowKey={(post) => post.job_id}
          onRowClick={(post) => setSelectedJobId(post.job_id)}
          page={Math.floor(offset / PAGE_SIZE) + 1}
          hasNextPage={offset + data.items.length < data.total}
          onPageChange={(page) => setOffset((page - 1) * PAGE_SIZE)}
        />
      )}
      {selectedJobId && (
        <V102PostEditModal
          jobId={selectedJobId}
          onClose={() => setSelectedJobId(null)}
          onSaved={() => setReloadKey((k) => k + 1)}
        />
      )}
    </>
  );
}
