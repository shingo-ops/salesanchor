/**
 * /super-admin/settings — 全体設定（運営専用）。管理センターと同じ形（左の小さなメニュー＋右に Outlet）。
 * 項目の正本は settingsNav.ts。ADR-149（SubMenu）・ADR-087（hub-shell）。
 */
import { Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageLayout } from "../../../components/PageLayout";
import { LoadingBlock } from "../../../components/loading";
import { SubMenu, type SubMenuGroup } from "../../../components/SubMenu";
import { useSuperAdmin } from "../../../hooks/useSuperAdmin";
import { SETTINGS_MASTER_ITEMS, SETTINGS_MONEY_ITEMS } from "./settingsNav";

export default function SettingsHubPage() {
  const { t } = useTranslation();
  const location = useLocation();
  const { isSuperAdmin, loading } = useSuperAdmin();

  if (loading) {
    return (
      <PageLayout navKey="nav.superAdminSettings">
        <LoadingBlock />
      </PageLayout>
    );
  }

  if (!isSuperAdmin) {
    return (
      <PageLayout navKey="nav.superAdminSettings">
        <div className="error-message" role="alert">
          {t("superAdmin.accessDenied")}
        </div>
      </PageLayout>
    );
  }

  const groups: SubMenuGroup[] = [
    {
      title: t("superAdmin.settings.groupMoney"),
      items: SETTINGS_MONEY_ITEMS.map((i) => ({ key: i.key, label: t(i.labelKey), to: i.key })),
    },
    {
      title: t("analysisRules.sidebar.groupMasterManagement"),
      items: SETTINGS_MASTER_ITEMS.map((i) => ({
        key: i.key,
        label: t(i.labelKey),
        to: `masters/${i.key}`,
      })),
    },
  ];

  const allKeys = [...SETTINGS_MONEY_ITEMS, ...SETTINGS_MASTER_ITEMS].map((i) => i.key);
  const last = location.pathname.split("/").filter(Boolean).pop() ?? "";
  const activeKey = allKeys.includes(last) ? last : allKeys[0];

  return (
    <PageLayout navKey="nav.superAdminSettings" noScroll>
      <div className="hub-shell">
        <SubMenu variant="grouped" className="hub-subnav" groups={groups} activeKey={activeKey} />
        <div className="hub-content">
          <Outlet />
        </div>
      </div>
    </PageLayout>
  );
}
