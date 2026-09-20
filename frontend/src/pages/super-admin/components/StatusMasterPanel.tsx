/**
 * StatusMasterPanel — ステータスマスタパネル（AnalysisRulesPage の hub-content 内で使用）
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
import { Modal } from "../../../components/Modal";
import ConfirmModal from "../../../components/ConfirmModal";
import { STATUS_ICONS } from "../../../constants/icons";
import { ICON } from "../../../constants/iconSizes";

interface StatusEntry {
  id: number;
  status_id: string;
  canonical: string;
  search_pattern: string;
  exclude_pattern: string;
  priority: number;
  enabled: boolean;
  note: string;
  match_type: string;
  effect: string;
  created_at: string;
  updated_at: string;
}

type StatusFormState = {
  status_id: string;
  canonical: string;
  search_pattern: string;
  exclude_pattern: string;
  priority: number;
  enabled: boolean;
  note: string;
  match_type: string;
  effect: string;
};

const emptyForm: StatusFormState = {
  status_id: "",
  canonical: "",
  search_pattern: "",
  exclude_pattern: "",
  priority: 100,
  enabled: true,
  note: "",
  match_type: "REGEX",
  effect: "OUTPUT",
};

const PER_PAGE = 50;

export function StatusMasterPanel() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const exportLock = useRef(false);
  const [exporting, setExporting] = useState(false);
  const f = "statusMaster";

  const [items, setItems] = useState<StatusEntry[]>([]);
  const [error, setError] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());

  async function downloadExport() {
    if (exportLock.current) return;
    exportLock.current = true; setExporting(true); setError("");
    let url: string | undefined;
    const anchor = document.createElement("a");
    try {
      const blob = await api.getBlob("/super-admin/status-master/export");
      url = URL.createObjectURL(blob); anchor.href = url;
      anchor.download = "status-master-export.csv";
      document.body.appendChild(anchor); anchor.click();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      anchor.remove(); if (url) URL.revokeObjectURL(url); exportLock.current = false; setExporting(false);
    }
  }

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<StatusFormState>(emptyForm);
  const [editId, setEditId] = useState<number | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const formRef = useRef<HTMLFormElement>(null);

  const MATCH_TYPE_OPTIONS = [
    { value: "REGEX", label: t(`${f}.matchTypeRegex`) },
    { value: "LITERAL", label: t(`${f}.matchTypeLiteral`) },
    { value: "DEFAULT", label: t(`${f}.matchTypeDefault`) },
  ];

  const EFFECT_OPTIONS = [
    { value: "OUTPUT", label: t(`${f}.effectOutput`) },
    { value: "EXCLUDE", label: t(`${f}.effectExclude`) },
  ];

  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams({ page: String(page), per_page: String(PER_PAGE) });
      if (search.trim()) params.set("q", search.trim());
      const data = await api.get<StatusEntry[]>(`/super-admin/status-master?${params.toString()}`);
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  }, [page, search, t]);

  useEffect(() => { void load(); }, [load]);

  const runSearch = () => { setSearch(searchInput); setPage(1); };

  const openCreate = () => { setEditId(null); setForm(emptyForm); setShowForm(true); };
  const openEdit = (s: StatusEntry) => {
    setEditId(s.id);
    setForm({
      status_id: s.status_id,
      canonical: s.canonical,
      search_pattern: s.search_pattern,
      exclude_pattern: s.exclude_pattern,
      priority: s.priority,
      enabled: s.enabled,
      note: s.note,
      match_type: s.match_type,
      effect: s.effect,
    });
    setShowForm(true);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      if (editId) {
        await api.patch(`/super-admin/status-master/${editId}`, form);
      } else {
        await api.post("/super-admin/status-master", form);
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
      selectedIds.map((id) => api.delete(`/super-admin/status-master/${id}`)),
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

  const columns: DataTableColumn<StatusEntry>[] = [
    { key: "status_id", header: t(`${f}.statusId`) },
    { key: "canonical", header: t(`${f}.canonical`) },
    { key: "match_type", header: t(`${f}.matchType`) },
    { key: "effect", header: t(`${f}.effect`) },
    { key: "priority", header: t(`${f}.priority`) },
    {
      key: "enabled",
      header: t(`${f}.enabled`),
      renderCell: row => row.enabled ? <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" /> : "-",
    },
    {
      key: "_edit",
      header: "",
      renderCell: row => (
        <HeaderButton
          variant="secondary"
          data-testid={`status-edit-${row.id}`}
          onClick={() => openEdit(row)}
        >
          {t("common.edit")}
        </HeaderButton>
      ),
    },
  ];

  return (
    <>
      <ContentToolbar
        right={
          <>
            <HeaderButton variant="secondary" disabled={exporting} data-testid="status-master-export" onClick={() => void downloadExport()}>
              {t(exporting ? "common.loading" : "statusMasterCsv.exportButton")}
            </HeaderButton>
            <HeaderButton variant="primary" data-testid="status-master-import" onClick={() => navigate("/super-admin/masters/status-master/import")}>
              {t("statusMasterCsv.importButton")}
            </HeaderButton>
            <HeaderButton
              variant="primary"
              data-testid="status-master-new"
              onClick={openCreate}
            >
              {t("common.create")}
            </HeaderButton>
            <HeaderButton
              variant="secondary"
              disabled={selectedKeys.size === 0}
              data-testid="status-master-bulk-delete"
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
            data-testid="status-master-search"
          />
        }
        right={
          <HeaderButton
            variant="primary"
            data-testid="status-master-search-btn"
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

      {/* 編集/新規 ポップアップ */}
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
                label={`${t(`${f}.statusId`)} *`}
                value={form.status_id}
                onChange={e => setForm({ ...form, status_id: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <TextField
                label={`${t(`${f}.canonical`)} *`}
                value={form.canonical}
                onChange={e => setForm({ ...form, canonical: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <TextField
                label={t(`${f}.searchPattern`)}
                value={form.search_pattern}
                onChange={e => setForm({ ...form, search_pattern: e.target.value })}
              />
            </div>
            <div className="form-group">
              <TextField
                label={t(`${f}.excludePattern`)}
                value={form.exclude_pattern}
                onChange={e => setForm({ ...form, exclude_pattern: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label className="field-label">{t(`${f}.matchType`)} *</label>
              {/* ui-allow: enum select for status match_type; no SelectControl variant with option map (#3594) */}
              <select
                className="field field-h-md"
                value={form.match_type}
                onChange={e => setForm({ ...form, match_type: e.target.value })}
                required
              >
                {MATCH_TYPE_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="field-label">{t(`${f}.effect`)} *</label>
              {/* ui-allow: enum select for status effect; no SelectControl variant with option map (#3594) */}
              <select
                className="field field-h-md"
                value={form.effect}
                onChange={e => setForm({ ...form, effect: e.target.value })}
                required
              >
                {EFFECT_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <TextField
                label={t(`${f}.priority`)}
                type="number"
                value={String(form.priority)}
                onChange={e => setForm({ ...form, priority: Number(e.target.value) })}
                required
              />
            </div>
            <div className="form-group">
              <TextField
                label={t(`${f}.note`)}
                value={form.note}
                onChange={e => setForm({ ...form, note: e.target.value })}
              />
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", gridColumn: "1 / -1" }}>
              <input
                type="checkbox"
                checked={form.enabled}
                onChange={e => setForm({ ...form, enabled: e.target.checked })}
              />
              {t(`${f}.enabled`)}
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
