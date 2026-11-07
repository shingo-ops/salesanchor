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
 *   tenant.profile.edit → 確認（設計図と今のサーバーの差）
 *   tenant.profile.edit → 反映
 *   tenant.profile.edit かつ channels.manage → Bot の招待
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../../lib/api";
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { usePermissions } from "../../hooks/usePermissions";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { Badge } from "../../components/Badge";
import ConfirmModal from "../../components/ConfirmModal";
import { DataTable } from "../../components/DataTable";
import { EmptyState } from "../../components/EmptyState";
import { LoadingBlock } from "../../components/loading";
import { getDiscordConnectErrorKey, getDiscordConnectErrorReason } from "../../features/discord-connect/discordConnectError";
import "./discord-config.css";

interface DiscordOwnConfig {
  guild_id: string | null;
  connected_at: string | null;
}

interface PlanRow {
  kind: string;
  key: string;
  name: string;
  field: string | null;
  before: string | null;
  after: string | null;
  reason?: string | null;
}

interface DeleteCandidate {
  kind: string;
  discord_id: string;
  name: string | null;
  parent_name: string | null;
  target: string | null;
}

interface AppRoleState {
  role_id: number;
  name: string;
  state: string;
  reason?: string | null;
}

interface OwnServerPlan {
  plan_digest: string;
  changes: PlanRow[];
  blocked: PlanRow[];
  delete_candidates: DeleteCandidate[];
  app_roles: AppRoleState[];
}

interface ApplyResultRow {
  kind: string;
  key: string;
  name: string;
  field: string | null;
  status: "success" | "blocked" | "failed";
  reason: string | null;
  discord_id: string | null;
  discord_status: number | null;
}

interface OwnServerApplyResult {
  run_id: number;
  success_count: number;
  blocked_count: number;
  failed_count: number;
  results: ApplyResultRow[];
}

