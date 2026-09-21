/**
 * WeightClassesMasterPanel — 重量クラスマスタパネル（AnalysisRulesPage の hub-content 内で使用）
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
import { STATUS_ICONS } from "../../../constants/icons";
import { ICON } from "../../../constants/iconSizes";

interface WeightClass {
  id: number;
  code: string;
  name: string;
  name_en: string | null;
  min_grams: number | null;
  max_grams: number | null;
  display_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

type WeightFormState = {
  code: string;
  name: string;
  name_en: string;
  min_grams: string;
  max_grams: string;
  display_order: number;
  is_active: boolean;
};

const emptyForm: WeightFormState = {
  code: "",
  name: "",
  name_en: "",
  min_grams: "",
  max_grams: "",
  display_order: 100,
  is_active: true,
};

const PER_PAGE = 200;

export function WeightClassesMasterPanel() {
  const { t } = useTranslation();
  const f = "weightClassesMaster";

  const [items, setItems] = useState<WeightClass[]>([]);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<WeightFormState>(emptyForm);
  const [editId, setEditId] = useState<number | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const formRef = useRef<HTMLFormElement>(null);

  const load = useCallback(async () => {
    try {
      const data = await api.get<WeightClass[]>("/super-admin/weight-classes");
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  }, [t]);

  useEffect(() => { void load(); }, [load]);

  const openCreate = () => { setEditId(null); setForm(emptyForm); setShowForm(true); };
  const openEdit = (item: WeightClass) => {
    setEditId(item.id);
    setForm({
      code: item.code,
      name: item.name,
      name_en: item.name_en || "",
      min_grams: item.min_grams !== null ? String(item.min_grams) : "",
      max_grams: item.max_grams !== null ? String(item.max_grams) : "",
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
      min_grams: form.min_grams !== "" ? Number(form.min_grams) : null,
      max_grams: form.max_grams !== "" ? Number(form.max_grams) : null,
      display_order: form.display_order,
      is_active: form.is_active,
    };
    try {
      if (editId) {
        await api.patch(`/super-admin/weight-classes/${editId}`, payload);
      } else {
        await api.post("/super-admin/weight-classes", payload);
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
      await api.delete(`/super-admin/weight-classes/${confirmDeleteId}`);
      setConfirmDeleteId(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
      setConfirmDeleteId(null);
    }
  };

  const formatGrams = (v: number | null) => v !== null ? String(v) : "-";

  const columns: DataTableColumn<WeightClass>[] = [
    { key: "code", header: t(`${f}.code`) },
    { key: "name", header: t(`${f}.name`) },
    { key: "name_en", header: t(`${f}.nameEn`), renderCell: row => row.name_en || "-" },
    { key: "min_grams", header: t(`${f}.minGrams`), renderCell: row => formatGrams(row.min_grams) },
    { key: "max_grams", header: t(`${f}.maxGrams`), renderCell: row => formatGrams(row.max_grams) },
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
          data-testid={`weight-class-edit-${row.id}`}
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
          data-testid={`weight-class-delete-${row.id}`}
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
            data-testid="weight-classes-new"
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
              <TextField
                type="number"
                label={t(`${f}.minGrams`)}
                value={form.min_grams}
                onChange={e => setForm({ ...form, min_grams: e.target.value })}
              />
            </div>
            <div className="form-group">
              <TextField
                type="number"
                label={t(`${f}.maxGrams`)}
                value={form.max_grams}
                onChange={e => setForm({ ...form, max_grams: e.target.value })}
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
