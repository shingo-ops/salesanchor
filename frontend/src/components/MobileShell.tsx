/**
 * MobileShell — モバイル専用 Shell コンポーネント（ADR-140 PR-B）
 *
 * ADR-137: MobileShell は DesktopShell（Layout.tsx）とは独立した DOM。
 * ADR-140: ハンバーガー+Drawer → 下部タブバー（3タブ＋メニュー）に刷新。
 * ADR-067: 色・余白・z-index はすべて CSS token 参照。hex / px マジックナンバー禁止。
 * ADR-027: 全 UI 文字列は t("key") 経由。ハードコード禁止。
 *
 * DOM 構造:
 *   MobileShell (.mobile-shell)
 *   ├── MobileTopBar (.mobile-topbar — sticky, z-index: var(--z-topbar)=100)
 *   │   └── PageTitle (span.mobile-topbar-title)
 *   ├── .mobile-content → <Outlet />
 *   ├── .mobile-more-backdrop（moreSheetOpen 時のみ）
 *   ├── .mobile-more-sheet（slide-up, z-index: var(--z-sidebar-overlay)=210）
 *   │   ├── NavItemList variant="mobile"（メニュー項目）
 *   │   └── action rows（theme / language / sign out）
 *   ├── MobileTabBar (.mobile-tabbar — position:fixed, bottom:0, z-index: var(--z-topbar)=100)
 *   │   ├── NavLink(受信箱: /lead-chat) — prefs.show_chat_menu 条件付き
 *   │   ├── NavLink(在庫表: /inventory) — products.view 権限
 *   │   ├── NavLink(受注管理: /orders) — orders.view 権限
 *   │   └── MenuButton（「…」シート開閉）
 *   └── ConfirmModal（ログアウト確認）
 *
 * 参照: docs/handoff/mobile-responsive/design.md §B-2
 */