const OWN_PATH = "/admin/discord-config/own";
const SNAPSHOT_PATH = "/admin/discord/own-server/snapshot";
const PLAN_PATH = "/admin/discord/own-server/plan";
const APPLY_PATH = "/admin/discord/own-server/apply";

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
  const [checking, setChecking] = useState(false);
  const [plan, setPlan] = useState<OwnServerPlan | null>(null);
  const [applyOpen, setApplyOpen] = useState(false);
  const [applying, setApplying] = useState(false);
  const [applyResult, setApplyResult] = useState<OwnServerApplyResult | null>(null);

  // 招待から戻ったときの結果を 1 回だけ読み、URL の残りを消す
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const status = params.get("discord_status");
    if (!status) return;
    if (status === "connected") {
      setNotice({ kind: "success", text: t("discordOwnServer.connectedSuccess") });
    } else if (status === "error") {
      setNotice({ kind: "danger", text: t(getDiscordConnectErrorKey(params.get("reason"))) });
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
    } catch (e) {
      setNotice({ kind: "danger", text: t(getDiscordConnectErrorKey(getDiscordConnectErrorReason(e))) });
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

  const handleCheck = async () => {
    setChecking(true);
    setNotice(null);
    setApplyResult(null);
    try {
      setPlan(await api.get<OwnServerPlan>(PLAN_PATH));
    } catch (err) {
      const noBlueprint = err instanceof ApiError && err.status === 404;
      setNotice({
        kind: "danger",
        text: noBlueprint ? t("discordOwnServer.planNoBlueprint") : t("discordOwnServer.planFailed"),
      });
    } finally {
      setChecking(false);
    }
  };

  const handleApply = async () => {
    if (!plan) return;
    setApplying(true);
    setNotice(null);
    try {
      const data = await api.post<OwnServerApplyResult>(APPLY_PATH, { plan_digest: plan.plan_digest });
      setApplyResult(data);
      setNotice({
        kind: "success",
        text: t("discordOwnServer.applyDone", {
          success: data.success_count,
          blocked: data.blocked_count,
          failed: data.failed_count,
        }),
      });
    } catch (err) {
      const conflict = err instanceof ApiError && err.status === 409;
      setNotice({
        kind: "danger",
        text: conflict ? t("discordOwnServer.applyConflict") : t("discordOwnServer.applyFailed"),
      });
    } finally {
      setApplyOpen(false);
      setApplying(false);
    }
  };

  const fieldLabel = (field: string | null) => {
    if (!field) return "";
    if (field.startsWith("overwrite:")) {
      return t("discordOwnServer.field.overwrite", { target: field.slice("overwrite:".length) });
    }
    return t(`discordOwnServer.field.${field}`);
  };

  const rowKeyOf = (row: Pick<PlanRow, "kind" | "key" | "field">) => `${row.kind}:${row.key}:${row.field ?? ""}`;
  const statusVariant = { success: "success", blocked: "warning", failed: "danger" } as const;
  const emptyRows = <EmptyState size="compact" title={t("discordOwnServer.emptyRows")} />;
  const planColumns = [
    { key: "kind", header: t("discordOwnServer.col.kind"), renderCell: (row: PlanRow) => t(`discordOwnServer.kind.${row.kind}`) },
    { key: "name", header: t("discordOwnServer.col.name") },
    { key: "field", header: t("discordOwnServer.col.field"), renderCell: (row: PlanRow) => fieldLabel(row.field) },
    { key: "before", header: t("discordOwnServer.col.before"), renderCell: (row: PlanRow) => row.before ?? "" },
    { key: "after", header: t("discordOwnServer.col.after"), renderCell: (row: PlanRow) => row.after ?? "" },
    {
      key: "reason",
      header: t("discordOwnServer.col.reason"),
      renderCell: (row: PlanRow) => (row.reason ? t(`discordOwnServer.reason.${row.reason}`) : ""),
    },
  ];
  const resultColumns = [
    { key: "kind", header: t("discordOwnServer.col.kind"), renderCell: (row: ApplyResultRow) => t(`discordOwnServer.kind.${row.kind}`) },
    { key: "name", header: t("discordOwnServer.col.name") },
    { key: "field", header: t("discordOwnServer.col.field"), renderCell: (row: ApplyResultRow) => fieldLabel(row.field) },
    {
      key: "status",
      header: t("discordOwnServer.col.status"),
      renderCell: (row: ApplyResultRow) => (
        <Badge variant={statusVariant[row.status]}>{t(`discordOwnServer.status.${row.status}`)}</Badge>
      ),
    },
    {
      key: "reason",
      header: t("discordOwnServer.col.reason"),
      renderCell: (row: ApplyResultRow) => (row.reason ? t(`discordOwnServer.reason.${row.reason}`) : ""),
    },
  ];
  const deleteColumns = [
    { key: "kind", header: t("discordOwnServer.col.kind"), renderCell: (row: DeleteCandidate) => t(`discordOwnServer.deleteKind.${row.kind}`) },
    { key: "name", header: t("discordOwnServer.col.name"), renderCell: (row: DeleteCandidate) => row.name ?? "" },
    { key: "parent_name", header: t("discordOwnServer.col.parent"), renderCell: (row: DeleteCandidate) => row.parent_name ?? "" },
    { key: "target", header: t("discordOwnServer.col.target"), renderCell: (row: DeleteCandidate) => row.target ?? "" },
  ];
  const appRoleColumns = [
    { key: "name", header: t("discordOwnServer.col.name") },
    {
      key: "state",
      header: t("discordOwnServer.col.appRoleState"),
      renderCell: (row: AppRoleState) => t(`discordOwnServer.appRoleState.${row.state}`),
    },
    {
      key: "reason",
      header: t("discordOwnServer.col.reason"),
      renderCell: (row: AppRoleState) => (row.reason ? t(`discordOwnServer.reason.${row.reason}`) : ""),
    },
  ];

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
          <Button variant="primary" onClick={() => void handleCheck()} loading={checking}>
            {t("discordOwnServer.check")}
          </Button>
        </div>
      )}
      {plan && (
        <div className="dc-result">
          <div className="dc-group">
            <h4 className="dc-group-title">{t("discordOwnServer.appRolesTitle", { count: plan.app_roles.length })}</h4>
            <DataTable<AppRoleState>
              columns={appRoleColumns}
              data={plan.app_roles}
              rowKey={(row) => `app_role:${row.role_id}`}
              emptyState={emptyRows}
            />
          </div>
          <div className="dc-group">
            <h4 className="dc-group-title">{t("discordOwnServer.changesTitle", { count: plan.changes.length })}</h4>
            <DataTable<PlanRow>
              columns={planColumns}
              data={plan.changes}
              rowKey={rowKeyOf}
              emptyState={emptyRows}
            />
          </div>
          <div className="dc-group">
            <h4 className="dc-group-title">{t("discordOwnServer.blockedTitle", { count: plan.blocked.length })}</h4>
            <DataTable<PlanRow>
              columns={planColumns}
              data={plan.blocked}
              rowKey={rowKeyOf}
              emptyState={emptyRows}
            />
          </div>
          <div className="dc-group">
            <h4 className="dc-group-title">{t("discordOwnServer.deleteTitle", { count: plan.delete_candidates.length })}</h4>
            <DataTable<DeleteCandidate>
              columns={deleteColumns}
              data={plan.delete_candidates}
              rowKey={(row) => `${row.kind}:${row.discord_id}:${row.target ?? ""}`}
              emptyState={emptyRows}
            />
            <p className="dc-hint">{t("discordOwnServer.deleteNote")}</p>
          </div>
          {canEdit && (
            <div className="dc-actions">
              <Button variant="primary" disabled={plan.changes.length === 0} onClick={() => setApplyOpen(true)}>
                {t("discordOwnServer.apply")}
              </Button>
            </div>
          )}
        </div>
      )}
      {applyResult && (
        <div className="dc-group">
          <h4 className="dc-group-title">
            {t("discordOwnServer.resultTitle", { count: applyResult.results.length })}
          </h4>
          <DataTable<ApplyResultRow>
            columns={resultColumns}
            data={applyResult.results}
            rowKey={rowKeyOf}
            emptyState={emptyRows}
          />
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
      <ConfirmModal
        open={applyOpen}
        title={t("discordOwnServer.applyConfirmTitle")}
        message={t("discordOwnServer.applyConfirmMessage", { count: plan?.changes.length ?? 0 })}
        confirmLabel={t("discordOwnServer.apply")}
        confirmLoading={applying}
        onConfirm={() => void handleApply()}
        onCancel={() => setApplyOpen(false)}
      />
    </Card>
  );
}
