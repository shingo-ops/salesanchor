/**
 * QuantityUnitsMasterPanel — 数量単位マスタパネル（AnalysisRulesPage の hub-content 内で使用）
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
import { Drawer } from "../../../components/Drawer";
import ConfirmModal from "../../../components/ConfirmModal";
import { STATUS_ICONS } from "../../../constants/icons";
import { ICON } from "../../../constants/iconSizes";

interface QuantityUnit {
  id: number;
  code: string;
  name: string;
  name_en: string | null;
  value: number | null;
  display_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  condition_count?: number;
  product_line_count?: number;
}

type UnitFormState = {
  code: string;
  name: string;
  name_en: string;
  value: string;
  display_order: number;
  is_active: boolean;
};

const emptyForm: UnitFormState = {
  code: "",
  name: "",
  name_en: "",
  value: "",
  display_order: 100,
  is_active: true,
};

const PER_PAGE = 200;

export function QuantityUnitsMasterPanel() {
  const { t } = useTranslation();
  const f = "quantityUnitsMaster";

  const [items, setItems] = useState<QuantityUnit[]>([]);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<UnitFormState>(emptyForm);
  const [editId, setEditId] = useState<number | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const formRef = useRef<HTMLFormElement>(null);

  const load = useCallback(async () => {
    try {
      const data = await api.get<QuantityUnit[]>("/super-admin/quantity-units");
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  }, [t]);

  useEffect(() => { void load(); }, [load]);

  const openCreate = () => { setEditId(null); setForm(emptyForm); setShowForm(true); };
  const openEdit = (item: QuantityUnit) => {
    setEditId(item.id);
    setForm({
      code: item.code,
      name: item.name,
      name_en: item.name_en || "",
      value: item.value !== null ? String(item.value) : "",
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
      value: form.value !== "" ? Number(form.value) : null,
      display_order: form.display_order,
      is_active: form.is_active,
    };
    try {
      if (editId) {
        await api.patch(`/super-admin/quantity-units/${editId}`, payload);
      } else {
        await api.post("/super-admin/quantity-units", payload);
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
      await api.delete(`/super-admin/quantity-units/${confirmDeleteId}`);
      setConfirmDeleteId(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
      setConfirmDeleteId(null);
    }
  };

  const columns: DataTableColumn<QuantityUnit>[] = [
    { key: "name", header: t(`${f}.name`) },
    { key: "name_en", header: t(`${f}.nameEn`), renderCell: row => row.name_en || "-" },
    { key: "value", header: t(`${f}.value`), renderCell: row => row.value !== null ? String(row.value) : "-" },
    { key: "display_order", header: t(`${f}.displayOrder`) },
    { key: "condition_count", header: t(`${f}.conditionCount`), renderCell: row => row.condition_count !== undefined ? String(row.condition_count) : "-" },
    { key: "product_line_count", header: t(`${f}.productLineCount`), renderCell: row => row.product_line_count !== undefined ? String(row.product_line_count) : "-" },
    {
      key: "is_active",
      header: t(`${f}.isActive`),
      renderCell: row => row.is_active
        ? <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" />
        : "-",
    },
  ];

  return (
    <>
      <ContentToolbar
        right={
          <HeaderButton
            variant="primary"
            data-testid="quantity-units-new"
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

      {/* 編集/新規 ドロワー */}
      <Drawer
        open={showForm}
        onClose={() => setShowForm(false)}
        title={editId ? t(`${f}.editTitle`) : t(`${f}.createTitle`)}
        footer={
          <>
            {editId && (
              <HeaderButton variant="secondary" onClick={() => { setShowForm(false); setConfirmDeleteId(editId); }}>
                {t("common.delete")}
              </HeaderButton>
            )}
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
              <TextField
                type="number"
                label={t(`${f}.value`)}
                value={form.value}
                onChange={e => setForm({ ...form, value: e.target.value })}
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
        </form>
      </Drawer>

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
