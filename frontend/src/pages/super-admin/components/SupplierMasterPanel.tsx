/**
 * SupplierMasterPanel — 仕入元マスタパネル（AnalysisRulesPage の hub-content 内で使用）
 *
 * SupplierMasterPage の内容を PageLayout なしで抽出。
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型クラスのみ使用。
 */
import { useCallback, useEffect, useRef, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api } from "../../../lib/api";
import { ContentToolbar } from "../../../components/ContentToolbar";
import { HeaderButton } from "../../../components/HeaderButton";
import { DataTable, type DataTableColumn } from "../../../components/DataTable";
import { EmptyState } from "../../../components/EmptyState";
import { TextField } from "../../../components/TextField";
import { Modal } from "../../../components/Modal";
import ConfirmModal from "../../../components/ConfirmModal";

interface CentralSupplier {
  id: number;
  supplier_code: string | null;
  name: string;
  email: string | null;
  phone: string | null;
  is_active: boolean;
  line_name: string | null;
  postal_code: string | null;
  prefecture: string | null;
  city: string | null;
  address1: string | null;
  address2: string | null;
  discord_channel_id: string | null;
}

interface DiscordRouting {
  id: number;
  supplier_id: number;
  discord_guild_id: string;
  discord_channel_id: string;
  is_active: boolean;
}

type SupplierFormState = {
  name: string;
  line_name: string;
  email: string;
  phone: string;
  postal_code: string;
  prefecture: string;
  city: string;
  address1: string;
  address2: string;
  is_active: boolean;
};

const emptyForm: SupplierFormState = {
  name: "",
  line_name: "",
  email: "",
  phone: "",
  postal_code: "",
  prefecture: "",
  city: "",
  address1: "",
  address2: "",
  is_active: true,
};

const PER_PAGE = 50;

