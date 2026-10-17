/**
 * /super-admin/viewers — 閲覧者（社外の在庫閲覧専用アカウント）の管理画面（ADR-1019 段4a-2）。
 *
 * - 一覧・状態変更（本契約・延長・停止・停止の解除）・ログイン記録
 * - is_super_admin=true のみアクセス可（Page 内で 403 ガード）
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { ButtonLink } from "../../components/ButtonLink";
import { Badge, type BadgeVariant } from "../../components/Badge";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { EmptyState } from "../../components/EmptyState";
import { Modal } from "../../components/Modal";
import { Drawer } from "../../components/Drawer";
import { TextField } from "../../components/TextField";

interface ViewerItem {
  id: number;
  email: string;
  line_name: string;
  inventory_issue: string | null;
  status: string;
  trial_expires_at: string | null;
  created_at: string;
  discord_user_id: string | null;
  discord_channel_id: string | null;
  discord_channel_url: string | null;
  flag_many_ips: boolean;
  flag_shared_ip: boolean;
}

interface LoginItem {
  created_at: string;
  event_type: string;
  client_ip: string | null;
  user_agent: string | null;
}

type Action = "activate" | "suspend" | "unsuspend" | "extend";

const STATUS_VARIANT: Record<string, BadgeVariant> = {
  active: "success",
  trial: "info",
  suspended: "danger",
  pending: "neutral",
  verified: "neutral",
};

const STATUS_KEY: Record<string, string> = {
  pending: "statusPending",
  verified: "statusVerified",
  trial: "statusTrial",
  active: "statusActive",
  suspended: "statusSuspended",
};

const EVENT_KEY: Record<string, string> = {
  login_succeeded: "eventLoginSucceeded",
  login_failed: "eventLoginFailed",
  password_changed: "eventPasswordChanged",
  password_reset_requested: "eventPasswordResetRequested",
  password_reset_done: "eventPasswordResetDone",
  signup: "eventSignup",
  code_matched: "eventCodeMatched",
};

function formatDate(value: string | null): string | null {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

export default function ViewerAccountsPage() {
  const { t } = useTranslation();
  const { isSuperAdmin, loading: authLoading } = useSuperAdmin();
  const f = "superAdmin.viewers";
  const [items, setItems] = useState<ViewerItem[]>([]);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState<{ viewer: ViewerItem; action: Action } | null>(null);
  const [daysText, setDaysText] = useState("7");
  const [running, setRunning] = useState(false);
  const [loginsFor, setLoginsFor] = useState<ViewerItem | null>(null);
  const [logins, setLogins] = useState<LoginItem[]>([]);

  const load = useCallback(async () => {
    setFetching(true);
    try {
      const data = await api.get<{ items: ViewerItem[] }>("/super-admin/viewers");
      setItems(data.items);
    } catch {
      setError(t(`${f}.loadError`));
    } finally {
      setFetching(false);
    }
  }, [t]);

  useEffect(() => {
    if (!authLoading && isSuperAdmin) {
      void load();
    }
  }, [authLoading, isSuperAdmin, load]);

  const errorMessage = (e: unknown): string => {
    if (e instanceof ApiError) {
      if (e.status === 409) return t(`${f}.conflictError`);
      if (e.status === 404) return t(`${f}.notFoundError`);
    }
    return t(`${f}.genericError`);
  };

  const openAction = (viewer: ViewerItem, action: Action) => {
    setError("");
    setDaysText("7");
    setPending({ viewer, action });
  };

  const days = Number(daysText);
  const daysValid = daysText.trim() !== "" && Number.isInteger(days) && days >= 1 && days <= 365;

  const run = async () => {
    if (!pending) return;
    if (pending.action === "extend" && !daysValid) return;
    setRunning(true);
    setError("");
    try {
      const path = `/super-admin/viewers/${pending.viewer.id}/${pending.action}`;
      if (pending.action === "extend") {
        await api.post(path, { days });
      } else {
        await api.post(path, {});
      }
      setPending(null);
      await load();
    } catch (e) {
      setPending(null);
      setError(errorMessage(e));
    } finally {
      setRunning(false);
    }
  };

  const openLogins = async (viewer: ViewerItem) => {
    setError("");
    setLoginsFor(viewer);
    setLogins([]);
    try {
      const data = await api.get<{ items: LoginItem[] }>(`/super-admin/viewers/${viewer.id}/logins`);
      setLogins(data.items);
    } catch (e) {
      setLoginsFor(null);
      setError(errorMessage(e));
    }
  };

  if (authLoading) {
    return <div className="page">{t("common.loading")}</div>;
  }

  if (!isSuperAdmin) {
    return (
      <PageLayout navKey="nav.superAdminViewers">
        <div className="error-message" role="alert">
          {t("superAdmin.accessDenied")}
        </div>
      </PageLayout>
    );
  }

  const columns: DataTableColumn<ViewerItem>[] = [
    { key: "email", header: t(`${f}.colEmail`) },
    { key: "line_name", header: t(`${f}.colLineName`) },
    {
      key: "status",
      header: t(`${f}.colStatus`),
      renderCell: row => (
        <Badge variant={STATUS_VARIANT[row.status] ?? "neutral"}>
          {STATUS_KEY[row.status] ? t(`${f}.${STATUS_KEY[row.status]}`) : row.status}
        </Badge>
      ),
    },
    {
      key: "trial_expires_at",
      header: t(`${f}.colExpires`),
      renderCell: row => formatDate(row.trial_expires_at) ?? t(`${f}.empty`),
    },
    {
      key: "discord_user_id",
      header: t(`${f}.colDiscord`),
      renderCell: row => (
        <>
          {row.discord_user_id ?? t(`${f}.empty`)}
          {row.discord_channel_url && (
            <ButtonLink
              href={row.discord_channel_url}
              variant="ghost"
              size="sm"
              target="_blank"
              rel="noopener noreferrer"
            >
              {t(`${f}.openRoom`)}
            </ButtonLink>
          )}
        </>
      ),
    },
    {
      key: "flags",
      header: t(`${f}.colFlags`),
      renderCell: row => (
        <>
          {row.flag_many_ips && <Badge variant="warning">{t(`${f}.flagManyIps`)}</Badge>}
          {row.flag_shared_ip && <Badge variant="warning">{t(`${f}.flagSharedIp`)}</Badge>}
        </>
      ),
    },
    {
      key: "created_at",
      header: t(`${f}.colCreated`),
      renderCell: row => formatDate(row.created_at) ?? t(`${f}.empty`),
    },
    {
      key: "actions",
      header: t(`${f}.colActions`),
      renderCell: row => (
        <>
          {row.status === "trial" && (
            <>
              <Button size="sm" variant="primary" onClick={() => openAction(row, "activate")}>
                {t(`${f}.activate`)}
              </Button>
              <Button size="sm" variant="secondary" onClick={() => openAction(row, "extend")}>
                {t(`${f}.extend`)}
              </Button>
            </>
          )}
          {row.status !== "suspended" && (
            <Button size="sm" variant="danger" onClick={() => openAction(row, "suspend")}>
              {t(`${f}.suspend`)}
            </Button>
          )}
          {row.status === "suspended" && (
            <Button size="sm" variant="secondary" onClick={() => openAction(row, "unsuspend")}>
              {t(`${f}.unsuspend`)}
            </Button>
          )}
          <Button size="sm" variant="ghost" onClick={() => { void openLogins(row); }}>
            {t(`${f}.logins`)}
          </Button>
        </>
      ),
    },
  ];

  const confirmKey: Record<Action, string> = {
    activate: "confirmActivate",
    suspend: "confirmSuspend",
    unsuspend: "confirmUnsuspend",
    extend: "extendTarget",
  };
  const pendingTitle = pending
    ? pending.action === "extend"
      ? t(`${f}.extendTitle`)
      : t(`${f}.${pending.action}`)
    : "";

  return (
    <PageLayout navKey="nav.superAdminViewers" subtitleKey="superAdmin.viewers.subtitle">
      {error && (
        <div className="error-message" role="alert" data-testid="viewers-error">
          {error}
        </div>
      )}
      {fetching && items.length === 0 ? (
        <div>{t("common.loading")}</div>
      ) : (
        <DataTable
          columns={columns}
          data={items}
          rowKey={row => String(row.id)}
          emptyState={<EmptyState title={t("common.noData")} size="compact" />}
        />
      )}

      <Modal
        open={pending !== null}
        onClose={() => setPending(null)}
        title={pendingTitle}
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setPending(null)}>
              {t("common.cancel")}
            </Button>
            <Button
              variant="primary"
              onClick={() => { void run(); }}
              disabled={running || (pending?.action === "extend" && !daysValid)}
              data-testid="viewers-run"
            >
              {t(`${f}.run`)}
            </Button>
          </>
        }
      >
        {pending && (
          <>
            <p>
              {t(`${f}.${confirmKey[pending.action]}`, {
                name: pending.viewer.line_name,
                email: pending.viewer.email,
              })}
            </p>
            {pending.action === "extend" && (
              <TextField
                label={t(`${f}.extendDays`)}
                type="number"
                min={1}
                max={365}
                step={1}
                value={daysText}
                onChange={e => setDaysText(e.target.value)}
                data-testid="viewers-extend-days"
              />
            )}
          </>
        )}
      </Modal>

      <Drawer
        open={loginsFor !== null}
        onClose={() => setLoginsFor(null)}
        title={t(`${f}.loginsTitle`)}
      >
        {logins.length === 0 ? (
          <p>{t(`${f}.loginsEmpty`)}</p>
        ) : (
          <DataTable
            columns={[
              { key: "created_at", header: t(`${f}.colLoginAt`), renderCell: (row: LoginItem) => formatDate(row.created_at) ?? "" },
              {
                key: "event_type",
                header: t(`${f}.colLoginType`),
                renderCell: (row: LoginItem) => (EVENT_KEY[row.event_type] ? t(`${f}.${EVENT_KEY[row.event_type]}`) : row.event_type),
              },
              { key: "client_ip", header: t(`${f}.colLoginIp`), renderCell: (row: LoginItem) => row.client_ip ?? t(`${f}.empty`) },
              { key: "user_agent", header: t(`${f}.colLoginAgent`), renderCell: (row: LoginItem) => row.user_agent ?? t(`${f}.empty`) },
            ]}
            data={logins}
            rowKey={row => `${row.created_at}|${row.event_type}|${row.client_ip ?? ""}`}
          />
        )}
      </Drawer>
    </PageLayout>
  );
}
