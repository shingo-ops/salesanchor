/**
 * ExtractionErrorLogPanel — 抽出エラーログ専用パネル
 *
 * API:
 *   GET /api/v1/tcg/extraction-errors?offset=0&limit=50
 *
 * ADR-027: 全UI文字列は t("key") 経由
 * ADR-067: 色・サイズはデザイントークンのみ
 * ADR-144: Card / DataTable 金型のみ使用
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../../lib/api";
import { Card } from "../../../components/Card";
import { DataTable } from "../../../components/DataTable";
import type { DataTableColumn } from "../../../components/DataTable";
import { Button } from "../../../components/Button";

// ---------------------------------------------------------------------------
// 型定義
// ---------------------------------------------------------------------------

interface ExtractionErrorItem {
  id: string;
  error_message: string | null;
  created_at: string | null;
  prompt_version: string | null;
  supplier_name: string | null;
}

const PAGE_SIZE = 50;

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

  function fetchErrors(nextOffset: number) {
    setLoading(true);
    setError(null);
    api
      .get<ExtractionErrorItem[]>(
        `/api/v1/tcg/extraction-errors?offset=${nextOffset}&limit=${PAGE_SIZE}`
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

  const columns: DataTableColumn<ExtractionErrorItem>[] = [
    {
      key: "supplier_name",
      header: t("analysisRules.errorLog.supplier"),
      width: "140px",
      renderCell: (row) => row.supplier_name ?? "-",
    },
    {
      key: "error_message",
      header: t("analysisRules.errorLog.errorMessage"),
      renderCell: (row) => row.error_message ?? "-",
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

      {error && (
        <p style={{ color: "var(--color-error)", fontSize: "var(--font-sm)" }}>
          {error}
        </p>
      )}

      <Card variant="container" density="compact">
        <DataTable<ExtractionErrorItem>
          columns={columns}
          data={items}
          rowKey={(row) => row.id}
          density="compact"
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
    </div>
  );
}
