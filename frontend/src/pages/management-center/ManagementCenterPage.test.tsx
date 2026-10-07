import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
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

const PAGES = {
  "discord-config": "Discord Integration",
  "discord-announce": "Discord Announce",
  "tenant-policy": "Tenant Policy",
  "channel-masters": "Channel Management",
};

const view = (path: string) =>
  render(
    <MemoryRouter initialEntries={[`/management-center/${path}`]}>
      <Routes>
        <Route path="/management-center" element={<ManagementCenterPage />}>
          {Object.keys(PAGES).concat("staff").map((p) => (
            <Route key={p} path={p} element={<div data-testid="child">{p}</div>} />
          ))}
        </Route>
      </Routes>
    </MemoryRouter>,
  );

it("links the 4 admin pages under the management-center layout", () => {
  mockPermissions(true);
  view("staff");
  for (const [path, label] of Object.entries(PAGES)) {
    expect(screen.getByRole("link", { name: label }).getAttribute("href")).toBe(`/management-center/${path}`);
  }
});

it.each(Object.entries(PAGES))("keeps the left menu and highlights %s when opened", (path, label) => {
  mockPermissions(true);
  view(path);
  expect(screen.getByTestId("child").textContent).toBe(path);
  const link = screen.getByRole("link", { name: label });
  expect(link.className).toContain("comp-subnav__item--active");
  expect(screen.getAllByRole("link").length).toBeGreaterThan(4);
});

it("hides the admin page entries without permission", () => {
  mockPermissions(false);
  view("staff");
  for (const label of Object.values(PAGES)) {
    expect(screen.queryByRole("link", { name: label })).toBeNull();
  }
});
