import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api, ApiError } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import i18n from "../../i18n";
import ViewerAccountsPage from "./ViewerAccountsPage";

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, api: { get: vi.fn(), post: vi.fn(), patch: vi.fn() } };
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

it("lists viewers with status badges in 5 columns only (no email, Discord ID or flags)", async () => {
  renderPage();
  await screen.findByText("Taro");
  const headers = screen.getAllByRole("columnheader").map(h => h.textContent);
  expect(headers).toEqual(["LINE name", "Status", "Registered", "Expires", "Actions"]);
  expect(within(row("Taro")).getByText("Trial")).toBeTruthy();
  expect(within(row("Sato")).getByText("Suspended")).toBeTruthy();
  expect(screen.queryByText("t1@example.com")).toBeNull();
  expect(screen.queryByText("d-222")).toBeNull();
  expect(screen.queryByText("Many IPs")).toBeNull();
});

it("opens a detail drawer on row click with email, Discord ID and flags (present / none)", async () => {
  renderPage();
  await screen.findByText("Taro");
  fireEvent.click(within(row("Taro")).getByText("Taro"));
  let detail = within(await screen.findByTestId("viewers-detail"));
  expect(detail.getByText("t1@example.com")).toBeTruthy();
  expect(detail.getByText("Many IPs")).toBeTruthy();
  expect(detail.queryByText("None")).toBeNull();
  fireEvent.click(within(row("Sato")).getByText("Sato"));
  detail = within(await screen.findByTestId("viewers-detail"));
  expect(detail.getByText("s2@example.com")).toBeTruthy();
  expect(detail.getByText("d-222")).toBeTruthy();
  expect(detail.getByText("None")).toBeTruthy();
  expect(detail.queryByText("Many IPs")).toBeNull();
});

it("shows the open room link only in the detail of rows that have a discord_channel_url", async () => {
  vi.mocked(api.get).mockImplementation(async (path: string) => {
    if (path === "/super-admin/viewers") {
      return {
        items: [
          v({ id: 1, discord_user_id: "d-111", discord_channel_id: "555", discord_channel_url: "https://discord.com/channels/10/555" }),
          v({ id: 2, email: "s2@example.com", line_name: "Sato", discord_user_id: "d-222", discord_channel_url: null }),
        ],
      };
    }
    return { items: [] };
  });
  renderPage();
  await screen.findByText("Taro");
  expect(screen.queryByRole("link", { name: "Open room" })).toBeNull();
  fireEvent.click(within(row("Taro")).getByText("Taro"));
  const link = within(await screen.findByTestId("viewers-detail")).getByRole("link", { name: "Open room" });
  expect(link.getAttribute("href")).toBe("https://discord.com/channels/10/555");
  expect(link.getAttribute("target")).toBe("_blank");
  fireEvent.click(within(row("Sato")).getByText("Sato"));
  await screen.findByText("s2@example.com");
  expect(screen.queryByRole("link", { name: "Open room" })).toBeNull();
});

it("does not open the detail drawer when an action button is pressed, and still shows the confirm dialog", async () => {
  renderPage();
  await screen.findByText("Taro");
  fireEvent.click(within(row("Taro")).getByRole("button", { name: "Make active" }));
  expect(await screen.findByTestId("viewers-run")).toBeTruthy();
  expect(screen.queryByTestId("viewers-detail")).toBeNull();
});

