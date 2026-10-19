import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
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

function LocationProbe() {
  const loc = useLocation();
  return <div data-testid="probe-search">{loc.search}</div>;
}

function renderPage(entry = "/") {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <ViewerAccountsPage />
      <LocationProbe />
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

it("shows the open room link only on rows that have a discord_channel_url", async () => {
  vi.mocked(api.get).mockImplementation(async (path: string) => {
    if (path === "/super-admin/viewers") {
      return {
        items: [
          v({ id: 1, discord_user_id: "d-111", discord_channel_id: "555", discord_channel_url: "https://discord.com/channels/10/555" }),
          v({ id: 2, email: "s2@example.com", discord_user_id: "d-222", discord_channel_url: null }),
        ],
      };
    }
    return { items: [] };
  });
  renderPage();
  await screen.findByText("t1@example.com");
  const link = within(row("t1@example.com")).getByRole("link", { name: "Open room" });
  expect(link.getAttribute("href")).toBe("https://discord.com/channels/10/555");
  expect(link.getAttribute("target")).toBe("_blank");
  expect(within(row("s2@example.com")).queryByRole("link", { name: "Open room" })).toBeNull();
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

const MIXED = [
  v({ id: 1, email: "t1@example.com", status: "trial" }),
  v({ id: 2, email: "s2@example.com", status: "suspended", trial_expires_at: null }),
  v({ id: 3, email: "p3@example.com", line_name: "Pen", status: "pending", trial_expires_at: null }),
  v({ id: 4, email: "a4@example.com", status: "active", trial_expires_at: null }),
  v({ id: 5, email: "a5@example.com", status: "active", trial_expires_at: null }),
];

function mockMixed() {
  vi.mocked(api.get).mockImplementation(async (path: string) => {
    if (path === "/super-admin/viewers") return { items: MIXED };
    return { items: [] };
  });
}

it("shows a left menu with 5 entries and counts, and filters by trial with ?status=trial", async () => {
  mockMixed();
  renderPage();
  await screen.findByText("t1@example.com");
  const menu = ["All", "Pending", "Trial", "Active", "Suspended"].map(name =>
    screen.getByRole("button", { name: new RegExp(`^${name}\\s*\\d+$`) }),
  );
  expect(menu.map(b => b.textContent)).toEqual(["All5", "Pending1", "Trial1", "Active2", "Suspended1"]);
  fireEvent.click(menu[2]);
  await waitFor(() => expect(screen.getByTestId("probe-search").textContent).toBe("?status=trial"));
  expect(screen.getByText("t1@example.com")).toBeTruthy();
  expect(screen.queryByText("a4@example.com")).toBeNull();
  expect(screen.queryByText("s2@example.com")).toBeNull();
  fireEvent.click(menu[0]);
  await waitFor(() => expect(screen.getByTestId("probe-search").textContent).toBe(""));
  expect(screen.getByText("a4@example.com")).toBeTruthy();
});

it("opens with ?status=active and shows only active rows", async () => {
  mockMixed();
  renderPage("/?status=active");
  await screen.findByText("a4@example.com");
  expect(screen.getByText("a5@example.com")).toBeTruthy();
  expect(screen.queryByText("t1@example.com")).toBeNull();
});

it("copies the signup form URL and shows Copied", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
  mockMixed();
  renderPage();
  await screen.findByText("t1@example.com");
  fireEvent.click(screen.getByRole("button", { name: "Copy signup form URL" }));
  expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/viewer/#signup`);
  expect(await screen.findByRole("button", { name: "Copied" })).toBeTruthy();
});

it("shows Reissue only on pending rows, confirms, posts and shows code, expiry and invite", async () => {
  mockMixed();
  vi.mocked(api.post).mockResolvedValue({
    signup_code: "ABCD-EFGH-JKMN-PQRS",
    expires_at: "2026-10-26T00:00:00Z",
    invite_url: "https://discord.gg/fakecode",
  });
  renderPage();
  await screen.findByText("t1@example.com");
  expect(within(row("t1@example.com")).queryByRole("button", { name: "Reissue code and invite" })).toBeNull();
  expect(within(row("a4@example.com")).queryByRole("button", { name: "Reissue code and invite" })).toBeNull();
  fireEvent.click(within(row("p3@example.com")).getByRole("button", { name: "Reissue code and invite" }));
  expect(await screen.findByText(/Reissue the signup code and invite link for Pen \(p3@example.com\)/)).toBeTruthy();
  fireEvent.click(screen.getByTestId("viewers-reissue-run"));
  expect(await screen.findByTestId("viewers-reissue-code")).toBeTruthy();
  expect(api.post).toHaveBeenCalledWith("/super-admin/viewers/3/reissue-signup-code", {});
  expect(screen.getByTestId("viewers-reissue-code").textContent).toBe("ABCD-EFGH-JKMN-PQRS");
  expect(screen.getByTestId("viewers-reissue-invite").textContent).toBe("https://discord.gg/fakecode");
  expect(screen.getByText(i18n.t("superAdmin.viewers.reissueOnlyOnce"))).toBeTruthy();
});

it("shows the failure text when the invite link is null", async () => {
  mockMixed();
  vi.mocked(api.post).mockResolvedValue({
    signup_code: "ABCD-EFGH-JKMN-PQRS",
    expires_at: "2026-10-26T00:00:00Z",
    invite_url: null,
  });
  renderPage();
  await screen.findByText("p3@example.com");
  fireEvent.click(within(row("p3@example.com")).getByRole("button", { name: "Reissue code and invite" }));
  fireEvent.click(await screen.findByTestId("viewers-reissue-run"));
  expect(await screen.findByTestId("viewers-reissue-invite-failed")).toBeTruthy();
});
