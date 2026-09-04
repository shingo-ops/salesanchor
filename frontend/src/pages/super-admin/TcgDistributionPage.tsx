/**
 * /super-admin/tcg-distribution — TCG 配信先管理
 *
 * CC_TASK_DISTUI-01: 配信先マスタ CRUD + プレビュー + 配信実行
 * 認証: is_super_admin 必須
 */
import { useEffect, useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import { NAV_ICONS } from "../../constants/icons";
import { DistributionPreview } from "../../features/tcg-distribution/DistributionPreview";
import { DistributionTargetList } from "../../features/tcg-distribution/DistributionTargetList";
import { DistributionTargetForm } from "../../features/tcg-distribution/DistributionTargetForm";
import { listTargets } from "../../features/tcg-distribution/distributionApi";
import type { DistributionTarget } from "../../features/tcg-distribution/distributionApi";
import "../../features/tcg-distribution/distribution.css";

export default function TcgDistributionPage() {
  const { t } = useTranslation();
  const { isSuperAdmin, loading: superAdminLoading } = useSuperAdmin();
  const [targets, setTargets] = useState<DistributionTarget[]>([]);
  const [loadError, setLoadError] = useState("");
  const [showNewForm, setShowNewForm] = useState(false);

  const loadTargets = useCallback(() => {
    setLoadError("");
    listTargets()
      .then(setTargets)
      .catch((e: unknown) => setLoadError(e instanceof Error ? e.message : String(e)));
  }, []);

  useEffect(() => {
    if (isSuperAdmin) loadTargets();
  }, [isSuperAdmin, loadTargets]);

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
      onClick={() => setShowNewForm(true)}
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
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
        {/* プレビュー + 全件配信 */}
        <DistributionPreview onRefreshTargets={loadTargets} />

        {/* 配信先一覧 */}
        {loadError ? (
          <p style={{ color: "var(--color-error)", fontSize: "var(--font-sm)" }}>
            {t("common.fetchError")}: {loadError}
          </p>
        ) : (
          <DistributionTargetList targets={targets} onRefresh={loadTargets} />
        )}
      </div>

      {/* 新規登録ドロワー */}
      {showNewForm && (
        <DistributionTargetForm
          target={null}
          onClose={() => setShowNewForm(false)}
          onSaved={() => {
            setShowNewForm(false);
            loadTargets();
          }}
        />
      )}
    </PageLayout>
  );
}
