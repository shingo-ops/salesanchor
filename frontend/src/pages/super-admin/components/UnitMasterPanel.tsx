/**
 * UnitMasterPanel — 単位マスタパネル（AnalysisRulesPage の hub-content 内で使用）
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
import { Drawer } from "../../../components/Drawer";
import ConfirmModal from "../../../components/ConfirmModal";
import { STATUS_ICONS } from "../../../constants/icons";
import { ICON } from "../../../constants/iconSizes";

interface CentralUnit {
  id: number;
  code: string;
  canonical: string;
  kubun: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface UnitAlias {
  id: number;
  unit_id: number;
  alias_text: string;
  lang: string;
  updated_at: string;
}

type UnitFormState = {
  code: string;
  canonical: string;
  kubun: string;
  is_active: boolean;
};

const emptyForm: UnitFormState = {
  code: "",
  canonical: "",
  kubun: "",
  is_active: true,
};

const PER_PAGE = 50;

export function UnitMasterPanel() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const exportLock = useRef(false);
  const [exporting, setExporting] = useState(false);
  const [items, setItems] = useState<CentralUnit[]>([]);
  const [error, setError] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<UnitFormState>(emptyForm);
  const [editId, setEditId] = useState<number | null>(null);

  const [confirmDelete, setConfirmDelete] = useState(false);

  // 別名管理（編集モーダル内）
  const [aliasesFor, setAliasesFor] = useState<{ id: number; code: string } | null>(null);
  const [aliases, setAliases] = useState<UnitAlias[]>([]);
  const [aliasForm, setAliasForm] = useState({ alias_text: "", lang: "ja" });

  const unitFormRef = useRef<HTMLFormElement>(null);
  const aliasFormRef = useRef<HTMLFormElement>(null);

  async function downloadExport() {
    if (exportLock.current) return;
    exportLock.current = true; setExporting(true); setError("");
    let url: string | undefined;
    const anchor = document.createElement("a");
    try {
      const blob = await api.getBlob("/super-admin/units/export");
      url = URL.createObjectURL(blob); anchor.href = url;
      anchor.download = "units-export.csv";
      document.body.appendChild(anchor); anchor.click();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      anchor.remove(); if (url) URL.revokeObjectURL(url); exportLock.current = false; setExporting(false);
    }
  }

  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams({ page: String(page), per_page: String(PER_PAGE) });
      params.set("is_active", "true");
      if (search.trim()) params.set("q", search.trim());
      const data = await api.get<CentralUnit[]>(`/super-admin/units?${params.toString()}`);
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  }, [page, search, t]);

  useEffect(() => { void load(); }, [load]);

  const runSearch = () => { setSearch(searchInput); setPage(1); };

  const openCreate = () => { setEditId(null); setForm(emptyForm); setShowForm(true); };
  const openEdit = (u: CentralUnit) => {
    setEditId(u.id);
    setForm({
      code: u.code,
      canonical: u.canonical,
      kubun: u.kubun || "",
      is_active: u.is_active,
    });
    setShowForm(true);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const toNull = (v: string) => v || null;
    const payload = {
      code: form.code,
      canonical: form.canonical,
      kubun: toNull(form.kubun),
      is_active: form.is_active,
    };
    try {
      if (editId) {
        await api.patch(`/super-admin/units/${editId}`, payload);
      } else {
        await api.post("/super-admin/units", payload);
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
      selectedIds.map((id) => api.delete(`/super-admin/units/${id}`)),
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

  // --- aliases ---
  const openAliases = async () => {
    if (editId === null) return;
    setAliasesFor({ id: editId, code: form.code });
    try {
      const data = await api.get<UnitAlias[]>(`/super-admin/units/${editId}/aliases`);
      setAliases(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  };

  const addAlias = async (e: FormEvent) => {
    e.preventDefault();
    if (!aliasesFor) return;
    try {
      await api.post(`/super-admin/units/${aliasesFor.id}/aliases`, {
        unit_id: aliasesFor.id,
        ...aliasForm,
      });
      setAliasForm({ alias_text: "", lang: "ja" });
      setAliases(await api.get<UnitAlias[]>(`/super-admin/units/${aliasesFor.id}/aliases`));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    }
  };

  const deleteAlias = async (id: number) => {
    if (!aliasesFor) return;
    try {
      await api.delete(`/super-admin/units/aliases/${id}`);
      setAliases(await api.get<UnitAlias[]>(`/super-admin/units/${aliasesFor.id}/aliases`));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.deleteError"));
    }
  };

  const f = "unitMaster";

  const columns: DataTableColumn<CentralUnit>[] = [
    { key: "canonical", header: t(`${f}.canonical`) },
    { key: "kubun", header: t(`${f}.kubun`), renderCell: row => row.kubun || "-" },
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
            <HeaderButton variant="secondary" disabled={exporting} data-testid="units-export" onClick={() => void downloadExport()}>
              {t(exporting ? "common.loading" : "unitCsv.exportButton")}
            </HeaderButton>
            <HeaderButton variant="primary" data-testid="units-import" onClick={() => navigate("/super-admin/masters/units/import")}>
              {t("unitCsv.importButton")}
            </HeaderButton>
            <HeaderButton
              variant="primary"
              data-testid="units-new"
              onClick={openCreate}
            >
              {t("common.create")}
            </HeaderButton>
            <HeaderButton
              variant="secondary"
              disabled={selectedKeys.size === 0}
              data-testid="units-bulk-delete"
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
            data-testid="units-search"
          />
        }
        right={
          <HeaderButton
            variant="primary"
            data-testid="units-search-btn"
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
                onClick={() => unitFormRef.current?.requestSubmit()}
              >
                {editId ? t("common.update") : t("common.create")}
              </HeaderButton>
            </div>
          </>
        }
      >
        <form ref={unitFormRef} onSubmit={e => { void submit(e); }}>
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
                label={`${t(`${f}.canonical`)} *`}
                value={form.canonical}
                onChange={e => setForm({ ...form, canonical: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <TextField
                label={t(`${f}.kubun`)}
                value={form.kubun}
                onChange={e => setForm({ ...form, kubun: e.target.value })}
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
            {editId !== null && (
              <div style={{ gridColumn: "1 / -1" }}>
                <HeaderButton
                  variant="secondary"
                  data-testid="unit-open-aliases"
                  onClick={() => { void openAliases(); }}
                >
                  {t(`${f}.aliases`)}
                </HeaderButton>
              </div>
            )}
          </div>
        </form>
      </Drawer>

      {/* 別名管理モーダル */}
      <Modal
        open={!!aliasesFor}
        onClose={() => setAliasesFor(null)}
        title={aliasesFor ? `${t(`${f}.aliases`)} — ${aliasesFor.code}` : ""}
        size="md"
      >
        {/* ui-allow: alias table is a small inline form, not a data listing */}
        <form
          ref={aliasFormRef}
          onSubmit={e => { void addAlias(e); }}
          style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: "var(--space-2)", margin: "var(--space-2) 0" }}
        >
          <TextField
            label={t(`${f}.aliasText`)}
            value={aliasForm.alias_text}
            onChange={e => setAliasForm({ ...aliasForm, alias_text: e.target.value })}
            required
          />
          <TextField
            label={t(`${f}.aliasLang`)}
            value={aliasForm.lang}
            onChange={e => setAliasForm({ ...aliasForm, lang: e.target.value })}
            required
          />
          <HeaderButton
            variant="primary"
            onClick={() => aliasFormRef.current?.requestSubmit()}
          >
            {t(`${f}.addAlias`)}
          </HeaderButton>
        </form>
        <table className="data-table">
          <thead>
            <tr>
              <th>{t(`${f}.aliasText`)}</th>
              <th>{t(`${f}.aliasLang`)}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {aliases.map(a => (
              <tr key={a.id}>
                <td>{a.alias_text}</td>
                <td>{a.lang}</td>
                <td style={{ textAlign: "right" }}>
                  <HeaderButton
                    variant="secondary"
                    onClick={() => { void deleteAlias(a.id); }}
                  >
                    {t(`${f}.deleteAlias`)}
                  </HeaderButton>
                </td>
              </tr>
            ))}
            {aliases.length === 0 && (
              <tr><td colSpan={3} className="empty">{t("common.noData")}</td></tr>
            )}
          </tbody>
        </table>
        <div style={{ marginTop: "var(--space-2)", textAlign: "right" }}>
          <HeaderButton variant="secondary" onClick={() => setAliasesFor(null)}>
            {t("common.close")}
          </HeaderButton>
        </div>
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
