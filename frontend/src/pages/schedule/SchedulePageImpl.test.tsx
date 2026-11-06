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
  meetAvailable: false,
  events: [] as Array<Record<string, unknown>>,
  canManageOthers: false,
}));

vi.mock("../../lib/api", () => ({
  api: {
    get: vi.fn(async (path: string) => {
      if (path === "/me/permissions") return { permissions: answers.canManageOthers ? ["staff.view"] : [], is_tenant_admin: answers.isTenantAdmin };
      if (path === "/google-calendar/status") return { connected: answers.connected, meet_available: answers.meetAvailable };
      if (path === "/calendar/owners") {
        return {
          can_manage_others: answers.canManageOthers,
          current_staff_id: 7,
          current_user_id: 101,
          owners: [
            { staff_id: 7, user_id: 101, staff_code: "A01", name: "Owner Self", primary_email: null, color: null, is_visible: true, share_mode: "self", is_self: true },
            { staff_id: 8, user_id: 202, staff_code: "B02", name: "Owner Other", primary_email: null, color: null, is_visible: false, share_mode: "view", is_self: false },
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
  answers.meetAvailable = false;
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

describe("SchedulePage popover placement (K1)", () => {
  const callbacks: Array<() => void> = [];
  let popoverHeight = 500;

  beforeEach(() => {
    callbacks.length = 0;
    popoverHeight = 500;
    vi.stubGlobal(
      "ResizeObserver",
      class {
        constructor(cb: () => void) { callbacks.push(cb); }
        observe() {}
        unobserve() {}
        disconnect() {}
      },
    );
    vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function (this: Element) {
      if (this.classList.contains("schedule-popover")) {
        return { top: 0, left: 0, right: 320, bottom: popoverHeight, width: 320, height: popoverHeight, x: 0, y: 0, toJSON: () => ({}) };
      }
      // 画面（高さ 768）の一番下にある枠を押した、という測り値
      return { top: 700, left: 100, right: 180, bottom: 748, width: 80, height: 48, x: 100, y: 700, toJSON: () => ({}) };
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  const popoverTop = () => (document.querySelector(".schedule-popover") as HTMLElement).style.top;

  it("places the popover from its measured height so the bottom stays inside the viewport", async () => {
    answers.events = [apiEvent({})];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    await waitFor(() => expect(document.querySelector(".schedule-popover")).not.toBeNull());
    // 768 - 500 - 12
    expect(popoverTop()).toBe("256px");
  });

  it("measures again when the content grows", async () => {
    answers.events = [apiEvent({})];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    await waitFor(() => expect(popoverTop()).toBe("256px"));
    popoverHeight = 600;
    expect(callbacks.length).toBeGreaterThan(0);
    callbacks.forEach((cb) => cb());
    // 768 - 600 - 12
    await waitFor(() => expect(popoverTop()).toBe("156px"));
  });
});

describe("SchedulePage keyboard shortcuts (K7)", () => {
  const rangeText = () => document.querySelector(".schedule-shell__range")?.textContent ?? "";
  const pressed = (name: string) =>
    screen.getByRole("button", { name }).getAttribute("aria-pressed") === "true";
  const press = (key: string, init: Record<string, unknown> = {}, target: Element = document.body) =>
    fireEvent.keyDown(target, { key, ...init });
  const ready = async () => {
    view();
    await screen.findByRole("button", { name: i18n.t("schedule.create") });
  };
  const titleInput = () => screen.queryByPlaceholderText(i18n.t("schedule.eventTitle"));

  describe("keys that act", () => {
    it("T goes back to today", async () => {
      await ready();
      const initial = rangeText();
      press("j");
      expect(rangeText()).not.toBe(initial);
      press("t");
      expect(rangeText()).toBe(initial);
    });

    it("J moves to the next period", async () => {
      await ready();
      const initial = rangeText();
      press("j");
      expect(rangeText()).not.toBe(initial);
    });

    it("ArrowRight moves to the next period", async () => {
      await ready();
      const initial = rangeText();
      press("ArrowRight");
      expect(rangeText()).not.toBe(initial);
    });

    it("K moves to the previous period", async () => {
      await ready();
      const initial = rangeText();
      press("k");
      expect(rangeText()).not.toBe(initial);
    });

    it("ArrowLeft moves to the previous period", async () => {
      await ready();
      const initial = rangeText();
      press("ArrowLeft");
      expect(rangeText()).not.toBe(initial);
    });

    it("D switches to the day view", async () => {
      await ready();
      press("d");
      expect(pressed(i18n.t("schedule.dayView"))).toBe(true);
    });

    it("W switches to the week view", async () => {
      await ready();
      press("d");
      press("w");
      expect(pressed(i18n.t("schedule.weekView"))).toBe(true);
    });

    it("M switches to the month view", async () => {
      await ready();
      press("m");
      expect(pressed(i18n.t("schedule.monthView"))).toBe(true);
    });

    it("A switches to the list view and CapsLock does not matter", async () => {
      await ready();
      press("A");
      expect(pressed(i18n.t("schedule.listView"))).toBe(true);
    });

    it("C opens the create popover", async () => {
      await ready();
      press("c");
      expect(await screen.findByPlaceholderText(i18n.t("schedule.eventTitle"))).toBeTruthy();
    });

    it("Escape closes the popover", async () => {
      await ready();
      press("c");
      await screen.findByPlaceholderText(i18n.t("schedule.eventTitle"));
      press("Escape");
      expect(titleInput()).toBeNull();
    });

    it("? opens the shortcut list", async () => {
      await ready();
      press("?", { shiftKey: true });
      expect(await screen.findByRole("dialog", { name: i18n.t("schedule.shortcuts.title") })).toBeTruthy();
    });
  });

  describe("keys that must not act", () => {
    it("ignores letter keys typed in an input", async () => {
      await ready();
      const input = document.createElement("input");
      document.body.appendChild(input);
      press("m", {}, input);
      expect(pressed(i18n.t("schedule.monthView"))).toBe(false);
      input.remove();
    });

    it("Escape inside an input still closes the popover", async () => {
      await ready();
      press("c");
      const input = await screen.findByPlaceholderText(i18n.t("schedule.eventTitle"));
      press("Escape", {}, input);
      expect(titleInput()).toBeNull();
    });

    it("Escape during IME composition does not close the popover", async () => {
      await ready();
      press("c");
      const input = await screen.findByPlaceholderText(i18n.t("schedule.eventTitle"));
      press("Escape", { isComposing: true }, input);
      expect(titleInput()).not.toBeNull();
    });

    it("ignores Ctrl + letter", async () => {
      await ready();
      press("m", { ctrlKey: true });
      expect(pressed(i18n.t("schedule.monthView"))).toBe(false);
    });

    it("ignores Meta (Command) + letter", async () => {
      await ready();
      press("m", { metaKey: true });
      expect(pressed(i18n.t("schedule.monthView"))).toBe(false);
    });

    it("ignores Alt + letter", async () => {
      await ready();
      press("m", { altKey: true });
      expect(pressed(i18n.t("schedule.monthView"))).toBe(false);
    });

    it("ignores letter keys while a popover is open", async () => {
      await ready();
      press("c");
      await screen.findByPlaceholderText(i18n.t("schedule.eventTitle"));
      press("m");
      expect(pressed(i18n.t("schedule.monthView"))).toBe(false);
    });

    it("ignores letter keys while the shortcut list is open", async () => {
      await ready();
      press("?", { shiftKey: true });
      await screen.findByRole("dialog", { name: i18n.t("schedule.shortcuts.title") });
      press("m");
      expect(pressed(i18n.t("schedule.monthView"))).toBe(false);
    });
  });
});

describe("SchedulePage Google Meet (K12)", () => {
  const addMeetLabel = () => i18n.t("schedule.addMeet");
  const joinLabel = () => i18n.t("schedule.joinMeet");
  const MEET = "https://meet.google.com/abc-defg-hij";
  const openCreate = async () => {
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("schedule.create") }));
    await screen.findByPlaceholderText(i18n.t("schedule.eventTitle"));
  };
  const save = () => {
    fireEvent.change(screen.getByPlaceholderText(i18n.t("schedule.eventTitle")), { target: { value: "Meet Meeting" } });
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
  };
  const enableMeet = () => {
    answers.isTenantAdmin = true;
    answers.connected = true;
    answers.meetAvailable = true;
  };

  it("hides the Meet toggle when meet_available is false", async () => {
    answers.isTenantAdmin = true;
    answers.connected = true;
    answers.meetAvailable = false;
    view();
    await openCreate();
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith("/google-calendar/status"));
    expect(screen.queryByRole("switch", { name: addMeetLabel() })).toBeNull();
    save();
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const body = vi.mocked(api.post).mock.calls[0][1] as Record<string, unknown>;
    expect("add_meet" in body).toBe(false);
  });

  it("sends add_meet only when the toggle is on", async () => {
    enableMeet();
    view();
    await openCreate();
    const toggle = (await screen.findByRole("switch", { name: addMeetLabel() })) as HTMLInputElement;
    expect(toggle.checked).toBe(false);
    fireEvent.click(toggle);
    vi.mocked(api.post).mockResolvedValueOnce({ id: 1, meet_url: MEET });
    save();
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const body = vi.mocked(api.post).mock.calls[0][1] as Record<string, unknown>;
    expect(body.add_meet).toBe(true);
    expect(screen.queryByText(i18n.t("schedule.meetFailed"))).toBeNull();
  });

  it("does not send add_meet when the toggle is left off", async () => {
    enableMeet();
    view();
    await openCreate();
    await screen.findByRole("switch", { name: addMeetLabel() });
    save();
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const body = vi.mocked(api.post).mock.calls[0][1] as Record<string, unknown>;
    expect("add_meet" in body).toBe(false);
  });

  it("shows the failure banner when the reply has no meet_url", async () => {
    enableMeet();
    view();
    await openCreate();
    fireEvent.click(await screen.findByRole("switch", { name: addMeetLabel() }));
    vi.mocked(api.post).mockResolvedValueOnce({ id: 1, meet_url: null });
    save();
    expect(await screen.findByText(i18n.t("schedule.meetFailed"))).toBeTruthy();
    // 予定は保存済みなので小窓は閉じる
    await waitFor(() => expect(screen.queryByPlaceholderText(i18n.t("schedule.eventTitle"))).toBeNull());
  });

  it("shows the join link for an event with meet_url and no toggle on edit", async () => {
    enableMeet();
    answers.events = [apiEvent({ meet_url: MEET })];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    const link = (await screen.findByRole("link", { name: joinLabel() })) as HTMLAnchorElement;
    expect(link.getAttribute("href")).toBe(MEET);
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    await screen.findByPlaceholderText(i18n.t("schedule.eventTitle"));
    expect(screen.queryByRole("switch", { name: addMeetLabel() })).toBeNull();
    expect(screen.getByRole("link", { name: joinLabel() })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    const body = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect("add_meet" in body).toBe(false);
  });

  it("shows the toggle when editing an own event that has no Meet yet", async () => {
    enableMeet();
    answers.events = [apiEvent({ google_event_id: "g1" })];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    fireEvent.click(await screen.findByRole("switch", { name: addMeetLabel() }));
    vi.mocked(api.patch).mockResolvedValueOnce({ id: 1, meet_url: MEET });
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    expect((vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>).add_meet).toBe(true);
  });

  it("hides the toggle when editing an own event that was never sent to Google", async () => {
    enableMeet();
    answers.events = [apiEvent({ google_event_id: null })];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    await screen.findByPlaceholderText(i18n.t("schedule.eventTitle"));
    expect(screen.queryByRole("switch", { name: addMeetLabel() })).toBeNull();
  });

  it("does not show a join link for a URL outside meet.google.com", async () => {
    enableMeet();
    answers.events = [apiEvent({ meet_url: "https://evil.example.com/abc" })];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") });
    expect(screen.queryByRole("link", { name: joinLabel() })).toBeNull();
  });
});

describe("SchedulePage slot click opens create at the clicked hour", () => {
  const openAt = async (slotIndex: number | null) => {
    const { container } = view();
    await waitFor(() => expect(container.querySelectorAll(".schedule-day-column").length).toBeGreaterThan(0));
    if (slotIndex === null) {
      fireEvent.click(container.querySelector(".schedule-day-head") as HTMLElement);
    } else {
      const column = container.querySelectorAll(".schedule-day-column")[0];
      fireEvent.click(column.querySelectorAll(".schedule-slot")[slotIndex] as HTMLElement);
    }
    const inputs = await screen.findAllByLabelText(i18n.t("schedule.time"));
    return inputs as HTMLInputElement[];
  };

  it.each([
    [10, "10:00", "11:00"],
    [4, "04:00", "05:00"],
    [15, "15:00", "16:00"],
  ])("slot %i opens at %s-%s", async (index, start, end) => {
    const inputs = await openAt(index);
    expect(inputs[0].value).toBe(start);
    expect(inputs[1].value).toBe(end);
  });

  it("day head keeps the default 07:00-08:00", async () => {
    const inputs = await openAt(null);
    expect(inputs[0].value).toBe("07:00");
    expect(inputs[1].value).toBe("08:00");
  });
});
