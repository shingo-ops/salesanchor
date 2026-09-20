/**
 * ConditionsMasterPanel — 状態マスタパネル（AnalysisRulesPage の hub-content 内で使用）
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型クラスのみ使用。
 */
import { useCallback, useEffect, useRef, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../../lib/api";
import { ContentToolbar } from "../../../components/ContentToolbar";
import { HeaderButton } from "../../../components/HeaderButton";
import { DataTable, type DataTableColumn } from "../../../components/DataTable";
import { EmptyState } from "../../../components/EmptyState";
import { TextField } from "../../../components/TextField";
import { Modal } from "../../../components/Modal";
import ConfirmModal from "../../../components/ConfirmModal";
import { Check } from "../../../constants/icons";

interface CentralCondition {
  id: number;
  code: string;
  canonical: string;
  app_kubun: string | null;
  is_active: boolean;
  priority: number | null;
  search_kw: string;
  exclude_kw: string;
}

type ConditionFormState = {
  code: string;
  canonical: string;
  app_kubun: string;
  is_active: boolean;
  priority: string;
  search_kw: string;
  exclude_kw: string;
};

const emptyForm: ConditionFormState = {
  code: "",
  canonical: "",
  app_kubun: "",
  is_active: true,
  priority: "",
  search_kw: "",
  exclude_kw: "",
};

const PER_PAGE = 50;

export function ConditionsMasterPanel() {
  const { t } = useTranslation();
  const [items, setItems] = useState<CentralCondition[]>([]);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());

  // 編集/新規ポップアップ
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<ConditionFormState>(emptyForm);
  const [editId, setEditId] = useState<number | null>(null);

  // 一括削除確認
  const [confirmDelete, setConfirmDelete] = useState(false);

  const conditionsFormRef = useRef<HTMLFormElement>(null);

  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams({ page: String(page), per_page: String(PER_PAGE) });
      const data = await api.get<CentralCondition[]>(`/super-admin/conditions?${params.toString()}`);
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  }, [page, t]);

  useEffect(() => { void load(); }, [load]);

  const openCreate = () => { setEditId(null); setForm(emptyForm); setShowForm(true); };
  const openEdit = (c: CentralCondition) => {
    setEditId(c.id);
    setForm({
      code: c.code,
      canonical: c.canonical,
      app_kubun: c.app_kubun ?? "",
      is_active: c.is_active,
      priority: c.priority != null ? String(c.priority) : "",
      search_kw: c.search_kw,
      exclude_kw: c.exclude_kw,
    });
    setShowForm(true);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const payload = {
      code: form.code,
      canonical: form.canonical,
      app_kubun: form.app_kubun || null,
      is_active: form.is_active,
      priority: form.priority !== "" ? parseInt(form.priority, 10) : null,
      search_kw: form.search_kw,
      exclude_kw: form.exclude_kw,
    };
    try {
      if (editId) {
        await api.patch(`/super-admin/conditions/${editId}`, payload);
      } else {
        await api.post("/super-admin/conditions", payload);
      }
      setShowForm(false);
      setForm(emptyForm);
      setEditId(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    }
  };

  const bulkDelete = async () => {
    setConfirmDelete(false);
    const selectedIds = Array.from(selectedKeys).map(Number);
    const results = await Promise.allSettled(
      selectedIds.map((id) => api.delete(`/super-admin/conditions/${id}`)),
    );
    try {
      if (results.some((r) => r.status === "rejected")) {
        setError(t("common.deleteError"));
      }
      setSelectedKeys(new Set());
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
    }
  };

  const f = "superAdmin.conditionsAdmin.fields";

  const columns: DataTableColumn<CentralCondition>[] = [
    { key: "code", header: t(`${f}.code`) },
    { key: "canonical", header: t(`${f}.canonical`) },
    { key: "app_kubun", header: t(`${f}.appKubun`), renderCell: row => row.app_kubun ?? "—" },
    { key: "priority", header: t(`${f}.priority`), renderCell: row => row.priority ?? "—" },
    {
      key: "is_active",
      header: t(`${f}.isActive`),
      renderCell: row => row.is_active ? <Check size={16} /> : "—",
    },
    {
      key: "_edit",
      header: "",
      renderCell: row => (
        <HeaderButton variant="secondary" data-testid={`condition-edit-${row.id}`} onClick={() => openEdit(row)}>
          {t("common.edit")}
        </HeaderButton>
      ),
    },
  ];

  return (
    <>
      <ContentToolbar
        right={
          <>
            <HeaderButton variant="primary" data-testid="conditions-new" onClick={openCreate}>
              {t("superAdmin.conditionsAdmin.newCondition")}
            </HeaderButton>
            <HeaderButton variant="secondary" disabled={selectedKeys.size === 0} data-testid="conditions-bulk-delete" onClick={() => setConfirmDelete(true)}>
              {t("common.delete")}
            </HeaderButton>
          </>
        }
      />
      {error && <p role="alert">{error}</p>}
      <DataTable
        columns={columns}
        data={items}
        rowKey={row => String(row.id)}
        selectable
        selectedKeys={selectedKeys}
        onSelectChange={setSelectedKeys}
        onRowClick={row => openEdit(row)}
        emptyState={<EmptyState title={t("common.noData")} size="compact" />}
        page={page}
        hasNextPage={items.length >= PER_PAGE}
        onPageChange={setPage}
        prevPageLabel={t("common.prevPage")}
        nextPageLabel={t("common.nextPage")}
      />

      {/* 編集/新規 ポップアップ */}
      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title={editId ? t("common.edit") : t("common.create")}
        size="lg"
      >
        <form ref={conditionsFormRef} onSubmit={e => { void submit(e); }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3) var(--space-4)" }}>
            <div className="form-group">
              <TextField
                label={`${t(`${f}.code`)} *`}
                value={form.code}
                onChange={e => setForm({ ...form, code: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <TextField
                label={`${t(`${f}.canonical`)} *`}
                value={form.canonical}
                onChange={e => setForm({ ...form, canonical: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <TextField
                label={t(`${f}.appKubun`)}
                value={form.app_kubun}
                onChange={e => setForm({ ...form, app_kubun: e.target.value })}
              />
            </div>
            <div className="form-group">
              <TextField
                type="number"
                label={t(`${f}.priority`)}
                value={form.priority}
                onChange={e => setForm({ ...form, priority: e.target.value })}
              />
            </div>
            <div className="form-group" style={{ gridColumn: "1 / -1" }}>
              <label style={{ display: "block", marginBottom: "var(--space-1)" }}>
                {t(`${f}.searchKw`)}
              </label>
              <textarea
                value={form.search_kw}
                onChange={e => setForm({ ...form, search_kw: e.target.value })}
                rows={3}
                style={{ width: "100%", resize: "vertical" }}
              />
            </div>
            <div className="form-group" style={{ gridColumn: "1 / -1" }}>
              <label style={{ display: "block", marginBottom: "var(--space-1)" }}>
                {t(`${f}.excludeKw`)}
              </label>
              <textarea
                value={form.exclude_kw}
                onChange={e => setForm({ ...form, exclude_kw: e.target.value })}
                rows={3}
                style={{ width: "100%", resize: "vertical" }}
              />
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <input type="checkbox" checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} />
              {t(`${f}.isActive`)}
            </label>
          </div>
          <div className="form-actions">
            <HeaderButton variant="secondary" onClick={() => setShowForm(false)}>{t("common.cancel")}</HeaderButton>
            <HeaderButton variant="primary" onClick={() => conditionsFormRef.current?.requestSubmit()}>{editId ? t("common.update") : t("common.create")}</HeaderButton>
          </div>
        </form>
      </Modal>

      <ConfirmModal
        open={confirmDelete}
        title={t("common.delete")}
        message={t("superAdmin.conditionsAdmin.bulkDeleteConfirm")}
        confirmLabel={t("common.delete")}
        danger
        onConfirm={() => { void bulkDelete(); }}
        onCancel={() => setConfirmDelete(false)}
      />
    </>
  );
}
