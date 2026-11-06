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
import AdminLoginRequestList from "../../features/auth/AdminLoginRequestList";

export default function LoginRequestsPage() {
  const { t } = useTranslation();
  const { isSuperAdmin, loading: authLoading } = useSuperAdmin();

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
      <AdminLoginRequestList
        listPath="/super-admin/login-requests?status=pending"
        approvePath={(id) => `/super-admin/login-requests/${id}/approve`}
      />
    </PageLayout>
  );
}
