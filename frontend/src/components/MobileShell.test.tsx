/**
 * MobileShell unit tests（PR-R2-B）
 *
 * テスト対象:
 *   - rendering: MobileTopBar / NavItemList が描画される
 *   - drawer open/close: hamburger click で open、backdrop click で close
 *   - Escape key: keydown Escape で drawer close
 *   - nav click: onNavClick で drawer close
 *   - unread badge: unreadCount > 0 時に leadChat item のバッジ表示
 *   - navLoading: permsLoading=true 時に items が空
 *
 * 参照: docs/handoff/mobile-shell-pr-r2b/design.md §KPI-1
 */

import { render, screen, fireEvent, act, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import MobileShell from "./MobileShell";

// ─── モック群（vi.hoisted で hoisting 安全化） ──────────────────────────────

const {
  mockHasPermission,
  mockHasAny,
  mockLoadUnread,
} = vi.hoisted(() => ({
  mockHasPermission: vi.fn(() => false),
  mockHasAny: vi.fn(() => false),
  mockLoadUnread: vi.fn(),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    Outlet: () => <div data-testid="outlet" />,
    useNavigate: () => vi.fn(),
  };
});

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({
    user: { email: "test@example.com" },
    signOut: vi.fn(),
  }),
}));

vi.mock("../contexts/LocaleContext", () => ({
  useLocale: () => ({ locale: "ja", changeLanguage: vi.fn() }),
}));

vi.mock("../contexts/ThemeContext", () => ({
  useTheme: () => ({ theme: "light", changeTheme: vi.fn() }),
}));

vi.mock("../contexts/UiPrefsContext", () => ({
  useUiPrefs: () => ({
    prefs: { show_chat_menu: true, show_sales_menu: false },
    loading: false,
    staffName: "Test Staff",
  }),
}));

vi.mock("../hooks/usePermissions", () => ({
  usePermissions: () => ({
    hasPermission: mockHasPermission,
    hasAny: mockHasAny,
    loading: false,
  }),
}));

vi.mock("../hooks/useSuperAdmin", () => ({
  useSuperAdmin: () => ({ isSuperAdmin: false }),
}));

vi.mock("../hooks/usePageTitle", () => ({
  usePageTitle: () => "Dashboard",
}));

vi.mock("../lib/messages", () => ({
  listConversations: mockLoadUnread,
}));

vi.mock("../hooks/useSSE", () => ({
  useSSE: () => undefined,
}));

vi.mock("../constants/icons", () => {
  const Icon = ({ size }: { size?: number }) => (
    <span data-testid="icon" data-size={size} />
  );
  return {
    NAV_ICONS: {
      menu: Icon,
      close: Icon,
      logout: Icon,
      dashboard: Icon,
      schedule: Icon,
      inventory: Icon,
      purchaseOrders: Icon,
      fileText: Icon,
      leads: Icon,
      orders: Icon,
      sales: Icon,
      commissions: Icon,
      admin: Icon,
      saasAdmin: Icon,
      chevronDown: Icon,
      more: Icon,
    },
    THEME_ICONS: { light: Icon, dark: Icon },
    GlobeIcon: Icon,
    LeadChatIcon: Icon,
    ACCOUNT_ICONS: { profile: Icon },
  };
});

vi.mock("../constants/iconSizes", () => ({
  ICON: { base: 20, md: 16, sm: 14 },
}));

vi.mock("./ConfirmModal", () => ({
  default: () => null,
}));

// ─── ヘルパー ─────────────────────────────────────────────────────────────────

function renderMobileShell() {
  return render(
    <MemoryRouter>
      <MobileShell />
    </MemoryRouter>,
  );
}

// ─── テスト ──────────────────────────────────────────────────────────────────

