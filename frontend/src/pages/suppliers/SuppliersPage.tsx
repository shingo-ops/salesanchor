import { useEffect, useRef, useState, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Modal } from "../../components/Modal";
import { Button } from "../../components/Button";
import { Drawer } from "../../components/Drawer";
import { api } from "../../lib/api";
import ConfirmModal from "../../components/ConfirmModal";
import { usePermissions } from "../../hooks/usePermissions";
import { useRecordDrawer } from "../../hooks/useRecordDrawer";
import { PageLayout } from "../../components/PageLayout";
import { ContentToolbar } from "../../components/ContentToolbar";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";
import { SupplierFormFields, type SupplierFormState } from "./SupplierFormFields";
import { TextField } from "../../components/TextField";
import { HeaderButton } from "../../components/HeaderButton";

interface Supplier {
  id: number; supplier_code: string | null; name: string; contact_name: string | null;
  email: string | null; phone: string | null; address: string | null;
  notes: string | null; is_active: boolean; created_at: string;
}

const emptyForm: SupplierFormState = {
  name: "", contact_name: "", email: "", phone: "", address: "", notes: "",
};

const toForm = (s: Supplier): SupplierFormState => ({
  name: s.name,
  contact_name: s.contact_name ?? "",
  email: s.email ?? "",
  phone: s.phone ?? "",
  address: s.address ?? "",
  notes: s.notes ?? "",
});

