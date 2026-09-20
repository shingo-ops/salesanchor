/**
 * StatusMasterPage — ステータスマスタ管理（管理センター内）
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型クラスのみ使用。
 */
import { useEffect, useRef, useState, FormEvent } from "react";
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

interface StatusEntry {
  id: number;
  status_id: string;
  canonical: string;
  search_pattern: string;
  exclude_pattern: string;
  priority: number;
  enabled: boolean;
  note: string;
  match_type: string;
  effect: string;
  created_at: string;
  updated_at: string;
}

type StatusFormState = {
  status_id: string;
  canonical: string;
  search_pattern: string;
  exclude_pattern: string;
  priority: number;
  enabled: boolean;
  note: string;
  match_type: string;
  effect: string;
};

const emptyForm: StatusFormState = {
  status_id: "",
  canonical: "",
  search_pattern: "",
  exclude_pattern: "",
  priority: 100,
  enabled: true,
  note: "",
  match_type: "REGEX",
  effect: "OUTPUT",
};

const toForm = (s: StatusEntry): StatusFormState => ({
  status_id: s.status_id,
  canonical: s.canonical,
  search_pattern: s.search_pattern,
  exclude_pattern: s.exclude_pattern,
  priority: s.priority,
  enabled: s.enabled,
  note: s.note,
  match_type: s.match_type,
  effect: s.effect,
});

