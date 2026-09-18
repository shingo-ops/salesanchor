import { type FormEvent, useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Drawer } from "../../components/Drawer";
import { TextField } from "../../components/TextField";
import { Button } from "../../components/Button";
import ConfirmModal from "../../components/ConfirmModal";
import { HeaderButton } from "../../components/HeaderButton";
import { api, ApiError } from "../../lib/api";

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

type Draft = {
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

const emptyDraft: Draft = {
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

function draftFromSupplier(s: CentralSupplier): Draft {
  return {
    name: s.name,
    line_name: s.line_name ?? "",
    email: s.email ?? "",
    phone: s.phone ?? "",
    postal_code: s.postal_code ?? "",
    prefecture: s.prefecture ?? "",
    city: s.city ?? "",
    address1: s.address1 ?? "",
    address2: s.address2 ?? "",
    is_active: s.is_active,
  };
}

export function SupplierDetailDrawer({
  supplierId,
  onClose,
  onSaved,
  open: openProp,
  mode = "edit",
}: {
  supplierId: number | null;
  onClose: () => void;
  onSaved: () => void;
  open?: boolean;
  mode?: "edit" | "create";
}) {
  const { t } = useTranslation();
  const formId = useId();
  const routingFormRef = useRef<HTMLFormElement>(null);
  const [supplier, setSupplier] = useState<CentralSupplier | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [initial, setInitial] = useState<Draft | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const inFlight = useRef(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const [confirmation, setConfirmation] = useState<"close" | "reload" | null>(null);
  const [reload, setReload] = useState(0);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showRouting, setShowRouting] = useState(false);
  const [routings, setRoutings] = useState<DiscordRouting[]>([]);
  const [routingForm, setRoutingForm] = useState({ discord_guild_id: "", discord_channel_id: "" });

  const dirty = draft !== null && JSON.stringify(draft) !== JSON.stringify(initial);
  const isOpen = openProp !== undefined ? openProp : supplierId !== null;

  const f = "superAdmin.suppliersAdmin.fields";
  const s = "superAdmin.suppliersAdmin";

  // 編集モード: 詳細ロード
  useEffect(() => {
    if (mode !== "edit") return;
    let cancelled = false;
    setSupplier(null); setDraft(null); setInitial(null); setError(""); setSaved(false);
    setBlocked(false); setConfirmation(null); setShowRouting(false); setRoutings([]);
    if (!supplierId) { setLoading(false); return; }
    setLoading(true);
    void api.get<CentralSupplier>(`/super-admin/suppliers/${supplierId}`).then(result => {
      if (cancelled) return;
      const next = draftFromSupplier(result);
      setSupplier(result); setDraft(next); setInitial(next);
    }).catch(() => { if (!cancelled) setError(`${s}.loadError`); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [supplierId, reload, mode, s]);

  // 作成モード: 空フォーム初期化
  useEffect(() => {
    if (mode !== "create" || !isOpen) return;
    setError(""); setSaved(false); setBlocked(false); setConfirmation(null);
    setDraft(emptyDraft); setInitial(emptyDraft);
  }, [mode, isOpen]);

  useEffect(() => {
    if (!dirty) return;
    const guard = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", guard);
    return () => window.removeEventListener("beforeunload", guard);
  }, [dirty]);

  function requestClose() {
    if (inFlight.current || confirmation) return;
    if (dirty) setConfirmation("close");
    else onClose();
  }

  function change<K extends keyof Draft>(field: K, value: Draft[K]) {
    setDraft((previous: Draft | null) => previous ? { ...previous, [field]: value } : previous);
    setSaved(false);
  }

  async function save() {
    if (mode === "create") {
      await saveCreate();
    } else {
      await saveEdit();
    }
  }

  async function saveEdit() {
    if (!draft || !supplier || !supplierId || !dirty || blocked || inFlight.current) return;
    if (!draft.name.trim()) { setError(`${s}.nameRequired`); return; }
    inFlight.current = true; setSaving(true); setError(""); setSaved(false);
    try {
      const toNull = (v: string) => v || null;
      const result = await api.patch<CentralSupplier>(`/super-admin/suppliers/${supplierId}`, {
        name: draft.name,
        is_active: draft.is_active,
        line_name: toNull(draft.line_name),
        email: toNull(draft.email),
        phone: toNull(draft.phone),
        postal_code: toNull(draft.postal_code),
        prefecture: toNull(draft.prefecture),
        city: toNull(draft.city),
        address1: toNull(draft.address1),
        address2: toNull(draft.address2),
      });
      const next = draftFromSupplier(result);
      setSupplier(result); setDraft(next); setInitial(next); setSaved(true);
      onSaved();
    } catch (err) {
      const invalid = err instanceof ApiError && err.status === 422;
      setBlocked(!invalid);
      setError(`${s}.saveError`);
    } finally { inFlight.current = false; setSaving(false); }
  }

  async function saveCreate() {
    if (!draft || !dirty || blocked || inFlight.current) return;
    if (!draft.name.trim()) { setError(`${s}.nameRequired`); return; }
    inFlight.current = true; setSaving(true); setError(""); setSaved(false);
    try {
      const toNull = (v: string) => v || null;
      await api.post("/super-admin/suppliers", {
        name: draft.name,
        is_active: draft.is_active,
        line_name: toNull(draft.line_name),
        email: toNull(draft.email),
        phone: toNull(draft.phone),
        postal_code: toNull(draft.postal_code),
        prefecture: toNull(draft.prefecture),
        city: toNull(draft.city),
        address1: toNull(draft.address1),
        address2: toNull(draft.address2),
      });
      setSaved(true);
      onSaved();
      onClose();
    } catch (err) {
      const invalid = err instanceof ApiError && err.status === 422;
      setBlocked(!invalid);
      setError(`${s}.saveError`);
    } finally { inFlight.current = false; setSaving(false); }
  }

  const confirmDiscard = () => {
    const action = confirmation; setConfirmation(null);
    if (action === "reload") setReload((value: number) => value + 1);
    else onClose();
  };

  async function handleDelete() {
    if (!supplierId || deleting) return;
    setDeleting(true);
    try {
      await api.delete(`/super-admin/suppliers/${supplierId}`);
      onSaved();
      onClose();
    } catch (e: unknown) {
      setError(e instanceof ApiError ? `${s}.deleteError` : `${s}.deleteError`);
    } finally {
      setDeleting(false);
      setConfirmDelete(false);
    }
  }

  const loadRoutings = async () => {
    if (!supplierId) return;
    try {
      const data = await api.get<DiscordRouting[]>(`/super-admin/suppliers/${supplierId}/discord-routing`);
      setRoutings(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  };

  const openRouting = async () => {
    setShowRouting(true);
    await loadRoutings();
  };

  const addRouting = async (e: FormEvent) => {
    e.preventDefault();
    if (!supplierId) return;
    try {
      await api.post(`/super-admin/suppliers/${supplierId}/discord-routing`, {
        supplier_id: supplierId,
        discord_guild_id: routingForm.discord_guild_id,
        discord_channel_id: routingForm.discord_channel_id,
        is_active: true,
      });
      setRoutingForm({ discord_guild_id: "", discord_channel_id: "" });
      await loadRoutings();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    }
  };

  const deleteRouting = async (id: number) => {
    try {
      await api.delete(`/super-admin/suppliers/discord-routing/${id}`);
      await loadRoutings();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.deleteError"));
    }
  };

  return (
    <>
      <Drawer
        open={isOpen}
        onClose={requestClose}
        title={mode === "create" ? t("common.create") : t(`${s}.title`)}
        footer={
          draft && !confirmation ? (
            <div className="product-detail__actions">
              {mode === "edit" && (
                <Button
                  type="button"
                  variant="danger"
                  onClick={() => setConfirmDelete(true)}
                  disabled={deleting || saving}
                >
                  {t("common.delete")}
                </Button>
              )}
              <Button type="button" variant="secondary" onClick={requestClose} disabled={saving}>
                {t("common.close")}
              </Button>
              <Button type="submit" form={formId} disabled={saving || blocked || !dirty}>
                {t(saving ? `${s}.saving` : mode === "create" ? "common.create" : "common.save")}
              </Button>
            </div>
          ) : undefined
        }
      >
        {confirmation ? (
          <div className="product-detail__confirmation" role="alert">
            <p>{t(`${s}.discardMessage`)}</p>
            <div className="product-detail__actions">
              <Button type="button" variant="secondary" autoFocus onClick={() => setConfirmation(null)}>
                {t(`${s}.keepEditing`)}
              </Button>
              <Button type="button" variant="danger" onClick={confirmDiscard}>
                {t(`${s}.discard`)}
              </Button>
            </div>
          </div>
        ) : (
          <>
            {loading && <p role="status">{t("common.loading")}</p>}
            {error && <p role="alert">{t(error)}</p>}
            {mode === "edit" && !loading && (blocked || (!supplier && error)) && (
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  if (dirty) setConfirmation("reload");
                  else setReload(value => value + 1);
                }}
              >
                {t(`${s}.reload`)}
              </Button>
            )}
            {saved && <p role="status">{t(`${s}.saved`)}</p>}
            {draft && (mode === "create" || supplier) && (
              <form
                id={formId}
                className="product-detail__form"
                onSubmit={event => { event.preventDefault(); void save(); }}
              >
                <TextField
                  label={`${t(`${f}.name`)} *`}
                  value={draft.name}
                  onChange={e => change("name", e.target.value)}
                  required
                  disabled={saving}
                  fullWidth
                />
                <TextField
                  label={t(`${f}.lineName`)}
                  value={draft.line_name}
                  onChange={e => change("line_name", e.target.value)}
                  disabled={saving}
                  fullWidth
                />
                <TextField
                  label={t(`${f}.email`)}
                  type="email"
                  value={draft.email}
                  onChange={e => change("email", e.target.value)}
                  disabled={saving}
                  fullWidth
                />
                <TextField
                  label={t(`${f}.phone`)}
                  value={draft.phone}
                  onChange={e => change("phone", e.target.value)}
                  disabled={saving}
                  fullWidth
                />
                <TextField
                  label={t(`${f}.postalCode`)}
                  value={draft.postal_code}
                  onChange={e => change("postal_code", e.target.value)}
                  disabled={saving}
                  fullWidth
                />
                <TextField
                  label={t(`${f}.prefecture`)}
                  value={draft.prefecture}
                  onChange={e => change("prefecture", e.target.value)}
                  disabled={saving}
                  fullWidth
                />
                <TextField
                  label={t(`${f}.city`)}
                  value={draft.city}
                  onChange={e => change("city", e.target.value)}
                  disabled={saving}
                  fullWidth
                />
                <TextField
                  label={t(`${f}.address1`)}
                  value={draft.address1}
                  onChange={e => change("address1", e.target.value)}
                  disabled={saving}
                  fullWidth
                />
                <TextField
                  label={t(`${f}.address2`)}
                  value={draft.address2}
                  onChange={e => change("address2", e.target.value)}
                  disabled={saving}
                  fullWidth
                />
                {/* ui-allow: single boolean toggle (#3564) */}
                <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                  <input
                    type="checkbox"
                    checked={draft.is_active}
                    onChange={e => change("is_active", e.target.checked)}
                    disabled={saving}
                  />
                  {t(`${f}.isActive`)}
                </label>

                {mode === "edit" && supplierId !== null && (
                  <div style={{ marginTop: "var(--space-4)" }}>
                    <HeaderButton
                      variant="secondary"
                      data-testid="supplier-open-routing"
                      onClick={() => { void openRouting(); }}
                    >
                      {t(`${s}.discordRouting`)}
                    </HeaderButton>
                    {showRouting && (
                      <div style={{ marginTop: "var(--space-3)" }}>
                        {/* ui-allow: Discord routing table is a small inline form (#3564) */}
                        <form
                          ref={routingFormRef}
                          onSubmit={e => { void addRouting(e); }}
                          style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr) auto", gap: "var(--space-2)", marginBottom: "var(--space-2)" }}
                        >
                          <TextField
                            label={t(`${s}.guildId`)}
                            value={routingForm.discord_guild_id}
                            onChange={e => setRoutingForm({ ...routingForm, discord_guild_id: e.target.value })}
                            required
                          />
                          <TextField
                            label={t(`${s}.channelId`)}
                            value={routingForm.discord_channel_id}
                            onChange={e => setRoutingForm({ ...routingForm, discord_channel_id: e.target.value })}
                            required
                          />
                          <div style={{ display: "flex", alignItems: "flex-end" }}>
                            <HeaderButton variant="primary" onClick={() => routingFormRef.current?.requestSubmit()}>
                              {t(`${s}.addRouting`)}
                            </HeaderButton>
                          </div>
                        </form>
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th>{t(`${s}.guildId`)}</th>
                              <th>{t(`${s}.channelId`)}</th>
                              <th></th>
                            </tr>
                          </thead>
                          <tbody>
                            {routings.map(r => (
                              <tr key={r.id}>
                                <td><code>{r.discord_guild_id}</code></td>
                                <td><code>{r.discord_channel_id}</code></td>
                                <td style={{ textAlign: "right" }}>
                                  <HeaderButton variant="secondary" onClick={() => { void deleteRouting(r.id); }}>
                                    {t("common.delete")}
                                  </HeaderButton>
                                </td>
                              </tr>
                            ))}
                            {routings.length === 0 && (
                              <tr><td colSpan={3} className="empty">{t("common.noData")}</td></tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}
              </form>
            )}
          </>
        )}
      </Drawer>
      {mode === "edit" && (
        <ConfirmModal
          open={confirmDelete}
          title={t(`${s}.deleteTitle`)}
          message={t(`${s}.deleteConfirm`)}
          confirmLabel={t(`${s}.deleteAction`)}
          danger
          onConfirm={() => void handleDelete()}
          onCancel={() => setConfirmDelete(false)}
        />
      )}
    </>
  );
}
