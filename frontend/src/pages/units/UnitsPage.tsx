/**
 * UnitsPage — 単位マスタ管理（管理センター内）
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

interface Unit {
  id: number;
  code: string;
  canonical: string;
  kubun: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

type UnitFormState = {
  code: string;
  canonical: string;
  kubun: string;
  is_active: boolean;
};

const emptyForm: UnitFormState = {
  code: "",
  canonical: "",
  kubun: "",
  is_active: true,
};

const toForm = (u: Unit): UnitFormState => ({
  code: u.code,
  canonical: u.canonical,
  kubun: u.kubun ?? "",
  is_active: u.is_active,
});

export default function UnitsPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const [units, setUnits] = useState<Unit[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const PER_PAGE = 100;
  const [hasNext, setHasNext] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");

  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<UnitFormState>(emptyForm);

  const [editId, setEditId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<UnitFormState>(emptyForm);
  const [showEdit, setShowEdit] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<Unit | null>(null);

  const createFormRef = useRef<HTMLFormElement>(null);
  const editFormRef = useRef<HTMLFormElement>(null);

  const f = "unitMaster";

  const load = async () => {
    try {
      const params = new URLSearchParams({ page: String(page), per_page: String(PER_PAGE) });
      if (search.trim()) params.set("search", search.trim());
      const data = await api.get<Unit[]>(`/units?${params.toString()}`);
      setUnits(data);
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
    const toNull = (v: string) => v || null;
    const payload = {
      code: createForm.code,
      canonical: createForm.canonical,
      kubun: toNull(createForm.kubun),
      is_active: createForm.is_active,
    };
    try {
      await api.post("/units", payload);
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
    const toNull = (v: string) => v || null;
    const payload = {
      code: editForm.code,
      canonical: editForm.canonical,
      kubun: toNull(editForm.kubun),
      is_active: editForm.is_active,
    };
    try {
      await api.patch(`/units/${editId}`, payload);
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
      await api.delete(`/units/${deleteTarget.id}`);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
    }
  };

  const openEdit = (u: Unit) => {
    setEditId(u.id);
    setEditForm(toForm(u));
    setShowEdit(true);
  };

  const columns: DataTableColumn<Unit>[] = [
    { key: "code", header: t(`${f}.code`), renderCell: u => <span className="mono">{u.code}</span> },
    { key: "canonical", header: t(`${f}.canonical`) },
    { key: "kubun", header: t(`${f}.kubun`), renderCell: u => u.kubun || "-" },
    {
      key: "is_active",
      header: t(`${f}.isActive`),
      renderCell: u => u.is_active ? <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" /> : "-",
    },
    {
      key: "actions",
      header: t("common.actions"),
      renderCell: u => (
        <span className="actions">
          {hasPermission("suppliers.view") && (
            <button className="btn-sm" onClick={(e) => { e.stopPropagation(); openEdit(u); }}>
              {t("common.edit")}
            </button>
          )}
          {hasPermission("suppliers.view") && (
            <button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(u); }}>
              {t("common.delete")}
            </button>
          )}
        </span>
      ),
    },
  ];

  return (
    <PageLayout
      navKey="nav.units"
      subtitleKey="unitMaster.title"
      headerAction={
        hasPermission("suppliers.view") ? (
          <HeaderButton
            variant="primary"
            onClick={() => { setShowCreate(true); setCreateForm(emptyForm); }}
            data-testid="units-new"
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
              data-testid="units-search"
            />
            <button type="submit" className="btn-secondary field-h-md" data-testid="units-search-btn">
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
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3) var(--space-4)" }}>
            <div className="form-group">
              <TextField
                label={`${t(`${f}.code`)} *`}
                value={createForm.code}
                onChange={e => setCreateForm({ ...createForm, code: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <TextField
                label={`${t(`${f}.canonical`)} *`}
                value={createForm.canonical}
                onChange={e => setCreateForm({ ...createForm, canonical: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <TextField
                label={t(`${f}.kubun`)}
                value={createForm.kubun}
                onChange={e => setCreateForm({ ...createForm, kubun: e.target.value })}
              />
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <input
                type="checkbox"
                checked={createForm.is_active}
                onChange={e => setCreateForm({ ...createForm, is_active: e.target.checked })}
              />
              {t(`${f}.isActive`)}
            </label>
          </div>
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
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3) var(--space-4)" }}>
            <div className="form-group">
              <TextField
                label={`${t(`${f}.code`)} *`}
                value={editForm.code}
                onChange={e => setEditForm({ ...editForm, code: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <TextField
                label={`${t(`${f}.canonical`)} *`}
                value={editForm.canonical}
                onChange={e => setEditForm({ ...editForm, canonical: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <TextField
                label={t(`${f}.kubun`)}
                value={editForm.kubun}
                onChange={e => setEditForm({ ...editForm, kubun: e.target.value })}
              />
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <input
                type="checkbox"
                checked={editForm.is_active}
                onChange={e => setEditForm({ ...editForm, is_active: e.target.checked })}
              />
              {t(`${f}.isActive`)}
            </label>
          </div>
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
        <DataTable<Unit>
          columns={columns}
          data={units}
          rowKey={u => String(u.id)}
          onRowClick={hasPermission("suppliers.view") ? u => openEdit(u) : undefined}
          emptyState={t(`${f}.empty`)}
        />
      )}

      {!loading && units.length > 0 && (
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
          data-testid="units-pagination"
        >
          {(page > 1 || hasNext) && (
            <button
              className="btn-sm"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              data-testid="units-page-prev"
            >
              {t("common.prevPage")}
            </button>
          )}
          <span style={{ color: "var(--text-secondary)" }} data-testid="units-page-info">
            {t(`${f}.total`, { count: units.length })}
          </span>
          {(page > 1 || hasNext) && (
            <button
              className="btn-sm"
              onClick={() => setPage(p => p + 1)}
              disabled={!hasNext}
              data-testid="units-page-next"
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
