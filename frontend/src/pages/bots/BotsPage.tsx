/**
 * Bot 管理ページ。Phase 1 再設計版。
 *
 * bots テーブルの CRUD。API キーは作成/再発行時のみ平文表示。
 *
 * 変更履歴:
 *   2026-06-10: 編集を Drawer 化（useRecordDrawer, ADR-122 バッチA）
 */

import { useEffect, useState, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Modal } from "../../components/Modal";
import { Drawer } from "../../components/Drawer";
import { api } from "../../lib/api";
import ConfirmModal from "../../components/ConfirmModal";
import { usePermissions } from "../../hooks/usePermissions";
import { useRecordDrawer } from "../../hooks/useRecordDrawer";
import { STATUS_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import { PageLayout } from "../../components/PageLayout";
import { getStatusPresentation } from "../../utils/statusPresentation";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";
import { BotFormFields, type BotFormState, type BotStaff } from "./BotFormFields";

interface Bot {
  id: number;
  tenant_id: number;
  bot_code: string;
  display_name: string;
  purpose: string;
  status: string;
  discord_user_id: string | null;
  sender_email: string | null;
  owner_staff_id: number;
  owner_staff_name: string | null;
  last_executed_at: string | null;
  execution_count: number;
  created_at: string;
  updated_at: string;
}

interface BotCreated extends Bot {
  api_key: string;
}

type CreateFormState = {
  bot_code: string;
  display_name: string;
  purpose: string;
  status: string;
  discord_user_id: string;
  sender_email: string;
  owner_staff_id: string;
};

const emptyCreateForm: CreateFormState = {
  bot_code: "", display_name: "", purpose: "invoice", status: "active",
  discord_user_id: "", sender_email: "", owner_staff_id: "",
};

const emptyEditForm: BotFormState = {
  display_name: "", purpose: "invoice", status: "active",
  owner_staff_id: "", discord_user_id: "", sender_email: "",
};

const toForm = (b: Bot): BotFormState => ({
  display_name: b.display_name,
  purpose: b.purpose,
  status: b.status,
  owner_staff_id: String(b.owner_staff_id),
  discord_user_id: b.discord_user_id ?? "",
  sender_email: b.sender_email ?? "",
});

export default function BotsPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const navigate = useNavigate();
  const [bots, setBots] = useState<Bot[]>([]);
  const [staff, setStaff] = useState<BotStaff[]>([]);
  // 新規作成モーダル
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<CreateFormState>(emptyCreateForm);
  // 編集ドロワー
  const { drawerOpen, editId, editForm, setEditForm, handleRowClick, closeDrawer } =
    useRecordDrawer<Bot, BotFormState>({ toForm, emptyForm: emptyEditForm });

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Bot | null>(null);
  const [rotateTarget, setRotateTarget] = useState<Bot | null>(null);
  const [newApiKey, setNewApiKey] = useState<string | null>(null);

  const purposeLabel = (p: string) => (({ invoice: t("bots.purposeInvoice"), shipment: t("bots.purposeShipment"), notification: t("bots.purposeNotification"), custom: t("bots.purposeCustom") } as Record<string, string>)[p] ?? p);
  const statusLabel  = (s: string) => (({ active: t("bots.statusActive"), inactive: t("bots.statusInactive"), maintenance: t("bots.statusMaintenance") } as Record<string, string>)[s] ?? s);

  const loadAll = async () => {
    try {
      const [b, s] = await Promise.all([
        api.get<Bot[]>("/bots"),
        api.get<BotStaff[]>("/staff"),
      ]);
      setBots(b);
      setStaff(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadAll(); }, []);

  const toNull = (v: string) => (v ? v : null);

  /* ── 新規作成（Modal） ── */
  const handleCreateSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError("");
    const payload: Record<string, unknown> = {
      display_name: createForm.display_name,
      purpose: createForm.purpose,
      status: createForm.status,
      discord_user_id: toNull(createForm.discord_user_id),
      sender_email: toNull(createForm.sender_email),
      owner_staff_id: parseInt(createForm.owner_staff_id, 10),
    };
    if (createForm.bot_code.trim()) payload.bot_code = createForm.bot_code.trim();
    try {
      const created = await api.post<BotCreated>("/bots", payload);
      setNewApiKey(created.api_key);
      setShowCreate(false);
      setCreateForm(emptyCreateForm);
      loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    } finally {
      setSubmitting(false);
    }
  };

  /* ── ドロワー内編集保存 ── */
  const handleEditSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!editId) return;
    try {
      await api.patch<Bot>(`/bots/${editId}`, {
        display_name: editForm.display_name,
        purpose: editForm.purpose,
        status: editForm.status,
        owner_staff_id: parseInt(editForm.owner_staff_id, 10),
        discord_user_id: toNull(editForm.discord_user_id),
        sender_email: toNull(editForm.sender_email),
      });
      closeDrawer();
      loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    }
  };

  const performRotate = async () => {
    if (!rotateTarget) return;
    const b = rotateTarget;
    setRotateTarget(null);
    try {
      const res = await api.post<BotCreated>(`/bots/${b.id}/rotate-key`, {});
      setNewApiKey(res.api_key);
      loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.operationError"));
    }
  };

  const performDelete = async () => {
    if (!deleteTarget) return;
    const id = deleteTarget.id;
    setDeleteTarget(null);
    try {
      await api.delete(`/bots/${id}`);
      loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.deleteError"));
    }
  };

  return (
    <PageLayout
      navKey="nav.bots"
      subtitleKey="bots.subtitle"
      headerAction={hasPermission("bots.create") ? (
        <div className="page-header-actions">
          <button className="btn-primary" onClick={() => { setShowCreate(true); setCreateForm(emptyCreateForm); }}>
            {t("bots.newBot")}
          </button>
        </div>
      ) : undefined}
    >
      {error && <div className="error-message">{error}</div>}

      {newApiKey && (
        <div className="notice" style={{ padding: "var(--space-4)", background: "var(--warning-bg)", border: "1px solid var(--warning-text)", borderRadius: "var(--radius-sm)", margin: "16px 0" }}>
          <strong><STATUS_ICONS.warning size={ICON.sm} aria-hidden="true" /> {t("bots.apiKeyIssued")}</strong>
          <div className="mono" style={{ padding: "var(--space-2)", background: "var(--bg-surface)", marginTop: "var(--space-2)", wordBreak: "break-all" }}>{newApiKey}</div>
          <button className="btn-sm" onClick={() => setNewApiKey(null)} style={{ marginTop: "var(--space-2)" }}>{t("bots.apiKeyConfirm")}</button>
        </div>
      )}

      {/* 新規作成 Modal（APIキー発行フロー保持） */}
      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title={t("bots.newBot")}
        size="md"
      >
        <form onSubmit={handleCreateSubmit}>
          <div className="form-group">
            <label>{t("bots.botCodeLabel")}</label>
            <input value={createForm.bot_code} placeholder={t("bots.botCodePlaceholder")} onChange={(e) => setCreateForm({ ...createForm, bot_code: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("bots.displayName")} *</label>
            <input required value={createForm.display_name} onChange={(e) => setCreateForm({ ...createForm, display_name: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("bots.purposeLabel")} *</label>
            <select required value={createForm.purpose} onChange={(e) => setCreateForm({ ...createForm, purpose: e.target.value })}>
              <option value="invoice">{t("bots.purposeInvoice")}</option>
              <option value="shipment">{t("bots.purposeShipment")}</option>
              <option value="notification">{t("bots.purposeNotification")}</option>
              <option value="custom">{t("bots.purposeCustom")}</option>
            </select>
          </div>
          <div className="form-group"><label>{t("common.status")}</label>
            <select value={createForm.status} onChange={(e) => setCreateForm({ ...createForm, status: e.target.value })}>
              <option value="active">{t("bots.statusActive")}</option>
              <option value="inactive">{t("bots.statusInactive")}</option>
              <option value="maintenance">{t("bots.statusMaintenance")}</option>
            </select>
          </div>
          <div className="form-group"><label>{t("bots.ownerStaff")} *</label>
            <select required value={createForm.owner_staff_id} onChange={(e) => setCreateForm({ ...createForm, owner_staff_id: e.target.value })}>
              <option value="">{t("common.pleaseSelect")}</option>
              {staff.map((s) => <option key={s.id} value={s.id}>{s.surname_jp} {s.given_name_jp}</option>)}
            </select>
          </div>
          <div className="form-group"><label>Discord Bot ID</label>
            <input value={createForm.discord_user_id} onChange={(e) => setCreateForm({ ...createForm, discord_user_id: e.target.value })} />
          </div>
          <div className="form-group"><label>{t("bots.senderEmail")}</label>
            <input type="email" value={createForm.sender_email} onChange={(e) => setCreateForm({ ...createForm, sender_email: e.target.value })} />
          </div>
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={() => setShowCreate(false)} disabled={submitting}>{t("common.cancel")}</button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? t("common.submitting") : t("bots.registerIssueKey")}
            </button>
          </div>
        </form>
      </Modal>

      {/* 編集 Drawer（行クリックで開く・useRecordDrawer フック） */}
      <Drawer
        open={drawerOpen}
        onClose={closeDrawer}
        title={t("bots.editBot")}
        onOpenFullPage={editId ? () => { closeDrawer(); navigate(`/bots/${editId}/edit`); } : undefined}
      >
        <form onSubmit={handleEditSubmit}>
          <BotFormFields
            form={editForm}
            onChange={(field, value) => setEditForm((prev) => ({ ...prev, [field]: value }))}
            staff={staff}
          />
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={closeDrawer}>{t("common.cancel")}</button>
            <button type="submit" className="btn-primary">{t("common.update")}</button>
          </div>
        </form>
      </Drawer>

      {loading ? (
        <div className="loading">{t("common.loading")}</div>
      ) : (() => {
        const columns: DataTableColumn<Bot>[] = [
          { key: "display_name", header: t("common.name") },
          { key: "purpose", header: t("bots.purposeLabel"), renderCell: (b) => purposeLabel(b.purpose) },
          {
            key: "status",
            header: t("common.status"),
            renderCell: (b) => (
              <span className={`badge badge-${getStatusPresentation("bot", b.status).badgeVariant}`}>
                {statusLabel(b.status)}
              </span>
            ),
          },
          { key: "owner_staff_name", header: t("bots.ownerStaff"), renderCell: (b) => b.owner_staff_name || "-" },
          { key: "execution_count", header: t("bots.executionCount"), renderCell: (b) => b.execution_count.toLocaleString("ja-JP") },
          { key: "last_executed_at", header: t("bots.lastExecuted"), renderCell: (b) => b.last_executed_at ? new Date(b.last_executed_at).toLocaleDateString("ja-JP") : "-" },
          {
            key: "actions",
            header: t("common.actions"),
            renderCell: (b) => (
              <span className="actions">
                {hasPermission("bots.update") && <button className="btn-sm" onClick={(e) => { e.stopPropagation(); handleRowClick(b); }}>{t("common.edit")}</button>}
                {hasPermission("bots.update") && <button className="btn-sm" onClick={(e) => { e.stopPropagation(); setRotateTarget(b); }}>{t("bots.rotateKey")}</button>}
                {hasPermission("bots.delete") && <button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(b); }}>{t("common.delete")}</button>}
              </span>
            ),
          },
        ];
        return (
          <DataTable
            columns={columns}
            data={bots}
            rowKey={(b) => String(b.id)}
            onRowClick={hasPermission("bots.update") ? handleRowClick : undefined}
            emptyState={<span>{t("bots.noB")}</span>}
          />
        );
      })()}

      <ConfirmModal
        open={!!deleteTarget}
        title={t("bots.deleteBot")}
        message={<><strong>{deleteTarget?.display_name}</strong>{t("common.deleteConfirmSuffix")}<br />{t("common.irreversible")}</>}
        confirmLabel={t("common.delete")}
        danger
        onConfirm={performDelete}
        onCancel={() => setDeleteTarget(null)}
      />
      <ConfirmModal
        open={!!rotateTarget}
        title={t("bots.rotateKeyTitle")}
        message={
          <>
            <strong>{rotateTarget?.display_name}</strong>{t("bots.rotateKeyDescSuffix")}<br />
            <strong>{t("bots.rotateKeyWarn1")}</strong><br />
            {t("bots.rotateKeyWarn2")}
          </>
        }
        confirmLabel={t("bots.rotateKeyConfirm")}
        danger
        onConfirm={performRotate}
        onCancel={() => setRotateTarget(null)}
      />
    </PageLayout>
  );
}
