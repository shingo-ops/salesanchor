/**
 * ConditionsPage — テナント固有状態マスタ管理（管理センター内）
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型クラスのみ使用。
 */
import { useEffect, useRef, useState, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { Modal } from "../../components/Modal";
import ConfirmModal from "../../components/ConfirmModal";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";
import { ContentToolbar } from "../../components/ContentToolbar";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { TextField } from "../../components/TextField";
import { HeaderButton } from "../../components/HeaderButton";
import { STATUS_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";

interface ConditionEntry {
  id: number;
  code: string;
  canonical: string;
  app_kubun: string;
  is_active: boolean;
  priority: number;
  search_kw: string;
  exclude_kw: string;
  tenant_id: number | null;
  created_at: string;
  updated_at: string;
}

type ConditionFormState = {
  code: string;
  canonical: string;
  app_kubun: string;
  is_active: boolean;
  priority: number;
  search_kw: string;
  exclude_kw: string;
};

const emptyForm: ConditionFormState = {
  code: "",
  canonical: "",
  app_kubun: "",
  is_active: true,
  priority: 100,
  search_kw: "",
  exclude_kw: "",
};

const toForm = (c: ConditionEntry): ConditionFormState => ({
  code: c.code,
  canonical: c.canonical,
  app_kubun: c.app_kubun ?? "",
  is_active: c.is_active,
  priority: c.priority,
  search_kw: c.search_kw ?? "",
  exclude_kw: c.exclude_kw ?? "",
});

export default function ConditionsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { hasPermission } = usePermissions();
  const exportLock = useRef(false);
  const [exporting, setExporting] = useState(false);
  const [items, setItems] = useState<ConditionEntry[]>([]);
  const [catalog, setCatalog] = useState<ConditionEntry[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const PER_PAGE = 50;
  const [hasNext, setHasNext] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");

  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<ConditionFormState>(emptyForm);

  async function downloadExport() {
    if (exportLock.current) return;
    exportLock.current = true; setExporting(true); setError("");
    let url: string | undefined;
    const anchor = document.createElement("a");
    try {
      const blob = await api.getBlob("/conditions/export");
      url = URL.createObjectURL(blob); anchor.href = url;
      anchor.download = "conditions-export.csv";
      document.body.appendChild(anchor); anchor.click();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      anchor.remove(); if (url) URL.revokeObjectURL(url); exportLock.current = false; setExporting(false);
    }
  }

  const [editId, setEditId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<ConditionFormState>(emptyForm);
  const [showEdit, setShowEdit] = useState(false);

  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [showBulkDelete, setShowBulkDelete] = useState(false);

  const createFormRef = useRef<HTMLFormElement>(null);
  const editFormRef = useRef<HTMLFormElement>(null);

  const f = "conditionsMaster";

  const load = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), per_page: String(PER_PAGE) });
      if (search.trim()) params.set("search", search.trim());
      const data = await api.get<ConditionEntry[]>(`/conditions?${params.toString()}`);
      setItems(data);
      setHasNext(data.length === PER_PAGE);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  };

  const loadCatalog = async () => {
    try {
      const data = await api.get<ConditionEntry[]>("/conditions/catalog");
      setCatalog(data);
    } catch {
      // catalog is supplementary; silent fail
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [page, search]);
  useEffect(() => { loadCatalog(); }, []);

  const handleCreateSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.post("/conditions", createForm);
      setShowCreate(false);
      setCreateForm(emptyForm);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  const handleEditSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!editId) return;
    try {
      await api.patch(`/conditions/${editId}`, editForm);
      setShowEdit(false);
      setEditId(null);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  const performBulkDelete = async () => {
    setShowBulkDelete(false);
    try {
      await Promise.all(
        Array.from(selected).map(id => api.delete(`/conditions/${id}`))
      );
      setSelected(new Set());
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
    }
  };

  const openEdit = (c: ConditionEntry) => {
    setEditId(c.id);
    setEditForm(toForm(c));
    setShowEdit(true);
  };

  const toggleSelect = (id: number) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const columns: DataTableColumn<ConditionEntry>[] = [
    {
      key: "select",
      header: "",
      renderCell: c => (
        hasPermission("conditions.delete") ? (
          <input
            type="checkbox"
            checked={selected.has(c.id)}
            onChange={() => toggleSelect(c.id)}
            onClick={e => e.stopPropagation()}
            aria-label={t(`${f}.fields.code`)}
          />
        ) : null
      ),
    },
    { key: "code", header: t(`${f}.fields.code`), renderCell: c => <span className="mono">{c.code}</span> },
    { key: "canonical", header: t(`${f}.fields.canonical`) },
    { key: "app_kubun", header: t(`${f}.fields.appKubun`) },
    { key: "priority", header: t(`${f}.fields.priority`) },
    { key: "search_kw", header: t(`${f}.fields.searchKw`), renderCell: c => <span style={{ whiteSpace: "pre-wrap", maxWidth: "var(--modal-wide-w)", display: "inline-block" }}>{c.search_kw}</span> },
    { key: "exclude_kw", header: t(`${f}.fields.excludeKw`), renderCell: c => <span style={{ whiteSpace: "pre-wrap", maxWidth: "var(--modal-wide-w)", display: "inline-block" }}>{c.exclude_kw}</span> },
    {
      key: "is_active",
      header: t(`${f}.fields.isActive`),
      renderCell: c => c.is_active ? <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" /> : "-",
    },
    {
      key: "actions",
      header: t("common.actions"),
      renderCell: c => (
        <span className="actions">
          {hasPermission("conditions.update") && (
            <button className="btn-sm" onClick={(e) => { e.stopPropagation(); openEdit(c); }}>
              {t("common.edit")}
            </button>
          )}
        </span>
      ),
    },
  ];

  const catalogColumns: DataTableColumn<ConditionEntry>[] = [
    { key: "code", header: t(`${f}.fields.code`), renderCell: c => <span className="mono">{c.code}</span> },
    { key: "canonical", header: t(`${f}.fields.canonical`) },
    { key: "app_kubun", header: t(`${f}.fields.appKubun`) },
    { key: "priority", header: t(`${f}.fields.priority`) },
    {
      key: "is_active",
      header: t(`${f}.fields.isActive`),
      renderCell: c => c.is_active ? <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" /> : "-",
    },
  ];

  const renderFormFields = (
    form: ConditionFormState,
    setForm: (f: ConditionFormState) => void,
  ) => (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3) var(--space-4)" }}>
      <div className="form-group">
        <TextField
          label={`${t(`${f}.fields.code`)} *`}
          value={form.code}
          onChange={e => setForm({ ...form, code: e.target.value })}
          required
        />
      </div>
      <div className="form-group">
        <TextField
          label={`${t(`${f}.fields.canonical`)} *`}
          value={form.canonical}
          onChange={e => setForm({ ...form, canonical: e.target.value })}
          required
        />
      </div>
      <div className="form-group">
        <TextField
          label={t(`${f}.fields.appKubun`)}
          value={form.app_kubun}
          onChange={e => setForm({ ...form, app_kubun: e.target.value })}
        />
      </div>
      <div className="form-group">
        <TextField
          label={t(`${f}.fields.priority`)}
          type="number"
          value={String(form.priority)}
          onChange={e => setForm({ ...form, priority: Number(e.target.value) })}
          required
        />
      </div>
      <div className="form-group" style={{ gridColumn: "1 / -1" }}>
        <label className="field-label">{t(`${f}.fields.searchKw`)}</label>
        {/* ui-allow: multi-line keyword input; TextField does not support textarea variant (#3594) */}
        <textarea
          className="field field-h-md"
          style={{ height: "80px", resize: "vertical", width: "100%" }}
          value={form.search_kw}
          onChange={e => setForm({ ...form, search_kw: e.target.value })}
        />
      </div>
      <div className="form-group" style={{ gridColumn: "1 / -1" }}>
        <label className="field-label">{t(`${f}.fields.excludeKw`)}</label>
        {/* ui-allow: multi-line keyword input; TextField does not support textarea variant (#3594) */}
        <textarea
          className="field field-h-md"
          style={{ height: "80px", resize: "vertical", width: "100%" }}
          value={form.exclude_kw}
          onChange={e => setForm({ ...form, exclude_kw: e.target.value })}
        />
      </div>
      <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", gridColumn: "1 / -1" }}>
        <input
          type="checkbox"
          checked={form.is_active}
          onChange={e => setForm({ ...form, is_active: e.target.checked })}
        />
        {t(`${f}.fields.isActive`)}
      </label>
    </div>
  );

  return (
    <PageLayout
      navKey="nav.conditionsMaster"
      subtitleKey={`${f}.subtitle`}
      headerAction={
        hasPermission("conditions.view") ? (
          <>
            <HeaderButton variant="secondary" disabled={exporting} data-testid="conditions-export" onClick={() => void downloadExport()}>
              {t(exporting ? "common.loading" : "conditionCsv.exportButton")}
            </HeaderButton>
            <HeaderButton variant="primary" data-testid="conditions-import" onClick={() => navigate("/management-center/conditions/import")}>
              {t("conditionCsv.importButton")}
            </HeaderButton>
            {hasPermission("conditions.create") && (
              <HeaderButton
                variant="primary"
                onClick={() => { setShowCreate(true); setCreateForm(emptyForm); }}
                data-testid="conditions-new"
              >
                {t(`${f}.newCondition`)}
              </HeaderButton>
            )}
          </>
        ) : undefined
      }
    >
      {error && <div className="error-message">{error}</div>}

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
              data-testid="conditions-search"
            />
            <button type="submit" className="btn-secondary field-h-md" data-testid="conditions-search-btn">
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
        right={
          selected.size > 0 && hasPermission("conditions.delete") ? (
            <HeaderButton
              variant="secondary"
              onClick={() => setShowBulkDelete(true)}
              data-testid="conditions-bulk-delete"
            >
              {t("common.delete")} ({selected.size})
            </HeaderButton>
          ) : undefined
        }
      />

      {/* 新規作成 Modal */}
      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title={t(`${f}.newCondition`)}
        size="md"
      >
        <form ref={createFormRef} onSubmit={handleCreateSubmit}>
          {renderFormFields(createForm, setCreateForm)}
          <div className="form-actions">
            <HeaderButton variant="secondary" onClick={() => setShowCreate(false)}>
              {t("common.cancel")}
            </HeaderButton>
            <HeaderButton variant="primary" onClick={() => createFormRef.current?.requestSubmit()}>
              {t("common.register")}
            </HeaderButton>
          </div>
        </form>
      </Modal>

      {/* 編集 Modal */}
      <Modal
        open={showEdit}
        onClose={() => setShowEdit(false)}
        title={t("common.edit")}
        size="md"
      >
        <form ref={editFormRef} onSubmit={handleEditSubmit}>
          {renderFormFields(editForm, setEditForm)}
          <div className="form-actions">
            <HeaderButton variant="secondary" onClick={() => setShowEdit(false)}>
              {t("common.cancel")}
            </HeaderButton>
            <HeaderButton variant="primary" onClick={() => editFormRef.current?.requestSubmit()}>
              {t("common.update")}
            </HeaderButton>
          </div>
        </form>
      </Modal>

      {loading ? (
        <div className="loading">{t("common.loading")}</div>
      ) : items.length === 0 ? (
        <div className="empty-state">{t(`${f}.noData`)}</div>
      ) : (
        <DataTable<ConditionEntry>
          columns={columns}
          data={items}
          rowKey={c => String(c.id)}
          onRowClick={hasPermission("conditions.update") ? c => openEdit(c) : undefined}
          emptyState={t(`${f}.noData`)}
        />
      )}

      {!loading && items.length > 0 && (
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
          data-testid="conditions-pagination"
        >
          {(page > 1 || hasNext) && (
            <button
              className="btn-sm"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              data-testid="conditions-page-prev"
            >
              {t("common.prevPage")}
            </button>
          )}
          <span style={{ color: "var(--text-secondary)" }} data-testid="conditions-page-info">
            {t(`${f}.total`, { count: items.length })}
          </span>
          {(page > 1 || hasNext) && (
            <button
              className="btn-sm"
              onClick={() => setPage(p => p + 1)}
              disabled={!hasNext}
              data-testid="conditions-page-next"
            >
              {t("common.nextPage")}
            </button>
          )}
        </div>
      )}

      {/* 共有状態カタログ */}
      {catalog.length > 0 && (
        <div style={{ marginTop: "var(--space-6)" }}>
          <h3 style={{ fontSize: "var(--text-sm)", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "var(--space-2)" }}>
            {t(`${f}.catalogTitle`)}
          </h3>
          <p style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)", marginBottom: "var(--space-3)" }}>
            {t(`${f}.catalogDescription`)}
          </p>
          <DataTable<ConditionEntry>
            columns={catalogColumns}
            data={catalog}
            rowKey={c => String(c.id)}
            emptyState=""
          />
        </div>
      )}

      <ConfirmModal
        open={showBulkDelete}
        title={t("common.delete")}
        message={t(`${f}.bulkDeleteConfirm`)}
        confirmLabel={t("common.delete")}
        danger
        onConfirm={performBulkDelete}
        onCancel={() => setShowBulkDelete(false)}
      />
    </PageLayout>
  );
}
