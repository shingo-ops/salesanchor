/**
 * NoteMasterPage — 備考マスタ管理（管理センター内）
 *
 * テナント個別エントリのみ編集可能。共用エントリ（super-admin管理）は読み取り専用で表示。
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
import { Select } from "../../components/Select";
import { HeaderButton } from "../../components/HeaderButton";
import { STATUS_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";

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

export default function NoteMasterPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { hasPermission } = usePermissions();
  const exportLock = useRef(false);
  const [exporting, setExporting] = useState(false);
  const [notes, setNotes] = useState<TcgNoteMaster[]>([]);
  const [error, setError] = useState("");

  async function downloadExport() {
    if (exportLock.current) return;
    exportLock.current = true; setExporting(true); setError("");
    let url: string | undefined;
    const anchor = document.createElement("a");
    try {
      const blob = await api.getBlob("/note-master/export");
      url = URL.createObjectURL(blob); anchor.href = url;
      anchor.download = "note-master-export.csv";
      document.body.appendChild(anchor); anchor.click();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      anchor.remove(); if (url) URL.revokeObjectURL(url); exportLock.current = false; setExporting(false);
    }
  }
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);

  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<NoteFormState>(emptyForm);

  const [editId, setEditId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<NoteFormState>(emptyForm);
  const [showEdit, setShowEdit] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<TcgNoteMaster | null>(null);

  const createFormRef = useRef<HTMLFormElement>(null);
  const editFormRef = useRef<HTMLFormElement>(null);

  const f = "analysisRules.noteMaster";

  const load = async () => {
    try {
      const params = new URLSearchParams({ page: String(page), per_page: String(PER_PAGE) });
      const data = await api.get<TcgNoteMaster[]>(`/note-master?${params.toString()}`);
      setNotes(data);
      setHasNext(data.length === PER_PAGE);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [page]);

  const handleCreateSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const toNull = (v: string) => v || null;
    const payload = {
      label_ja: createForm.label_ja,
      label_en: createForm.label_en,
      category: createForm.category,
      match_type: createForm.match_type,
      priority: parseInt(createForm.priority, 10) || 0,
      enabled: createForm.enabled,
      search_keywords: createForm.search_keywords,
      exclude_keywords: createForm.exclude_keywords,
      search_pattern: toNull(createForm.search_pattern),
      label_template: toNull(createForm.label_template),
    };
    try {
      await api.post("/note-master", payload);
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
    if (editId === null) return;
    const toNull = (v: string) => v || null;
    const payload = {
      label_ja: editForm.label_ja,
      label_en: editForm.label_en,
      category: editForm.category,
      match_type: editForm.match_type,
      priority: parseInt(editForm.priority, 10) || 0,
      enabled: editForm.enabled,
      search_keywords: editForm.search_keywords,
      exclude_keywords: editForm.exclude_keywords,
      search_pattern: toNull(editForm.search_pattern),
      label_template: toNull(editForm.label_template),
    };
    try {
      await api.patch(`/note-master/${editId}`, payload);
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
      await api.delete(`/note-master/${deleteTarget.id}`);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
    }
  };

  const openEdit = (n: TcgNoteMaster) => {
    setEditId(n.id);
    setEditForm(toForm(n));
    setShowEdit(true);
  };

  const columns: DataTableColumn<TcgNoteMaster>[] = [
    { key: "label_ja", header: t(`${f}.labelJa`) },
    { key: "label_en", header: t(`${f}.labelEn`) },
    { key: "category", header: t(`${f}.category`), renderCell: n => n.category || "-" },
    {
      key: "match_type",
      header: t(`${f}.matchType`),
      renderCell: n => <span className="badge">{n.match_type}</span>,
    },
    { key: "priority", header: t(`${f}.priority`) },
    {
      key: "enabled",
      header: t(`${f}.enabled`),
      renderCell: n => n.enabled
        ? <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" />
        : "-",
    },
    {
      key: "actions",
      header: t("common.actions"),
      renderCell: n => (
        <span className="actions">
          {hasPermission("suppliers.view") && (
            <button
              className="btn-sm"
              onClick={(e) => { e.stopPropagation(); openEdit(n); }}
            >
              {t("common.edit")}
            </button>
          )}
          {hasPermission("suppliers.view") && (
            <button
              className="btn-sm btn-danger"
              onClick={(e) => { e.stopPropagation(); setDeleteTarget(n); }}
            >
              {t("common.delete")}
            </button>
          )}
        </span>
      ),
    },
  ];

  function NoteFormFields({
    form: formState,
    setForm: setFormState,
  }: {
    form: NoteFormState;
    setForm: (f: NoteFormState) => void;
  }) {
    return (
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3) var(--space-4)" }}>
        <div className="form-group">
          <TextField
            label={`${t(`${f}.labelJa`)} *`}
            value={formState.label_ja}
            onChange={e => setFormState({ ...formState, label_ja: e.target.value })}
            required
          />
        </div>
        <div className="form-group">
          <TextField
            label={`${t(`${f}.labelEn`)} *`}
            value={formState.label_en}
            onChange={e => setFormState({ ...formState, label_en: e.target.value })}
            required
          />
        </div>
        <div className="form-group">
          <TextField
            label={t(`${f}.category`)}
            value={formState.category}
            onChange={e => setFormState({ ...formState, category: e.target.value })}
          />
        </div>
        <div className="form-group">
          <Select
            label={t(`${f}.matchType`)}
            options={MATCH_TYPE_OPTIONS}
            value={formState.match_type}
            onChange={e => setFormState({ ...formState, match_type: e.target.value })}
            fullWidth
          />
        </div>
        <div className="form-group">
          <TextField
            type="number"
            label={`${t(`${f}.priority`)} *`}
            value={formState.priority}
            onChange={e => setFormState({ ...formState, priority: e.target.value })}
            required
          />
        </div>
        <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
          <input
            type="checkbox"
            checked={formState.enabled}
            onChange={e => setFormState({ ...formState, enabled: e.target.checked })}
          />
          {t(`${f}.enabled`)}
        </label>
        <div className="form-group" style={{ gridColumn: "1 / -1" }}>
          <TextField
            label={t(`${f}.searchKeywords`)}
            value={formState.search_keywords}
            onChange={e => setFormState({ ...formState, search_keywords: e.target.value })}
          />
        </div>
        <div className="form-group" style={{ gridColumn: "1 / -1" }}>
          <TextField
            label={t(`${f}.excludeKeywords`)}
            value={formState.exclude_keywords}
            onChange={e => setFormState({ ...formState, exclude_keywords: e.target.value })}
          />
        </div>
        <div className="form-group" style={{ gridColumn: "1 / -1" }}>
          <TextField
            label={t(`${f}.searchPattern`)}
            value={formState.search_pattern}
            onChange={e => setFormState({ ...formState, search_pattern: e.target.value })}
          />
        </div>
        <div className="form-group" style={{ gridColumn: "1 / -1" }}>
          <TextField
            label={t(`${f}.labelTemplate`)}
            value={formState.label_template}
            onChange={e => setFormState({ ...formState, label_template: e.target.value })}
          />
        </div>
      </div>
    );
  }

  return (
    <PageLayout
      navKey="nav.noteMaster"
      subtitleKey={`${f}.description`}
      headerAction={
        hasPermission("suppliers.view") ? (
          <>
            <HeaderButton variant="secondary" disabled={exporting} data-testid="note-master-export" onClick={() => void downloadExport()}>
              {t(exporting ? "common.loading" : "noteMasterCsv.exportButton")}
            </HeaderButton>
            <HeaderButton variant="primary" data-testid="note-master-import" onClick={() => navigate("/management-center/note-master/import")}>
              {t("noteMasterCsv.importButton")}
            </HeaderButton>
            <HeaderButton
              variant="primary"
              onClick={() => { setShowCreate(true); setCreateForm(emptyForm); }}
              data-testid="note-master-new"
            >
              {t(`${f}.addNote`)}
            </HeaderButton>
          </>
        ) : undefined
      }
    >
      {error && <div className="error-message">{error}</div>}

      <ContentToolbar right={undefined} />

      {loading ? (
        <div className="loading">{t("common.loading")}</div>
      ) : (
        <DataTable<TcgNoteMaster>
          columns={columns}
          data={notes}
          rowKey={n => String(n.id)}
          onRowClick={hasPermission("suppliers.view") ? n => openEdit(n) : undefined}
          emptyState={t(`${f}.noNotes`)}
          page={page}
          hasNextPage={hasNext}
          onPageChange={setPage}
          prevPageLabel={t("common.prevPage")}
          nextPageLabel={t("common.nextPage")}
        />
      )}

      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title={t(`${f}.addNote`)}
        size="lg"
      >
        <form ref={createFormRef} onSubmit={handleCreateSubmit}>
          <NoteFormFields form={createForm} setForm={setCreateForm} />
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

      <Modal
        open={showEdit}
        onClose={() => setShowEdit(false)}
        title={t(`${f}.editNote`)}
        size="lg"
      >
        <form ref={editFormRef} onSubmit={handleEditSubmit}>
          <NoteFormFields form={editForm} setForm={setEditForm} />
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

      <ConfirmModal
        open={!!deleteTarget}
        title={t("common.delete")}
        message={t(`${f}.deleteConfirm`)}
        confirmLabel={t("common.delete")}
        danger
        onConfirm={performDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </PageLayout>
  );
}
