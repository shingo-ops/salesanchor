/**
 * MobileShell — モバイル専用 Shell コンポーネント（ADR-140 PR-B）
 *
 * ADR-137: MobileShell は DesktopShell（Layout.tsx）とは独立した DOM。
 * ADR-140: ハンバーガー+Drawer → 下部タブバー（主役4タブ＋「もっと」シート）に刷新。
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
 *   │   └── NavItemList variant="mobile"（脇役全項目）
 *   ├── MobileTabBar (.mobile-tabbar — position:fixed, bottom:0, z-index: var(--z-topbar)=100)
 *   │   ├── NavLink(ホーム: /)
 *   │   ├── NavLink(受信箱: /lead-chat) — prefs.show_chat_menu 条件付き
 *   │   ├── NavLink(受注管理: /orders) — orders.view 権限
 *   │   ├── NavLink(在庫: /inventory) — products.view 権限
 *   │   ├── MoreButton（「もっと」シート開閉）
 *   │   └── AvatarButton（ユーザーメニュー）
 *   ├── User drawer backdrop
 *   ├── User drawer panel
 *   └── ConfirmModal（ログアウト確認）
 *
 * 参照: docs/handoff/mobile-responsive/design.md §B-2
 */

import { useCallback, useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../contexts/AuthContext";
import { useLocale } from "../contexts/LocaleContext";
import { useTheme } from "../contexts/ThemeContext";
import { useUiPrefs } from "../contexts/UiPrefsContext";
import { usePermissions } from "../hooks/usePermissions";
import { useSuperAdmin } from "../hooks/useSuperAdmin";
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
import type { NavItem } from "../types/nav";
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

function navItemsToResolved(items: NavItem[]): ResolvedNavItem[] {
  return items.map((item) =>
    resolveItem(item.to, item.labelKey, <span />, item.to),
  );
}

// 主役タブの key セット（more sheet から除外）
const MAIN_TAB_KEYS = new Set(["dashboard", "leadChat", "inventory", "orders"]);

// ─── MobileShell ─────────────────────────────────────────────────────────────

export default function MobileShell() {
  const { t } = useTranslation();
  const { locale, changeLanguage } = useLocale();
  const { theme, changeTheme } = useTheme();
  const { user, signOut } = useAuth();
  const { hasPermission, hasAny, loading: permsLoading } = usePermissions();
  const { isSuperAdmin } = useSuperAdmin();
  const { prefs, loading: uiPrefsLoading, staffName } = useUiPrefs();
  const navigate = useNavigate();
  const pageTitle = usePageTitle();

  const navLoading = permsLoading || uiPrefsLoading;

  // ── シート/ドロワー状態 ──
  const [moreSheetOpen, setMoreSheetOpen] = useState(false);
  const [userDrawerOpen, setUserDrawerOpen] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  // Escape key で「もっと」シートを閉じる
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

  const showManagementCenter = hasAny(
    "staff.view",
    "teams.view",
    "roles.view",
    "bots.view",
    "shifts.view",
    "channels.view",
    "erp.view",
    "orders.view",
    "customers.view",
    "deals.view",
    "suppliers.view",
    "purchase_orders.view",
    "tenant.profile.view",
  );

  const saasAdminNavItems: NavItem[] = isSuperAdmin
    ? [
        { to: "/super-admin/masters", labelKey: "nav.superAdminMasters" },
        { to: "/super-admin/inbound", labelKey: "nav.superAdminInbound" },
        {
          to: "/super-admin/inventory-offers",
          labelKey: "nav.superAdminInventoryOffers",
        },
        {
          to: "/super-admin/phase-switch",
          labelKey: "nav.superAdminPhaseSwitch",
        },
      ]
    : [];

  const resolvedItems: ResolvedNavItem[] = navLoading
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
        ...(prefs.show_chat_menu
          ? [
              resolveItem(
                "leadChat",
                "nav.leadChat",
                <LeadChatIcon size={ICON.base} aria-hidden="true" />,
                "/lead-chat",
                { unread: true },
              ),
            ]
          : []),
        ...(hasPermission("products.view")
          ? [
              resolveItem(
                "inventory",
                "nav.inventory",
                <NAV_ICONS.inventory size={ICON.base} aria-hidden="true" />,
                "/inventory",
              ),
            ]
          : []),
        ...(hasPermission("purchase_orders.view")
          ? [
              resolveItem(
                "purchaseOrders",
                "nav.purchaseOrders",
                <NAV_ICONS.purchaseOrders size={ICON.base} aria-hidden="true" />,
                "/purchase-orders",
              ),
            ]
          : []),
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
        ...(hasPermission("orders.view")
          ? [
              resolveItem(
                "orders",
                "nav.orders",
                <NAV_ICONS.orders size={ICON.base} aria-hidden="true" />,
                "/orders",
              ),
              resolveItem(
                "sales",
                "nav.sales",
                <NAV_ICONS.sales size={ICON.base} aria-hidden="true" />,
                "/sales",
              ),
              resolveItem(
                "commissions",
                "nav.commissions",
                <NAV_ICONS.commissions size={ICON.base} aria-hidden="true" />,
                "/commissions",
              ),
            ]
          : []),
        ...(showManagementCenter
          ? [
              resolveItem(
                "managementCenter",
                "nav.managementCenter",
                <NAV_ICONS.admin size={ICON.base} aria-hidden="true" />,
                "/management-center",
              ),
            ]
          : []),
        ...(isSuperAdmin
          ? [
              resolveItem(
                "saasAdmin",
                "nav.saasAdmin",
                <NAV_ICONS.saasAdmin size={ICON.base} aria-hidden="true" />,
                "/super-admin",
                { children: navItemsToResolved(saasAdminNavItems) },
              ),
            ]
          : []),
      ];

  // 「もっと」シート用: 主役タブ4つを除いた残り
  const moreItems = resolvedItems.filter((item) => !MAIN_TAB_KEYS.has(item.key));

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
        aria-label={t("nav.mobileMore")}
      >
        <NavItemList
          variant="mobile"
          items={moreItems}
          onNavClick={() => setMoreSheetOpen(false)}
          unreadCount={unreadCount}
        />
      </div>

      {/* ============ MobileTabBar（fixed bottom） ============ */}
      <nav className="mobile-tabbar" aria-label={t("nav.openMenu")}>
        {/* ホーム */}
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            `mobile-tab${isActive ? " mobile-tab--active" : ""}`
          }
          aria-label={t("nav.dashboard")}
        >
          <NAV_ICONS.dashboard size={ICON.base} aria-hidden="true" />
          <span className="mobile-tab-label">{t("nav.dashboard")}</span>
        </NavLink>

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

        {/* もっと */}
        <button
          className="mobile-tab"
          onClick={() => setMoreSheetOpen(true)}
          aria-label={t("nav.mobileMore")}
          aria-expanded={moreSheetOpen}
        >
          <NAV_ICONS.more size={ICON.base} aria-hidden="true" />
          <span className="mobile-tab-label">{t("nav.mobileMore")}</span>
        </button>

        {/* アバター（ユーザーメニュー） */}
        <button
          className="mobile-tab mobile-tab-avatar"
          onClick={() => setUserDrawerOpen(true)}
          aria-label={t("nav.openUserMenu")}
        >
          <span className="mobile-tab-avatar-icon">
            {user?.email ? user.email[0].toUpperCase() : <NAV_ICONS.logout size={18} aria-hidden="true" />}
          </span>
        </button>
      </nav>

      {/* ============ User drawer backdrop ============ */}
      {userDrawerOpen && (
        <div
          className="user-drawer-backdrop"
          onClick={() => setUserDrawerOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* ============ User drawer panel ============ */}
      <div
        className={`user-drawer${userDrawerOpen ? " user-drawer--open" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={t("nav.account")}
      >
        <div className="user-drawer-header">
          <span className="user-drawer-title">{t("nav.account")}</span>
          <button
            className="user-drawer-close"
            onClick={() => setUserDrawerOpen(false)}
            aria-label={t("common.close")}
            data-tooltip={t("common.close")}
          >
            <NAV_ICONS.close size={ICON.md} aria-hidden="true" />
          </button>
        </div>
        <div className="user-drawer-body">
          <div className="user-drawer-email">{user?.email}</div>
          {staffName && <div className="user-drawer-name">{staffName}</div>}

          <button
            className="user-drawer-action"
            onClick={() => {
              setUserDrawerOpen(false);
              navigate("/account/settings");
            }}
          >
            <ACCOUNT_ICONS.profile size={ICON.md} aria-hidden="true" />
            <span>{t("nav.accountSettings")}</span>
          </button>

          <hr className="user-drawer-sep" />

          <button
            className="user-drawer-action"
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
            className="user-drawer-action"
            onClick={() => changeLanguage(locale === "ja" ? "en" : "ja")}
          >
            <GlobeIcon size={ICON.md} aria-hidden="true" />
            <span>{locale === "ja" ? t("language.en") : t("language.ja")}</span>
          </button>

          <button
            className="user-drawer-action user-drawer-action--danger"
            onClick={() => {
              setUserDrawerOpen(false);
              setShowLogoutConfirm(true);
            }}
          >
            <NAV_ICONS.logout size={ICON.md} aria-hidden="true" />
            <span>{t("nav.signOut")}</span>
          </button>
        </div>
      </div>

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
