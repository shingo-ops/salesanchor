/**
 * NoteMasterPanel — 備考マスタパネル（AnalysisRulesPage の hub-content 内で使用）
 *
 * SupplierMasterPanel パターンを踏襲。
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
import { Select } from "../../../components/Select";
import { Drawer } from "../../../components/Drawer";
import ConfirmModal from "../../../components/ConfirmModal";
import { STATUS_ICONS } from "../../../constants/icons";
import { ICON } from "../../../constants/iconSizes";

interface TcgNoteMaster {
  id: number;
  label_ja: string;
  label_en: string;
  enabled: boolean;
  search_keywords: string;
  exclude_keywords: string;
  category: string;
  priority: number;
  match_type: string;
  search_pattern: string | null;
  label_template: string | null;
}

type NoteFormState = {
  label_ja: string;
  label_en: string;
  category: string;
  match_type: string;
  priority: string;
  enabled: boolean;
  search_keywords: string;
  exclude_keywords: string;
  search_pattern: string;
  label_template: string;
};

const emptyForm: NoteFormState = {
  label_ja: "",
  label_en: "",
  category: "",
  match_type: "LITERAL",
  priority: "0",
  enabled: true,
  search_keywords: "",
  exclude_keywords: "",
  search_pattern: "",
  label_template: "",
};

const toForm = (n: TcgNoteMaster): NoteFormState => ({
  label_ja: n.label_ja,
  label_en: n.label_en,
  category: n.category,
  match_type: n.match_type,
  priority: String(n.priority),
  enabled: n.enabled,
  search_keywords: n.search_keywords,
  exclude_keywords: n.exclude_keywords,
  search_pattern: n.search_pattern ?? "",
  label_template: n.label_template ?? "",
});

const MATCH_TYPE_OPTIONS = [
  { value: "LITERAL", label: "LITERAL" },
  { value: "REGEX", label: "REGEX" },
  { value: "DEFAULT", label: "DEFAULT" },
];

const PER_PAGE = 100;

export function NoteMasterPanel() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const exportLock = useRef(false);
  const [exporting, setExporting] = useState(false);
  const [items, setItems] = useState<TcgNoteMaster[]>([]);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<NoteFormState>(emptyForm);
  const [editId, setEditId] = useState<number | null>(null);

  async function downloadExport() {
    if (exportLock.current) return;
    exportLock.current = true; setExporting(true); setError("");
    let url: string | undefined;
    const anchor = document.createElement("a");
    try {
      const blob = await api.getBlob("/super-admin/note-master/export");
      url = URL.createObjectURL(blob); anchor.href = url;
      anchor.download = "note-master-export.csv";
      document.body.appendChild(anchor); anchor.click();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      anchor.remove(); if (url) URL.revokeObjectURL(url); exportLock.current = false; setExporting(false);
    }
  }

  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);

  const formRef = useRef<HTMLFormElement>(null);

  const f = "analysisRules.noteMaster";

  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams({ page: String(page), per_page: String(PER_PAGE) });
      const data = await api.get<TcgNoteMaster[]>(`/super-admin/note-master?${params.toString()}`);
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  }, [page, t]);

  useEffect(() => { void load(); }, [load]);

  const openCreate = () => { setEditId(null); setForm(emptyForm); setShowForm(true); };
  const openEdit = (n: TcgNoteMaster) => {
    setEditId(n.id);
    setForm(toForm(n));
    setShowForm(true);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const toNull = (v: string) => v || null;
    const payload = {
      label_ja: form.label_ja,
      label_en: form.label_en,
      category: form.category,
      match_type: form.match_type,
      priority: parseInt(form.priority, 10) || 0,
      enabled: form.enabled,
      search_keywords: form.search_keywords,
      exclude_keywords: form.exclude_keywords,
      search_pattern: toNull(form.search_pattern),
      label_template: toNull(form.label_template),
    };
    try {
      if (editId !== null) {
        await api.patch(`/super-admin/note-master/${editId}`, payload);
      } else {
        await api.post("/super-admin/note-master", payload);
      }
      setShowForm(false);
      setForm(emptyForm);
      setEditId(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    }
  };

  const performDelete = async (id: number) => {
    setConfirmDelete(null);
    try {
      await api.delete(`/super-admin/note-master/${id}`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
    }
  };

  const columns: DataTableColumn<TcgNoteMaster>[] = [
    { key: "label_ja", header: t(`${f}.labelJa`) },
    { key: "label_en", header: t(`${f}.labelEn`) },
    { key: "category", header: t(`${f}.category`), renderCell: row => row.category || "-" },
    {
      key: "match_type",
      header: t(`${f}.matchType`),
      renderCell: row => <span className="badge">{row.match_type}</span>,
    },
    { key: "priority", header: t(`${f}.priority`) },
    {
      key: "enabled",
      header: t(`${f}.enabled`),
      renderCell: row => row.enabled
        ? <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" />
        : "-",
    },
  ];

  return (
    <>
      <ContentToolbar
        right={
          <>
            <HeaderButton variant="secondary" disabled={exporting} data-testid="note-master-export" onClick={() => void downloadExport()}>
              {t(exporting ? "common.loading" : "noteMasterCsv.exportButton")}
            </HeaderButton>
            <HeaderButton variant="primary" data-testid="note-master-import" onClick={() => navigate("/super-admin/masters/note-master/import")}>
              {t("noteMasterCsv.importButton")}
            </HeaderButton>
            <HeaderButton variant="primary" data-testid="note-master-new" onClick={openCreate}>
              {t(`${f}.addNote`)}
            </HeaderButton>
          </>
        }
      />
      {error && <p role="alert">{error}</p>}
      <DataTable
        columns={columns}
        data={items}
        rowKey={row => String(row.id)}
        onRowClick={row => openEdit(row)}
        emptyState={<EmptyState title={t(`${f}.noNotes`)} size="compact" />}
        page={page}
        hasNextPage={items.length >= PER_PAGE}
        onPageChange={setPage}
        prevPageLabel={t("common.prevPage")}
        nextPageLabel={t("common.nextPage")}
      />

      <Drawer
        open={showForm}
        onClose={() => setShowForm(false)}
        title={editId !== null ? t(`${f}.editNote`) : t(`${f}.addNote`)}
        footer={
          <>
            {editId !== null && (
              <HeaderButton variant="secondary" onClick={() => { setShowForm(false); setConfirmDelete(editId); }}>
                {t("common.delete")}
              </HeaderButton>
            )}
            <div style={{ marginLeft: "auto", display: "flex", gap: "var(--space-2)" }}>
              <HeaderButton variant="secondary" onClick={() => setShowForm(false)}>
                {t("common.back")}
              </HeaderButton>
              <HeaderButton variant="primary" onClick={() => formRef.current?.requestSubmit()}>
                {editId !== null ? t("common.update") : t("common.create")}
              </HeaderButton>
            </div>
          </>
        }
      >
        <form ref={formRef} onSubmit={e => { void submit(e); }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3) var(--space-4)" }}>
            <div className="form-group">
              <TextField
                label={`${t(`${f}.labelJa`)} *`}
                value={form.label_ja}
                onChange={e => setForm({ ...form, label_ja: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <TextField
                label={`${t(`${f}.labelEn`)} *`}
                value={form.label_en}
                onChange={e => setForm({ ...form, label_en: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <TextField
                label={t(`${f}.category`)}
                value={form.category}
                onChange={e => setForm({ ...form, category: e.target.value })}
              />
            </div>
            <div className="form-group">
              <Select
                label={t(`${f}.matchType`)}
                options={MATCH_TYPE_OPTIONS}
                value={form.match_type}
                onChange={e => setForm({ ...form, match_type: e.target.value })}
                fullWidth
              />
            </div>
            <div className="form-group">
              <TextField
                type="number"
                label={`${t(`${f}.priority`)} *`}
                value={form.priority}
                onChange={e => setForm({ ...form, priority: e.target.value })}
                required
              />
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <input
                type="checkbox"
                checked={form.enabled}
                onChange={e => setForm({ ...form, enabled: e.target.checked })}
              />
              {t(`${f}.enabled`)}
            </label>
            <div className="form-group" style={{ gridColumn: "1 / -1" }}>
              <TextField
                label={t(`${f}.searchKeywords`)}
                value={form.search_keywords}
                onChange={e => setForm({ ...form, search_keywords: e.target.value })}
              />
            </div>
            <div className="form-group" style={{ gridColumn: "1 / -1" }}>
              <TextField
                label={t(`${f}.excludeKeywords`)}
                value={form.exclude_keywords}
                onChange={e => setForm({ ...form, exclude_keywords: e.target.value })}
              />
            </div>
            <div className="form-group" style={{ gridColumn: "1 / -1" }}>
              <TextField
                label={t(`${f}.searchPattern`)}
                value={form.search_pattern}
                onChange={e => setForm({ ...form, search_pattern: e.target.value })}
              />
            </div>
            <div className="form-group" style={{ gridColumn: "1 / -1" }}>
              <TextField
                label={t(`${f}.labelTemplate`)}
                value={form.label_template}
                onChange={e => setForm({ ...form, label_template: e.target.value })}
              />
            </div>
          </div>
        </form>
      </Drawer>

      <ConfirmModal
        open={confirmDelete !== null}
        title={t("common.delete")}
        message={t(`${f}.deleteConfirm`)}
        confirmLabel={t("common.delete")}
        danger
        onConfirm={() => { if (confirmDelete !== null) void performDelete(confirmDelete); }}
        onCancel={() => setConfirmDelete(null)}
      />
    </>
  );
}
