/**
 * MobileShell unit tests（ADR-140 PR-B）
 *
 * テスト対象:
 *   - rendering: MobileTopBar / MobileTabBar / NavItemList が描画される
 *   - menu sheet open/close: 「…」ボタン click で open、backdrop click で close
 *   - Escape key: keydown Escape で more sheet close
 *   - nav click: onNavClick で more sheet close
 *   - unread badge: unreadCount > 0 時に tabbar の受信箱バッジ表示
 *   - permission filtering: 権限に応じてタブ・more sheet 項目が変わる
 *
 * 参照: docs/handoff/mobile-responsive/design.md §B-2
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
    prefs: { show_chat_menu: true, show_sales_menu: true },
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
    it("renders MobileTopBar with pageTitle", () => {
      renderMobileShell();
      expect(screen.getByText("Dashboard")).toBeTruthy();
    });

    it("renders Outlet", () => {
      renderMobileShell();
      expect(screen.getByTestId("outlet")).toBeTruthy();
    });

    it("renders .mobile-tabbar", () => {
      const { container } = renderMobileShell();
      expect(container.querySelector(".mobile-tabbar")).toBeTruthy();
    });

    it("renders menu button in tabbar", () => {
      renderMobileShell();
      expect(
        screen.getByRole("button", { name: "nav.menu" }),
      ).toBeTruthy();
    });

    it("renders 4 bottom tabs when permissions exist", () => {
      mockHasPermission.mockReturnValue(true);

      renderMobileShell();

      expect(
        document.querySelectorAll(".mobile-tabbar .mobile-tab").length,
      ).toBe(4);
    });

    it("more sheet is not open on initial render", () => {
      const { container } = renderMobileShell();
      expect(container.querySelector(".mobile-more-sheet--open")).toBeNull();
    });

    it("NavItemList variant=mobile is rendered inside more sheet", () => {
      const { container } = renderMobileShell();
      expect(container.querySelector(".nav-item-list--mobile")).toBeTruthy();
    });
  });

  describe("more sheet open/close", () => {
    it("menu button click opens more sheet", () => {
      const { container } = renderMobileShell();
      fireEvent.click(screen.getByRole("button", { name: "nav.menu" }));
      expect(container.querySelector(".mobile-more-sheet--open")).toBeTruthy();
    });

    it("menu sheet renders 5 navigation items", () => {
      mockHasPermission.mockReturnValue(true);
      const { container } = renderMobileShell();
      fireEvent.click(screen.getByRole("button", { name: "nav.menu" }));

      expect(
        container.querySelectorAll(".mobile-more-sheet--open .nav-item-list__item").length,
      ).toBe(5);
    });

    it("backdrop is visible when more sheet is open", () => {
      const { container } = renderMobileShell();
      fireEvent.click(screen.getByRole("button", { name: "nav.menu" }));
      expect(container.querySelector(".mobile-more-backdrop")).toBeTruthy();
    });

    it("backdrop click closes more sheet", () => {
      const { container } = renderMobileShell();
      fireEvent.click(screen.getByRole("button", { name: "nav.menu" }));
      const backdrop = container.querySelector(".mobile-more-backdrop");
      expect(backdrop).toBeTruthy();
      fireEvent.click(backdrop!);
      expect(container.querySelector(".mobile-more-sheet--open")).toBeNull();
    });
  });

  describe("Escape key", () => {
    it("Escape keydown closes more sheet when open", () => {
      const { container } = renderMobileShell();
      fireEvent.click(screen.getByRole("button", { name: "nav.menu" }));
      expect(container.querySelector(".mobile-more-sheet--open")).toBeTruthy();
      fireEvent.keyDown(document, { key: "Escape" });
      expect(container.querySelector(".mobile-more-sheet--open")).toBeNull();
    });

    it("Escape keydown when more sheet is closed does not throw", () => {
      const { container } = renderMobileShell();
      fireEvent.keyDown(document, { key: "Escape" });
      expect(container.querySelector(".mobile-more-sheet--open")).toBeNull();
    });
  });

  describe("nav click in more sheet", () => {
    it("clicking nav item in more sheet closes it", () => {
      mockHasPermission.mockReturnValue(true);
      const { container } = renderMobileShell();
      fireEvent.click(screen.getByRole("button", { name: "nav.menu" }));
      expect(container.querySelector(".mobile-more-sheet--open")).toBeTruthy();

      // schedule is shown without permission gate (in menu sheet)
      const scheduleLink = screen.getByText("nav.schedule");
      fireEvent.click(scheduleLink);
      expect(container.querySelector(".mobile-more-sheet--open")).toBeNull();
    });
  });

  describe("unread badge", () => {
    it("shows badge on leadChat tab when unreadCount > 0", async () => {
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
    it("schedule item is visible in menu sheet without any permissions", () => {
      renderMobileShell();
      expect(screen.getByText("nav.schedule")).toBeTruthy();
    });

    it("dashboard tab is hidden from bottom tabs when dashboard.view permission is denied", () => {
      mockHasPermission.mockReturnValue(false);
      renderMobileShell();
      expect(
        screen.queryByRole("link", { name: "nav.dashboard" }),
      ).toBeNull();
    });

    it("dashboard item is shown in menu sheet when dashboard.view permission is granted", () => {
      mockHasPermission.mockReturnValue(true);
      renderMobileShell();
      fireEvent.click(screen.getByRole("button", { name: "nav.menu" }));
      expect(screen.getByRole("link", { name: "nav.dashboard" })).toBeTruthy();
    });
  });
});
