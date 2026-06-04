/**
 * AdminHubPage — SaaS 管理者ハブ
 *
 * 各テナント管理機能をボトムタブで統合するシェルページ。
 * 左サブナビ（ManagementCenterPage）と同じ Outlet パターンを採用し、
 * タブナビゲーションはページ最下部に配置する。
 *
 * ルート: /admin/*
 * タブ:
 *   - tenant-profile     : 発行者情報
 *   - discord-config     : Discord 連携設定
 *   - discord-announce   : Discord アナウンス
 *   - inventory-visibility: 在庫表示権限
 */

import { NavLink, Outlet } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ADMIN_HUB_ICONS } from "../../constants/icons";
import "./admin-hub.css";

const TABS = [
  {
    to:       "tenant-profile",
    labelKey: "nav.tenantProfile",
    Icon:     ADMIN_HUB_ICONS.tenantProfile,
  },
  {
    to:       "tenant-policy",
    labelKey: "nav.tenantPolicy",
    Icon:     ADMIN_HUB_ICONS.tenantPolicy,
  },
  {
    to:       "discord-config",
    labelKey: "nav.discordConfig",
    Icon:     ADMIN_HUB_ICONS.discordConfig,
  },
  {
    to:       "discord-announce",
    labelKey: "nav.discordAnnounce",
    Icon:     ADMIN_HUB_ICONS.discordAnnounce,
  },
  {
    to:       "inventory-visibility",
    labelKey: "nav.inventoryVisibility",
    Icon:     ADMIN_HUB_ICONS.inventoryVisibility,
  },
] as const;

export default function AdminHubPage() {
  const { t } = useTranslation();

  return (
    <div className="admin-hub">
      <div className="admin-hub-content">
        <Outlet />
      </div>

      <nav className="admin-hub-tabs" aria-label={t("nav.admin")}>
        {TABS.map(({ to, labelKey, Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `admin-hub-tab${isActive ? " active" : ""}`
            }
          >
            <Icon size={22} aria-hidden="true" />
            <span className="admin-hub-tab-label">{t(labelKey)}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
