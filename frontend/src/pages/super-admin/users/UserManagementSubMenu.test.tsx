import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import i18n from "../../../i18n";
import { UserManagementSubMenu, type UserMenuStatus } from "./UserManagementSubMenu";

const label = (k: UserMenuStatus) => (k === "all" ? "All" : k);

function Where() {
  const loc = useLocation();
  return <output data-testid="where">{loc.pathname + loc.search}</output>;
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
});
afterEach(() => cleanup());

// K7: the viewer group (all + statuses) and, below it, one login approvals link.
it("shows the viewer group with counts and one login approvals link", () => {
  render(
    <MemoryRouter initialEntries={["/super-admin/users/viewers"]}>
      <UserManagementSubMenu activeKey="all" counts={{ all: 5, pending: 1, trial: 1, active: 2 }} onChange={vi.fn()} statusLabel={label} />
    </MemoryRouter>,
  );
  expect(screen.getByText(i18n.t("superAdmin.users.groupViewers"))).toBeTruthy();
  expect(["All", "pending", "trial", "active"].map(n => screen.getByRole("button", { name: new RegExp(`^${n}`) }).textContent)).toEqual([
    "All5", "pending1", "trial1", "active2",
  ]);
  const link = screen.getByRole("link", { name: i18n.t("nav.superAdminLoginRequests") });
  expect(link.getAttribute("href")).toBe("/super-admin/users/login-requests");
});

it("on the login screen it shows no counts and a status moves to the viewers screen", () => {
  render(
    <MemoryRouter initialEntries={["/super-admin/users/login-requests"]}>
      <Routes>
        <Route path="/super-admin/users/login-requests" element={<><UserManagementSubMenu statusLabel={label} /><Where /></>} />
        <Route path="/super-admin/users/viewers" element={<Where />} />
      </Routes>
    </MemoryRouter>,
  );
  expect(screen.getByRole("button", { name: "trial" }).textContent).toBe("trial");
  expect(screen.getByRole("link", { name: i18n.t("nav.superAdminLoginRequests") }).className).toContain("comp-subnav__item--active");
  fireEvent.click(screen.getByRole("button", { name: "trial" }));
  expect(screen.getByTestId("where").textContent).toBe("/super-admin/users/viewers?status=trial");
});

it("the All status goes to the viewers screen without a query", () => {
  render(
    <MemoryRouter initialEntries={["/super-admin/users/login-requests"]}>
      <Routes>
        <Route path="/super-admin/users/login-requests" element={<UserManagementSubMenu statusLabel={label} />} />
        <Route path="/super-admin/users/viewers" element={<Where />} />
      </Routes>
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByRole("button", { name: "All" }));
  expect(screen.getByTestId("where").textContent).toBe("/super-admin/users/viewers");
});