export default function StatusMasterPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const [items, setItems] = useState<StatusEntry[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const PER_PAGE = 100;
  const [hasNext, setHasNext] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");

  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<StatusFormState>(emptyForm);

  const [editId, setEditId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<StatusFormState>(emptyForm);
  const [showEdit, setShowEdit] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<StatusEntry | null>(null);

  const createFormRef = useRef<HTMLFormElement>(null);
  const editFormRef = useRef<HTMLFormElement>(null);

  const f = "statusMaster";

  const MATCH_TYPE_OPTIONS = [
    { value: "REGEX", label: t(`${f}.matchTypeRegex`) },
    { value: "LITERAL", label: t(`${f}.matchTypeLiteral`) },
    { value: "DEFAULT", label: t(`${f}.matchTypeDefault`) },
  ];

  const EFFECT_OPTIONS = [
    { value: "OUTPUT", label: t(`${f}.effectOutput`) },
    { value: "EXCLUDE", label: t(`${f}.effectExclude`) },
  ];

  const load = async () => {
    try {
      const params = new URLSearchParams({ page: String(page), per_page: String(PER_PAGE) });
      if (search.trim()) params.set("search", search.trim());
      const data = await api.get<StatusEntry[]>(`/status-master?${params.toString()}`);
      setItems(data);
      setHasNext(data.length === PER_PAGE);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [page, search]);

  const handleCreateSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.post("/status-master", createForm);
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
      await api.patch(`/status-master/${editId}`, editForm);
      setShowEdit(false);
      setEditId(null);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  const performDelete = async () => {
    if (!deleteTarget) return;
    setDeleteTarget(null);
    try {
      await api.delete(`/status-master/${deleteTarget.id}`);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
    }
  };

  const openEdit = (s: StatusEntry) => {
    setEditId(s.id);
    setEditForm(toForm(s));
    setShowEdit(true);
  };

  const columns: DataTableColumn<StatusEntry>[] = [
    { key: "status_id", header: t(`${f}.statusId`), renderCell: s => <span className="mono">{s.status_id}</span> },
    { key: "canonical", header: t(`${f}.canonical`) },
    { key: "match_type", header: t(`${f}.matchType`) },
    { key: "effect", header: t(`${f}.effect`) },
    { key: "priority", header: t(`${f}.priority`) },
    {
      key: "enabled",
      header: t(`${f}.enabled`),
      renderCell: s => s.enabled ? <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" /> : "-",
    },
    {
      key: "actions",
      header: t("common.actions"),
      renderCell: s => (
        <span className="actions">
          {hasPermission("suppliers.view") && (
            <button className="btn-sm" onClick={(e) => { e.stopPropagation(); openEdit(s); }}>
              {t("common.edit")}
            </button>
          )}
          {hasPermission("suppliers.view") && (
            <button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(s); }}>
              {t("common.delete")}
            </button>
          )}
        </span>
      ),
    },
  ];

  const renderFormFields = (
    form: StatusFormState,
    setForm: (f: StatusFormState) => void,
  ) => (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3) var(--space-4)" }}>
      <div className="form-group">
        <TextField
          label={`${t(`${f}.statusId`)} *`}
          value={form.status_id}
          onChange={e => setForm({ ...form, status_id: e.target.value })}
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
          label={t(`${f}.searchPattern`)}
          value={form.search_pattern}
          onChange={e => setForm({ ...form, search_pattern: e.target.value })}
        />
      </div>
      <div className="form-group">
        <TextField
          label={t(`${f}.excludePattern`)}
          value={form.exclude_pattern}
          onChange={e => setForm({ ...form, exclude_pattern: e.target.value })}
        />
      </div>
      <div className="form-group">
        <label className="field-label">{t(`${f}.matchType`)} *</label>
        {/* ui-allow: enum select for status match_type; no SelectControl variant with option map (#3594) */}
        <select
          className="field field-h-md"
          value={form.match_type}
          onChange={e => setForm({ ...form, match_type: e.target.value })}
          required
        >
          {MATCH_TYPE_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>
      <div className="form-group">
        <label className="field-label">{t(`${f}.effect`)} *</label>
        {/* ui-allow: enum select for status effect; no SelectControl variant with option map (#3594) */}
        <select
          className="field field-h-md"
          value={form.effect}
          onChange={e => setForm({ ...form, effect: e.target.value })}
          required
        >
          {EFFECT_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>
      <div className="form-group">
        <TextField
          label={t(`${f}.priority`)}
          type="number"
          value={String(form.priority)}
          onChange={e => setForm({ ...form, priority: Number(e.target.value) })}
          required
        />
      </div>
      <div className="form-group">
        <TextField
          label={t(`${f}.note`)}
          value={form.note}
          onChange={e => setForm({ ...form, note: e.target.value })}
        />
      </div>
      <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", gridColumn: "1 / -1" }}>
        <input
          type="checkbox"
          checked={form.enabled}
          onChange={e => setForm({ ...form, enabled: e.target.checked })}
        />
        {t(`${f}.enabled`)}
      </label>
    </div>
  );

  return (
    <PageLayout
      navKey="nav.statusMaster"
      subtitleKey="statusMaster.title"
      headerAction={
        hasPermission("suppliers.view") ? (
          <HeaderButton
            variant="primary"
            onClick={() => { setShowCreate(true); setCreateForm(emptyForm); }}
            data-testid="status-master-new"
          >
            {t("common.create")}
          </HeaderButton>
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
              placeholder={t(`${f}.search`)}
              aria-label={t(`${f}.search`)}
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              data-testid="status-master-search"
            />
            <button type="submit" className="btn-secondary field-h-md" data-testid="status-master-search-btn">
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

      {/* 新規作成 Modal */}
      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title={t(`${f}.createTitle`)}
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
        title={t(`${f}.editTitle`)}
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
      ) : (
        <DataTable<StatusEntry>
          columns={columns}
          data={items}
          rowKey={s => String(s.id)}
          onRowClick={hasPermission("suppliers.view") ? s => openEdit(s) : undefined}
          emptyState={t(`${f}.empty`)}
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
          data-testid="status-master-pagination"
        >
          {(page > 1 || hasNext) && (
            <button
              className="btn-sm"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              data-testid="status-master-page-prev"
            >
              {t("common.prevPage")}
            </button>
          )}
          <span style={{ color: "var(--text-secondary)" }} data-testid="status-master-page-info">
            {t(`${f}.total`, { count: items.length })}
          </span>
          {(page > 1 || hasNext) && (
            <button
              className="btn-sm"
              onClick={() => setPage(p => p + 1)}
              disabled={!hasNext}
              data-testid="status-master-page-next"
            >
              {t("common.nextPage")}
            </button>
          )}
        </div>
      )}

      <ConfirmModal
        open={!!deleteTarget}
        title={t("common.delete")}
        message={t(`${f}.confirmDelete`)}
        confirmLabel={t("common.delete")}
        danger
        onConfirm={performDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </PageLayout>
  );
}
