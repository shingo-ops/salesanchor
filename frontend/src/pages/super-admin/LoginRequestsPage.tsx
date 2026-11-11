/**
 * /super-admin/login-requests — ログインの許可待ち一覧（ADR-1055 段A・K7）。
 *
 * - いつもの機械も予備の合言葉も無い人の依頼を、super admin が本人確認のうえ許可する
 * - 一覧と許可の小窓は会社のオーナーの画面と共有（features/auth/AdminLoginRequestList）
 * - is_super_admin=true のみアクセス可（Page 内で 403 の表示）
 */
import { useTranslation } from "react-i18next";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import { LoadingBlock } from "../../components/loading";
import { UserManagementSubMenu, type UserMenuStatus } from "./users/UserManagementSubMenu";
import AdminLoginRequestList from "../../features/auth/AdminLoginRequestList";

const STATUS_KEY = { pending: "statusPending", trial: "statusTrial", active: "statusActive" } as const;

export default function LoginRequestsPage() {
  const { t } = useTranslation();
  const { isSuperAdmin, loading: authLoading } = useSuperAdmin();
  const statusLabel = (key: UserMenuStatus) =>
    key === "all" ? t("superAdmin.viewers.menuAll") : t(`superAdmin.viewers.${STATUS_KEY[key]}`);

  if (authLoading) return <LoadingBlock />;

  if (!isSuperAdmin) {
    return (
      <PageLayout navKey="nav.superAdminLoginRequests">
        <div className="error-message" role="alert">
          {t("superAdmin.accessDenied")}
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout navKey="nav.superAdminLoginRequests" subtitleKey="superAdmin.loginRequests.subtitle">
      <div className="hub-shell">
        <UserManagementSubMenu statusLabel={statusLabel} />
        <div className="hub-content">
          <AdminLoginRequestList
            listPath="/super-admin/login-requests?status=pending"
            approvePath={(id) => `/super-admin/login-requests/${id}/approve`}
          />
        </div>
      </div>
    </PageLayout>
  );
}
