/**
 * ProductLinesMasterPanel — 中分類マスタパネル（AnalysisRulesPage の hub-content 内で使用）
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
import { SelectControl } from "../../../components/Select";
import { STATUS_ICONS } from "../../../constants/icons";
import { ICON } from "../../../constants/iconSizes";

interface ProductKind {
  id: number;
  code: string;
  name: string;
}

interface ProductType {
  id: number;
  code: string;
  name_ja: string;
  name_en: string | null;
}

interface ProductLine {
  id: number;
  code: string;
  name: string;
  name_en: string | null;
  kind_id: number | null;
  type_id: number | null;
  display_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

type LineFormState = {
  code: string;
  name: string;
  name_en: string;
  kind_id: number | null;
  type_id: number | null;
  display_order: number;
  is_active: boolean;
};

const emptyForm: LineFormState = {
  code: "",
  name: "",
  name_en: "",
  kind_id: null,
  type_id: null,
  display_order: 100,
  is_active: true,
};

const PER_PAGE = 200;

export function ProductLinesMasterPanel() {
  const { t } = useTranslation();
  const f = "productLinesMaster";

  const [items, setItems] = useState<ProductLine[]>([]);
  const [kinds, setKinds] = useState<ProductKind[]>([]);
  const [types, setTypes] = useState<ProductType[]>([]);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<LineFormState>(emptyForm);
  const [editId, setEditId] = useState<number | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const formRef = useRef<HTMLFormElement>(null);

  const load = useCallback(async () => {
    try {
      const data = await api.get<ProductLine[]>("/super-admin/product-lines");
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  }, [t]);

  const loadKinds = useCallback(async () => {
    try {
      const data = await api.get<ProductKind[]>("/super-admin/product-kinds");
      setKinds(data);
    } catch {
      // 選択肢取得失敗は無視（空選択肢として表示）
    }
  }, []);

  const loadTypes = useCallback(async () => {
    try {
      const data = await api.get<ProductType[]>("/super-admin/tcg/types");
      setTypes(data);
    } catch {
      // 選択肢取得失敗は無視（空選択肢として表示）
    }
  }, []);

  useEffect(() => {
    void load();
    void loadKinds();
    void loadTypes();
  }, [load, loadKinds, loadTypes]);

  const openCreate = () => { setEditId(null); setForm(emptyForm); setShowForm(true); };
  const openEdit = (item: ProductLine) => {
    setEditId(item.id);
    setForm({
      code: item.code,
      name: item.name,
      name_en: item.name_en || "",
      kind_id: item.kind_id,
      type_id: item.type_id,
      display_order: item.display_order,
      is_active: item.is_active,
    });
    setShowForm(true);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const payload = {
      code: form.code,
      name: form.name,
      name_en: form.name_en || null,
      kind_id: form.kind_id,
      type_id: form.type_id,
      display_order: form.display_order,
      is_active: form.is_active,
    };
    try {
      if (editId) {
        await api.patch(`/super-admin/product-lines/${editId}`, payload);
      } else {
        await api.post("/super-admin/product-lines", payload);
      }
      setShowForm(false);
      setForm(emptyForm);
      setEditId(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    }
  };

  const confirmDelete = async () => {
    if (confirmDeleteId === null) return;
    setError("");
    try {
      await api.delete(`/super-admin/product-lines/${confirmDeleteId}`);
      setConfirmDeleteId(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
      setConfirmDeleteId(null);
    }
  };

  const getKindName = (id: number | null) => {
    if (id === null) return "-";
    return kinds.find(k => k.id === id)?.name ?? String(id);
  };

  const getTypeName = (id: number | null) => {
    if (id === null) return "-";
    return types.find(tp => tp.id === id)?.name_ja ?? String(id);
  };

  const columns: DataTableColumn<ProductLine>[] = [
    { key: "code", header: t(`${f}.code`) },
    { key: "name", header: t(`${f}.name`) },
    { key: "kind_id", header: t(`${f}.kindId`), renderCell: row => getKindName(row.kind_id) },
    { key: "type_id", header: t(`${f}.typeId`), renderCell: row => getTypeName(row.type_id) },
    { key: "display_order", header: t(`${f}.displayOrder`) },
    {
      key: "is_active",
      header: t(`${f}.isActive`),
      renderCell: row => row.is_active
        ? <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" />
        : "-",
    },
    {
      key: "_edit",
      header: "",
      renderCell: row => (
        <HeaderButton
          variant="secondary"
          data-testid={`product-line-edit-${row.id}`}
          onClick={() => openEdit(row)}
        >
          {t("common.edit")}
        </HeaderButton>
      ),
    },
    {
      key: "_delete",
      header: "",
      renderCell: row => (
        <HeaderButton
          variant="secondary"
          data-testid={`product-line-delete-${row.id}`}
          onClick={() => setConfirmDeleteId(row.id)}
        >
          {t("common.delete")}
        </HeaderButton>
      ),
    },
  ];

  return (
    <>
      <ContentToolbar
        right={
          <HeaderButton
            variant="primary"
            data-testid="product-lines-new"
            onClick={openCreate}
          >
            {t(`${f}.addNew`)}
          </HeaderButton>
        }
      />
      {error && <p role="alert">{error}</p>}
      <DataTable
        columns={columns}
        data={items}
        rowKey={row => String(row.id)}
        onRowClick={row => openEdit(row)}
        emptyState={<EmptyState title={t(`${f}.noData`)} size="compact" />}
        page={1}
        hasNextPage={items.length >= PER_PAGE}
        onPageChange={() => undefined}
        prevPageLabel={t("common.prevPage")}
        nextPageLabel={t("common.nextPage")}
      />

      {/* 編集/新規 モーダル */}
      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title={editId ? t(`${f}.editTitle`) : t(`${f}.createTitle`)}
        size="md"
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
                label={`${t(`${f}.name`)} *`}
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <TextField
                label={t(`${f}.nameEn`)}
                value={form.name_en}
                onChange={e => setForm({ ...form, name_en: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label style={{ display: "block", fontSize: "var(--font-sm)", marginBottom: "var(--space-1)" }}>
                {t(`${f}.kindId`)}
              </label>
              <SelectControl
                options={[
                  { value: "", label: "—" },
                  ...kinds.map(k => ({ value: String(k.id), label: k.name })),
                ]}
                value={form.kind_id != null ? String(form.kind_id) : ""}
                onChange={e => setForm({ ...form, kind_id: e.target.value ? Number(e.target.value) : null })}
                fullWidth
              />
            </div>
            <div className="form-group">
              <label style={{ display: "block", fontSize: "var(--font-sm)", marginBottom: "var(--space-1)" }}>
                {t(`${f}.typeId`)}
              </label>
              <SelectControl
                options={[
                  { value: "", label: "—" },
                  ...types.map(tp => ({ value: String(tp.id), label: tp.name_ja })),
                ]}
                value={form.type_id != null ? String(form.type_id) : ""}
                onChange={e => setForm({ ...form, type_id: e.target.value ? Number(e.target.value) : null })}
                fullWidth
              />
            </div>
            <div className="form-group">
              <TextField
                type="number"
                label={t(`${f}.displayOrder`)}
                value={String(form.display_order)}
                onChange={e => setForm({ ...form, display_order: Number(e.target.value) })}
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
          <div className="form-actions">
            <HeaderButton variant="secondary" onClick={() => setShowForm(false)}>
              {t("common.cancel")}
            </HeaderButton>
            <HeaderButton
              variant="primary"
              onClick={() => formRef.current?.requestSubmit()}
            >
              {editId ? t("common.update") : t("common.create")}
            </HeaderButton>
          </div>
        </form>
      </Modal>

      <ConfirmModal
        open={confirmDeleteId !== null}
        title={t("common.delete")}
        message={t(`${f}.confirmDelete`)}
        confirmLabel={t("common.delete")}
        danger
        onConfirm={() => { void confirmDelete(); }}
        onCancel={() => setConfirmDeleteId(null)}
      />
    </>
  );
}
