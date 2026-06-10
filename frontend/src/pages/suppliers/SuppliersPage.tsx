import { useEffect, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Modal } from "../../components/Modal";
import { api } from "../../lib/api";
import ConfirmModal from "../../components/ConfirmModal";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";

interface Supplier {
  id: number; supplier_code: string | null; name: string; contact_name: string | null;
  email: string | null; phone: string | null; address: string | null;
  notes: string | null; is_active: boolean; created_at: string;
}

const emptyForm = { name: "", contact_name: "", email: "", phone: "", address: "", notes: "" };

export default function SuppliersPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<Supplier | null>(null);
  // QA r7: 47 件全件閲覧のため pagination 追加。backend per_page max=100
  const [page, setPage] = useState(1);
  const PER_PAGE = 100;
  const [hasNext, setHasNext] = useState(false);

  const load = async () => {
    try {
      const data = await api.get<Supplier[]>(`/suppliers?page=${page}&per_page=${PER_PAGE}`);
      setSuppliers(data);
      setHasNext(data.length === PER_PAGE);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [page]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault(); setError("");
    const toNull = (v: string) => v || null;
    const payload = { name: form.name, contact_name: toNull(form.contact_name), email: toNull(form.email), phone: toNull(form.phone), address: toNull(form.address), notes: toNull(form.notes) };
    try {
      if (editId) await api.patch(`/suppliers/${editId}`, payload);
      else await api.post("/suppliers", payload);
      setShowForm(false); setEditId(null); setForm(emptyForm); load();
    } catch (e) { setError(e instanceof Error ? e.message : t("common.saveError")); }
  };

  const handleEdit = (s: Supplier) => {
    setEditId(s.id);
    setForm({ name: s.name, contact_name: s.contact_name || "", email: s.email || "", phone: s.phone || "", address: s.address || "", notes: s.notes || "" });
    setShowForm(true);
  };

  const performDelete = async () => {
    if (!deleteTarget) return;
    setDeleteTarget(null);
    try { await api.delete(`/suppliers/${deleteTarget.id}`); load(); }
    catch (e) { setError(e instanceof Error ? e.message : t("common.deleteError")); }
  };

  return (
    <PageLayout
      navKey="nav.suppliers"
      subtitleKey="suppliers.subtitle"
      headerAction={hasPermission("suppliers.create") ? (
        <div className="page-header-actions">
          <button className="btn-primary" onClick={() => { setShowForm(true); setEditId(null); setForm(emptyForm); }}>{t("suppliers.newSupplier")}</button>
        </div>
      ) : undefined}
    >
      {error && <div className="error-message">{error}</div>}
      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title={editId ? t("suppliers.editSupplier") : t("suppliers.newSupplier")}
        size="md"
      >
        <form onSubmit={handleSubmit}>
          <div className="form-group"><label>{t("suppliers.supplierName")} *</label><input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
          <div className="form-group"><label>{t("suppliers.contactName")}</label><input value={form.contact_name} onChange={e => setForm({ ...form, contact_name: e.target.value })} /></div>
          <div className="form-group"><label>{t("common.email")}</label><input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></div>
          <div className="form-group"><label>{t("common.phone")}</label><input value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} /></div>
          <div className="form-group"><label>{t("suppliers.address")}</label><textarea value={form.address} onChange={e => setForm({ ...form, address: e.target.value })} /></div>
          <div className="form-group"><label>{t("common.notes")}</label><textarea value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></div>
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>{t("common.cancel")}</button>
            <button type="submit" className="btn-primary">{editId ? t("common.update") : t("common.register")}</button>
          </div>
        </form>
      </Modal>
      {loading ? <div className="loading">{t("common.loading")}</div> : (() => {
        const columns: DataTableColumn<Supplier>[] = [
          { key: "supplier_code", header: t("common.code"), renderCell: (s) => <span className="mono">{s.supplier_code || "-"}</span> },
          { key: "name", header: t("suppliers.supplierName") },
          { key: "contact_name", header: t("suppliers.colContact"), renderCell: (s) => s.contact_name || "-" },
          { key: "email", header: t("common.email"), renderCell: (s) => s.email || "-" },
          { key: "phone", header: t("common.phone"), renderCell: (s) => s.phone || "-" },
          { key: "actions", header: t("common.actions"), renderCell: (s) => (
            <span className="actions">
              {hasPermission("suppliers.update") && <button className="btn-sm" onClick={() => handleEdit(s)}>{t("common.edit")}</button>}
              {hasPermission("suppliers.delete") && <button className="btn-sm btn-danger" onClick={() => setDeleteTarget(s)}>{t("suppliers.deleteSupplier")}</button>}
            </span>
          )},
        ];
        return (
          <DataTable<Supplier>
            columns={columns}
            data={suppliers}
            rowKey={(s) => String(s.id)}
            onRowClick={hasPermission("suppliers.update") ? (s) => handleEdit(s) : undefined}
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
