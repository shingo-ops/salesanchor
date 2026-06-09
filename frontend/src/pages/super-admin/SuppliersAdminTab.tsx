/**
 * /super-admin/masters — 仕入元（中央 admin、public.suppliers）+ Discord routing タブ。
 *
 * ADR-093 改修 (2026-06-03):
 *   - 検索は仕入元名のみ（検索窓＋検索ボタン）。
 *   - ヘッダー右に小さい「新規作成」＋一括「削除」（チェックしたものを削除）。
 *   - 一覧は閲覧専用。列= チェック / 仕入元名 / LINE名 / Discord ID / 電話 / メール ＋ 編集ボタン。
 *     （Discord ID は紐付け済み routing の channel_id を表示。編集は従来の紐付けUIで）
 *   - 編集はポップアップ。住所（郵便番号・都道府県・市町村・住所1・住所2）も編集可。
 *   - ページネーション付き。
 *   - 既定言語(default_language)/法人個人(supplier_type) は UI から撤去（既定値で送信）。
 */
import { useCallback, useEffect, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { Modal } from "../../components/Modal";
import ConfirmModal from "../../components/ConfirmModal";

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

export default function SuppliersAdminTab() {
  const { t } = useTranslation();
  const [items, setItems] = useState<CentralSupplier[]>([]);
  const [error, setError] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  // 編集/新規ポップアップ
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<SupplierFormState>(emptyForm);
  const [editId, setEditId] = useState<number | null>(null);

  // 一括削除確認
  const [confirmDelete, setConfirmDelete] = useState(false);

  // Discord routing 編集（編集ポップアップから開く）
  const [routingFor, setRoutingFor] = useState<{ id: number; name: string } | null>(null);
  const [routings, setRoutings] = useState<DiscordRouting[]>([]);
  const [routingForm, setRoutingForm] = useState({ discord_guild_id: "", discord_channel_id: "", is_active: true });

  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams({ page: String(page), per_page: String(PER_PAGE) });
      // 削除は soft delete (is_active=FALSE) のため、一覧は有効な仕入元のみ表示する
      // （削除＝一覧から消える、というユーザー想定に合わせる）。
      params.set("is_active", "true");
      if (search.trim()) params.set("q", search.trim());
      const data = await api.get<CentralSupplier[]>(`/super-admin/suppliers?${params.toString()}`);
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  }, [page, search, t]);

  useEffect(() => { load(); }, [load]);

  const runSearch = () => { setSearch(searchInput); setPage(1); };

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

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
    // supplier_type / default_language は backend 既定値（corporate / ja）に委ねる。
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
    // 一部失敗しても残りは削除し、最後に必ず一覧を再取得して整合させる。
    const results = await Promise.allSettled(
      Array.from(selectedIds).map((id) => api.delete(`/super-admin/suppliers/${id}`)),
    );
    try {
      if (results.some((r) => r.status === "rejected")) {
        setError(t("common.deleteError"));
      }
      setSelectedIds(new Set());
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
    }
  };

  // --- Discord routing（編集ポップアップ内の「Discord紐付け」ボタンから開く） ---
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

  return (
    <div className="super-admin-suppliers-tab">
      {error && <div className="error-message">{error}</div>}

      {/* ヘッダー: 検索（仕入元名）＋検索 / 右に 新規作成・削除(一括) */}
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", flexWrap: "wrap", margin: "var(--space-2) 0 var(--space-4)" }}>
        <input
          type="search"
          placeholder={t(`${f}.name`)}
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") runSearch(); }}
          style={{ width: "22rem", maxWidth: "100%" }}
          data-testid="suppliers-search"
        />
        <button type="button" className="btn-primary btn-sm" onClick={runSearch} data-testid="suppliers-search-btn">{t("common.search")}</button>
        <button type="button" className="btn-primary btn-sm" onClick={openCreate} data-testid="suppliers-new" style={{ marginLeft: "auto" }}>{t("superAdmin.suppliersAdmin.newSupplier")}</button>
        <button type="button" className="btn-danger btn-sm" disabled={selectedIds.size === 0} onClick={() => setConfirmDelete(true)} data-testid="suppliers-bulk-delete">{t("common.delete")}</button>
      </div>

      {/* 一覧は閲覧専用。編集はポップアップ。 */}
      <table className="data-table">
        <thead>
          <tr>
            <th style={{ width: "var(--col-width-checkbox)", textAlign: "center" }} aria-label={t("common.select")}></th>
            <th>{t(`${f}.name`)}</th>
            <th>{t(`${f}.lineName`)}</th>
            <th>{t(`${f}.discordId`)}</th>
            <th>{t(`${f}.phone`)}</th>
            <th>{t(`${f}.email`)}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {items.map((s) => (
            <tr key={s.id} data-testid={`supplier-row-${s.id}`}>
              <td style={{ textAlign: "center" }}>
                <input type="checkbox" checked={selectedIds.has(s.id)} onChange={() => toggleSelect(s.id)} aria-label={s.name} data-testid={`supplier-select-${s.id}`} />
              </td>
              <td>{s.name}</td>
              <td>{s.line_name || "-"}</td>
              <td>{s.discord_channel_id ? <code>{s.discord_channel_id}</code> : "-"}</td>
              <td>{s.phone || "-"}</td>
              <td>{s.email || "-"}</td>
              <td style={{ textAlign: "right" }}>
                <button type="button" className="btn-sm" onClick={() => openEdit(s)} data-testid={`supplier-edit-${s.id}`}>{t("common.edit")}</button>
              </td>
            </tr>
          ))}
          {items.length === 0 && <tr><td colSpan={7} className="empty">{t("common.noData")}</td></tr>}
        </tbody>
      </table>

      {/* ページネーション */}
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "var(--space-3)", padding: "var(--space-3) 0" }}>
        <button type="button" className="btn-sm" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))} data-testid="suppliers-prev">{t("common.prevPage")}</button>
        <span style={{ color: "var(--text-secondary)" }} data-testid="suppliers-page">{page}</span>
        <button type="button" className="btn-sm" disabled={items.length < PER_PAGE} onClick={() => setPage((p) => p + 1)} data-testid="suppliers-next">{t("common.nextPage")}</button>
      </div>

      {/* 編集/新規 ポップアップ */}
      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title={editId ? t("common.edit") : t("common.create")}
        size="lg"
      >
        <form onSubmit={submit}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3) var(--space-4)" }}>
                <div className="form-group" style={{ gridColumn: "1 / -1" }}><label>{t(`${f}.name`)} *</label>
                  <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                </div>
                <div className="form-group"><label>{t(`${f}.lineName`)}</label>
                  <input value={form.line_name} onChange={(e) => setForm({ ...form, line_name: e.target.value })} />
                </div>
                <div className="form-group"><label>{t(`${f}.phone`)}</label>
                  <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
                </div>
                <div className="form-group" style={{ gridColumn: "1 / -1" }}><label>{t(`${f}.email`)}</label>
                  <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                </div>
                <div className="form-group"><label>{t(`${f}.postalCode`)}</label>
                  <input value={form.postal_code} onChange={(e) => setForm({ ...form, postal_code: e.target.value })} />
                </div>
                <div className="form-group"><label>{t(`${f}.prefecture`)}</label>
                  <input value={form.prefecture} onChange={(e) => setForm({ ...form, prefecture: e.target.value })} />
                </div>
                <div className="form-group"><label>{t(`${f}.city`)}</label>
                  <input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
                </div>
                <div className="form-group"><label>{t(`${f}.address1`)}</label>
                  <input value={form.address1} onChange={(e) => setForm({ ...form, address1: e.target.value })} />
                </div>
                <div className="form-group" style={{ gridColumn: "1 / -1" }}><label>{t(`${f}.address2`)}</label>
                  <input value={form.address2} onChange={(e) => setForm({ ...form, address2: e.target.value })} />
                </div>
                <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                  <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
                  {t(`${f}.isActive`)}
                </label>
                {/* Discord ID は紐付けUIで編集（既存の routing 管理） */}
                {editId !== null && (
                  <div style={{ gridColumn: "1 / -1" }}>
                    <button type="button" className="btn-secondary btn-sm" onClick={openRouting} data-testid="supplier-open-routing">
                      {t("superAdmin.suppliersAdmin.discordRouting")}
                    </button>
                  </div>
                )}
              </div>
              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>{t("common.cancel")}</button>
                <button type="submit" className="btn-primary">{editId ? t("common.update") : t("common.create")}</button>
              </div>
        </form>
      </Modal>

      {/* Discord routing モーダル（編集ポップアップから開く・従来の紐付けUI） */}
      <Modal
        open={!!routingFor}
        onClose={() => setRoutingFor(null)}
        title={routingFor ? `${t("superAdmin.suppliersAdmin.discordRouting")} — ${routingFor.name}` : ""}
        size="md"
      >
            <form onSubmit={addRouting} style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "var(--space-2)", margin: "var(--space-2) 0" }}>
              <input placeholder={t("superAdmin.suppliersAdmin.guildId")} value={routingForm.discord_guild_id} onChange={(e) => setRoutingForm({ ...routingForm, discord_guild_id: e.target.value })} required />
              <input placeholder={t("superAdmin.suppliersAdmin.channelId")} value={routingForm.discord_channel_id} onChange={(e) => setRoutingForm({ ...routingForm, discord_channel_id: e.target.value })} required />
              <button type="submit" className="btn-primary">{t("superAdmin.suppliersAdmin.addRouting")}</button>
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
                {routings.map((r) => (
                  <tr key={r.id}>
                    <td><code>{r.discord_guild_id}</code></td>
                    <td><code>{r.discord_channel_id}</code></td>
                    <td style={{ textAlign: "right" }}>
                      <button type="button" onClick={() => deleteRouting(r.id)} className="btn-sm btn-danger">{t("common.delete")}</button>
                    </td>
                  </tr>
                ))}
                {routings.length === 0 && <tr><td colSpan={3} className="empty">{t("common.noData")}</td></tr>}
              </tbody>
            </table>
            <div style={{ marginTop: "var(--space-2)", textAlign: "right" }}>
              <button type="button" onClick={() => setRoutingFor(null)} className="btn-secondary">{t("common.close")}</button>
            </div>
      </Modal>

      <ConfirmModal
        open={confirmDelete}
        title={t("common.delete")}
        message={t("superAdmin.suppliersAdmin.bulkDeleteConfirm", { count: selectedIds.size })}
        confirmLabel={t("common.delete")}
        danger
        onConfirm={bulkDelete}
        onCancel={() => setConfirmDelete(false)}
      />
    </div>
  );
}
