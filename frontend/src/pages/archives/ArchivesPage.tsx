import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";

interface Archive { id: number; source_table: string; source_id: number; archived_by: number | null; archived_at: string; restored_at: string | null; }

export default function ArchivesPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const [archives, setArchives] = useState<Archive[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try { setArchives(await api.get<Archive[]>("/archives")); }
    catch (e) { setError(e instanceof Error ? e.message : t("common.fetchError")); }
    finally { setLoading(false); }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, []);

  const restore = async (id: number) => {
    try { await api.post(`/archives/${id}/restore`, {}); load(); }
    catch (e) { setError(e instanceof Error ? e.message : t("common.operationError")); }
  };

  return (
    <PageLayout navKey="nav.archive" subtitleKey="archives.subtitle">
      {error && <div className="error-message">{error}</div>}
      {loading ? <div className="loading">{t("common.loading")}</div> : (() => {
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
                {!a.restored_at && hasPermission("archive.manage") && <button className="btn-sm btn-primary" onClick={() => restore(a.id)}>{t("archives.restore")}</button>}
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
