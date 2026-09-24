/**
 * TypeMasterPanel — 中分類マスタパネル（AnalysisRulesPage の hub-content 内で使用）
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

interface TypeMaster {
  id: number;
  code: string;
  name_ja: string;
  name_en: string | null;
  kind_id: number | null;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

type TypeFormState = {
  code: string;
  name_ja: string;
  name_en: string;
  kind_id: number | null;
  sort_order: number;
  is_active: boolean;
};

const emptyForm: TypeFormState = {
  code: "",
  name_ja: "",
  name_en: "",
  kind_id: null,
  sort_order: 100,
  is_active: true,
};

const PER_PAGE = 200;

export function TypeMasterPanel() {
  const { t } = useTranslation();
  const f = "typeMaster";

  const [items, setItems] = useState<TypeMaster[]>([]);
  const [kinds, setKinds] = useState<ProductKind[]>([]);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<TypeFormState>(emptyForm);
  const [editId, setEditId] = useState<number | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const formRef = useRef<HTMLFormElement>(null);

  const load = useCallback(async () => {
    try {
      const [typesData, kindsData] = await Promise.all([
        api.get<TypeMaster[]>("/super-admin/tcg/types"),
        api.get<ProductKind[]>("/super-admin/product-kinds"),
      ]);
      setItems(typesData);
      setKinds(kindsData);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  }, [t]);

  useEffect(() => { void load(); }, [load]);

  const openCreate = () => { setEditId(null); setForm(emptyForm); setShowForm(true); };
  const openEdit = (item: TypeMaster) => {
    setEditId(item.id);
    setForm({
      code: item.code,
      name_ja: item.name_ja,
      name_en: item.name_en || "",
      kind_id: item.kind_id,
      sort_order: item.sort_order,
      is_active: item.is_active,
    });
    setShowForm(true);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const payload = {
      code: form.code,
      name_ja: form.name_ja,
      name_en: form.name_en || null,
      kind_id: form.kind_id,
      sort_order: form.sort_order,
      is_active: form.is_active,
    };
    try {
      if (editId) {
        await api.patch(`/super-admin/tcg/types/${editId}`, payload);
      } else {
        await api.post("/super-admin/tcg/types", payload);
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
      await api.delete(`/super-admin/tcg/types/${confirmDeleteId}`);
      setConfirmDeleteId(null);
      await load();
    } catch (e) {
      const msg = e instanceof Error ? e.message : t("common.deleteError");
      // 409 = 使用中（小分類で参照中）
      if (e instanceof Error && e.message.includes("409")) {
        setError(t(`${f}.deleteBlocked`));
      } else {
        setError(msg);
      }
      setConfirmDeleteId(null);
    }
  };

  const kindName = (kindId: number | null) => {
    if (kindId === null) return "-";
    const found = kinds.find(k => k.id === kindId);
    return found ? found.name : String(kindId);
  };

  const kindOptions = [
    { value: "", label: "—" },
    ...kinds.map(k => ({ value: String(k.id), label: k.name })),
  ];

  const columns: DataTableColumn<TypeMaster>[] = [
    { key: "code", header: t(`${f}.code`) },
    { key: "name_ja", header: t(`${f}.nameJa`) },
    { key: "kind_id", header: t(`${f}.kindId`), renderCell: row => kindName(row.kind_id) },
    { key: "sort_order", header: t(`${f}.sortOrder`) },
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
          data-testid={`type-master-edit-${row.id}`}
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
          data-testid={`type-master-delete-${row.id}`}
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
            data-testid="type-master-new"
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
                label={`${t(`${f}.nameJa`)} *`}
                value={form.name_ja}
                onChange={e => setForm({ ...form, name_ja: e.target.value })}
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
              <label style={{ display: "block", marginBottom: "var(--space-1)", fontSize: "var(--font-sm)" }}>
                {t(`${f}.kindId`)}
              </label>
              <SelectControl
                options={kindOptions}
                value={form.kind_id !== null ? String(form.kind_id) : ""}
                onChange={e => setForm({ ...form, kind_id: e.target.value ? Number(e.target.value) : null })}
                fullWidth
              />
            </div>
            <div className="form-group">
              <TextField
                type="number"
                label={t(`${f}.sortOrder`)}
                value={String(form.sort_order)}
                onChange={e => setForm({ ...form, sort_order: Number(e.target.value) })}
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
