/**
 * 自社用 Discord サーバーの登録（/admin/discord-config の「自社用」タブ）
 *
 * Bot を招待すると purpose=own で登録される（顧客用の登録とは別の行）。
 * 招待から戻ると URL の discord_status で結果を 1 回だけ表示する。
 *
 * 権限:
 *   tenant.profile.view → 閲覧
 *   tenant.profile.edit → 登録の解除
 *   tenant.profile.edit → 今のサーバーの読み取り
 *   tenant.profile.edit かつ channels.manage → Bot の招待
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { usePermissions } from "../../hooks/usePermissions";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { Badge } from "../../components/Badge";
import ConfirmModal from "../../components/ConfirmModal";
import { LoadingBlock } from "../../components/loading";
import "./discord-config.css";

interface DiscordOwnConfig {
  guild_id: string | null;
  connected_at: string | null;
}

const OWN_PATH = "/admin/discord-config/own";
const SNAPSHOT_PATH = "/admin/discord/own-server/snapshot";

type Notice = { kind: "success" | "danger"; text: string } | null;

export function DiscordOwnServerPanel() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const canEdit = hasPermission("tenant.profile.edit");
  const canInvite = canEdit && hasPermission("channels.manage");

  const ownQ = useApiQuery<DiscordOwnConfig>(OWN_PATH);
  const invalidate = useInvalidateApi();

  const [notice, setNotice] = useState<Notice>(null);
  const [inviting, setInviting] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [reading, setReading] = useState(false);

  // 招待から戻ったときの結果を 1 回だけ読み、URL の残りを消す
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const status = params.get("discord_status");
    if (!status) return;
    if (status === "connected") {
      setNotice({ kind: "success", text: t("discordOwnServer.connectedSuccess") });
    } else if (status === "error") {
      setNotice({
        kind: "danger",
        text:
          params.get("reason") === "guild_already_registered"
            ? t("discordOwnServer.guildAlreadyRegistered")
            : t("discordOwnServer.connectError"),
      });
    }
    window.history.replaceState({}, "", window.location.pathname + "?tab=own");
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 開いたとき 1 回だけ
  }, []);

  const refresh = () => invalidate(["admin", "discord-config", "own"]);

  const handleInvite = async () => {
    setInviting(true);
    setNotice(null);
    try {
      const data = await api.post<{ invite_url: string }>("/discord/oauth/start", {
        purpose: "own",
      });
      window.open(data.invite_url, "_blank", "noopener,noreferrer");
      window.addEventListener("focus", () => void refresh(), { once: true });
    } catch {
      setNotice({ kind: "danger", text: t("discordOwnServer.requestFailed") });
    } finally {
      setInviting(false);
    }
  };

  const handleRemove = async () => {
    setRemoving(true);
    try {
      await api.delete(OWN_PATH);
      await refresh();
      setConfirmOpen(false);
    } catch {
      setConfirmOpen(false);
      setNotice({ kind: "danger", text: t("discordOwnServer.requestFailed") });
    } finally {
      setRemoving(false);
    }
  };

  const handleSnapshot = async () => {
    setReading(true);
    setNotice(null);
    try {
      const data = await api.post<{ snapshot_id: number; role_count: number; channel_count: number }>(
        SNAPSHOT_PATH,
        {},
      );
      setNotice({
        kind: "success",
        text: t("discordOwnServer.snapshotDone", { roles: data.role_count, channels: data.channel_count }),
      });
    } catch {
      setNotice({ kind: "danger", text: t("discordOwnServer.snapshotFailed") });
    } finally {
      setReading(false);
    }
  };

  if (ownQ.isPending) return <LoadingBlock />;

  const guildId = ownQ.data?.guild_id ?? null;
  const isConnected = Boolean(guildId);

  return (
    <Card>
      <div className="dc-card-head">
        <h3 className="dc-card-title">{t("discordOwnServer.title")}</h3>
        <Badge variant={isConnected ? "success" : "neutral"} dot>
          {isConnected ? t("discordOwnServer.connected") : t("discordOwnServer.notConnected")}
        </Badge>
      </div>
      <p>{t("discordOwnServer.description")}</p>
      {ownQ.error && <Badge variant="danger">{t("discordOwnServer.loadError")}</Badge>}
      {notice && <Badge variant={notice.kind}>{notice.text}</Badge>}
      {!isConnected && canInvite && (
        <div className="dc-actions">
          <Button variant="primary" onClick={() => void handleInvite()} loading={inviting}>
            {t("discordOwnServer.invite")}
          </Button>
        </div>
      )}
      {isConnected && (
        <div className="dc-row">
          <span className="dc-server-id dc-grow">{guildId}</span>
          {canEdit && (
            <Button variant="secondary" size="sm" onClick={() => setConfirmOpen(true)}>
              {t("discordOwnServer.disconnect")}
            </Button>
          )}
        </div>
      )}
      {isConnected && canEdit && (
        <div className="dc-actions">
          <Button variant="secondary" onClick={() => void handleSnapshot()} loading={reading}>
            {t("discordOwnServer.snapshot")}
          </Button>
        </div>
      )}
      <ConfirmModal
        open={confirmOpen}
        title={t("discordOwnServer.confirmTitle")}
        message={t("discordOwnServer.confirmMessage")}
        danger
        confirmLoading={removing}
        onConfirm={() => void handleRemove()}
        onCancel={() => setConfirmOpen(false)}
      />
    </Card>
  );
}
