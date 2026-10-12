/**
 * ProductFormatsMasterPanel — 商品形態マスタパネル（AnalysisRulesPage の hub-content 内で使用）
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
import { SelectControl } from "../../../components/Select";
import { STATUS_ICONS } from "../../../constants/icons";
import { ICON } from "../../../constants/iconSizes";

interface ProductLine {
  id: number;
  code: string;
  name: string;
}

interface TcgType {
  id: number;
  code: string;
  name_ja: string;
  name_en: string | null;
}

interface ProductFormat {
  id: number;
  code: string;
  name: string;
  name_en: string | null;
  line_id: number | null;
  type_master_id: number | null;
  display_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

type FormatFormState = {
  code: string;
  name: string;
  name_en: string;
  line_id: number | null;
  type_master_id: number | null;
  display_order: number;
  is_active: boolean;
};

const emptyForm: FormatFormState = {
  code: "",
  name: "",
  name_en: "",
  line_id: null,
  type_master_id: null,
  display_order: 100,
  is_active: true,
};

const PER_PAGE = 200;

export function ProductFormatsMasterPanel() {
  const { t } = useTranslation();
  const f = "productFormatsMaster";

  const [items, setItems] = useState<ProductFormat[]>([]);
  const [lines, setLines] = useState<ProductLine[]>([]);
  const [tcgTypes, setTcgTypes] = useState<TcgType[]>([]);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<FormatFormState>(emptyForm);
  const [editId, setEditId] = useState<number | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const formRef = useRef<HTMLFormElement>(null);

  const load = useCallback(async () => {
    try {
      const data = await api.get<ProductFormat[]>("/super-admin/product-formats");
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  }, [t]);

  const loadLines = useCallback(async () => {
    try {
      const data = await api.get<ProductLine[]>("/super-admin/product-lines");
      setLines(data);
    } catch {
      // 選択肢取得失敗は無視（空選択肢として表示）
    }
  }, []);

  const loadTcgTypes = useCallback(async () => {
    try {
      const data = await api.get<TcgType[]>("/super-admin/tcg/types");
      setTcgTypes(data);
    } catch {
      // 選択肢取得失敗は無視（空選択肢として表示）
    }
  }, []);

  useEffect(() => {
    void load();
    void loadLines();
    void loadTcgTypes();
  }, [load, loadLines, loadTcgTypes]);

  const openCreate = () => { setEditId(null); setForm(emptyForm); setShowForm(true); };
  const openEdit = (item: ProductFormat) => {
    setEditId(item.id);
    setForm({
      code: item.code,
      name: item.name,
      name_en: item.name_en || "",
      line_id: item.line_id,
      type_master_id: item.type_master_id,
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
      line_id: form.line_id,
      type_master_id: form.type_master_id,
      display_order: form.display_order,
      is_active: form.is_active,
    };
    try {
      if (editId) {
        await api.patch(`/super-admin/product-formats/${editId}`, payload);
      } else {
        await api.post("/super-admin/product-formats", payload);
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
      await api.delete(`/super-admin/product-formats/${confirmDeleteId}`);
      setConfirmDeleteId(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
      setConfirmDeleteId(null);
    }
  };

  const getLineName = (id: number | null) => {
    if (id === null) return "-";
    return lines.find(l => l.id === id)?.name ?? String(id);
  };

  const getGameName = (id: number | null) => {
    if (id === null) return "-";
    const found = tcgTypes.find(t => t.id === id);
    return found ? found.name_ja : String(id);
  };

  const columns: DataTableColumn<ProductFormat>[] = [
    { key: "name", header: t(`${f}.name`) },
    { key: "type_master_id", header: t(`${f}.typeMasterId`), renderCell: row => getGameName(row.type_master_id) },
    { key: "line_id", header: t(`${f}.lineId`), renderCell: row => getLineName(row.line_id) },
    { key: "display_order", header: t(`${f}.displayOrder`) },
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
            data-testid="product-formats-new"
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
              <label style={{ display: "block", fontSize: "var(--font-sm)", marginBottom: "var(--space-1)" }}>
                {t(`${f}.lineId`)}
              </label>
              <SelectControl
                options={[
                  { value: "", label: "—" },
                  ...lines.map(l => ({ value: String(l.id), label: l.name })),
                ]}
                value={form.line_id != null ? String(form.line_id) : ""}
                onChange={e => setForm({ ...form, line_id: e.target.value ? Number(e.target.value) : null })}
                fullWidth
              />
            </div>
            <div className="form-group">
              <label style={{ display: "block", fontSize: "var(--font-sm)", marginBottom: "var(--space-1)" }}>
                {t(`${f}.typeMasterId`)}
              </label>
              <SelectControl
                options={[
                  { value: "", label: "—" },
                  ...tcgTypes.map(g => ({ value: String(g.id), label: g.name_ja })),
                ]}
                value={form.type_master_id != null ? String(form.type_master_id) : ""}
                onChange={e => setForm({ ...form, type_master_id: e.target.value ? Number(e.target.value) : null })}
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
