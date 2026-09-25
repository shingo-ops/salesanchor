/**
 * ProductCategoriesMasterPanel — 商品カテゴリマスタパネル（AnalysisRulesPage の hub-content 内で使用）
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
import { Drawer } from "../../../components/Drawer";
import ConfirmModal from "../../../components/ConfirmModal";
import { STATUS_ICONS } from "../../../constants/icons";
import { ICON } from "../../../constants/iconSizes";

interface ProductCategory {
  id: number;
  code: string;
  display_name: string;
  kubun_type: string | null;
  is_active: boolean;
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

const PER_PAGE = 50;

export function ProductCategoriesMasterPanel() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const f = "productCategoriesMaster";

  const downloadExport = async () => {
    try {
      const blob = await api.getBlob("/super-admin/product-categories/export");
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

  const [items, setItems] = useState<ProductCategory[]>([]);
  const [error, setError] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CategoryFormState>(emptyForm);
  const [editId, setEditId] = useState<number | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const formRef = useRef<HTMLFormElement>(null);

  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams({ page: String(page), per_page: String(PER_PAGE) });
      if (search.trim()) params.set("q", search.trim());
      const data = await api.get<ProductCategory[]>(`/super-admin/product-categories?${params.toString()}`);
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  }, [page, search, t]);

  useEffect(() => { void load(); }, [load]);

  const runSearch = () => { setSearch(searchInput); setPage(1); };

  const openCreate = () => { setEditId(null); setForm(emptyForm); setShowForm(true); };
  const openEdit = (c: ProductCategory) => {
    setEditId(c.id);
    setForm({
      code: c.code,
      display_name: c.display_name,
      kubun_type: c.kubun_type || "",
      is_active: c.is_active,
    });
    setShowForm(true);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const toNull = (v: string) => v || null;
    const payload = {
      code: form.code,
      display_name: form.display_name,
      kubun_type: toNull(form.kubun_type),
      is_active: form.is_active,
    };
    try {
      if (editId) {
        await api.patch(`/super-admin/product-categories/${editId}`, payload);
      } else {
        await api.post("/super-admin/product-categories", payload);
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
      selectedIds.map((id) => api.delete(`/super-admin/product-categories/${id}`)),
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

  const columns: DataTableColumn<ProductCategory>[] = [
    { key: "display_name", header: t(`${f}.displayName`) },
    { key: "kubun_type", header: t(`${f}.kubunType`), renderCell: row => row.kubun_type || "-" },
    {
      key: "is_active",
      header: t(`${f}.isActive`),
      renderCell: row => row.is_active ? <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" /> : "-",
    },
  ];

  return (
    <>
      <ContentToolbar
        right={
          <>
            <HeaderButton
              variant="secondary"
              data-testid="product-categories-export"
              onClick={() => { void downloadExport(); }}
            >
              {t("productCategoriesCsv.exportButton")}
            </HeaderButton>
            <HeaderButton
              variant="secondary"
              data-testid="product-categories-import"
              onClick={() => navigate("/super-admin/masters/product-categories/import")}
            >
              {t("productCategoriesCsv.importButton")}
            </HeaderButton>
            <HeaderButton
              variant="primary"
              data-testid="product-categories-new"
              onClick={openCreate}
            >
              {t("common.create")}
            </HeaderButton>
            <HeaderButton
              variant="secondary"
              disabled={selectedKeys.size === 0}
              data-testid="product-categories-bulk-delete"
              onClick={() => setConfirmDelete(true)}
            >
              {t("common.delete")}
            </HeaderButton>
          </>
        }
      />
      {error && <p role="alert">{error}</p>}
      <ContentToolbar
        left={
          <TextField
            type="search"
            label={t(`${f}.search`)}
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") runSearch(); }}
            data-testid="product-categories-search"
          />
        }
        right={
          <HeaderButton
            variant="primary"
            data-testid="product-categories-search-btn"
            onClick={runSearch}
          >
            {t("common.search")}
          </HeaderButton>
        }
      />
      <DataTable
        columns={columns}
        data={items}
        rowKey={row => String(row.id)}
        selectable
        selectedKeys={selectedKeys}
        onSelectChange={setSelectedKeys}
        onRowClick={row => openEdit(row)}
        emptyState={<EmptyState title={t(`${f}.empty`)} size="compact" />}
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
        title={editId ? t(`${f}.editTitle`) : t(`${f}.createTitle`)}
        footer={
          <>
            <div style={{ marginLeft: "auto", display: "flex", gap: "var(--space-2)" }}>
              <HeaderButton variant="secondary" onClick={() => setShowForm(false)}>
                {t("common.back")}
              </HeaderButton>
              <HeaderButton
                variant="primary"
                onClick={() => formRef.current?.requestSubmit()}
              >
                {editId ? t("common.update") : t("common.create")}
              </HeaderButton>
            </div>
          </>
        }
      >
        <form ref={formRef} onSubmit={e => { void submit(e); }}>
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
        </form>
      </Drawer>

      <ConfirmModal
        open={confirmDelete}
        title={t("common.delete")}
        message={t(`${f}.confirmDelete`)}
        confirmLabel={t("common.delete")}
        danger
        onConfirm={() => { void bulkDelete(); }}
        onCancel={() => setConfirmDelete(false)}
      />
    </>
  );
}
