import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import DesktopShell from "./DesktopShell";

const { mockHasPermission, mockHasAny } = vi.hoisted(() => ({
  mockHasPermission: vi.fn<(perm: string) => boolean>(() => false),
  mockHasAny: vi.fn<(...keys: string[]) => boolean>(() => false),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
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
    prefs: { show_chat_menu: false, show_sales_menu: false },
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

vi.mock("../hooks/useSSE", () => ({
  useSSE: () => undefined,
}));

vi.mock("../lib/messages", () => ({
  listConversations: vi.fn().mockResolvedValue({ conversations: [] }),
}));

vi.mock("../constants/icons", () => {
  const Icon = ({ size }: { size?: number }) => <span data-testid="icon" data-size={size} />;
  return {
    NAV_ICONS: {
      close: Icon,
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
      logout: Icon,
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

function renderDesktopShell() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <DesktopShell />
    </MemoryRouter>,
  );
}

describe("DesktopShell", () => {
  beforeEach(() => {
    mockHasPermission.mockImplementation((perm: string) => perm === "dashboard.view" || perm === "schedule.view");
    mockHasAny.mockReturnValue(false);
  });

  it("keeps the sidebar collapsed after nav click until mouse leaves", async () => {
    const { container } = renderDesktopShell();
    const sidebar = container.querySelector("#sidebar-panel");
    expect(sidebar).toBeTruthy();

    fireEvent.mouseEnter(sidebar!);
    expect(container.querySelector(".sidebar-expanded")).toBeTruthy();

    fireEvent.click(screen.getByRole("link", { name: "nav.schedule" }));
    expect(container.querySelector(".sidebar-expanded")).toBeNull();
    expect(sidebar?.classList.contains("sidebar-hover-suppressed")).toBe(true);

    fireEvent.mouseEnter(sidebar!);
    expect(container.querySelector(".sidebar-expanded")).toBeNull();

    fireEvent.mouseLeave(sidebar!);
    fireEvent.mouseEnter(sidebar!);
    await waitFor(() => {
      expect(container.querySelector(".sidebar-expanded")).toBeTruthy();
    });
    expect(sidebar?.classList.contains("sidebar-hover-suppressed")).toBe(false);
  });
});
