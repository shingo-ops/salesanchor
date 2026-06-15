import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { NavItemList } from "./NavItemList";
import type { ResolvedNavItem } from "./NavItemList";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

const ICON_STUB = <span data-testid="icon" />;

const ITEMS: ResolvedNavItem[] = [
  { key: "dashboard", labelKey: "nav.dashboard", icon: ICON_STUB, path: "/" },
  { key: "leads", labelKey: "nav.leads", icon: ICON_STUB, path: "/leads" },
];

const ITEMS_WITH_CHILDREN: ResolvedNavItem[] = [
  {
    key: "more",
    labelKey: "nav.more",
    icon: ICON_STUB,
    path: "/more",
    children: [
      { key: "faq", labelKey: "nav.faq", icon: ICON_STUB, path: "/faq" },
      { key: "settings", labelKey: "nav.settings", icon: ICON_STUB, path: "/settings" },
    ],
  },
];

const ITEMS_WITH_UNREAD: ResolvedNavItem[] = [
  { key: "inbox", labelKey: "nav.leadChat", icon: ICON_STUB, path: "/lead-chat", unread: true },
];

function renderList(
  items: ResolvedNavItem[],
  opts: {
    onNavClick?: () => void;
    variant?: "desktop" | "mobile";
    unreadCount?: number;
  } = {},
) {
  const onNavClick = opts.onNavClick ?? vi.fn();
  return render(
    <MemoryRouter>
      <NavItemList
        items={items}
        onNavClick={onNavClick}
        variant={opts.variant ?? "desktop"}
        unreadCount={opts.unreadCount}
      />
    </MemoryRouter>,
  );
}

describe("NavItemList", () => {
  describe("rendering", () => {
    it("renders all nav items", () => {
      renderList(ITEMS);
      expect(screen.getByText("nav.dashboard")).toBeTruthy();
      expect(screen.getByText("nav.leads")).toBeTruthy();
    });

    it("renders children items", () => {
      renderList(ITEMS_WITH_CHILDREN);
      expect(screen.getByText("nav.faq")).toBeTruthy();
      expect(screen.getByText("nav.settings")).toBeTruthy();
    });

    it("renders group label for items with children", () => {
      renderList(ITEMS_WITH_CHILDREN);
      expect(screen.getByText("nav.more")).toBeTruthy();
    });
  });

  describe("onNavClick", () => {
    it("calls onNavClick when a nav item is clicked", () => {
      const onNavClick = vi.fn();
      renderList(ITEMS, { onNavClick });
      fireEvent.click(screen.getByText("nav.dashboard"));
      expect(onNavClick).toHaveBeenCalledTimes(1);
    });

    it("calls onNavClick when a child nav item is clicked", () => {
      const onNavClick = vi.fn();
      renderList(ITEMS_WITH_CHILDREN, { onNavClick });
      fireEvent.click(screen.getByText("nav.faq"));
      expect(onNavClick).toHaveBeenCalledTimes(1);
    });
  });

  describe("variant", () => {
    it("applies desktop class when variant=desktop", () => {
      const { container } = renderList(ITEMS, { variant: "desktop" });
      expect(container.querySelector(".nav-item-list--desktop")).toBeTruthy();
    });

    it("applies mobile class when variant=mobile", () => {
      const { container } = renderList(ITEMS, { variant: "mobile" });
      expect(container.querySelector(".nav-item-list--mobile")).toBeTruthy();
    });
  });

  describe("unread badge", () => {
    it("shows badge when item.unread=true and unreadCount > 0", () => {
      renderList(ITEMS_WITH_UNREAD, { unreadCount: 3 });
      expect(screen.getByText("3")).toBeTruthy();
    });

    it("does not show badge when unreadCount=0", () => {
      renderList(ITEMS_WITH_UNREAD, { unreadCount: 0 });
      expect(screen.queryByText("0")).toBeNull();
    });

    it("does not show badge when item.unread is not set", () => {
      renderList(ITEMS, { unreadCount: 5 });
      expect(screen.queryByText("5")).toBeNull();
    });
  });
});
