/**
 * 管理センター（Management Center）
 *
 * Google Admin / macOS System Settings 方式の管理ハブ。
 * 左サブナビ + 右コンテンツ（Outlet）のシェル構造。
 * ロール・権限に基づいてサブナビ項目を表示制御する。
 *
 * ルート: /management-center/*
 *
 * 変更履歴:
 *   2026-05-25: 初版作成（ADR-069 管理センター一元化）
 */

import { NavLink, Outlet } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageLayout } from "../../components/PageLayout";
import { usePermissions } from "../../hooks/usePermissions";
import type { NavItem, NavSection } from "../../types/nav";


/** 権限フィルタリング前の生アイテム（このファイル内のみで使用） */
interface RawNavItem extends NavItem {
  visible: boolean;
}

export default function ManagementCenterPage() {
  const { t } = useTranslation();
  const { hasPermission, hasAny } = usePermissions();

  const rawSections: { key: string; titleKey: string; items: RawNavItem[] }[] = [
    {
      key: "team",
      titleKey: "managementCenter.sectionTeam",
      items: [
        { to: "staff",      labelKey: "nav.staff",             visible: hasPermission("staff.view") },
        { to: "roles",      labelKey: "nav.roles",             visible: hasAny("roles.view", "roles.create") },
        { to: "teams",      labelKey: "nav.teams",             visible: hasPermission("teams.view") },
        { to: "shifts",     labelKey: "nav.shifts",            visible: hasPermission("shifts.view") },
        { to: "commission", labelKey: "nav.commissionSettings", visible: hasPermission("orders.view") },
        { to: "reports",    labelKey: "nav.reports",           visible: true },
      ],
    },
    {
      key: "data",
      titleKey: "managementCenter.sectionData",
      items: [
        { to: "deals",          labelKey: "nav.deals",          visible: hasPermission("deals.view") },
        { to: "suppliers",      labelKey: "nav.suppliers",      visible: hasPermission("suppliers.view") },
        { to: "purchase-orders", labelKey: "nav.purchaseOrders", visible: hasPermission("purchase_orders.view") },
        { to: "data",           labelKey: "nav.dataManagement", visible: hasPermission("erp.view") },
      ],
    },
    {
      // API 連携（外部サービス連携設定）。現状は各項目とも「現在作成中」プレースホルダー。
      key: "apiIntegration",
      titleKey: "managementCenter.sectionApiIntegration",
      items: [
        { to: "integrations/google-drive", labelKey: "nav.integrationGoogleDrive", visible: hasPermission("erp.view") },
        { to: "integrations/fedex",        labelKey: "nav.integrationFedex",       visible: hasPermission("erp.view") },
        { to: "integrations/dhl",          labelKey: "nav.integrationDhl",         visible: hasPermission("erp.view") },
        { to: "integrations/ups",          labelKey: "nav.integrationUps",         visible: hasPermission("erp.view") },
        { to: "integrations/yamato",       labelKey: "nav.integrationYamato",      visible: hasPermission("erp.view") },
        { to: "integrations/sagawa",       labelKey: "nav.integrationSagawa",      visible: hasPermission("erp.view") },
      ],
    },
    {
      key: "business",
      titleKey: "managementCenter.sectionBusiness",
      items: [
        { to: "tenant-profile", labelKey: "nav.tenantProfile",
          visible: hasAny("tenant.profile.edit", "tenant.profile.view") },
        { to: "channels",       labelKey: "nav.channels",       visible: hasPermission("channels.view") },
        { to: "bots",           labelKey: "nav.bots",           visible: hasPermission("bots.view") },
        { to: "notifications",  labelKey: "nav.notifications",  visible: hasPermission("notifications.manage") },
        // ADR-SA-17: テナント翻訳グロッサリ
        { to: "tenant-glossary", labelKey: "nav.tenantGlossary", visible: hasPermission("messaging.view") },
      ],
    },
  ];

  // 権限フィルタリングして共有型 NavSection[] に変換
  const sections: NavSection[] = rawSections
    .map((s) => ({ key: s.key, titleKey: s.titleKey, items: s.items.filter((i) => i.visible) }))
    .filter((s) => s.items.length > 0);

  return (
    <PageLayout navKey="nav.managementCenter" subtitleKey="managementCenter.subtitle" noScroll>
      <div className="hub-shell">
        {/* 左サブナビ */}
        <nav className="hub-subnav" aria-label={t("nav.managementCenter")}>
          {sections.map((section) => (
            <div key={section.key} className="hub-subnav-section">
              <span className="hub-subnav-title">{t(section.titleKey)}</span>
              {section.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      `hub-subnav-item${isActive ? " active" : ""}`
                    }
                  >
                    {t(item.labelKey)}
                  </NavLink>
              ))}
            </div>
          ))}
        </nav>

        {/* 右コンテンツ（子ルートが展開される） */}
        <div className="hub-content">
          <Outlet />
        </div>
      </div>
    </PageLayout>
  );
}
