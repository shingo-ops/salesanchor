import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { usePermissions } from "../../hooks/usePermissions";
import i18n from "../../i18n";
import ManagementCenterPage from "./ManagementCenterPage";

vi.mock("../../hooks/usePermissions", () => ({ usePermissions: vi.fn() }));

const mockPermissions = (allowed: boolean) =>
  vi.mocked(usePermissions).mockReturnValue({
    loading: false, hasPermission: () => allowed, hasAny: () => allowed,
  } as unknown as ReturnType<typeof usePermissions>);

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
});
afterEach(() => cleanup());

const view = () => render(<MemoryRouter initialEntries={["/management-center/staff"]}><ManagementCenterPage /></MemoryRouter>);

it("links the 4 admin pages that had no entry point", () => {
  mockPermissions(true);
  view();
  const hrefs: Record<string, string> = {
    "Discord Integration": "/admin/discord-config",
    "Discord Announce": "/admin/discord-announce",
    "Tenant Policy": "/admin/tenant-policy",
    "Channel Management": "/admin/channel-masters",
  };
  for (const [label, href] of Object.entries(hrefs)) {
    const link = screen.getByRole("link", { name: label });
    expect(link.getAttribute("href")).toBe(href);
  }
});

it("hides the admin page entries without permission", () => {
  mockPermissions(false);
  view();
  expect(document.querySelector('a[href^="/admin/"]')).toBeNull();
});
