/**
 * ChannelMastersPage — テナント管理者用 手動チャネル管理
 *
 * 手動記録（SA-02 Stage 3）で使用するチャネルを追加・削除できる。
 * 自動連携チャネル（connection_type='auto'）は表示のみ（削除不可）。
 *
 * ルート: /admin/channel-masters
 * 権限: tenant.profile.edit（既存 admin 権限を流用）
 */
import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { TextFieldControl } from "../../components/TextField";
import { LoadingBlock, Spinner } from "../../components/loading";

interface ChannelMaster {
  id: number;
  platform: string;
  display_name: string;
  connection_type: "auto" | "manual";
  is_active: boolean;
}

/** 応答は配列か { data: 配列 } のどちらか（今までの読み方のまま） */
type ChannelMastersResponse = ChannelMaster[] | { data?: ChannelMaster[] };

/** 書いた後に取り直す写しの頭（ADR-1054） */
const CHANNEL_MASTERS_HEAD = ["channel-masters"] as const;

export default function ChannelMastersPage() {
  const { t } = useTranslation();
  // 写しを先に出して裏で取り直す（ADR-1054 段 2）
  const channelsQuery = useApiQuery<ChannelMastersResponse>("/channel-masters");
  const invalidate = useInvalidateApi();
  const channels: ChannelMaster[] = Array.isArray(channelsQuery.data)
    ? channelsQuery.data
    : channelsQuery.data?.data ?? [];
  const [newPlatform, setNewPlatform] = useState("");
  const [newDisplayName, setNewDisplayName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const shownError = error ?? (channelsQuery.isError ? t("channelMasters.loadError") : null);

  const handleAdd = useCallback(async () => {
    const platform = newPlatform.trim();
    const displayName = newDisplayName.trim();
    if (!platform || !displayName) return;
    setSaving(true);
    setError(null);
    try {
      await api.post("/admin/channel-masters", { platform, display_name: displayName });
      setNewPlatform("");
      setNewDisplayName("");
      void invalidate(CHANNEL_MASTERS_HEAD);
    } catch {
      setError(t("channelMasters.saveError"));
    } finally {
      setSaving(false);
    }
  }, [newPlatform, newDisplayName, invalidate, t]);

  const handleDelete = useCallback(async (id: number) => {
    setError(null);
    try {
      await api.delete(`/admin/channel-masters/${id}`);
      void invalidate(CHANNEL_MASTERS_HEAD);
    } catch {
      setError(t("channelMasters.deleteError"));
    }
  }, [invalidate, t]);

  return (
    <PageLayout
      navKey="nav.channelMasters"
      headerLeft={channelsQuery.isFetching && !channelsQuery.isPending ? <Spinner size="sm" /> : undefined}
    >
      {channelsQuery.isPending ? (
        <LoadingBlock />
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

          {shownError && <p role="alert" className="channel-masters-error">{shownError}</p>}

          <div className="channel-masters-add-form">
            <h3>{t("channelMasters.addTitle")}</h3>
            <TextFieldControl
              type="text"
              value={newPlatform}
              onChange={(e) => setNewPlatform(e.target.value)}
              placeholder={t("channelMasters.platformPlaceholder")}
              aria-label={t("channelMasters.platform")}
              disabled={saving}
              style={{ width: "auto" }}
            />
            <TextFieldControl
              type="text"
              value={newDisplayName}
              onChange={(e) => setNewDisplayName(e.target.value)}
              placeholder={t("channelMasters.displayNamePlaceholder")}
              aria-label={t("channelMasters.displayName")}
              disabled={saving}
              style={{ width: "auto" }}
            />
            <Button
              type="button"
              variant="primary"
              size="md"
              loading={saving}
              onClick={handleAdd}
              disabled={saving || !newPlatform.trim() || !newDisplayName.trim()}
              aria-label={t("channelMasters.add")}
            >
              {t("channelMasters.add")}
            </Button>
          </div>
        </>
      )}
    </PageLayout>
  );
}
