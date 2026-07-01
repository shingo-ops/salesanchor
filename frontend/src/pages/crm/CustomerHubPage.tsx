/**
 * 顧客管理ハブ（Customer Hub）
 *
 * 管理センターと同パターンの左サブナビ + 右コンテンツ（Outlet）シェル。
 * CRM 関連ページ（リード・会社・顧客(旧)・アーカイブ）を一元管理する。
 * 担当者は会社詳細ページの「担当者」タブで管理するためサブナビから除外。
 *
 * ルート: /crm/*
 */

import { Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageLayout } from "../../components/PageLayout";
import { usePermissions } from "../../hooks/usePermissions";
import { SubMenu } from "../../components/SubMenu";
import type { SubMenuGroup } from "../../components/SubMenu";


interface SubNavItem {
  to: string;
  labelKey: string;
  visible: boolean;
}

export default function CustomerHubPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();

  const items: SubNavItem[] = [
    {
      to: "leads",
      labelKey: "nav.leadsSection",
      visible: hasPermission("leads.view"),
    },
    {
      to: "companies",
      labelKey: "nav.companies",
      visible: hasPermission("customers.view"),
    },
    {
      to: "archive",
      labelKey: "nav.archive",
      visible:
        hasPermission("leads.view") || hasPermission("customers.view"),
    },
  ];

  const visibleItems = items.filter((i) => i.visible);

  // キット(SubMenu)へ渡す形に変換。labelKey は t() で翻訳済み文字列に。
  const groups: SubMenuGroup[] = [
    {
      items: visibleItems.map((i) => ({
        key: i.to,
        label: t(i.labelKey),
        to: i.to,
      })),
    },
  ];

  // 今開いているページを activeKey に反映（末尾セグメントで判定）
  const location = useLocation();
  const activeKey =
    visibleItems.find((i) => location.pathname.endsWith(`/${i.to}`))?.to ??
    visibleItems[0]?.to ??
    "";

  return (
    <PageLayout navKey="nav.leads" subtitleKey="crm.subtitle" noScroll>
      <div className="hub-shell">
        {/* 左サブナビ（共通部品 SubMenu に集約 / ADR-149） */}
        <SubMenu
          variant="grouped"
          className="hub-subnav"
          groups={groups}
          activeKey={activeKey}
        />

        {/* 右コンテンツ */}
        <div className="hub-content">
          <Outlet />
        </div>
      </div>
    </PageLayout>
  );
}
