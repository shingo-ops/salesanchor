import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import { ContentToolbar } from "../../components/ContentToolbar";
import { HeaderButton } from "../../components/HeaderButton";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { EmptyState } from "../../components/EmptyState";
import { TextField } from "../../components/TextField";
import { SupplierDetailDrawer } from "../../features/supplier-master";

interface CentralSupplier {
  id: number;
  supplier_code: string | null;
  name: string;
  email: string | null;
  phone: string | null;
  is_active: boolean;
  line_name: string | null;
  postal_code: string | null;
  prefecture: string | null;
  city: string | null;
  address1: string | null;
  address2: string | null;
  discord_channel_id: string | null;
}

const PER_PAGE = 50;

export default function SupplierMasterPage() {
  const { t } = useTranslation();
  const { isSuperAdmin, loading: authLoading } = useSuperAdmin();
  const [items, setItems] = useState<CentralSupplier[]>([]);
  const [error, setError] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [retry, setRetry] = useState(0);
  const [selectedSupplierId, setSelectedSupplierId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    if (authLoading || !isSuperAdmin) return;
    try {
      const params = new URLSearchParams({ page: String(page), per_page: String(PER_PAGE) });
      params.set("is_active", "true");
      if (search.trim()) params.set("q", search.trim());
      const data = await api.get<CentralSupplier[]>(`/super-admin/suppliers?${params.toString()}`);
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  }, [authLoading, isSuperAdmin, page, search, t]);

  useEffect(() => { void load(); }, [load, retry]);

  const f = "superAdmin.suppliersAdmin.fields";

  const columns: DataTableColumn<CentralSupplier>[] = [
    { key: "name", header: t(`${f}.name`) },
    { key: "line_name", header: t(`${f}.lineName`), renderCell: row => row.line_name || "-" },
    { key: "discord_channel_id", header: t(`${f}.discordId`), renderCell: row => row.discord_channel_id ? <code>{row.discord_channel_id}</code> : "-" },
    { key: "phone", header: t(`${f}.phone`), renderCell: row => row.phone || "-" },
    { key: "email", header: t(`${f}.email`), renderCell: row => row.email || "-" },
  ];

  return (
    <PageLayout
      navKey="nav.superAdminSupplierMaster"
      headerAction={isSuperAdmin ? (
        <HeaderButton variant="primary" data-testid="suppliers-new" onClick={() => setCreating(true)}>
          {t("common.create")}
        </HeaderButton>
      ) : undefined}
    >
      {authLoading ? (
        <p>{t("common.loading")}</p>
      ) : !isSuperAdmin ? (
        <p role="alert">{t("productCsv.denied")}</p>
      ) : (
        <>
          {error && <p role="alert">{error}</p>}
          <ContentToolbar
            left={
              <TextField
                type="search"
                label={t(`${f}.name`)}
                value={searchInput}
                onChange={e => setSearchInput(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") { setSearch(searchInput); setPage(1); } }}
                data-testid="suppliers-search"
              />
            }
          />
          <DataTable
            columns={columns}
            data={items}
            rowKey={row => String(row.id)}
            onRowClick={row => setSelectedSupplierId(row.id)}
            emptyState={<EmptyState title={t("common.noData")} size="compact" />}
            page={page}
            hasNextPage={items.length >= PER_PAGE}
            onPageChange={setPage}
            prevPageLabel={t("common.prevPage")}
            nextPageLabel={t("common.nextPage")}
          />

          <SupplierDetailDrawer
            supplierId={selectedSupplierId}
            onClose={() => setSelectedSupplierId(null)}
            onSaved={() => setRetry(v => v + 1)}
          />
          <SupplierDetailDrawer
            supplierId={null}
            open={creating}
            mode="create"
            onClose={() => setCreating(false)}
            onSaved={() => { setCreating(false); setRetry(v => v + 1); }}
          />
        </>
      )}
    </PageLayout>
  );
}
