import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { queryClient } from "../../lib/query/apiQuery";
import SchedulePage from "./SchedulePageImpl";

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: { uid: "user-a" } }),
}));

const answers = vi.hoisted(() => ({
  isTenantAdmin: false,
  connected: false,
  events: [] as Array<Record<string, unknown>>,
  canManageOthers: false,
}));

vi.mock("../../lib/api", () => ({
  api: {
    get: vi.fn(async (path: string) => {
      if (path === "/me/permissions") return { permissions: answers.canManageOthers ? ["staff.view"] : [], is_tenant_admin: answers.isTenantAdmin };
      if (path === "/google-calendar/status") return { connected: answers.connected };
      if (path === "/calendar/owners") {
        return {
          can_manage_others: answers.canManageOthers,
          current_staff_id: 7,
          current_user_id: 101,
          owners: [
            { staff_id: 7, user_id: 101, staff_code: "A01", name: "Owner Self", primary_email: null, color: "#111111", is_visible: true, share_mode: "self", is_self: true },
            { staff_id: 8, user_id: 202, staff_code: "B02", name: "Owner Other", primary_email: null, color: "#222222", is_visible: false, share_mode: "view", is_self: false },
          ],
        };
      }
      if (path.startsWith("/calendar/events")) return { events: answers.events };
      if (path === "/google-calendar/connect/start") return { auth_url: "https://accounts.example/auth" };
      return [];
    }),
    post: vi.fn(async () => ({})),
    patch: vi.fn(async () => ({})),
    put: vi.fn(async () => ({})),
    delete: vi.fn(async () => ({})),
  },
}));

import { api } from "../../lib/api";
const mockGet = vi.mocked(api.get);

const originalLocation = window.location;
const hrefSetter = vi.fn();

beforeEach(async () => {
  await i18n.changeLanguage("ja");
  answers.isTenantAdmin = false;
  answers.connected = false;
  answers.events = [];
  answers.canManageOthers = false;
  hrefSetter.mockReset();
  const fake = { ...window.location } as Record<string, unknown>;
  Object.defineProperty(fake, "href", { configurable: true, get: () => "http://localhost/", set: hrefSetter });
  Object.defineProperty(window, "location", { configurable: true, value: fake });
});

afterEach(() => {
  Object.defineProperty(window, "location", { configurable: true, value: originalLocation });
  cleanup();
  vi.clearAllMocks();
  queryClient.clear();
});

const view = () => render(<MemoryRouter><SchedulePage /></MemoryRouter>);

describe("SchedulePage Google calendar connect button", () => {
  it("shows an enabled button to a tenant admin and starts the connect flow on click", async () => {
    answers.isTenantAdmin = true;
    view();
    const btn = await screen.findByRole("button", { name: i18n.t("schedule.connectBtn") });
    await waitFor(() => expect((btn as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(btn);
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith("/google-calendar/connect/start"));
    await waitFor(() => expect(hrefSetter).toHaveBeenCalledWith("https://accounts.example/auth"));
  });

  it("shows a disabled connected label when already connected", async () => {
    answers.isTenantAdmin = true;
    answers.connected = true;
    view();
    const btn = await screen.findByRole("button", { name: i18n.t("schedule.connectBtnConnected") });
    expect((btn as HTMLButtonElement).disabled).toBe(true);
  });

  it("hides the button and never asks for status when not a tenant admin", async () => {
    answers.isTenantAdmin = false;
    view();
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith("/me/permissions"));
    await waitFor(() => expect(mockGet.mock.calls.length).toBeGreaterThan(1));
    expect(screen.queryByRole("button", { name: i18n.t("schedule.connectBtn") })).toBeNull();
    expect(mockGet).not.toHaveBeenCalledWith("/google-calendar/status");
  });
});


function todayAt(hour: number) {
  const d = new Date();
  d.setHours(hour, 0, 0, 0);
  return d.toISOString();
}

function apiEvent(over: Record<string, unknown>) {
  return {
    id: 1, user_id: 101, calendar_type: "shared", category: "meeting", title: "Own Event",
    description: null, location: null, start_datetime: todayAt(10), end_datetime: todayAt(11),
    is_all_day: false, google_event_id: null, source: "app", sync_status: "synced",
    created_by_user_id: 101, created_at: null, updated_at: null, owner_name: null, created_by_name: null,
    ...over,
  };
}

describe("SchedulePage share-with-staff toggle", () => {
  const label = () => i18n.t("schedule.shareWithStaff");

  it("shows the toggle on create, default on, and sends personal when switched off", async () => {
    view();
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("schedule.create") }));
    const toggle = (await screen.findByRole("switch", { name: label() })) as HTMLInputElement;
    expect(toggle.checked).toBe(true);
    fireEvent.click(toggle);
    expect(toggle.checked).toBe(false);
    fireEvent.change(screen.getByPlaceholderText(i18n.t("schedule.eventTitle")), { target: { value: "Secret" } });
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const [path, body] = vi.mocked(api.post).mock.calls[0] as [string, Record<string, unknown>];
    expect(path).toBe("/calendar/events");
    expect(body.calendar_type).toBe("personal");
  });

  it("shows the toggle when editing own event and sends calendar_type", async () => {
    answers.events = [apiEvent({})];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    expect(await screen.findByRole("switch", { name: label() })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    const body = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect(body.calendar_type).toBe("shared");
  });

  it("hides the toggle and omits calendar_type when editing someone else's event", async () => {
    answers.canManageOthers = true;
    answers.events = [apiEvent({ id: 2, user_id: 202, created_by_user_id: 202, title: "Other Event" })];
    view();
    fireEvent.click(await screen.findByRole("checkbox", { name: "Owner Other" }));
    fireEvent.click(await screen.findByText("Other Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    await screen.findByPlaceholderText(i18n.t("schedule.eventTitle"));
    expect(screen.queryByRole("switch", { name: label() })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    const body = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect("calendar_type" in body).toBe(false);
  });
});
