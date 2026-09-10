/**
 * /super-admin/tcg-distribution — TCG 配信先管理
 *
 * CC_TASK_DISTUI-01: 配信先マスタ CRUD + プレビュー + 配信実行
 * 認証: is_super_admin 必須
 */
import { useRef } from "react";
import { useTranslation } from "react-i18next";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import { NAV_ICONS } from "../../constants/icons";
import {
  DistributionWorkspace,
  type DistributionWorkspaceHandle,
} from "../../features/tcg-distribution/DistributionWorkspace";

export default function TcgDistributionPage() {
  const { t } = useTranslation();
  const { isSuperAdmin, loading: superAdminLoading } = useSuperAdmin();
  const workspaceRef = useRef<DistributionWorkspaceHandle>(null);

  if (superAdminLoading) {
    return (
      <PageLayout navKey="nav.superAdminTcgDistribution">
        {t("common.loading")}
      </PageLayout>
    );
  }

  if (!isSuperAdmin) {
    return (
      <PageLayout navKey="nav.superAdminTcgDistribution">
        <p style={{ color: "var(--color-error)" }}>
          {t("superAdmin.supplierQuality.superAdminOnly")}
        </p>
      </PageLayout>
    );
  }

  const newButton = (
    <button
      type="button"
      className="dist-btn dist-btn--primary"
      onClick={() => workspaceRef.current?.openNewTargetForm()}
      aria-label={t("distributionTarget.page.newBtn")}
    >
      <NAV_ICONS.add size={16} aria-hidden="true" />
      {t("distributionTarget.page.newBtn")}
    </button>
  );

  return (
    <PageLayout
      navKey="nav.superAdminTcgDistribution"
      subtitleKey="distributionTarget.page.subtitle"
      headerAction={newButton}
    >
      <DistributionWorkspace ref={workspaceRef} showNewTargetAction={false} />
    </PageLayout>
  );
}
