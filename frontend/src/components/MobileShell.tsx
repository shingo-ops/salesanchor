/**
 * MobileShell — モバイル専用 Shell コンポーネント（PR-R2-B）
 *
 * ADR-137: MobileShell は DesktopShell（Layout.tsx）とは独立した DOM。
 *   PR-R2-B 段階では App.tsx に接続しない（PR-R2-C で接続）。
 * ADR-067: 色・余白・z-index はすべて CSS token 参照。hex / px マジックナンバー禁止。
 * ADR-027: 全 UI 文字列は t("key") 経由。ハードコード禁止。
 *
 * DOM 構造:
 *   MobileShell (.mobile-shell)
 *   ├── MobileTopBar (.mobile-topbar — sticky, z-index: var(--z-topbar)=100)
 *   │   ├── HamburgerButton (.mobile-topbar-hamburger, aria-controls="mobile-drawer")
 *   │   ├── PageTitle (span.mobile-topbar-title)
 *   │   └── AvatarButton (.mobile-topbar-avatar — in-flow, NOT position:fixed)
 *   ├── MobileDrawerBackdrop (.mobile-drawer-backdrop — z-index: var(--z-sidebar)=200)
 *   ├── MobileDrawer (.mobile-drawer — z-index: var(--z-sidebar-overlay)=210 ★Backdropより前面★)
 *   │   └── NavItemList variant="mobile"
 *   └── .mobile-content
 *       └── <Outlet />
 *
 * z-index 前後関係:
 *   MobileDrawer(210) > MobileDrawerBackdrop(200) > コンテンツ
 *   Backdrop が Drawer を覆うとクリック不能になる → 必ず Drawer を前面に
 *
 * 参照: docs/handoff/mobile-shell-pr-r2b/design.md
 */

import { useCallback, useEffect, useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
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

  // ── ドロワー状態 ──
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [userDrawerOpen, setUserDrawerOpen] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  const openDrawer = () => setDrawerOpen(true);
  const closeDrawer = () => setDrawerOpen(false);

  // Escape key でナビドロワーを閉じる
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && drawerOpen) closeDrawer();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [drawerOpen]);

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

  // ── レンダリング ──

  return (
    <div className="mobile-shell">
      {/* ============ MobileTopBar ============ */}
      <div className="mobile-topbar">
        <button
          className="mobile-topbar-hamburger"
          onClick={openDrawer}
          aria-label={t("nav.openDrawer")}
          aria-expanded={drawerOpen}
          aria-controls="mobile-drawer"
        >
          <NAV_ICONS.menu size={ICON.md} aria-hidden="true" />
        </button>

        <span className="mobile-topbar-title">{pageTitle}</span>

        <button
          className="mobile-topbar-avatar"
          onClick={() => setUserDrawerOpen(true)}
          aria-label={t("nav.openUserMenu")}
          data-tooltip={t("nav.openUserMenu")}
        >
          {user?.email ? user.email[0].toUpperCase() : <NAV_ICONS.logout size={18} aria-hidden="true" />}
        </button>
      </div>

      {/* ============ MobileDrawerBackdrop（Drawer より背面: z-index 200） ============ */}
      {drawerOpen && (
        <div
          className="mobile-drawer-backdrop"
          onClick={closeDrawer}
          aria-hidden="true"
        />
      )}

      {/* ============ MobileDrawer（Backdropより前面: z-index 210） ============ */}
      <div
        id="mobile-drawer"
        className={`mobile-drawer${drawerOpen ? " mobile-drawer--open" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={t("nav.openDrawer")}
      >
        <div className="mobile-drawer-header">
          <img src="/favicon.png" alt="Sales Anchor" className="mobile-drawer-logo" />
          <button
            className="mobile-drawer-close"
            onClick={closeDrawer}
            aria-label={t("nav.closeDrawer")}
          >
            <NAV_ICONS.close size={ICON.md} aria-hidden="true" />
          </button>
        </div>

        <div className="mobile-drawer-nav">
          <NavItemList
            variant="mobile"
            items={resolvedItems}
            onNavClick={closeDrawer}
            unreadCount={unreadCount}
          />
        </div>
      </div>

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

      {/* ============ Outlet ============ */}
      <main className="mobile-content">
        <Outlet />
      </main>
    </div>
  );
}
