/**
 * /management-center/login-requests — 社員のログインの許可待ち（ADR-1063）。
 *
 * - 社員が新しい機械で「会社の管理者に頼む」を押した、同じ会社の依頼だけが並ぶ（会社の絞り込みは API 側）
 * - 会社のオーナー（is_tenant_owner）だけが開ける。それ以外は案内の文だけ
 * - 一覧と許可の小窓は運営の画面と共有（features/auth/AdminLoginRequestList）
 */
import { useTranslation } from "react-i18next";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";
import { LoadingBlock } from "../../components/loading";
import AdminLoginRequestList from "../../features/auth/AdminLoginRequestList";

export default function TenantLoginRequestsPage() {
  const { t } = useTranslation();
  const { isTenantOwner, loading } = usePermissions();

  if (loading) return <LoadingBlock />;

  if (!isTenantOwner) {
    return (
      <PageLayout navKey="nav.tenantLoginRequests" subtitleKey="managementCenter.loginRequests.subtitle">
        <div className="error-message" role="alert">
          {t("managementCenter.loginRequests.ownerOnly")}
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout navKey="nav.tenantLoginRequests" subtitleKey="managementCenter.loginRequests.subtitle">
      <AdminLoginRequestList
        listPath="/tenant/login-requests"
        approvePath={(id) => `/tenant/login-requests/${id}/approve`}
      />
    </PageLayout>
  );
}