export default function SuppliersPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const navigate = useNavigate();
  const exportLock = useRef(false);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  // 新規作成モーダル
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<SupplierFormState>(emptyForm);
  // 編集ドロワー（useRecordDrawer フック）
  const { drawerOpen, editId, editForm, setEditForm, handleRowClick, closeDrawer } =
    useRecordDrawer<Supplier, SupplierFormState>({ toForm, emptyForm });

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<Supplier | null>(null);
  // QA r7: 47 件全件閲覧のため pagination 追加。backend per_page max=100
  const [page, setPage] = useState(1);
  const PER_PAGE = 100;
  const [hasNext, setHasNext] = useState(false);
  // 検索（MasterListEditor パターンと統一）
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");

  const load = async () => {
    try {
      const params = new URLSearchParams({ page: String(page), per_page: String(PER_PAGE) });
      if (search.trim()) params.set("search", search.trim());
      const data = await api.get<Supplier[]>(`/suppliers?${params.toString()}`);
      setSuppliers(data);
      setHasNext(data.length === PER_PAGE);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [page, search]);

  /* ── 新規作成（Modal） ── */
  const handleCreateSubmit = async (e: FormEvent) => {
    e.preventDefault(); setError("");
    const toNull = (v: string) => v || null;
    const payload = { name: createForm.name, contact_name: toNull(createForm.contact_name), email: toNull(createForm.email), phone: toNull(createForm.phone), address: toNull(createForm.address), notes: toNull(createForm.notes) };
    try {
      await api.post("/suppliers", payload);
      setShowCreate(false); setCreateForm(emptyForm); load();
    } catch (e) { setError(e instanceof Error ? e.message : t("common.saveError")); }
  };

  /* ── ドロワー内編集保存 ── */
  const handleEditSubmit = async (e: FormEvent) => {
    e.preventDefault(); setError("");
    if (!editId) return;
    const toNull = (v: string) => v || null;
    const payload = { name: editForm.name, contact_name: toNull(editForm.contact_name), email: toNull(editForm.email), phone: toNull(editForm.phone), address: toNull(editForm.address), notes: toNull(editForm.notes) };
    try {
      await api.patch(`/suppliers/${editId}`, payload);
      closeDrawer(); load();
    } catch (e) { setError(e instanceof Error ? e.message : t("common.saveError")); }
  };

  const performDelete = async () => {
    if (!deleteTarget) return;
    setDeleteTarget(null);
    try { await api.delete(`/suppliers/${deleteTarget.id}`); load(); }
    catch (e) { setError(e instanceof Error ? e.message : t("common.deleteError")); }
  };

  async function handleExport() {
    if (exportLock.current) return;
    exportLock.current = true;
    try {
      const blob = await api.getBlob("/suppliers/export");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `suppliers_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      exportLock.current = false;
    }
  }

  return (
    <PageLayout
      navKey="nav.suppliers"
      subtitleKey="suppliers.subtitle"
      headerAction={
        <>
          {hasPermission("suppliers.view") && (
            <HeaderButton variant="secondary" onClick={() => void handleExport()} data-testid="suppliers-export">
              {t("supplierCsv.exportButton")}
            </HeaderButton>
          )}
          {hasPermission("suppliers.create") && (
            <HeaderButton variant="primary" onClick={() => { setShowCreate(true); setCreateForm(emptyForm); }} data-testid="suppliers-new">
              {t("suppliers.newSupplier")}
            </HeaderButton>
          )}
          {hasPermission("suppliers.create") && (
            <HeaderButton variant="primary" onClick={() => navigate("/suppliers/import")} data-testid="suppliers-import">
              {t("supplierCsv.importButton")}
            </HeaderButton>
          )}
        </>
      }
    >
      {error && <div className="error-message">{error}</div>}

      {/* 検索バー + 新規作成ボタン（MasterListEditor パターンと統一） */}
      <ContentToolbar
        left={
          <form
            className="search-bar"
            style={{ display: "flex", gap: "var(--space-2)", alignItems: "center" }}
            onSubmit={(e) => {
              e.preventDefault();
              setPage(1);
              setSearch(searchInput.trim());
            }}
          >
            <TextField
              type="text"
              size="md"
              placeholder={t("common.search")}
              aria-label={t("common.search")}
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              data-testid="suppliers-search"
            />
            <button type="submit" className="btn-secondary field-h-md" data-testid="suppliers-search-btn">
              {t("common.search")}
            </button>
            {search && (
              <button
                type="button"
                className="btn-sm"
                onClick={() => { setSearch(""); setSearchInput(""); setPage(1); }}
              >
                {t("common.clear")}
              </button>
            )}
          </form>
        }
        right={undefined}
      />

      {/* 新規作成 Modal（既存 UX 保持） */}
      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title={t("suppliers.newSupplier")}
        size="md"
      >
        <form onSubmit={handleCreateSubmit}>
          <SupplierFormFields
            form={createForm}
            onChange={(field, value) => setCreateForm(prev => ({ ...prev, [field]: value }))}
          />
          <div className="form-actions">
            <Button variant="secondary" size="md" type="button" onClick={() => setShowCreate(false)}>{t("common.cancel")}</Button>
            <Button variant="primary" size="md" type="submit">{t("common.register")}</Button>
          </div>
        </form>
      </Modal>

      {/* 編集 Drawer（行クリックで開く・useRecordDrawer フック） */}
      <Drawer
        open={drawerOpen}
        onClose={closeDrawer}
        title={t("suppliers.editSupplier")}
        onOpenFullPage={editId ? () => { closeDrawer(); navigate(`/suppliers/${editId}/edit`); } : undefined}
      >
        <form onSubmit={handleEditSubmit}>
          <SupplierFormFields
            form={editForm}
            onChange={(field, value) => setEditForm(prev => ({ ...prev, [field]: value }))}
          />
          <div className="form-actions">
            <Button variant="secondary" size="md" type="button" onClick={closeDrawer}>{t("common.cancel")}</Button>
            <Button variant="primary" size="md" type="submit">{t("common.update")}</Button>
          </div>
        </form>
      </Drawer>

      {loading ? <div className="loading">{t("common.loading")}</div> : (() => {
        const columns: DataTableColumn<Supplier>[] = [
          { key: "supplier_code", header: t("common.code"), renderCell: (s) => <span className="mono">{s.supplier_code || "-"}</span> },
          { key: "name", header: t("suppliers.supplierName") },
          { key: "contact_name", header: t("suppliers.colContact"), renderCell: (s) => s.contact_name || "-" },
          { key: "email", header: t("common.email"), renderCell: (s) => s.email || "-" },
          { key: "phone", header: t("common.phone"), renderCell: (s) => s.phone || "-" },
          { key: "actions", header: t("common.actions"), renderCell: (s) => (
            <span className="actions">
              {hasPermission("suppliers.update") && <button className="btn-sm" onClick={(e) => { e.stopPropagation(); handleRowClick(s); }}>{t("common.edit")}</button>}
              {hasPermission("suppliers.delete") && <button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(s); }}>{t("suppliers.deleteSupplier")}</button>}
            </span>
          )},
        ];
        return (
          <DataTable<Supplier>
            columns={columns}
            data={suppliers}
            rowKey={(s) => String(s.id)}
            onRowClick={hasPermission("suppliers.update") ? (s) => handleRowClick(s) : undefined}
            emptyState={t("suppliers.noSuppliers")}
          />
        );
      })()}

      {/* QA r7: 件数表示は常時、前/次 button は pagination 必要時のみ。
          管理センター内 (二重 PageLayout) でも見切れないよう sticky bottom。 */}
      {!loading && suppliers.length > 0 && (
        <div
          className="pagination"
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: "var(--space-3)",
            padding: "var(--space-3) 0",
            position: "sticky",
            bottom: 0,
            background: "var(--bg-surface)",
            borderTop: "1px solid var(--border-color)",
            zIndex: 1,
          }}
          data-testid="suppliers-pagination"
        >
          {(page > 1 || hasNext) && (
            <button
              className="btn-sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              data-testid="suppliers-page-prev"
            >
              {t("common.prevPage")}
            </button>
          )}
          <span style={{ color: "var(--text-secondary)" }} data-testid="suppliers-page-info">
            {t("suppliers.pageLabel", { page, count: suppliers.length })}
          </span>
          {(page > 1 || hasNext) && (
            <button
              className="btn-sm"
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasNext}
              data-testid="suppliers-page-next"
            >
              {t("common.nextPage")}
            </button>
          )}
        </div>
      )}

      <ConfirmModal open={!!deleteTarget} title={t("suppliers.deleteSupplier")} message={<><strong>{deleteTarget?.name}</strong>{t("suppliers.disableConfirmSuffix")}</>} confirmLabel={t("suppliers.disableLabel")} danger onConfirm={performDelete} onCancel={() => setDeleteTarget(null)} />
    </PageLayout>
  );
}
