/**
 * NavItemList — 共通 nav item 描画コンポーネント（SSoT）
 *
 * PR-R2-A で新規追加。DesktopShell / MobileShell が共通で利用する。
 * 権限判定・未読バッジカウントは親が実行済みであること（純粋描画のみ）。
 *
 * 参照: docs/handoff/mobile-shell-pr-r2a/design.md
 * ADR: ADR-137 / ADR-067 / ADR-027
 */

import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

export interface ResolvedNavItem {
  key: string;
  labelKey: string;
  icon: React.ReactNode;
  path: string;
  children?: ResolvedNavItem[];
  unread?: boolean;
}

interface NavItemListProps {
  items: ResolvedNavItem[];
  onNavClick: () => void;
  variant: "desktop" | "mobile";
  unreadCount?: number;
}

export function NavItemList({
  items,
  onNavClick,
  variant,
  unreadCount = 0,
}: NavItemListProps) {
  const { t } = useTranslation();

  return (
    <nav className={`nav-item-list nav-item-list--${variant}`} aria-label={t("nav.openMenu")}>
      {items.map((item) => {
        if (item.children && item.children.length > 0) {
          return (
            <div key={item.key} className="nav-item-list__group">
              <span className="nav-item-list__group-label">
                <span className="nav-item-list__icon">{item.icon}</span>
                <span className="nav-item-list__label">{t(item.labelKey)}</span>
              </span>
              <div className="nav-item-list__children">
                {item.children.map((child) => (
                  <NavLink
                    key={child.key}
                    to={child.path}
                    className={({ isActive }) =>
                      `nav-item-list__child${isActive ? " nav-item-list__child--active" : ""}`
                    }
                    onClick={onNavClick}
                  >
                    {t(child.labelKey)}
                  </NavLink>
                ))}
              </div>
            </div>
          );
        }

        return (
          <NavLink
            key={item.key}
            to={item.path}
            className={({ isActive }) =>
              `nav-item-list__item${isActive ? " nav-item-list__item--active" : ""}`
            }
            onClick={onNavClick}
          >
            <span className="nav-item-list__icon">{item.icon}</span>
            <span className="nav-item-list__label">{t(item.labelKey)}</span>
            {item.unread && unreadCount > 0 && (
              <span className="nav-item-list__badge" aria-hidden="true">
                {unreadCount}
              </span>
            )}
          </NavLink>
        );
      })}
    </nav>
  );
}