import { useCallback, useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../contexts/AuthContext";
import { useLocale } from "../contexts/LocaleContext";
import { useTheme } from "../contexts/ThemeContext";
import { useUiPrefs } from "../contexts/UiPrefsContext";
import { usePermissions } from "../hooks/usePermissions";
import { usePageTitle } from "../hooks/usePageTitle";
import { useSSE } from "../hooks/useSSE";
import { listConversations } from "../lib/messages";
import {
  NAV_ICONS,
  THEME_ICONS,
  GlobeIcon,
  LeadChatIcon,
  ACCOUNT_ICONS,
} from "../constants/icons";
import { ICON } from "../constants/iconSizes";
import { NavItemList } from "./NavItemList";
import type { ResolvedNavItem } from "./NavItemList";
import ConfirmModal from "./ConfirmModal";
import "../mobile-shell.css";

// ─── ユーティリティ: NavItem → ResolvedNavItem 変換 ──────────────────────────

function resolveItem(
  key: string,
  labelKey: string,
  icon: React.ReactNode,
  path: string,
  opts?: { unread?: boolean; children?: ResolvedNavItem[] },
): ResolvedNavItem {
  return { key, labelKey, icon, path, ...opts };
}

// ─── MobileShell ─────────────────────────────────────────────────────────────

export default function MobileShell() {
  const { t } = useTranslation();
  const { locale, changeLanguage } = useLocale();
  const { theme, changeTheme } = useTheme();
  const { signOut } = useAuth();
  const { hasPermission, loading: permsLoading } = usePermissions();
  const { prefs, loading: uiPrefsLoading } = useUiPrefs();
  const pageTitle = usePageTitle();

  const navLoading = permsLoading || uiPrefsLoading;

  // ── シート/ドロワー状態 ──
  const [moreSheetOpen, setMoreSheetOpen] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  // Escape key でメニューシートを閉じる
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && moreSheetOpen) setMoreSheetOpen(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [moreSheetOpen]);

  // ── 未読カウント（Layout.tsx:117-127 と同一パターン） ──
  const [unreadCount, setUnreadCount] = useState(0);
  const loadUnreadCount = useCallback(async () => {
    try {
      const data = await listConversations({ unread_only: true });
      setUnreadCount((data.conversations || []).length);
    } catch {
      // パーミッションなし・未認証等はバッジ非表示のまま維持
    }
  }, []);
  useEffect(() => {
    loadUnreadCount();
  }, [loadUnreadCount]);
  useSSE({ endpoint: "/api/v1/conversations/stream", onUpdate: loadUnreadCount });

  // ── nav items 解決（Layout.tsx:169-391 の権限判定を移植） ──

  const showCrmLink =
    hasPermission("leads.view") || hasPermission("customers.view");

  const showSalesLink =
    prefs.show_sales_menu &&
    (hasPermission("quotes.view") || hasPermission("invoices.view"));
  const salesLinkTo = hasPermission("quotes.view") ? "/quotes" : "/invoices";

  const menuItems: ResolvedNavItem[] = navLoading
    ? []
    : [
        ...(hasPermission("dashboard.view")
          ? [
              resolveItem(
                "dashboard",
                "nav.dashboard",
                <NAV_ICONS.dashboard size={ICON.base} aria-hidden="true" />,
                "/",
              ),
            ]
          : []),
        resolveItem(
          "schedule",
          "nav.schedule",
          <NAV_ICONS.schedule size={ICON.base} aria-hidden="true" />,
          "/schedule",
        ),
        ...(showSalesLink
          ? [
              resolveItem(
                "quotesInvoices",
                "nav.quotesInvoices",
                <NAV_ICONS.fileText size={ICON.base} aria-hidden="true" />,
                salesLinkTo,
              ),
            ]
          : []),
        ...(showCrmLink
          ? [
              resolveItem(
                "crm",
                "nav.leads",
                <NAV_ICONS.leads size={ICON.base} aria-hidden="true" />,
                "/crm",
              ),
            ]
          : []),
        resolveItem(
          "accountSettings",
          "nav.accountSettings",
          <ACCOUNT_ICONS.profile size={ICON.base} aria-hidden="true" />,
          "/account/settings",
        ),
      ];

  // ── レンダリング ──

  return (
    <div className="mobile-shell">
      {/* ============ MobileTopBar（タイトルのみ） ============ */}
      <div className="mobile-topbar">
        <span className="mobile-topbar-title">{pageTitle}</span>
      </div>

      {/* ============ Outlet ============ */}
      <main className="mobile-content">
        <Outlet />
      </main>

      {/* ============ MoreSheet backdrop（Drawer より背面: z-index 200） ============ */}
      {moreSheetOpen && (
        <div
          className="mobile-more-backdrop"
          onClick={() => setMoreSheetOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* ============ MoreSheet（Backdrop より前面: z-index 210、slide-up） ============ */}
      <div
        className={`mobile-more-sheet${moreSheetOpen ? " mobile-more-sheet--open" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={t("nav.menu")}
      >
        <NavItemList
          variant="mobile"
          items={menuItems}
          onNavClick={() => setMoreSheetOpen(false)}
          unreadCount={unreadCount}
        />

        <div className="mobile-menu-actions">
          <button
            className="mobile-menu-action"
            onClick={() => changeTheme(theme === "light" ? "dark" : "light")}
          >
            {theme === "light" ? (
              <THEME_ICONS.light size={ICON.md} aria-hidden="true" />
            ) : (
              <THEME_ICONS.dark size={ICON.md} aria-hidden="true" />
            )}
            <span>
              {theme === "light"
                ? t("nav.switchToDark")
                : t("nav.switchToLight")}
            </span>
          </button>

          <button
            className="mobile-menu-action"
            onClick={() => changeLanguage(locale === "ja" ? "en" : "ja")}
          >
            <GlobeIcon size={ICON.md} aria-hidden="true" />
            <span>{locale === "ja" ? t("language.en") : t("language.ja")}</span>
          </button>

          <button
            className="mobile-menu-action mobile-menu-action--danger"
            onClick={() => {
              setMoreSheetOpen(false);
              setShowLogoutConfirm(true);
            }}
          >
            <NAV_ICONS.logout size={ICON.md} aria-hidden="true" />
            <span>{t("nav.signOut")}</span>
          </button>
        </div>
      </div>

      {/* ============ MobileTabBar（fixed bottom） ============ */}
      <nav className="mobile-tabbar" aria-label={t("nav.openMenu")}>
        {/* 受信箱: prefs.show_chat_menu 条件付き */}
        {prefs.show_chat_menu && (
          <NavLink
            to="/lead-chat"
            className={({ isActive }) =>
              `mobile-tab${isActive ? " mobile-tab--active" : ""}`
            }
            aria-label={t("nav.leadChat")}
          >
            <LeadChatIcon size={ICON.base} aria-hidden="true" />
            <span className="mobile-tab-label">{t("nav.leadChat")}</span>
            {unreadCount > 0 && (
              <span className="mobile-tab-badge" aria-hidden="true">
                {unreadCount > 99 ? "99+" : unreadCount}
              </span>
            )}
          </NavLink>
        )}

        {/* 在庫: products.view 権限 */}
        {hasPermission("products.view") && (
          <NavLink
            to="/inventory"
            className={({ isActive }) =>
              `mobile-tab${isActive ? " mobile-tab--active" : ""}`
            }
            aria-label={t("nav.inventory")}
          >
            <NAV_ICONS.inventory size={ICON.base} aria-hidden="true" />
            <span className="mobile-tab-label">{t("nav.inventory")}</span>
          </NavLink>
        )}

        {/* 受注管理: orders.view 権限 */}
        {hasPermission("orders.view") && (
          <NavLink
            to="/orders"
            className={({ isActive }) =>
              `mobile-tab${isActive ? " mobile-tab--active" : ""}`
            }
            aria-label={t("nav.orders")}
          >
            <NAV_ICONS.orders size={ICON.base} aria-hidden="true" />
            <span className="mobile-tab-label">{t("nav.orders")}</span>
          </NavLink>
        )}

        {/* メニュー */}
        <button
          className="mobile-tab"
          onClick={() => setMoreSheetOpen(true)}
          aria-label={t("nav.menu")}
          aria-expanded={moreSheetOpen}
        >
          <NAV_ICONS.more size={ICON.base} aria-hidden="true" />
        </button>
      </nav>

      <ConfirmModal
        open={showLogoutConfirm}
        title={t("nav.signOutTitle")}
        message={t("nav.signOutMessage")}
        confirmLabel={t("nav.signOut")}
        onConfirm={() => {
          setShowLogoutConfirm(false);
          signOut();
        }}
        onCancel={() => setShowLogoutConfirm(false)}
      />
    </div>
  );
}
