/**
 * ChannelMastersPage — テナント管理者用 手動チャネル管理
 *
 * 手動記録（SA-02 Stage 3）で使用するチャネルを追加・削除できる。
 * 自動連携チャネル（connection_type='auto'）は表示のみ（削除不可）。
 *
 * ルート: /admin/channel-masters
 * 権限: tenant.profile.edit（既存 admin 権限を流用）
 */
import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { PageLayout } from "../../components/PageLayout";

interface ChannelMaster {
  id: number;
  platform: string;
  display_name: string;
  connection_type: "auto" | "manual";
  is_active: boolean;
}

export default function ChannelMastersPage() {
  const { t } = useTranslation();
  const [channels, setChannels] = useState<ChannelMaster[]>([]);
  const [loading, setLoading] = useState(true);
  const [newPlatform, setNewPlatform] = useState("");
  const [newDisplayName, setNewDisplayName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    api
      .get<ChannelMaster[]>("/api/v1/channel-masters")
      .then((res) => {
        const all: ChannelMaster[] = Array.isArray(res) ? res : (res as { data?: ChannelMaster[] }).data ?? [];
        setChannels(all);
      })
      .catch(() => setError(t("channelMasters.loadError")))
      .finally(() => setLoading(false));
  }, [t]);

  useEffect(() => { load(); }, [load]);

  const handleAdd = useCallback(async () => {
    const platform = newPlatform.trim();
    const displayName = newDisplayName.trim();
    if (!platform || !displayName) return;
    setSaving(true);
    setError(null);
    try {
      await api.post("/api/v1/admin/channel-masters", { platform, display_name: displayName });
      setNewPlatform("");
      setNewDisplayName("");
      load();
    } catch {
      setError(t("channelMasters.saveError"));
    } finally {
      setSaving(false);
    }
  }, [newPlatform, newDisplayName, load, t]);

  const handleDelete = useCallback(async (id: number) => {
    setError(null);
    try {
      await api.delete(`/api/v1/admin/channel-masters/${id}`);
      load();
    } catch {
      setError(t("channelMasters.deleteError"));
    }
  }, [load, t]);

  return (
    <PageLayout navKey="nav.channelMasters">
      {loading ? (
        <p>{t("channelMasters.loading")}</p>
      ) : (
        <>
          <table className="channel-masters-table">
            <thead>
              <tr>
                <th>{t("channelMasters.platform")}</th>
                <th>{t("channelMasters.displayName")}</th>
                <th>{t("channelMasters.type")}</th>
                <th>{t("channelMasters.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {channels.map((ch) => (
                <tr key={ch.id}>
                  <td>{ch.platform}</td>
                  <td>{ch.display_name}</td>
                  <td>{ch.connection_type === "auto" ? t("channelMasters.typeAuto") : t("channelMasters.typeManual")}</td>
                  <td>
                    {ch.connection_type === "manual" && (
                      <button
                        type="button"
                        onClick={() => handleDelete(ch.id)}
                        aria-label={t("channelMasters.deleteAriaLabel", { name: ch.display_name })}
                      >
                        {t("channelMasters.delete")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {error && <p role="alert" className="channel-masters-error">{error}</p>}

          <div className="channel-masters-add-form">
            <h3>{t("channelMasters.addTitle")}</h3>
            <input
              type="text"
              value={newPlatform}
              onChange={(e) => setNewPlatform(e.target.value)}
              placeholder={t("channelMasters.platformPlaceholder")}
              aria-label={t("channelMasters.platform")}
              disabled={saving}
            />
            <input
              type="text"
              value={newDisplayName}
              onChange={(e) => setNewDisplayName(e.target.value)}
              placeholder={t("channelMasters.displayNamePlaceholder")}
              aria-label={t("channelMasters.displayName")}
              disabled={saving}
            />
            <button
              type="button"
              onClick={handleAdd}
              disabled={saving || !newPlatform.trim() || !newDisplayName.trim()}
              aria-label={t("channelMasters.add")}
            >
              {saving ? t("channelMasters.saving") : t("channelMasters.add")}
            </button>
          </div>
        </>
      )}
    </PageLayout>
  );
}
