import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import i18n from "../../i18n";
import LoginRequestsPage from "./LoginRequestsPage";

vi.mock("../../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() } }));
vi.mock("../../hooks/useSuperAdmin", () => ({ useSuperAdmin: vi.fn() }));

const ROW = {
  id: "req-9",
  user_id: 3,
  email: "who@example.com",
  full_name: "Who Ami",
  status: "pending",
  label: "Android · Chrome",
  location: "Osaka, JP",
  created_at: "2026-11-01T01:00:00Z",
  expires_at: "2026-11-01T01:30:00Z",
};

function renderPage() {
  render(
    <MemoryRouter>
      <LoginRequestsPage />
    </MemoryRouter>,
  );
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
  vi.mocked(api.get).mockReset().mockResolvedValue({ items: [ROW] });
  vi.mocked(api.post).mockReset().mockResolvedValue({ status: "approved" });
});
afterEach(() => cleanup());

it("shows the access-denied message to a non super admin", async () => {
  vi.mocked(useSuperAdmin).mockReturnValue({ isSuperAdmin: false, loading: false } as never);
  renderPage();
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(api.get).not.toHaveBeenCalled();
});

it("lists pending requests and needs a note to approve", async () => {
  vi.mocked(useSuperAdmin).mockReturnValue({ isSuperAdmin: true, loading: false } as never);
  renderPage();
  await screen.findAllByText("Android · Chrome");
  expect(api.get).toHaveBeenCalledWith("/super-admin/login-requests?status=pending");

  fireEvent.click(screen.getAllByRole("button", { name: i18n.t("superAdmin.loginRequests.approve") })[0]);
  const approveButtons = await screen.findAllByRole("button", { name: i18n.t("superAdmin.loginRequests.approve") });
  const confirm = approveButtons[approveButtons.length - 1] as HTMLButtonElement;
  expect(confirm.disabled).toBe(true);

  fireEvent.change(screen.getByLabelText(i18n.t("superAdmin.loginRequests.noteLabel")), {
    target: { value: "confirmed by phone" },
  });
  expect(confirm.disabled).toBe(false);
  fireEvent.click(confirm);
  await waitFor(() =>
    expect(api.post).toHaveBeenCalledWith("/super-admin/login-requests/req-9/approve", { note: "confirmed by phone" }),
  );
});
