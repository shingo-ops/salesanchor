import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import i18n from "../../i18n";
import MetaReviewPage from "./MetaReviewPage";

vi.mock("../../lib/api", () => ({ api: { get: vi.fn(), put: vi.fn() } }));
vi.mock("../../hooks/useSuperAdmin", () => ({ useSuperAdmin: vi.fn() }));

type Status = { tenant_name: string | null; is_on: boolean; until: string | null };

function mockApi(status: Status, items: unknown[] = []) {
  vi.mocked(api.get).mockReset().mockImplementation(async (path: string) =>
    path.endsWith("/logins") ? { items } : status,
  );
}

function renderPage() {
  render(
    <MemoryRouter initialEntries={["/super-admin/users/meta-review"]}>
      <MetaReviewPage />
    </MemoryRouter>,
  );
}

const T = (key: string, opts?: Record<string, unknown>) => i18n.t(`superAdmin.metaReview.${key}`, opts);

beforeEach(async () => {
  await i18n.changeLanguage("en");
  vi.mocked(api.put).mockReset();
  vi.mocked(useSuperAdmin).mockReturnValue({ isSuperAdmin: true, loading: false } as never);
});
afterEach(() => cleanup());

it("shows the access-denied message to a non super admin and does not call the api", async () => {
  vi.mocked(useSuperAdmin).mockReturnValue({ isSuperAdmin: false, loading: false } as never);
  mockApi({ tenant_name: "Review Co", is_on: false, until: null });
  renderPage();
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(api.get).not.toHaveBeenCalled();
});

it("OFF with no until: shows the OFF badge, no auto-off note, and the empty history", async () => {
  mockApi({ tenant_name: "Review Co", is_on: false, until: null });
  renderPage();
  expect(await screen.findByText(T("badgeOff"))).toBeTruthy();
  expect(screen.queryByText(/Turned OFF automatically/)).toBeNull();
  expect(await screen.findByText(T("empty"))).toBeTruthy();
});

it("OFF with a past until: shows that it turned OFF automatically", async () => {
  mockApi({ tenant_name: "Review Co", is_on: false, until: "2026-11-01T01:00:00Z" });
  renderPage();
  expect(await screen.findByText(/Turned OFF automatically at/)).toBeTruthy();
});

it("toggling asks first; cancel does not call put, confirm puts once and turns the badge ON", async () => {
  mockApi({ tenant_name: "Review Co", is_on: false, until: null });
  vi.mocked(api.put).mockResolvedValue({ tenant_name: "Review Co", is_on: true, until: "2026-12-01T01:00:00Z" });
  renderPage();
  await screen.findByText(T("badgeOff"));

  fireEvent.click(screen.getByRole("switch", { name: T("toggleLabel") }));
  expect(await screen.findByText(T("confirmOnTitle"))).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: i18n.t("confirmModal.defaultCancel") }));
  expect(api.put).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("switch", { name: T("toggleLabel") }));
  fireEvent.click(await screen.findByRole("button", { name: T("confirmOn") }));
  await waitFor(() => expect(api.put).toHaveBeenCalledTimes(1));
  expect(api.put).toHaveBeenCalledWith("/super-admin/meta-review", { on: true });
  expect(await screen.findByText(T("badgeOn"))).toBeTruthy();
});

it("history: result badges and reasons are translated, an unknown reason falls back to other", async () => {
  mockApi({ tenant_name: "Review Co", is_on: true, until: "2026-12-01T01:00:00Z" }, [
    { created_at: "2026-11-02T01:00:00Z", email: "a@example.com", path: "/auth/login", status_code: 200, reason: "meta_review", device: "Chrome" },
    { created_at: "2026-11-02T02:00:00Z", email: "b@example.com", path: "/auth/login", status_code: 202, reason: "device_approval_required", device: "Safari" },
    { created_at: "2026-11-02T03:00:00Z", email: "c@example.com", path: "/auth/login", status_code: 401, reason: "weird_code", device: "Edge" },
  ]);
  renderPage();
  expect(await screen.findAllByText(T("resultOk"))).toBeTruthy();
  expect(screen.getAllByText(T("resultPending")).length).toBeGreaterThan(0);
  expect(screen.getAllByText(T("resultNg")).length).toBeGreaterThan(0);
  expect(screen.getAllByText(T("reason.meta_review")).length).toBeGreaterThan(0);
  expect(screen.getAllByText(T("reason.other", { code: "weird_code" })).length).toBeGreaterThan(0);
});