describe("MobileShell", () => {
  beforeEach(() => {
    mockLoadUnread.mockResolvedValue({ conversations: [] });
    mockHasPermission.mockReturnValue(false);
    mockHasAny.mockReturnValue(false);
  });

  describe("rendering", () => {
    it("renders MobileTopBar with hamburger, pageTitle and avatar", () => {
      renderMobileShell();
      expect(
        screen.getByRole("button", { name: "nav.openDrawer" }),
      ).toBeTruthy();
      expect(screen.getByText("Dashboard")).toBeTruthy();
      expect(
        screen.getByRole("button", { name: "nav.openUserMenu" }),
      ).toBeTruthy();
    });

    it("renders Outlet", () => {
      renderMobileShell();
      expect(screen.getByTestId("outlet")).toBeTruthy();
    });

    it("MobileDrawer is hidden on initial render (no open class)", () => {
      const { container } = renderMobileShell();
      const drawer = container.querySelector(".mobile-drawer");
      expect(drawer?.classList.contains("mobile-drawer--open")).toBe(false);
    });

    it("NavItemList variant=mobile is rendered inside MobileDrawer", () => {
      const { container } = renderMobileShell();
      expect(container.querySelector(".nav-item-list--mobile")).toBeTruthy();
    });
  });

  describe("drawer open/close", () => {
    it("hamburger click opens drawer", () => {
      const { container } = renderMobileShell();
      const hamburger = screen.getByRole("button", { name: "nav.openDrawer" });
      fireEvent.click(hamburger);
      const drawer = container.querySelector(".mobile-drawer");
      expect(drawer?.classList.contains("mobile-drawer--open")).toBe(true);
    });

    it("backdrop is visible when drawer is open", () => {
      const { container } = renderMobileShell();
      fireEvent.click(screen.getByRole("button", { name: "nav.openDrawer" }));
      expect(container.querySelector(".mobile-drawer-backdrop")).toBeTruthy();
    });

    it("backdrop click closes drawer", () => {
      const { container } = renderMobileShell();
      fireEvent.click(screen.getByRole("button", { name: "nav.openDrawer" }));
      const backdrop = container.querySelector(".mobile-drawer-backdrop");
      expect(backdrop).toBeTruthy();
      fireEvent.click(backdrop!);
      const drawer = container.querySelector(".mobile-drawer");
      expect(drawer?.classList.contains("mobile-drawer--open")).toBe(false);
    });

    it("close button click closes drawer", () => {
      const { container } = renderMobileShell();
      fireEvent.click(screen.getByRole("button", { name: "nav.openDrawer" }));
      const closeBtn = screen.getByRole("button", { name: "nav.closeDrawer" });
      fireEvent.click(closeBtn);
      const drawer = container.querySelector(".mobile-drawer");
      expect(drawer?.classList.contains("mobile-drawer--open")).toBe(false);
    });
  });

  describe("Escape key", () => {
    it("Escape keydown closes drawer", () => {
      const { container } = renderMobileShell();
      fireEvent.click(screen.getByRole("button", { name: "nav.openDrawer" }));
      fireEvent.keyDown(document, { key: "Escape" });
      const drawer = container.querySelector(".mobile-drawer");
      expect(drawer?.classList.contains("mobile-drawer--open")).toBe(false);
    });

    it("Escape keydown when drawer is closed does not throw", () => {
      const { container } = renderMobileShell();
      fireEvent.keyDown(document, { key: "Escape" });
      const drawer = container.querySelector(".mobile-drawer");
      expect(drawer?.classList.contains("mobile-drawer--open")).toBe(false);
    });
  });

  describe("nav click", () => {
    it("clicking nav item closes drawer", () => {
      mockHasPermission.mockReturnValue(false);
      const { container } = renderMobileShell();
      fireEvent.click(screen.getByRole("button", { name: "nav.openDrawer" }));
      expect(
        container.querySelector(".mobile-drawer--open"),
      ).toBeTruthy();

      // schedule is shown without permission gate
      const scheduleLink = screen.getByText("nav.schedule");
      fireEvent.click(scheduleLink);
      expect(
        container.querySelector(".mobile-drawer--open"),
      ).toBeNull();
    });
  });

  describe("unread badge", () => {
    it("shows badge on leadChat item when unreadCount > 0", async () => {
      mockLoadUnread.mockResolvedValue({
        conversations: [{ id: 1 }, { id: 2 }, { id: 3 }],
      });

      renderMobileShell();

      await waitFor(() => {
        expect(screen.getByText("3")).toBeTruthy();
      });
    });

    it("does not show badge when unreadCount = 0", async () => {
      mockLoadUnread.mockResolvedValue({ conversations: [] });

      renderMobileShell();

      await act(async () => {});
      expect(screen.queryByText("0")).toBeNull();
    });
  });

  describe("permission filtering", () => {
    it("schedule item is visible without any permissions", () => {
      renderMobileShell();
      expect(screen.getByText("nav.schedule")).toBeTruthy();
    });

    it("dashboard item is hidden when dashboard.view permission is denied", () => {
      mockHasPermission.mockReturnValue(false);
      renderMobileShell();
      expect(screen.queryByText("nav.dashboard")).toBeNull();
    });

    it("dashboard item is shown when dashboard.view permission is granted", () => {
      mockHasPermission.mockReturnValue(true);
      renderMobileShell();
      expect(screen.getByText("nav.dashboard")).toBeTruthy();
    });
  });
});
