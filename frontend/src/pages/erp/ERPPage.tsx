import { LoadingBlock, Spinner } from "../../components/loading";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { getAccessToken } from "../../lib/auth/selfAuth";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";
import { ContentToolbar } from "../../components/ContentToolbar";
import { getStatusPresentation } from "../../utils/statusPresentation";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";
import { Button } from "../../components/Button";

interface SyncLog { id: number; sync_type: string; direction: string; record_count: number; status: string; error_message: string | null; started_at: string; completed_at: string | null; }

export default function ERPPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const logsQ = useApiQuery<SyncLog[]>("/erp/sync-logs");
  const logs = logsQ.data ?? [];
  const [error, setError] = useState("");
  const shownError = error || (logsQ.error ? (logsQ.error instanceof Error ? logsQ.error.message : t("common.fetchError")) : "");
  const invalidate = useInvalidateApi();
  const [exporting, setExporting] = useState(false);

  const load = () => {
    void invalidate(["erp", "sync-logs"]);
  };

  const exportInvoices = async () => {
    setExporting(true); setError("");
    try {
      const resp = await fetch("/api/v1/erp/export-invoices", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${await getAccessToken()}`,
          "Content-Type": "application/json",
        },
      });
      if (!resp.ok) throw new Error(t("common.operationError"));
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = "erp_invoices.csv"; a.click();
      URL.revokeObjectURL(url);
      load();
    } catch (e) { setError(e instanceof Error ? e.message : t("common.operationError")); }
    finally { setExporting(false); }
  };

  return (
    <PageLayout
      navKey="nav.dataManagement"
      subtitleKey="erp.subtitle"
      headerLeft={logsQ.isFetching && !logsQ.isPending ? <Spinner size="sm" /> : undefined}
    >
      {shownError && <div className="error-message">{shownError}</div>}
      {hasPermission("erp.sync") ? (
        <ContentToolbar
          right={
            <Button loading={exporting} variant="primary" size="sm" layoutClassName="field-h-md" onClick={exportInvoices} disabled={exporting}>
              {t("erp.exportInvoices")}
            </Button>
          }
        />
      ) : undefined}
      <h3 style={{ marginBottom: "var(--space-3)" }}>{t("erp.syncLogs")}</h3>
      {logsQ.isPending ? <LoadingBlock /> : (() => {
        const columns: DataTableColumn<SyncLog>[] = [
          {
            key: "sync_type",
            header: t("erp.colType"),
            renderCell: (l) => <>{l.sync_type}</>,
          },
          {
            key: "direction",
            header: t("erp.colDirection"),
            renderCell: (l) => <>{l.direction === "export" ? t("erp.directionExport") : t("erp.directionImport")}</>,
          },
          {
            key: "record_count",
            header: t("erp.colCount"),
            renderCell: (l) => <>{l.record_count}</>,
          },
          {
            key: "status",
            header: t("common.status"),
            renderCell: (l) => (
              <span className={`badge badge-${getStatusPresentation("erpJobStatus", l.status).badgeVariant}`}>{l.status}</span>
            ),
          },
          {
            key: "started_at",
            header: t("erp.colStartedAt"),
            renderCell: (l) => <>{new Date(l.started_at).toLocaleString()}</>,
          },
          {
            key: "completed_at",
            header: t("erp.colCompletedAt"),
            renderCell: (l) => <>{l.completed_at ? new Date(l.completed_at).toLocaleString() : "-"}</>,
          },
          {
            key: "error_message",
            header: t("common.error"),
            renderCell: (l) => (
              <span style={{ color: "var(--danger)", maxWidth: 'var(--col-width-medium)', overflow: "hidden", textOverflow: "ellipsis" }}>
                {l.error_message || "-"}
              </span>
            ),
          },
        ];
        return (
          <DataTable<SyncLog>
            columns={columns}
            data={logs}
            rowKey={(l) => String(l.id)}
            emptyState={<span>{t("erp.noLogs")}</span>}
          />
        );
      })()}
    </PageLayout>
  );
}
