import { LoadingBlock, Spinner } from "../../components/loading";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";
import { Button } from "../../components/Button";

interface Archive { id: number; source_table: string; source_id: number; archived_by: number | null; archived_at: string; restored_at: string | null; }

export default function ArchivesPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const archivesQ = useApiQuery<Archive[]>("/archives");
  const archives = archivesQ.data ?? [];
  const [error, setError] = useState("");
  const shownError = error || (archivesQ.error ? (archivesQ.error instanceof Error ? archivesQ.error.message : t("common.fetchError")) : "");
  const invalidate = useInvalidateApi();

  const load = () => {
    void invalidate(["archives"]);
  };

  const restore = async (id: number) => {
    try { await api.post(`/archives/${id}/restore`, {}); load(); }
    catch (e) { setError(e instanceof Error ? e.message : t("common.operationError")); }
  };

  return (
    <PageLayout
      navKey="nav.archive"
      subtitleKey="archives.subtitle"
      headerLeft={archivesQ.isFetching && !archivesQ.isPending ? <Spinner size="sm" /> : undefined}
    >
      {shownError && <div className="error-message">{shownError}</div>}
      {archivesQ.isPending ? <LoadingBlock /> : (() => {
        const columns: DataTableColumn<Archive>[] = [
          {
            key: "source_table",
            header: t("common.type"),
          },
          {
            key: "source_id",
            header: t("archives.sourceId"),
            renderCell: (a) => String(a.source_id),
          },
          {
            key: "archived_at",
            header: t("common.date"),
            renderCell: (a) => new Date(a.archived_at).toLocaleDateString(),
          },
          {
            key: "restored_at",
            header: t("archives.restoredAt"),
            renderCell: (a) => a.restored_at ? new Date(a.restored_at).toLocaleDateString() : "-",
          },
          {
            key: "actions",
            header: t("common.actions"),
            renderCell: (a) => (
              <span className="actions">
                {!a.restored_at && hasPermission("archive.manage") && <Button variant="primary" size="sm" onClick={() => restore(a.id)}>{t("archives.restore")}</Button>}
                {a.restored_at && <span className="badge badge-won">{t("archives.restored")}</span>}
              </span>
            ),
          },
        ];
        return (
          <DataTable
            columns={columns}
            data={archives}
            rowKey={(a) => String(a.id)}
            emptyState={<span>{t("common.noData")}</span>}
          />
        );
      })()}
    </PageLayout>
  );
}