it("shows activate/extend/reissue on trial rows without a room, and no suspend or login buttons anywhere", async () => {
  renderPage();
  await screen.findByText("Taro");
  const trial = within(row("Taro"));
  expect(trial.getByRole("button", { name: "Make active" })).toBeTruthy();
  expect(trial.getByRole("button", { name: "Extend" })).toBeTruthy();
  expect(trial.getByRole("button", { name: "Reissue code and invite" })).toBeTruthy();
  const sus = within(row("Sato"));
  expect(sus.queryByRole("button", { name: "Make active" })).toBeNull();
  expect(sus.queryByRole("button", { name: "Reissue code and invite" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Suspend" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Unsuspend" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Login records" })).toBeNull();
});

it("extend cannot be sent with 0 and posts days 7", async () => {
  vi.mocked(api.post).mockResolvedValue({});
  renderPage();
  await screen.findByText("Taro");
  fireEvent.click(within(row("Taro")).getByRole("button", { name: "Extend" }));
  const input = await screen.findByTestId("viewers-extend-days");
  fireEvent.change(input, { target: { value: "0" } });
  expect((screen.getByTestId("viewers-run") as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(input, { target: { value: "7" } });
  fireEvent.click(screen.getByTestId("viewers-run"));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/super-admin/viewers/1/extend", { days: 7 }));
});

it("extend by date posts until_date and is disabled for empty or past dates", async () => {
  vi.mocked(api.post).mockResolvedValue({});
  renderPage();
  await screen.findByText("Taro");
  fireEvent.click(within(row("Taro")).getByRole("button", { name: "Extend" }));
  fireEvent.click(await screen.findByLabelText("Extend until date"));
  const input = await screen.findByTestId("viewers-extend-date");
  expect((screen.getByTestId("viewers-run") as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(input, { target: { value: "2000-01-01" } });
  expect((screen.getByTestId("viewers-run") as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(input, { target: { value: "2999-12-31" } });
  expect((screen.getByTestId("viewers-run") as HTMLButtonElement).disabled).toBe(false);
  fireEvent.click(screen.getByTestId("viewers-run"));
  await waitFor(() =>
    expect(api.post).toHaveBeenCalledWith("/super-admin/viewers/1/extend", { until_date: "2999-12-31" }),
  );
});

it("shows the conflict message on 409", async () => {
  vi.mocked(api.post).mockRejectedValue(new ApiError("viewer_status_conflict", 409, "viewer_status_conflict"));
  renderPage();
  await screen.findByText("Taro");
  fireEvent.click(within(row("Taro")).getByRole("button", { name: "Make active" }));
  fireEvent.click(await screen.findByTestId("viewers-run"));
  expect(await screen.findByText("This cannot be done in the current state.")).toBeTruthy();
});

const MIXED = [
  v({ id: 1, email: "t1@example.com", status: "trial" }),
  v({ id: 2, email: "s2@example.com", line_name: "Sato", status: "suspended", trial_expires_at: null }),
  v({ id: 3, email: "p3@example.com", line_name: "Pen", status: "pending", trial_expires_at: null }),
  v({ id: 4, email: "a4@example.com", line_name: "Ann", status: "active", trial_expires_at: null }),
  v({ id: 5, email: "a5@example.com", line_name: "Abe", status: "active", trial_expires_at: null }),
];

function mockMixed() {
  vi.mocked(api.get).mockImplementation(async (path: string) => {
    if (path === "/super-admin/viewers") return { items: MIXED };
    return { items: [] };
  });
}

it("shows a left menu with 4 entries (no Suspended) and counts, and filters by trial with ?status=trial", async () => {
  mockMixed();
  renderPage();
  await screen.findByText("Taro");
  expect(screen.queryByRole("button", { name: /^Suspended/ })).toBeNull();
  const menu = ["All", "Pending", "Trial", "Active"].map(name =>
    screen.getByRole("button", { name: new RegExp(`^${name}\\s*\\d+$`) }),
  );
  expect(menu.map(b => b.textContent)).toEqual(["All5", "Pending1", "Trial1", "Active2"]);
  fireEvent.click(menu[2]);
  await waitFor(() => expect(screen.getByTestId("probe-search").textContent).toBe("?status=trial"));
  expect(screen.getByText("Taro")).toBeTruthy();
  expect(screen.queryByText("Ann")).toBeNull();
  expect(screen.queryByText("Sato")).toBeNull();
  fireEvent.click(menu[0]);
  await waitFor(() => expect(screen.getByTestId("probe-search").textContent).toBe(""));
  expect(screen.getByText("Ann")).toBeTruthy();
});

it("opens with ?status=active and shows only active rows", async () => {
  mockMixed();
  renderPage("/?status=active");
  await screen.findByText("Ann");
  expect(screen.getByText("Abe")).toBeTruthy();
  expect(screen.queryByText("Taro")).toBeNull();
});

it("copies the signup form URL and shows Copied", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
  mockMixed();
  renderPage();
  await screen.findByText("Taro");
  fireEvent.click(screen.getByRole("button", { name: "Copy signup form URL" }));
  expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/viewer/#signup`);
  expect(await screen.findByRole("button", { name: "Copied" })).toBeTruthy();
});

it("copies the signup request message fetched from the API and shows Copied", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
  mockMixed();
  vi.mocked(api.get).mockImplementation(async (path: string) => {
    if (path === "/super-admin/viewers/signup-request") return { text: "REQUEST TEXT" };
    return { items: ITEMS };
  });
  renderPage();
  await screen.findByText("Taro");
  fireEvent.click(screen.getByRole("button", { name: "Copy signup request message" }));
  await waitFor(() => expect(writeText).toHaveBeenCalledWith("REQUEST TEXT"));
  expect(api.get).toHaveBeenCalledWith("/super-admin/viewers/signup-request");
  expect(await screen.findByRole("button", { name: "Copied" })).toBeTruthy();
});

it("copies the reissue message from the result modal", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
  mockMixed();
  vi.mocked(api.post).mockResolvedValue({
    signup_code: "ABCD-EFGH-JKMN-PQRS",
    expires_at: "2026-10-26T00:00:00Z",
    invite_url: "https://discord.gg/fakecode",
    message: "REISSUE MESSAGE",
  });
  renderPage();
  await screen.findByText("Pen");
  fireEvent.click(within(row("Pen")).getByRole("button", { name: "Reissue code and invite" }));
  fireEvent.click(await screen.findByTestId("viewers-reissue-run"));
  await screen.findByTestId("viewers-reissue-code");
  const label = screen.getByText(/^Message:/);
  fireEvent.click(within(label).getByRole("button", { name: "Copy" }));
  await waitFor(() => expect(writeText).toHaveBeenCalledWith("REISSUE MESSAGE"));
});

it("shows Reissue on rows without a room (pending, trial, active) but not on suspended or roomed rows, confirms, posts and shows code, expiry and invite", async () => {
  mockMixed();
  vi.mocked(api.post).mockResolvedValue({
    signup_code: "ABCD-EFGH-JKMN-PQRS",
    expires_at: "2026-10-26T00:00:00Z",
    invite_url: "https://discord.gg/fakecode",
  });
  renderPage();
  await screen.findByText("Taro");
  expect(within(row("Taro")).getByRole("button", { name: "Reissue code and invite" })).toBeTruthy();
  expect(within(row("Ann")).getByRole("button", { name: "Reissue code and invite" })).toBeTruthy();
  expect(within(row("Sato")).queryByRole("button", { name: "Reissue code and invite" })).toBeNull();
  fireEvent.click(within(row("Pen")).getByRole("button", { name: "Reissue code and invite" }));
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
  await screen.findByText("Pen");
  fireEvent.click(within(row("Pen")).getByRole("button", { name: "Reissue code and invite" }));
  fireEvent.click(await screen.findByTestId("viewers-reissue-run"));
  expect(await screen.findByTestId("viewers-reissue-invite-failed")).toBeTruthy();
});

it("hides Reissue on rows that already have a Discord room", async () => {
  vi.mocked(api.get).mockImplementation(async (path: string) => {
    if (path === "/super-admin/viewers") {
      return {
        items: [
          v({ id: 1, status: "trial", discord_user_id: "d-1", discord_channel_id: "5", discord_channel_url: "https://discord.com/channels/1/5" }),
          v({ id: 2, email: "n2@example.com", line_name: "Nao", status: "trial" }),
        ],
      };
    }
    return { items: [] };
  });
  renderPage();
  await screen.findByText("Taro");
  expect(within(row("Taro")).queryByRole("button", { name: "Reissue code and invite" })).toBeNull();
  expect(within(row("Nao")).getByRole("button", { name: "Reissue code and invite" })).toBeTruthy();
});

it("shows the already-linked message on 409 viewer_already_linked", async () => {
  mockMixed();
  vi.mocked(api.post).mockRejectedValue(new ApiError("viewer_already_linked", 409, "viewer_already_linked"));
  renderPage();
  await screen.findByText("Pen");
  fireEvent.click(within(row("Pen")).getByRole("button", { name: "Reissue code and invite" }));
  fireEvent.click(await screen.findByTestId("viewers-reissue-run"));
  expect(await screen.findByText("This viewer already has a Discord room.")).toBeTruthy();
});

// ── LINE名を直す（ADR-1019 段8） ──────────────────────────────

async function openDetail(name: string) {
  fireEvent.click(within(row(name)).getByText(name));
  return within(await screen.findByTestId("viewers-detail"));
}

it("shows a LINE name input with the current value, and no other editable input", async () => {
  renderPage();
  await screen.findByText("Taro");
  const detail = await openDetail("Taro");
  const input = detail.getByTestId("viewers-detail-line-name") as HTMLInputElement;
  expect(input.value).toBe("Taro");
  expect(detail.getAllByRole("textbox")).toHaveLength(1);
  expect(screen.getByTestId("viewers-detail-save")).toHaveProperty("disabled", true);
});

it("saves a changed LINE name with PATCH and updates both the drawer and the list", async () => {
  vi.mocked(api.patch).mockResolvedValue(v({ id: 1, line_name: "Jiro", flag_many_ips: true }));
  renderPage();
  await screen.findByText("Taro");
  const detail = await openDetail("Taro");
  fireEvent.change(detail.getByTestId("viewers-detail-line-name"), { target: { value: "  Jiro  " } });
  const save = screen.getByTestId("viewers-detail-save");
  expect(save).toHaveProperty("disabled", false);
  fireEvent.click(save);
  await waitFor(() =>
    expect(api.patch).toHaveBeenCalledWith("/super-admin/viewers/1", { line_name: "Jiro" }),
  );
  expect((await screen.findByTestId("viewers-detail-saved")).getAttribute("role")).toBe("status");
  expect((screen.getByTestId("viewers-detail-line-name") as HTMLInputElement).value).toBe("Jiro");
  expect(within(row("Jiro")).getByText("Trial")).toBeTruthy();
  expect(screen.queryByText("Taro")).toBeNull();
});

it("hides the saved message when the input is changed after saving", async () => {
  vi.mocked(api.patch).mockResolvedValue(v({ id: 1, line_name: "Jiro", flag_many_ips: true }));
  renderPage();
  await screen.findByText("Taro");
  const detail = await openDetail("Taro");
  fireEvent.change(detail.getByTestId("viewers-detail-line-name"), { target: { value: "Jiro" } });
  fireEvent.click(screen.getByTestId("viewers-detail-save"));
  await screen.findByTestId("viewers-detail-saved");
  fireEvent.change(screen.getByTestId("viewers-detail-line-name"), { target: { value: "Jiro2" } });
  expect(screen.queryByTestId("viewers-detail-saved")).toBeNull();
});

it("disables save when the LINE name is empty, blank or over 100 characters", async () => {
  renderPage();
  await screen.findByText("Taro");
  const detail = await openDetail("Taro");
  const input = detail.getByTestId("viewers-detail-line-name");
  for (const value of ["", "   ", "a".repeat(101)]) {
    fireEvent.change(input, { target: { value } });
    expect(screen.getByTestId("viewers-detail-save")).toHaveProperty("disabled", true);
  }
  fireEvent.change(input, { target: { value: "a".repeat(100) } });
  expect(screen.getByTestId("viewers-detail-save")).toHaveProperty("disabled", false);
  expect(api.patch).not.toHaveBeenCalled();
});

it("shows the invalid text in an alert on 422 and the generic save error otherwise", async () => {
  vi.mocked(api.patch).mockRejectedValueOnce(new ApiError("invalid_line_name", 422, "invalid_line_name"));
  renderPage();
  await screen.findByText("Taro");
  const detail = await openDetail("Taro");
  fireEvent.change(detail.getByTestId("viewers-detail-line-name"), { target: { value: "Jiro" } });
  fireEvent.click(screen.getByTestId("viewers-detail-save"));
  const alert = await screen.findByTestId("viewers-detail-save-error");
  expect(alert.getAttribute("role")).toBe("alert");
  expect(alert.textContent).toBe(i18n.t("superAdmin.viewers.lineNameInvalid"));
  vi.mocked(api.patch).mockRejectedValueOnce(new ApiError("boom", 500, "boom"));
  fireEvent.click(screen.getByTestId("viewers-detail-save"));
  await waitFor(() =>
    expect(screen.getByTestId("viewers-detail-save-error").textContent).toBe(
      i18n.t("superAdmin.viewers.saveError"),
    ),
  );
});

it("shows the room-notice failure guide with a copy button when the room notice failed", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
  vi.mocked(api.post).mockResolvedValue({ room_notice: "failed", room_notice_text: "NOTICE BODY" });
  renderPage();
  await screen.findByText("Taro");
  fireEvent.click(within(row("Taro")).getByRole("button", { name: "Extend" }));
  fireEvent.click(await screen.findByTestId("viewers-run"));
  const box = await screen.findByTestId("viewers-room-notice-failed");
  expect(within(box).getByText(i18n.t("superAdmin.viewers.roomNoticeFailed"))).toBeTruthy();
  expect(within(box).getByText("NOTICE BODY")).toBeTruthy();
  fireEvent.click(within(box).getByRole("button", { name: "Copy" }));
  await waitFor(() => expect(writeText).toHaveBeenCalledWith("NOTICE BODY"));
});

it("shows the same guide when the viewer has no room (no_room)", async () => {
  vi.mocked(api.post).mockResolvedValue({ room_notice: "no_room", room_notice_text: "NO ROOM BODY" });
  renderPage();
  await screen.findByText("Taro");
  fireEvent.click(within(row("Taro")).getByRole("button", { name: "Extend" }));
  fireEvent.click(await screen.findByTestId("viewers-run"));
  expect(await screen.findByText("NO ROOM BODY")).toBeTruthy();
});

it("shows the no-template message (without a copy text) when room_notice is no_template", async () => {
  vi.mocked(api.post).mockResolvedValue({ room_notice: "no_template", room_notice_text: null });
  renderPage();
  await screen.findByText("Taro");
  fireEvent.click(within(row("Taro")).getByRole("button", { name: "Extend" }));
  fireEvent.click(await screen.findByTestId("viewers-run"));
  const box = await screen.findByTestId("viewers-room-notice-no-template");
  expect(box.textContent).toBe(i18n.t("superAdmin.viewers.roomNoticeNoTemplate"));
  expect(screen.queryByTestId("viewers-room-notice-failed")).toBeNull();
});

it("shows no room-notice guide when the notice was sent or there is none", async () => {
  vi.mocked(api.post).mockResolvedValue({ room_notice: "sent", room_notice_text: "SENT BODY" });
  renderPage();
  await screen.findByText("Taro");
  fireEvent.click(within(row("Taro")).getByRole("button", { name: "Extend" }));
  fireEvent.click(await screen.findByTestId("viewers-run"));
  await waitFor(() => expect(api.post).toHaveBeenCalled());
  await waitFor(() => expect(screen.queryByTestId("viewers-run")).toBeNull());
  expect(screen.queryByTestId("viewers-room-notice-failed")).toBeNull();
  expect(screen.queryByText("SENT BODY")).toBeNull();
});

it("navigates to the viewer templates page with the header button", async () => {
  render(
    <MemoryRouter initialEntries={["/super-admin/viewers"]}>
      <Routes>
        <Route path="/super-admin/viewers" element={<ViewerAccountsPage />} />
        <Route path="/super-admin/viewer-templates" element={<div data-testid="templates-page" />} />
      </Routes>
    </MemoryRouter>,
  );
  await screen.findByText("Taro");
  fireEvent.click(screen.getByText(i18n.t("superAdmin.viewers.templates")));
  expect(await screen.findByTestId("templates-page")).toBeTruthy();
});
