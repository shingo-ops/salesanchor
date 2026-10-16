import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api, ApiError } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import i18n from "../../i18n";
import ViewerAccountsPage from "./ViewerAccountsPage";

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, api: { get: vi.fn(), post: vi.fn() } };
});
vi.mock("../../hooks/useSuperAdmin", () => ({ useSuperAdmin: vi.fn() }));

const v = (over: Record<string, unknown>) => ({
  id: 1,
  email: "t1@example.com",
  line_name: "Taro",
  inventory_issue: null,
  status: "trial",
  trial_expires_at: "2026-11-01T00:00:00Z",
  created_at: "2026-10-01T00:00:00Z",
  discord_user_id: null,
  discord_channel_id: null,
  flag_many_ips: false,
  flag_shared_ip: false,
  ...over,
});

const ITEMS = [
  v({ id: 1, status: "trial", flag_many_ips: true }),
  v({ id: 2, email: "s2@example.com", line_name: "Sato", status: "suspended", trial_expires_at: null, discord_user_id: "d-222" }),
];

function renderPage() {
  return render(
    <MemoryRouter>
      <ViewerAccountsPage />
    </MemoryRouter>,
  );
}

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: true });
  vi.mocked(api.get).mockImplementation(async (path: string) => {
    if (path === "/super-admin/viewers") return { items: ITEMS };
    return { items: [] };
  });
});
afterEach(() => cleanup());

const row = (email: string) => screen.getByText(email).closest("tr") as HTMLElement;

it("shows only the access denied message for a non super admin and loads nothing", () => {
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: false });
  renderPage();
  expect(screen.getByText(i18n.t("superAdmin.accessDenied"))).toBeTruthy();
  expect(api.get).not.toHaveBeenCalled();
});

it("lists viewers with status badges and flag badges only on flagged rows", async () => {
  renderPage();
  await screen.findByText("t1@example.com");
  expect(within(row("t1@example.com")).getByText("Trial")).toBeTruthy();
  expect(within(row("s2@example.com")).getByText("Suspended")).toBeTruthy();
  expect(within(row("t1@example.com")).getByText("Many IPs")).toBeTruthy();
  expect(within(row("s2@example.com")).queryByText("Many IPs")).toBeNull();
  expect(within(row("s2@example.com")).getByText("d-222")).toBeTruthy();
});

it("shows activate/extend/suspend on trial rows and only unsuspend on suspended rows", async () => {
  renderPage();
  await screen.findByText("t1@example.com");
  const trial = within(row("t1@example.com"));
  expect(trial.getByRole("button", { name: "Make active" })).toBeTruthy();
  expect(trial.getByRole("button", { name: "Extend" })).toBeTruthy();
  expect(trial.getByRole("button", { name: "Suspend" })).toBeTruthy();
  expect(trial.queryByRole("button", { name: "Unsuspend" })).toBeNull();
  const sus = within(row("s2@example.com"));
  expect(sus.getByRole("button", { name: "Unsuspend" })).toBeTruthy();
  expect(sus.queryByRole("button", { name: "Suspend" })).toBeNull();
  expect(sus.queryByRole("button", { name: "Make active" })).toBeNull();
});

it("suspend opens a confirm modal, posts and reloads the list", async () => {
  vi.mocked(api.post).mockResolvedValue({});
  renderPage();
  await screen.findByText("t1@example.com");
  fireEvent.click(within(row("t1@example.com")).getByRole("button", { name: "Suspend" }));
  fireEvent.click(await screen.findByTestId("viewers-run"));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/super-admin/viewers/1/suspend", {}));
  await waitFor(() => expect(vi.mocked(api.get).mock.calls.filter(c => c[0] === "/super-admin/viewers").length).toBe(2));
});

it("extend cannot be sent with 0 and posts days 7", async () => {
  vi.mocked(api.post).mockResolvedValue({});
  renderPage();
  await screen.findByText("t1@example.com");
  fireEvent.click(within(row("t1@example.com")).getByRole("button", { name: "Extend" }));
  const input = await screen.findByTestId("viewers-extend-days");
  fireEvent.change(input, { target: { value: "0" } });
  expect((screen.getByTestId("viewers-run") as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(input, { target: { value: "7" } });
  fireEvent.click(screen.getByTestId("viewers-run"));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/super-admin/viewers/1/extend", { days: 7 }));
});

it("shows the conflict message on 409", async () => {
  vi.mocked(api.post).mockRejectedValue(new ApiError("viewer_status_conflict", 409, "viewer_status_conflict"));
  renderPage();
  await screen.findByText("t1@example.com");
  fireEvent.click(within(row("t1@example.com")).getByRole("button", { name: "Suspend" }));
  fireEvent.click(await screen.findByTestId("viewers-run"));
  expect(await screen.findByText("This cannot be done in the current state.")).toBeTruthy();
});

it("shows login records with time, IP and device in a drawer", async () => {
  vi.mocked(api.get).mockImplementation(async (path: string) => {
    if (path === "/super-admin/viewers") return { items: ITEMS };
    if (path === "/super-admin/viewers/1/logins") {
      return { items: [{ created_at: "2026-10-10T01:02:03Z", event_type: "login_succeeded", client_ip: "203.0.113.9", user_agent: "TestAgent/1.0" }] };
    }
    return { items: [] };
  });
  renderPage();
  await screen.findByText("t1@example.com");
  fireEvent.click(within(row("t1@example.com")).getByRole("button", { name: "Login records" }));
  expect(await screen.findByText("203.0.113.9")).toBeTruthy();
  expect(screen.getByText("TestAgent/1.0")).toBeTruthy();
  expect(screen.getByText("Login succeeded")).toBeTruthy();
});
