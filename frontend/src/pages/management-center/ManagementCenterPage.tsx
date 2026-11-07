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

import { Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageLayout } from "../../components/PageLayout";
import { usePermissions } from "../../hooks/usePermissions";
import { canSeeMenu, type MenuId } from "../../constants/menuPermissions";
import type { NavItem, NavSection } from "../../types/nav";
import { SubMenu } from "../../components/SubMenu";
import type { SubMenuGroup } from "../../components/SubMenu";


/** 権限フィルタリング前の生アイテム（このファイル内のみで使用） */
interface RawNavItem extends NavItem {
  visible: boolean;
}

export default function ManagementCenterPage() {
  const { t } = useTranslation();
  const { hasAny, isTenantOwner } = usePermissions();
  const can = (id: MenuId) => canSeeMenu(id, hasAny);

  const rawSections: { key: string; titleKey: string; items: RawNavItem[] }[] = [
    {
      key: "team",
      titleKey: "managementCenter.sectionTeam",
      items: [
        { to: "staff",      labelKey: "nav.staff",             visible: can("staff") },
        { to: "roles",      labelKey: "nav.roles",             visible: can("roles") },
        { to: "teams",      labelKey: "nav.teams",             visible: can("teams") },
        { to: "shifts",     labelKey: "nav.shifts",            visible: can("shifts") },
        { to: "commission", labelKey: "nav.commissionSettings", visible: can("commissionSettings") },
        { to: "reports",    labelKey: "nav.reports",           visible: true },
        { to: "tenant-policy", labelKey: "nav.tenantPolicy",
          visible: can("tenantPolicy") },
      ],
    },
    {
      key: "data",
      titleKey: "managementCenter.sectionData",
      items: [
        { to: "suppliers",      labelKey: "nav.suppliers",      visible: can("suppliers") },
        { to: "status-master",  labelKey: "nav.statusMaster",   visible: can("statusMaster") },
        { to: "conditions",         labelKey: "nav.conditionsMaster",   visible: can("conditionsMaster") },
        { to: "product-categories", labelKey: "nav.productCategories",  visible: can("productCategories") },
        { to: "units",              labelKey: "nav.units",               visible: can("units") },
        { to: "note-master",    labelKey: "nav.noteMaster",     visible: can("noteMaster") },
        { to: "data",           labelKey: "nav.dataManagement", visible: can("dataManagement") },
      ],
    },
    {
      // API 連携（外部サービス連携設定）。現状は各項目とも「現在作成中」プレースホルダー。
      key: "apiIntegration",
      titleKey: "managementCenter.sectionApiIntegration",
      items: [
        { to: "integrations/google-drive", labelKey: "nav.integrationGoogleDrive", visible: can("integrationGoogleDrive") },
        { to: "integrations/fedex",        labelKey: "nav.integrationFedex",       visible: can("integrationFedex") },
        { to: "integrations/dhl",          labelKey: "nav.integrationDhl",         visible: can("integrationDhl") },
        { to: "integrations/ups",          labelKey: "nav.integrationUps",         visible: can("integrationUps") },
        { to: "integrations/paypal",       labelKey: "nav.integrationPaypal",      visible: can("integrationPaypal") },
        { to: "discord-config",     labelKey: "nav.discordConfig",
          visible: can("discordConfig") },
        { to: "discord-announce",   labelKey: "nav.discordAnnounce",
          visible: can("discordAnnounce") },
      ],
    },
    {
      key: "business",
      titleKey: "managementCenter.sectionBusiness",
      items: [
        { to: "tenant-profile", labelKey: "nav.tenantProfile",
          visible: can("tenantProfile") },
        { to: "channels",       labelKey: "nav.channels",       visible: can("channels") },
        { to: "channel-masters", labelKey: "nav.channelMasters", visible: can("channelMasters") },
        { to: "bots",           labelKey: "nav.bots",           visible: can("bots") },
        { to: "notifications",  labelKey: "nav.notifications",  visible: can("notifications") },
        { to: "login-requests", labelKey: "nav.tenantLoginRequests", visible: isTenantOwner },
      ],
    },
  ];

  // 権限フィルタリングして共有型 NavSection[] に変換
  const sections: NavSection[] = rawSections
    .map((s) => ({ key: s.key, titleKey: s.titleKey, items: s.items.filter((i) => i.visible) }))
    .filter((s) => s.items.length > 0);

  // キット(SubMenu)へ渡す形に変換。titleKey/labelKey は t() で翻訳済み文字列に。
  const groups: SubMenuGroup[] = sections.map((section) => ({
    title: t(section.titleKey),
    items: section.items.map((item) => ({
      key: item.to,
      label: t(item.labelKey),
      to: item.to,
    })),
  }));

  // 今開いているページを activeKey に反映（末尾セグメントで判定）
  const location = useLocation();
  const allItems = sections.flatMap((s) => s.items);
  const activeKey =
    allItems.find((i) => location.pathname.endsWith(`/${i.to}`))?.to ??
    allItems[0]?.to ??
    "";

  return (
    <PageLayout navKey="nav.managementCenter" subtitleKey="managementCenter.subtitle" noScroll>
      <div className="hub-shell">
        {/* 左サブナビ（共通部品 SubMenu に集約 / ADR-149） */}
        <SubMenu
          variant="grouped"
          className="hub-subnav"
          groups={groups}
          activeKey={activeKey}
        />

        {/* 右コンテンツ（子ルートが展開される） */}
        <div className="hub-content">
          <Outlet />
        </div>
      </div>
    </PageLayout>
  );
}
