import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "../../lib/api";
import { usePermissions } from "../../hooks/usePermissions";
import i18n from "../../i18n";
import TenantLoginRequestsPage from "./TenantLoginRequestsPage";

vi.mock("../../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() } }));
vi.mock("../../hooks/usePermissions", () => ({ usePermissions: vi.fn() }));

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
      <TenantLoginRequestsPage />
    </MemoryRouter>,
  );
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
  vi.mocked(api.get).mockReset().mockResolvedValue({ items: [ROW] });
  vi.mocked(api.post).mockReset().mockResolvedValue({ status: "approved" });
});
afterEach(() => cleanup());

it("U1 shows the owner-only message to a non owner and does not call the API", async () => {
  vi.mocked(usePermissions).mockReturnValue({ isTenantOwner: false, loading: false } as never);
  renderPage();
  expect(await screen.findByText(i18n.t("managementCenter.loginRequests.ownerOnly"))).toBeTruthy();
  expect(api.get).not.toHaveBeenCalled();
});

it("U2 lists the company requests for the owner", async () => {
  vi.mocked(usePermissions).mockReturnValue({ isTenantOwner: true, loading: false } as never);
  renderPage();
  await screen.findAllByText(ROW.full_name);
  expect(api.get).toHaveBeenCalledWith("/tenant/login-requests");
});

it("U3 approve needs a note and posts it to the tenant endpoint", async () => {
  vi.mocked(usePermissions).mockReturnValue({ isTenantOwner: true, loading: false } as never);
  renderPage();
  await screen.findAllByText(ROW.full_name);

  fireEvent.click(screen.getAllByRole("button", { name: i18n.t("superAdmin.loginRequests.approve") })[0]);
  const approveButtons = await screen.findAllByRole("button", { name: i18n.t("superAdmin.loginRequests.approve") });
  const confirm = approveButtons[approveButtons.length - 1] as HTMLButtonElement;

  fireEvent.change(screen.getByLabelText(i18n.t("superAdmin.loginRequests.noteLabel")), {
    target: { value: "phone" },
  });
  fireEvent.click(confirm);
  await waitFor(() =>
    expect(api.post).toHaveBeenCalledWith("/tenant/login-requests/req-9/approve", { note: "phone" }),
  );
});
