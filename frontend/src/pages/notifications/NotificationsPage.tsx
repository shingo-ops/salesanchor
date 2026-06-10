import { useEffect, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { PageLayout } from "../../components/PageLayout";
import { usePermissions } from "../../hooks/usePermissions";
import { Modal } from "../../components/Modal";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";

interface Channel { id: number; channel_name: string; webhook_url: string; event_types: string; is_active: boolean; created_at: string; }

export default function NotificationsPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const [channels, setChannels] = useState<Channel[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ channel_name: "", webhook_url: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try { setChannels(await api.get<Channel[]>("/notification-channels")); }
    catch (e) { setError(e instanceof Error ? e.message : t("common.fetchError")); }
    finally { setLoading(false); }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault(); setError("");
    try {
      await api.post("/notification-channels", { channel_name: form.channel_name, webhook_url: form.webhook_url });
      setShowForm(false); setForm({ channel_name: "", webhook_url: "" }); load();
    } catch (e) { setError(e instanceof Error ? e.message : t("common.saveError")); }
  };

  const handleDelete = async (id: number) => {
    try { await api.delete(`/notification-channels/${id}`); load(); }
    catch (e) { setError(e instanceof Error ? e.message : t("common.deleteError")); }
  };

  return (
    <PageLayout
      navKey="nav.notifications"
      subtitleKey="settings.subtitle"
      headerAction={
        hasPermission("notifications.manage") ? (
          <div className="page-header-actions">
            <button className="btn-primary" onClick={() => setShowForm(true)}>{t("settings.addChannel")}</button>
          </div>
        ) : undefined
      }
    >
      {error && <div className="error-message">{error}</div>}
      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title={t("settings.addDiscordWebhook")}
        size="md"
      >
        <form onSubmit={handleSubmit}>
          {/* eslint-disable-next-line local/no-japanese-literal -- TODO: placeholder を翻訳キーに統合（ADR-027 既知負債） */}
          <div className="form-group"><label>{t("settings.channelName")} *</label><input required value={form.channel_name} onChange={e => setForm({ ...form, channel_name: e.target.value })} placeholder="例: #crm-activity" /></div>
          <div className="form-group"><label>Webhook URL *</label><input required value={form.webhook_url} onChange={e => setForm({ ...form, webhook_url: e.target.value })} placeholder="https://discord.com/api/webhooks/..." /></div>
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>{t("common.cancel")}</button>
            <button type="submit" className="btn-primary">{t("common.add")}</button>
          </div>
        </form>
      </Modal>
      {loading ? <div className="loading">{t("common.loading")}</div> : (() => {
        const columns: DataTableColumn<Channel>[] = [
          {
            key: "channel_name",
            header: t("settings.channelName"),
            renderCell: (ch) => <>{ch.channel_name}</>,
          },
          {
            key: "webhook_url",
            header: "Webhook URL",
            renderCell: (ch) => (
              <span className="mono" style={{ maxWidth: 'var(--col-width-url)', overflow: 'hidden', textOverflow: 'ellipsis' }}>{ch.webhook_url}</span>
            ),
          },
          {
            key: "status",
            header: t("common.status"),
            renderCell: (ch) => (
              /* status-ssot-exempt: is_active boolean (status ドメインではなく boolean flag) */
              <span className={`badge badge-${ch.is_active ? "won" : "lost"}`}>{ch.is_active ? t("common.active") : t("common.inactive")}</span>
            ),
          },
          {
            key: "actions",
            header: t("common.actions"),
            renderCell: (ch) => (
              <span className="actions">
                {hasPermission("notifications.manage") && (
                  <button className="btn-sm btn-danger" onClick={() => handleDelete(ch.id)}>{t("common.delete")}</button>
                )}
              </span>
            ),
          },
        ];
        return (
          <DataTable<Channel>
            columns={columns}
            data={channels}
            rowKey={(ch) => String(ch.id)}
            emptyState={<span>{t("settings.noChannels")}</span>}
          />
        );
      })()}
    </PageLayout>
  );
}
