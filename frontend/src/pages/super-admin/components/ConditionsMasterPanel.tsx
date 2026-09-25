/**
 * ConditionsMasterPanel — 状態マスタパネル（AnalysisRulesPage の hub-content 内で使用）
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型クラスのみ使用。
 */
import { useCallback, useEffect, useRef, useState, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../../lib/api";
import { ContentToolbar } from "../../../components/ContentToolbar";
import { HeaderButton } from "../../../components/HeaderButton";
import { DataTable, type DataTableColumn } from "../../../components/DataTable";
import { EmptyState } from "../../../components/EmptyState";
import { TextField } from "../../../components/TextField";
import { Modal } from "../../../components/Modal";
import { Drawer } from "../../../components/Drawer";
import ConfirmModal from "../../../components/ConfirmModal";
import { Check } from "../../../constants/icons";

interface ConditionAlias {
  id: number;
  condition_id: number;
  alias_text: string;
  lang: string;
  updated_at: string;
}

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
  const navigate = useNavigate();
  const exportLock = useRef(false);
  const [exporting, setExporting] = useState(false);
  const [items, setItems] = useState<CentralCondition[]>([]);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());

  async function downloadExport() {
    if (exportLock.current) return;
    exportLock.current = true; setExporting(true); setError("");
    let url: string | undefined;
    const anchor = document.createElement("a");
    try {
      const blob = await api.getBlob("/super-admin/conditions/export");
      url = URL.createObjectURL(blob); anchor.href = url;
      anchor.download = "conditions-export.csv";
      document.body.appendChild(anchor); anchor.click();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      anchor.remove(); if (url) URL.revokeObjectURL(url); exportLock.current = false; setExporting(false);
    }
  }

  // 編集/新規ポップアップ
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<ConditionFormState>(emptyForm);
  const [editId, setEditId] = useState<number | null>(null);

  // 一括削除確認
  const [confirmDelete, setConfirmDelete] = useState(false);

  // 別名管理（編集モーダル内）
  const [aliasesFor, setAliasesFor] = useState<{ id: number; code: string } | null>(null);
  const [aliases, setAliases] = useState<ConditionAlias[]>([]);
  const [aliasForm, setAliasForm] = useState({ alias_text: "", lang: "ja" });

  const conditionsFormRef = useRef<HTMLFormElement>(null);
  const aliasFormRef = useRef<HTMLFormElement>(null);

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

  // --- aliases ---
  const openAliases = async () => {
    if (editId === null) return;
    setAliasesFor({ id: editId, code: form.code });
    try {
      const data = await api.get<ConditionAlias[]>(`/super-admin/conditions/${editId}/aliases`);
      setAliases(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  };

  const addAlias = async (e: FormEvent) => {
    e.preventDefault();
    if (!aliasesFor) return;
    try {
      await api.post(`/super-admin/conditions/${aliasesFor.id}/aliases`, {
        condition_id: aliasesFor.id,
        ...aliasForm,
      });
      setAliasForm({ alias_text: "", lang: "ja" });
      setAliases(await api.get<ConditionAlias[]>(`/super-admin/conditions/${aliasesFor.id}/aliases`));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    }
  };

  const deleteAlias = async (id: number) => {
    if (!aliasesFor) return;
    try {
      await api.delete(`/super-admin/conditions/aliases/${id}`);
      setAliases(await api.get<ConditionAlias[]>(`/super-admin/conditions/${aliasesFor.id}/aliases`));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.deleteError"));
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
  const fa = "superAdmin.conditionsAdmin";

  const columns: DataTableColumn<CentralCondition>[] = [
    { key: "canonical", header: t(`${f}.canonical`) },
    { key: "app_kubun", header: t(`${f}.appKubun`), renderCell: row => row.app_kubun ?? "—" },
    { key: "priority", header: t(`${f}.priority`), renderCell: row => row.priority ?? "—" },
    {
      key: "is_active",
      header: t(`${f}.isActive`),
      renderCell: row => row.is_active ? <Check size={16} /> : "—",
    },
  ];

  return (
    <>
      <ContentToolbar
        right={
          <>
            <HeaderButton variant="secondary" disabled={exporting} data-testid="conditions-export" onClick={() => void downloadExport()}>
              {t(exporting ? "common.loading" : "conditionCsv.exportButton")}
            </HeaderButton>
            <HeaderButton variant="primary" data-testid="conditions-import" onClick={() => navigate("/super-admin/masters/conditions/import")}>
              {t("conditionCsv.importButton")}
            </HeaderButton>
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

      {/* 編集/新規 ドロワー */}
      <Drawer
        open={showForm}
        onClose={() => setShowForm(false)}
        title={editId ? t("common.edit") : t("common.create")}
        footer={
          <>
            <div style={{ marginLeft: "auto", display: "flex", gap: "var(--space-2)" }}>
              <HeaderButton variant="secondary" onClick={() => setShowForm(false)}>{t("common.back")}</HeaderButton>
              <HeaderButton variant="primary" onClick={() => conditionsFormRef.current?.requestSubmit()}>{editId ? t("common.update") : t("common.create")}</HeaderButton>
            </div>
          </>
        }
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
            {editId !== null && (
              <div style={{ gridColumn: "1 / -1" }}>
                <HeaderButton
                  variant="secondary"
                  data-testid="condition-open-aliases"
                  onClick={() => { void openAliases(); }}
                >
                  {t(`${fa}.aliases`)}
                </HeaderButton>
              </div>
            )}
          </div>
        </form>
      </Drawer>

      {/* 別名管理モーダル */}
      <Modal
        open={!!aliasesFor}
        onClose={() => setAliasesFor(null)}
        title={aliasesFor ? `${t(`${fa}.aliases`)} \u2014 ${aliasesFor.code}` : ""}
        size="md"
      >
        {/* ui-allow: alias table is a small inline form, not a data listing */}
        <form
          ref={aliasFormRef}
          onSubmit={e => { void addAlias(e); }}
          style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: "var(--space-2)", margin: "var(--space-2) 0" }}
        >
          <TextField
            label={t(`${fa}.aliasText`)}
            value={aliasForm.alias_text}
            onChange={e => setAliasForm({ ...aliasForm, alias_text: e.target.value })}
            required
          />
          <TextField
            label={t(`${fa}.aliasLang`)}
            value={aliasForm.lang}
            onChange={e => setAliasForm({ ...aliasForm, lang: e.target.value })}
            required
          />
          <HeaderButton
            variant="primary"
            onClick={() => aliasFormRef.current?.requestSubmit()}
          >
            {t(`${fa}.addAlias`)}
          </HeaderButton>
        </form>
        <table className="data-table">
          <thead>
            <tr>
              <th>{t(`${fa}.aliasText`)}</th>
              <th>{t(`${fa}.aliasLang`)}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {aliases.map(a => (
              <tr key={a.id}>
                <td>{a.alias_text}</td>
                <td>{a.lang}</td>
                <td style={{ textAlign: "right" }}>
                  <HeaderButton
                    variant="secondary"
                    onClick={() => { void deleteAlias(a.id); }}
                  >
                    {t(`${fa}.deleteAlias`)}
                  </HeaderButton>
                </td>
              </tr>
            ))}
            {aliases.length === 0 && (
              <tr><td colSpan={3} className="empty">{t("common.noData")}</td></tr>
            )}
          </tbody>
        </table>
        <div style={{ marginTop: "var(--space-2)", textAlign: "right" }}>
          <HeaderButton variant="secondary" onClick={() => setAliasesFor(null)}>
            {t("common.close")}
          </HeaderButton>
        </div>
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