export function SupplierMasterPanel() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [items, setItems] = useState<CentralSupplier[]>([]);
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);
  const exportLock = useRef(false);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());

  // 編集/新規ポップアップ
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<SupplierFormState>(emptyForm);
  const [editId, setEditId] = useState<number | null>(null);

  // 一括削除確認
  const [confirmDelete, setConfirmDelete] = useState(false);

  // Discord routing 編集（編集ポップアップ内の「Discord紐付け」ボタンから開く）
  const [routingFor, setRoutingFor] = useState<{ id: number; name: string } | null>(null);
  const [routings, setRoutings] = useState<DiscordRouting[]>([]);
  const [routingForm, setRoutingForm] = useState({ discord_guild_id: "", discord_channel_id: "", is_active: true });

  const supplierFormRef = useRef<HTMLFormElement>(null);
  const routingFormRef = useRef<HTMLFormElement>(null);

  async function downloadExport() {
    if (exportLock.current) return;
    exportLock.current = true; setExporting(true); setError("");
    let url: string | undefined;
    const anchor = document.createElement("a");
    try {
      const blob = await api.getBlob("/super-admin/suppliers/export");
      url = URL.createObjectURL(blob); anchor.href = url;
      anchor.download = "suppliers-export.csv";
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
      const data = await api.get<CentralSupplier[]>(`/super-admin/suppliers?${params.toString()}`);
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  }, [page, search, t]);

  useEffect(() => { void load(); }, [load]);

  const runSearch = () => { setSearch(searchInput); setPage(1); };

  const openCreate = () => { setEditId(null); setForm(emptyForm); setShowForm(true); };
  const openEdit = (s: CentralSupplier) => {
    setEditId(s.id);
    setForm({
      name: s.name,
      line_name: s.line_name || "",
      email: s.email || "",
      phone: s.phone || "",
      postal_code: s.postal_code || "",
      prefecture: s.prefecture || "",
      city: s.city || "",
      address1: s.address1 || "",
      address2: s.address2 || "",
      is_active: s.is_active,
    });
    setShowForm(true);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const toNull = (v: string) => v || null;
    const payload = {
      name: form.name,
      is_active: form.is_active,
      line_name: toNull(form.line_name),
      email: toNull(form.email),
      phone: toNull(form.phone),
      postal_code: toNull(form.postal_code),
      prefecture: toNull(form.prefecture),
      city: toNull(form.city),
      address1: toNull(form.address1),
      address2: toNull(form.address2),
    };
    try {
      if (editId) {
        await api.patch(`/super-admin/suppliers/${editId}`, payload);
      } else {
        await api.post("/super-admin/suppliers", payload);
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
      selectedIds.map((id) => api.delete(`/super-admin/suppliers/${id}`)),
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

  // --- Discord routing ---
  const openRouting = async () => {
    if (editId === null) return;
    setRoutingFor({ id: editId, name: form.name });
    try {
      const data = await api.get<DiscordRouting[]>(`/super-admin/suppliers/${editId}/discord-routing`);
      setRoutings(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  };
  const addRouting = async (e: FormEvent) => {
    e.preventDefault();
    if (!routingFor) return;
    try {
      await api.post(`/super-admin/suppliers/${routingFor.id}/discord-routing`, { supplier_id: routingFor.id, ...routingForm });
      setRoutingForm({ discord_guild_id: "", discord_channel_id: "", is_active: true });
      setRoutings(await api.get<DiscordRouting[]>(`/super-admin/suppliers/${routingFor.id}/discord-routing`));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    }
  };
  const deleteRouting = async (id: number) => {
    if (!routingFor) return;
    try {
      await api.delete(`/super-admin/suppliers/discord-routing/${id}`);
      setRoutings(await api.get<DiscordRouting[]>(`/super-admin/suppliers/${routingFor.id}/discord-routing`));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.deleteError"));
    }
  };

  const f = "superAdmin.suppliersAdmin.fields";

  const columns: DataTableColumn<CentralSupplier>[] = [
    { key: "name", header: t(`${f}.name`) },
    { key: "line_name", header: t(`${f}.lineName`), renderCell: row => row.line_name || "-" },
    { key: "discord_channel_id", header: t(`${f}.discordId`), renderCell: row => row.discord_channel_id ? <code>{row.discord_channel_id}</code> : "-" },
    { key: "phone", header: t(`${f}.phone`), renderCell: row => row.phone || "-" },
    { key: "email", header: t(`${f}.email`), renderCell: row => row.email || "-" },
    {
      key: "_edit",
      header: "",
      renderCell: row => (
        <HeaderButton variant="secondary" data-testid={`supplier-edit-${row.id}`} onClick={() => openEdit(row)}>
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
            <HeaderButton variant="secondary" disabled={exporting} data-testid="suppliers-export" onClick={() => void downloadExport()}>
              {t(exporting ? "common.loading" : "supplierCsv.exportButton")}
            </HeaderButton>
            <HeaderButton variant="primary" data-testid="suppliers-new" onClick={openCreate}>
              {t("superAdmin.suppliersAdmin.newSupplier")}
            </HeaderButton>
            <HeaderButton variant="primary" data-testid="suppliers-import" onClick={() => navigate("/super-admin/masters/suppliers/import")}>
              {t("supplierCsv.importButton")}
            </HeaderButton>
            <HeaderButton variant="secondary" disabled={selectedKeys.size === 0} data-testid="suppliers-bulk-delete" onClick={() => setConfirmDelete(true)}>
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
            label={t(`${f}.name`)}
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") runSearch(); }}
            data-testid="suppliers-search"
          />
        }
        right={
          <HeaderButton variant="primary" data-testid="suppliers-search-btn" onClick={runSearch}>
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
        emptyState={<EmptyState title={t("common.noData")} size="compact" />}
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
        title={editId ? t("common.edit") : t("common.create")}
        size="lg"
      >
        <form ref={supplierFormRef} onSubmit={e => { void submit(e); }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3) var(--space-4)" }}>
            <div className="form-group" style={{ gridColumn: "1 / -1" }}>
              <TextField
                label={`${t(`${f}.name`)} *`}
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <TextField
                label={t(`${f}.lineName`)}
                value={form.line_name}
                onChange={e => setForm({ ...form, line_name: e.target.value })}
              />
            </div>
            <div className="form-group">
              <TextField
                label={t(`${f}.phone`)}
                value={form.phone}
                onChange={e => setForm({ ...form, phone: e.target.value })}
              />
            </div>
            <div className="form-group" style={{ gridColumn: "1 / -1" }}>
              <TextField
                type="email"
                label={t(`${f}.email`)}
                value={form.email}
                onChange={e => setForm({ ...form, email: e.target.value })}
              />
            </div>
            <div className="form-group">
              <TextField
                label={t(`${f}.postalCode`)}
                value={form.postal_code}
                onChange={e => setForm({ ...form, postal_code: e.target.value })}
              />
            </div>
            <div className="form-group">
              <TextField
                label={t(`${f}.prefecture`)}
                value={form.prefecture}
                onChange={e => setForm({ ...form, prefecture: e.target.value })}
              />
            </div>
            <div className="form-group">
              <TextField
                label={t(`${f}.city`)}
                value={form.city}
                onChange={e => setForm({ ...form, city: e.target.value })}
              />
            </div>
            <div className="form-group">
              <TextField
                label={t(`${f}.address1`)}
                value={form.address1}
                onChange={e => setForm({ ...form, address1: e.target.value })}
              />
            </div>
            <div className="form-group" style={{ gridColumn: "1 / -1" }}>
              <TextField
                label={t(`${f}.address2`)}
                value={form.address2}
                onChange={e => setForm({ ...form, address2: e.target.value })}
              />
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <input type="checkbox" checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} />
              {t(`${f}.isActive`)}
            </label>
            {editId !== null && (
              <div style={{ gridColumn: "1 / -1" }}>
                <HeaderButton variant="secondary" data-testid="supplier-open-routing" onClick={() => { void openRouting(); }}>
                  {t("superAdmin.suppliersAdmin.discordRouting")}
                </HeaderButton>
              </div>
            )}
          </div>
          <div className="form-actions">
            <HeaderButton variant="secondary" onClick={() => setShowForm(false)}>{t("common.cancel")}</HeaderButton>
            <HeaderButton variant="primary" onClick={() => supplierFormRef.current?.requestSubmit()}>{editId ? t("common.update") : t("common.create")}</HeaderButton>
          </div>
        </form>
      </Modal>

      {/* Discord routing モーダル */}
      <Modal
        open={!!routingFor}
        onClose={() => setRoutingFor(null)}
        title={routingFor ? `${t("superAdmin.suppliersAdmin.discordRouting")} — ${routingFor.name}` : ""}
        size="md"
      >
        {/* ui-allow: Discord routing table is a small inline form, not a data listing (#3558) */}
        <form ref={routingFormRef} onSubmit={e => { void addRouting(e); }} style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "var(--space-2)", margin: "var(--space-2) 0" }}>
          <TextField
            label={t("superAdmin.suppliersAdmin.guildId")}
            value={routingForm.discord_guild_id}
            onChange={e => setRoutingForm({ ...routingForm, discord_guild_id: e.target.value })}
            required
          />
          <TextField
            label={t("superAdmin.suppliersAdmin.channelId")}
            value={routingForm.discord_channel_id}
            onChange={e => setRoutingForm({ ...routingForm, discord_channel_id: e.target.value })}
            required
          />
          <HeaderButton variant="primary" onClick={() => routingFormRef.current?.requestSubmit()}>{t("superAdmin.suppliersAdmin.addRouting")}</HeaderButton>
        </form>
        <table className="data-table">
          <thead>
            <tr>
              <th>{t("superAdmin.suppliersAdmin.guildId")}</th>
              <th>{t("superAdmin.suppliersAdmin.channelId")}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {routings.map(r => (
              <tr key={r.id}>
                <td><code>{r.discord_guild_id}</code></td>
                <td><code>{r.discord_channel_id}</code></td>
                <td style={{ textAlign: "right" }}>
                  <HeaderButton variant="secondary" onClick={() => { void deleteRouting(r.id); }}>{t("common.delete")}</HeaderButton>
                </td>
              </tr>
            ))}
            {routings.length === 0 && <tr><td colSpan={3} className="empty">{t("common.noData")}</td></tr>}
          </tbody>
        </table>
        <div style={{ marginTop: "var(--space-2)", textAlign: "right" }}>
          <HeaderButton variant="secondary" onClick={() => setRoutingFor(null)}>{t("common.close")}</HeaderButton>
        </div>
      </Modal>

      <ConfirmModal
        open={confirmDelete}
        title={t("common.delete")}
        message={t("superAdmin.suppliersAdmin.bulkDeleteConfirm", { count: selectedKeys.size })}
        confirmLabel={t("common.delete")}
        danger
        onConfirm={() => { void bulkDelete(); }}
        onCancel={() => setConfirmDelete(false)}
      />
    </>
  );
}
