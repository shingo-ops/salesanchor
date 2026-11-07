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
import { api, ApiError } from "../../lib/api";
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { Badge } from "../../components/Badge";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";
import { Toggle } from "../../components/Toggle";
import { TextFieldControl } from "../../components/TextField";
import { LoadingBlock, Spinner } from "../../components/loading";

interface ChannelMaster {
  id: number;
  platform: string;
  display_name: string;
  connection_type: "auto" | "manual";
  is_active: boolean;
  is_shared: boolean;
  is_hidden: boolean;
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
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 409
          ? t("channelMasters.duplicateError")
          : t("channelMasters.saveError"),
      );
    } finally {
      setSaving(false);
    }
  }, [newPlatform, newDisplayName, invalidate, t]);

  const handleVisibility = useCallback(async (id: number, isHidden: boolean) => {
    setError(null);
    try {
      await api.put(`/admin/channel-masters/${id}/visibility`, { is_hidden: isHidden });
      void invalidate(CHANNEL_MASTERS_HEAD);
    } catch {
      setError(t("channelMasters.visibilityError"));
    }
  }, [invalidate, t]);

  const handleDelete = useCallback(async (id: number) => {
    setError(null);
    try {
      await api.delete(`/admin/channel-masters/${id}`);
      void invalidate(CHANNEL_MASTERS_HEAD);
    } catch {
      setError(t("channelMasters.deleteError"));
    }
  }, [invalidate, t]);

  const columns: DataTableColumn<ChannelMaster>[] = [
    { key: "platform", header: t("channelMasters.platform") },
    { key: "displayName", header: t("channelMasters.displayName"), renderCell: (ch) => ch.display_name },
    {
      key: "type",
      header: t("channelMasters.type"),
      renderCell: (ch) => (
        <>
          {ch.connection_type === "auto" ? t("channelMasters.typeAuto") : t("channelMasters.typeManual")}
          {ch.is_shared && (
            <>
              {" "}
              <Badge variant="neutral" size="sm">{t("channelMasters.shared")}</Badge>
            </>
          )}
        </>
      ),
    },
    {
      key: "visible",
      header: t("channelMasters.visible"),
      renderCell: (ch) =>
        ch.connection_type === "manual" ? (
          <Toggle
            checked={!ch.is_hidden}
            onCheckedChange={(v) => void handleVisibility(ch.id, !v)}
            aria-label={t("channelMasters.visibleAriaLabel", { name: ch.display_name })}
          />
        ) : null,
    },
    {
      key: "actions",
      header: t("channelMasters.actions"),
      renderCell: (ch) =>
        ch.connection_type === "manual" && !ch.is_shared ? (
          <Button
            type="button"
            variant="danger"
            size="sm"
            onClick={() => handleDelete(ch.id)}
            aria-label={t("channelMasters.deleteAriaLabel", { name: ch.display_name })}
          >
            {t("channelMasters.delete")}
          </Button>
        ) : null,
    },
  ];

  return (
    <PageLayout
      navKey="nav.channelMasters"
      headerLeft={channelsQuery.isFetching && !channelsQuery.isPending ? <Spinner size="sm" /> : undefined}
    >
      {channelsQuery.isPending ? (
        <LoadingBlock />
      ) : (
        <>
          <p className="text-xs text-token-text-secondary">{t("channelMasters.visibleHelp")}</p>
          <DataTable columns={columns} data={channels} rowKey={(ch) => String(ch.id)} />

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
