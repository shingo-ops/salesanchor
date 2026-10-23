import { useEffect, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { PageLayout } from "../../components/PageLayout";
import { ContentToolbar } from "../../components/ContentToolbar";
import { usePermissions } from "../../hooks/usePermissions";
import { Modal } from "../../components/Modal";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";
import { Button } from "../../components/Button";
import { TextFieldControl } from "../../components/TextField";
import { Checkbox } from "../../components/Checkbox";
import { SCHEDULE_POPOVER_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import { NOTIFICATION_EVENT_LABEL_KEYS } from "../../constants/notificationEventTypes";
import { LoadingBlock } from "../../components/loading";

interface Channel { id: number; channel_name: string; webhook_url: string; event_types: string; is_active: boolean; created_at: string; }
interface EventTypeOption { code: string; }
interface ChannelFormState { channel_name: string; webhook_url: string; event_types: string[]; }

const EMPTY_FORM: ChannelFormState = { channel_name: "", webhook_url: "", event_types: [] };

function parseEventTypes(raw: string): string[] {
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function toggleEventType(current: string[], code: string): string[] {
  return current.includes(code) ? current.filter((c) => c !== code) : [...current, code];
}

export default function NotificationsPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const [channels, setChannels] = useState<Channel[]>([]);
  const [eventTypes, setEventTypes] = useState<EventTypeOption[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<ChannelFormState>(EMPTY_FORM);
  const [editingChannel, setEditingChannel] = useState<Channel | null>(null);
  const [editForm, setEditForm] = useState<ChannelFormState>(EMPTY_FORM);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const eventTypeLabel = (code: string) => {
    const key = NOTIFICATION_EVENT_LABEL_KEYS[code];
    return key ? t(key) : code;
  };

  const load = async () => {
    try {
      const [channelsResult, eventTypesResult] = await Promise.all([
        api.get<Channel[]>("/notification-channels"),
        api.get<EventTypeOption[]>("/notification-event-types"),
      ]);
      setChannels(channelsResult);
      setEventTypes(eventTypesResult);
    }
    catch (e) { setError(e instanceof Error ? e.message : t("common.fetchError")); }
    finally { setLoading(false); }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault(); setError("");
    try {
      await api.post("/notification-channels", {
        channel_name: form.channel_name,
        webhook_url: form.webhook_url,
        event_types: form.event_types,
      });
      setShowForm(false); setForm(EMPTY_FORM); load();
    } catch (e) { setError(e instanceof Error ? e.message : t("common.saveError")); }
  };

  const openEdit = (ch: Channel) => {
    setEditingChannel(ch);
    setEditForm({
      channel_name: ch.channel_name,
      webhook_url: ch.webhook_url,
      event_types: parseEventTypes(ch.event_types),
    });
  };

  const handleEditSubmit = async (e: FormEvent) => {
    e.preventDefault(); setError("");
    if (!editingChannel) return;
    try {
      await api.patch(`/notification-channels/${editingChannel.id}`, {
        channel_name: editForm.channel_name,
        webhook_url: editForm.webhook_url,
        event_types: editForm.event_types,
      });
      setEditingChannel(null); load();
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
    >
      {error && <div className="error-message">{error}</div>}
      {hasPermission("notifications.manage") ? (
        <ContentToolbar
          right={<Button variant="primary" size="md" onClick={() => setShowForm(true)}>{t("settings.addChannel")}</Button>}
        />
      ) : undefined}
      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title={t("settings.addDiscordWebhook")}
        size="md"
      >
        <form onSubmit={handleSubmit}>
          {/* eslint-disable-next-line local/no-japanese-literal -- TODO: placeholder を翻訳キーに統合（ADR-027 既知負債） */}
          <div className="form-group"><label>{t("settings.channelName")} *</label><TextFieldControl required value={form.channel_name} onChange={e => setForm({ ...form, channel_name: e.target.value })} placeholder="例: #crm-activity" /></div>
          <div className="form-group"><label>Webhook URL *</label><TextFieldControl required value={form.webhook_url} onChange={e => setForm({ ...form, webhook_url: e.target.value })} placeholder="https://discord.com/api/webhooks/..." /></div>
          <div className="form-group">
            <label>{t("notifications.eventTypesLabel")}</label>
            {eventTypes.map((et) => (
              <div key={et.code}>
                <Checkbox
                  label={eventTypeLabel(et.code)}
                  checked={form.event_types.includes(et.code)}
                  onChange={() => setForm({ ...form, event_types: toggleEventType(form.event_types, et.code) })}
                />
              </div>
            ))}
          </div>
          <div className="form-actions">
            <Button type="button" variant="secondary" size="md" onClick={() => setShowForm(false)}>{t("common.cancel")}</Button>
            <Button type="submit" variant="primary" size="md">{t("common.add")}</Button>
          </div>
        </form>
      </Modal>
      <Modal
        open={editingChannel != null}
        onClose={() => setEditingChannel(null)}
        title={t("notifications.editChannel")}
        size="md"
      >
        <form onSubmit={handleEditSubmit}>
          <div className="form-group"><label>{t("settings.channelName")} *</label><TextFieldControl required value={editForm.channel_name} onChange={e => setEditForm({ ...editForm, channel_name: e.target.value })} /></div>
          <div className="form-group"><label>Webhook URL *</label><TextFieldControl required value={editForm.webhook_url} onChange={e => setEditForm({ ...editForm, webhook_url: e.target.value })} /></div>
          <div className="form-group">
            <label>{t("notifications.eventTypesLabel")}</label>
            {eventTypes.map((et) => (
              <div key={et.code}>
                <Checkbox
                  label={eventTypeLabel(et.code)}
                  checked={editForm.event_types.includes(et.code)}
                  onChange={() => setEditForm({ ...editForm, event_types: toggleEventType(editForm.event_types, et.code) })}
                />
              </div>
            ))}
          </div>
          <div className="form-actions">
            <Button type="button" variant="secondary" size="md" onClick={() => setEditingChannel(null)}>{t("common.cancel")}</Button>
            <Button type="submit" variant="primary" size="md">{t("common.save")}</Button>
          </div>
        </form>
      </Modal>
      {loading ? <LoadingBlock /> : (() => {
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
            key: "event_types",
            header: t("notifications.eventTypesColumn"),
            renderCell: (ch) => {
              const codes = parseEventTypes(ch.event_types);
              return codes.length > 0
                ? <>{codes.map(eventTypeLabel).join("、")}</>
                : <span className="text-muted">{t("notifications.eventTypesEmpty")}</span>;
            },
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
                  <>
                    <Button variant="ghost" size="sm" iconOnly aria-label={t("notifications.editChannel")} onClick={() => openEdit(ch)}>
                      <SCHEDULE_POPOVER_ICONS.edit size={ICON.sm} aria-hidden="true" />
                    </Button>
                    <Button variant="danger" size="sm" onClick={() => handleDelete(ch.id)}>{t("common.delete")}</Button>
                  </>
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
