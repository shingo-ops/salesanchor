/**
 * ProductCategoriesPage — テナント固有商品カテゴリマスタ管理（管理センター内）
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

interface ProductCategoryEntry {
  id: number;
  code: string;
  display_name: string;
  kubun_type: string | null;
  is_active: boolean;
  tenant_id: number | null;
  created_at: string;
  updated_at: string;
}

type CategoryFormState = {
  code: string;
  display_name: string;
  kubun_type: string;
  is_active: boolean;
};

const emptyForm: CategoryFormState = {
  code: "",
  display_name: "",
  kubun_type: "",
  is_active: true,
};

const toForm = (c: ProductCategoryEntry): CategoryFormState => ({
  code: c.code,
  display_name: c.display_name,
  kubun_type: c.kubun_type ?? "",
  is_active: c.is_active,
});

export default function ProductCategoriesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { hasPermission } = usePermissions();
  const [items, setItems] = useState<ProductCategoryEntry[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const PER_PAGE = 50;
  const [hasNext, setHasNext] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");

  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<CategoryFormState>(emptyForm);

  const [editId, setEditId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<CategoryFormState>(emptyForm);
  const [showEdit, setShowEdit] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<ProductCategoryEntry | null>(null);

  const createFormRef = useRef<HTMLFormElement>(null);
  const editFormRef = useRef<HTMLFormElement>(null);

  const f = "productCategoriesMaster";

  const downloadExport = async () => {
    try {
      const blob = await api.getBlob("/product-categories/export");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "product-categories.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  };

  const load = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), per_page: String(PER_PAGE) });
      if (search.trim()) params.set("search", search.trim());
      const data = await api.get<ProductCategoryEntry[]>(`/product-categories?${params.toString()}`);
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
    const toNull = (v: string) => v || null;
    try {
      await api.post("/product-categories", {
        ...createForm,
        kubun_type: toNull(createForm.kubun_type),
      });
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
    try {
      await api.patch(`/product-categories/${editId}`, {
        ...editForm,
        kubun_type: toNull(editForm.kubun_type),
      });
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
      await api.delete(`/product-categories/${deleteTarget.id}`);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
    }
  };

  const openEdit = (c: ProductCategoryEntry) => {
    setEditId(c.id);
    setEditForm(toForm(c));
    setShowEdit(true);
  };

  const columns: DataTableColumn<ProductCategoryEntry>[] = [
    { key: "code", header: t(`${f}.code`), renderCell: c => <span className="mono">{c.code}</span> },
    { key: "display_name", header: t(`${f}.displayName`) },
    { key: "kubun_type", header: t(`${f}.kubunType`), renderCell: c => c.kubun_type || "-" },
    {
      key: "is_active",
      header: t(`${f}.isActive`),
      renderCell: c => c.is_active ? <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" /> : "-",
    },
    {
      key: "actions",
      header: t("common.actions"),
      renderCell: c => (
        <span className="actions">
          {hasPermission("product_categories.edit") && (
            <button className="btn-sm" onClick={(e) => { e.stopPropagation(); openEdit(c); }}>
              {t("common.edit")}
            </button>
          )}
          {hasPermission("product_categories.delete") && (
            <button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(c); }}>
              {t("common.delete")}
            </button>
          )}
        </span>
      ),
    },
  ];

  const renderFormFields = (
    form: CategoryFormState,
    setForm: (f: CategoryFormState) => void,
  ) => (
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
          label={`${t(`${f}.displayName`)} *`}
          value={form.display_name}
          onChange={e => setForm({ ...form, display_name: e.target.value })}
          required
        />
      </div>
      <div className="form-group">
        <TextField
          label={t(`${f}.kubunType`)}
          value={form.kubun_type}
          onChange={e => setForm({ ...form, kubun_type: e.target.value })}
        />
      </div>
      <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
        <input
          type="checkbox"
          checked={form.is_active}
          onChange={e => setForm({ ...form, is_active: e.target.checked })}
        />
        {t(`${f}.isActive`)}
      </label>
    </div>
  );

  return (
    <PageLayout
      navKey="nav.productCategories"
      subtitleKey={`${f}.subtitle`}
      headerAction={
        <>
          <HeaderButton
            variant="secondary"
            data-testid="product-categories-export"
            onClick={() => { void downloadExport(); }}
          >
            {t("productCategoriesCsv.exportButton")}
          </HeaderButton>
          {hasPermission("product_categories.edit") && (
            <HeaderButton
              variant="secondary"
              data-testid="product-categories-import"
              onClick={() => navigate("/management-center/product-categories/import")}
            >
              {t("productCategoriesCsv.importButton")}
            </HeaderButton>
          )}
          {hasPermission("product_categories.edit") && (
            <HeaderButton
              variant="primary"
              onClick={() => { setShowCreate(true); setCreateForm(emptyForm); }}
              data-testid="product-categories-new"
            >
              {t(`${f}.newCategory`)}
            </HeaderButton>
          )}
        </>
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
              data-testid="product-categories-search"
            />
            <button type="submit" className="btn-secondary field-h-md" data-testid="product-categories-search-btn">
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
        <DataTable<ProductCategoryEntry>
          columns={columns}
          data={items}
          rowKey={c => String(c.id)}
          onRowClick={hasPermission("product_categories.edit") ? c => openEdit(c) : undefined}
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
          data-testid="product-categories-pagination"
        >
          {(page > 1 || hasNext) && (
            <button
              className="btn-sm"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              data-testid="product-categories-page-prev"
            >
              {t("common.prevPage")}
            </button>
          )}
          <span style={{ color: "var(--text-secondary)" }} data-testid="product-categories-page-info">
            {t(`${f}.total`, { count: items.length })}
          </span>
          {(page > 1 || hasNext) && (
            <button
              className="btn-sm"
              onClick={() => setPage(p => p + 1)}
              disabled={!hasNext}
              data-testid="product-categories-page-next"
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
