/**
 * /super-admin/users/meta-review — Meta 審査用のスイッチ（ADR-1055 What 11・設計 3-8）。
 *
 * - 審査用の印が付いた会社だけ、登録していない機械からのログインを 14 日間許すスイッチ
 * - 下にログインの履歴（新しい順）。30 秒ごとに読み直す
 * - is_super_admin=true のみアクセス可（Page 内で 403 の表示）
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import { LoadingBlock } from "../../components/loading";
import { Stack } from "../../components/Stack";
import { SectionCard } from "../../components/SectionCard";
import { Toggle } from "../../components/Toggle";
import { Badge } from "../../components/Badge";
import ConfirmModal from "../../components/ConfirmModal";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { EmptyState } from "../../components/EmptyState";
import { formatDate } from "../../features/tcg-analysis-review/formatDateTime";
import { UserManagementSubMenu, type UserMenuStatus } from "./users/UserManagementSubMenu";

const STATUS_KEY = {
  pending: "statusPending",
  trial: "statusTrial",
  contracting: "statusContracting",
  active: "statusActive",
} as const;

interface MetaReviewStatus {
  tenant_name: string | null;
  is_on: boolean;
  until: string | null;
}

interface MetaReviewLoginItem {
  created_at: string | null;
  email: string | null;
  path: string | null;
  status_code: number;
  reason: string | null;
  device: string | null;
}

const REASON_KEYS: Record<string, string> = {
  ok: "superAdmin.metaReview.reason.ok",
  meta_review: "superAdmin.metaReview.reason.meta_review",
  first_login: "superAdmin.metaReview.reason.first_login",
  device_approval_required: "superAdmin.metaReview.reason.device_approval_required",
  bad_password: "superAdmin.metaReview.reason.bad_password",
  inactive: "superAdmin.metaReview.reason.inactive",
  locked: "superAdmin.metaReview.reason.locked",
  passkey_new_device: "superAdmin.metaReview.reason.passkey_new_device",
  recovery_code_wrong: "superAdmin.metaReview.reason.recovery_code_wrong",
  approved_recovery: "superAdmin.metaReview.reason.approved_recovery",
  approved_admin: "superAdmin.metaReview.reason.approved_admin",
  approved_device: "superAdmin.metaReview.reason.approved_device",
};

export default function MetaReviewPage() {
  const { t, i18n } = useTranslation();
  const { isSuperAdmin, loading: authLoading } = useSuperAdmin();
  const [status, setStatus] = useState<MetaReviewStatus | null>(null);
  const [statusError, setStatusError] = useState(false);
  const [pending, setPending] = useState<boolean | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const [logins, setLogins] = useState<MetaReviewLoginItem[]>([]);
  const [historyError, setHistoryError] = useState(false);

  const statusLabel = (key: UserMenuStatus) =>
    key === "all" ? t("superAdmin.viewers.menuAll") : t(`superAdmin.viewers.${STATUS_KEY[key]}`);

  const loadLogins = useCallback(async () => {
    try {
      const res = await api.get<{ items: MetaReviewLoginItem[] }>("/super-admin/meta-review/logins");
      setLogins(res.items);
      setHistoryError(false);
    } catch {
      setHistoryError(true);
    }
  }, []);

  useEffect(() => {
    if (!isSuperAdmin) return;
    let alive = true;
    api
      .get<MetaReviewStatus>("/super-admin/meta-review")
      .then((res) => {
        if (alive) setStatus(res);
      })
      .catch(() => {
        if (alive) setStatusError(true);
      });
    return () => {
      alive = false;
    };
  }, [isSuperAdmin]);

  useEffect(() => {
    if (!isSuperAdmin) return;
    void loadLogins();
    const timer = setInterval(() => void loadLogins(), 30_000);
    return () => clearInterval(timer);
  }, [isSuperAdmin, loadLogins]);

  const confirmSwitch = async () => {
    if (pending === null) return;
    setSaving(true);
    setSaveError(false);
    try {
      const res = await api.put<MetaReviewStatus>("/super-admin/meta-review", { on: pending });
      setStatus(res);
      await loadLogins();
    } catch {
      setSaveError(true);
    } finally {
      setSaving(false);
      setPending(null);
    }
  };

  if (authLoading) return <LoadingBlock />;

  if (!isSuperAdmin) {
    return (
      <PageLayout navKey="nav.superAdminMetaReview">
        <div className="error-message" role="alert">
          {t("superAdmin.accessDenied")}
        </div>
      </PageLayout>
    );
  }

  const resultBadge = (code: number) => {
    if (code === 200) return <Badge variant="success">{t("superAdmin.metaReview.resultOk")}</Badge>;
    if (code === 202) return <Badge variant="warning">{t("superAdmin.metaReview.resultPending")}</Badge>;
    return <Badge variant="danger">{t("superAdmin.metaReview.resultNg")}</Badge>;
  };

  const reasonText = (reason: string | null) => {
    const key = reason ? REASON_KEYS[reason] : undefined;
    return key ? t(key) : t("superAdmin.metaReview.reason.other", { code: reason ?? "-" });
  };

  const columns: DataTableColumn<MetaReviewLoginItem>[] = [
    {
      key: "created_at",
      header: t("superAdmin.metaReview.colWhen"),
      renderCell: (row) => (row.created_at ? formatDate(row.created_at, i18n.language) : ""),
    },
    {
      key: "email",
      header: t("superAdmin.metaReview.colEmail"),
      renderCell: (row) => row.email ?? "",
    },
    {
      key: "status_code",
      header: t("superAdmin.metaReview.colResult"),
      renderCell: (row) => resultBadge(row.status_code),
    },
    {
      key: "reason",
      header: t("superAdmin.metaReview.colReason"),
      renderCell: (row) => reasonText(row.reason),
    },
    {
      key: "device",
      header: t("superAdmin.metaReview.colDevice"),
      renderCell: (row) => row.device ?? "",
    },
  ];

  const whenText = status?.until ? formatDate(status.until, i18n.language) : "";

  return (
    <PageLayout navKey="nav.superAdminMetaReview" subtitleKey="superAdmin.metaReview.subtitle">
      <div className="hub-shell">
        <UserManagementSubMenu activeKey="meta-review" statusLabel={statusLabel} />
        <div className="hub-content">
          <Stack gap="4">
            <SectionCard title={t("superAdmin.metaReview.switchTitle")}>
              {statusError && (
                <div className="error-message" role="alert">
                  {t("superAdmin.metaReview.loadError")}
                </div>
              )}
              {saveError && (
                <div className="error-message" role="alert">
                  {t("superAdmin.metaReview.saveError")}
                </div>
              )}
              {status && (
                <Stack gap="3">
                  {status.tenant_name === null ? (
                    <div>{t("superAdmin.metaReview.noTenant")}</div>
                  ) : (
                    <div>{t("superAdmin.metaReview.tenant", { name: status.tenant_name })}</div>
                  )}
                  <Stack direction="row" gap="3">
                    <Toggle
                      checked={status.is_on}
                      aria-label={t("superAdmin.metaReview.toggleLabel")}
                      disabled={saving || status.tenant_name === null}
                      onCheckedChange={(next) => setPending(next)}
                    />
                    {status.is_on ? (
                      <Badge variant="success">{t("superAdmin.metaReview.badgeOn")}</Badge>
                    ) : (
                      <Badge variant="neutral">{t("superAdmin.metaReview.badgeOff")}</Badge>
                    )}
                  </Stack>
                  {status.is_on && status.until && (
                    <div>{t("superAdmin.metaReview.autoOffAt", { when: whenText })}</div>
                  )}
                  {!status.is_on && status.until && (
                    <div>{t("superAdmin.metaReview.autoOffDone", { when: whenText })}</div>
                  )}
                </Stack>
              )}
            </SectionCard>

            <SectionCard title={t("superAdmin.metaReview.historyTitle")}>
              {historyError && (
                <div className="error-message" role="alert">
                  {t("superAdmin.metaReview.historyLoadError")}
                </div>
              )}
              <DataTable
                columns={columns}
                data={logins}
                rowKey={(row) => `${row.created_at}-${logins.indexOf(row)}`}
                mobileCards
                emptyState={<EmptyState size="compact" title={t("superAdmin.metaReview.empty")} />}
              />
            </SectionCard>
          </Stack>
        </div>
      </div>

      <ConfirmModal
        open={pending !== null}
        danger={pending === false}
        title={pending ? t("superAdmin.metaReview.confirmOnTitle") : t("superAdmin.metaReview.confirmOffTitle")}
        message={pending ? t("superAdmin.metaReview.confirmOnMessage") : t("superAdmin.metaReview.confirmOffMessage")}
        confirmLabel={pending ? t("superAdmin.metaReview.confirmOn") : t("superAdmin.metaReview.confirmOff")}
        confirmLoading={saving}
        onConfirm={() => void confirmSwitch()}
        onCancel={() => setPending(null)}
      />
    </PageLayout>
  );
}
