/**
 * ExtractionErrorLogPanel — 抽出エラーログ専用パネル
 *
 * API:
 *   GET /api/v1/tcg/extraction-errors?offset=0&limit=50
 *   POST /api/v1/tcg/diagnostics/retry-extraction
 *   （api クライアントが /api/v1 を付与するため、呼び出し時はプレフィックスなしで渡す）
 *
 * ADR-027: 全UI文字列は t("key") 経由
 * ADR-067: 色・サイズはデザイントークンのみ
 * ADR-144: Card / DataTable / Badge / Modal / Button 金型のみ使用
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../../lib/api";
import { Card } from "../../../components/Card";
import { DataTable } from "../../../components/DataTable";
import type { DataTableColumn } from "../../../components/DataTable";
import { Button } from "../../../components/Button";
import { Badge } from "../../../components/Badge";
import type { BadgeVariant } from "../../../components/Badge";
import { Modal } from "../../../components/Modal";
import { ContentToolbar } from "../../../components/ContentToolbar";

// ---------------------------------------------------------------------------
// 型定義
// ---------------------------------------------------------------------------

type ErrorCategory =
  | "gemini_rate_limit"
  | "gemini_http_error"
  | "gemini_timeout"
  | "gemini_unknown"
  | "system_timeout"
  | "system_db_error"
  | "system_input_error"
  | "logic_parse_error"
  | "logic_conflict"
  | null
  | undefined;

interface ExtractionErrorItem {
  id: string;
  error_message: string | null;
  error_category: ErrorCategory;
  error_detail: string | null;
  created_at: string | null;
  prompt_version: string | null;
  supplier_name: string | null;
}

const PAGE_SIZE = 50;

const CATEGORY_VARIANT: Record<string, BadgeVariant> = {
  gemini_rate_limit: "warning",
  gemini_http_error: "danger",
  gemini_timeout: "warning",
  gemini_unknown: "neutral",
  system_timeout: "danger",
  system_db_error: "danger",
  system_input_error: "info",
  logic_parse_error: "info",
  logic_conflict: "info",
};

// ---------------------------------------------------------------------------
// コンポーネント
// ---------------------------------------------------------------------------

export function ExtractionErrorLogPanel() {
  const { t } = useTranslation();
  const [items, setItems] = useState<ExtractionErrorItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showRetryModal, setShowRetryModal] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);
  const [retrySuccess, setRetrySuccess] = useState<string | null>(null);

  function fetchErrors(nextOffset: number) {
    setLoading(true);
    setError(null);
    api
      .get<ExtractionErrorItem[]>(
        `/tcg/extraction-errors?offset=${nextOffset}&limit=${PAGE_SIZE}`
      )
      .then((rows) => {
        if (nextOffset === 0) {
          setItems(rows);
        } else {
          setItems((prev) => [...prev, ...rows]);
        }
        setHasMore(rows.length === PAGE_SIZE);
        setOffset(nextOffset + rows.length);
      })
      .catch(() => {
        setError(t("analysisRules.errorLog.fetchError"));
      })
      .finally(() => {
        setLoading(false);
      });
  }

  useEffect(() => {
    fetchErrors(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleRetry() {
    setIsRetrying(true);
    setRetryError(null);
    setRetrySuccess(null);
    try {
      await api.post("/tcg/diagnostics/retry-extraction", {
        job_ids: Array.from(selectedIds),
      });
      setRetrySuccess(
        t("analysisRules.errorLog.retrySuccess", { count: selectedIds.size })
      );
      setSelectedIds(new Set());
      setShowRetryModal(false);
      fetchErrors(0);
    } catch {
      setRetryError(t("analysisRules.errorLog.retryError"));
    } finally {
      setIsRetrying(false);
    }
  }

  const columns: DataTableColumn<ExtractionErrorItem>[] = [
    {
      key: "supplier_name",
      header: t("analysisRules.errorLog.supplier"),
      width: "140px",
      renderCell: (row) => row.supplier_name ?? "-",
    },
    {
      key: "error_category",
      header: t("analysisRules.errorLog.errorCategory"),
      width: "160px",
      renderCell: (row) => {
        const category = row.error_category;
        const variant: BadgeVariant = category
          ? (CATEGORY_VARIANT[category] ?? "neutral")
          : "neutral";
        const label = category
          ? t(`analysisRules.errorLog.category.${category}`)
          : t("analysisRules.errorLog.category.unknown");
        return <Badge variant={variant} size="sm">{label}</Badge>;
      },
    },
    {
      key: "error_message",
      header: t("analysisRules.errorLog.errorMessage"),
      renderCell: (row) => row.error_message ?? "-",
    },
    {
      key: "error_detail",
      header: t("analysisRules.errorLog.errorDetail"),
      renderCell: (row) =>
        row.error_detail ? (
          <span
            style={{
              display: "block",
              maxWidth: "240px",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
            title={row.error_detail}
          >
            {row.error_detail}
          </span>
        ) : (
          "-"
        ),
    },
    {
      key: "prompt_version",
      header: t("analysisRules.errorLog.promptVersion"),
      width: "200px",
      renderCell: (row) => row.prompt_version ?? "-",
    },
    {
      key: "created_at",
      header: t("analysisRules.errorLog.createdAt"),
      width: "180px",
      renderCell: (row) =>
        row.created_at
          ? new Date(row.created_at).toLocaleString("ja-JP", {
              timeZone: "Asia/Tokyo",
              year: "numeric",
              month: "long",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })
          : "-",
    },
  ];

  return (
    <div
      style={{
        padding: "var(--space-4)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-4)",
      }}
    >
      <p
        style={{
          margin: 0,
          fontSize: "var(--font-lg)",
          fontWeight: "var(--font-weight-bold)",
          color: "var(--text-primary)",
        }}
      >
        {t("analysisRules.errorLog.title")}
      </p>

      <ContentToolbar
        right={
          <Button
            variant="secondary"
            size="sm"
            disabled={selectedIds.size === 0 || isRetrying}
            onClick={() => setShowRetryModal(true)}
          >
            {t("analysisRules.errorLog.retrySelected")}
          </Button>
        }
      />

      {error && (
        <p style={{ color: "var(--color-error)", fontSize: "var(--font-sm)" }}>
          {error}
        </p>
      )}

      {retrySuccess && (
        <p style={{ color: "var(--color-success)", fontSize: "var(--font-sm)" }}>
          {retrySuccess}
        </p>
      )}

      {retryError && (
        <p style={{ color: "var(--color-error)", fontSize: "var(--font-sm)" }}>
          {retryError}
        </p>
      )}

      <Card variant="container" density="compact">
        <DataTable<ExtractionErrorItem>
          columns={columns}
          data={items}
          rowKey={(row) => row.id}
          density="compact"
          selectable
          selectedKeys={selectedIds}
          onSelectChange={setSelectedIds}
          emptyState={
            loading ? t("common.loading") : t("analysisRules.errorLog.noErrors")
          }
        />
      </Card>

      {hasMore && !loading && (
        <div style={{ display: "flex", justifyContent: "center" }}>
          <Button
            variant="ghost"
            size="md"
            onClick={() => fetchErrors(offset)}
          >
            {t("analysisRules.errorLog.loadMore")}
          </Button>
        </div>
      )}

      {loading && items.length > 0 && (
        <p
          style={{
            textAlign: "center",
            color: "var(--text-muted)",
            fontSize: "var(--font-sm)",
          }}
        >
          {t("common.loading")}
        </p>
      )}

      <Modal
        open={showRetryModal}
        onClose={() => setShowRetryModal(false)}
        title={t("analysisRules.errorLog.retrySelected")}
        footer={
          <Button
            variant="primary"
            size="md"
            loading={isRetrying}
            onClick={handleRetry}
          >
            {t("analysisRules.errorLog.retrySelected")}
          </Button>
        }
      >
        <p>
          {t("analysisRules.errorLog.retryConfirm", {
            count: selectedIds.size,
          })}
        </p>
      </Modal>
    </div>
  );
}
