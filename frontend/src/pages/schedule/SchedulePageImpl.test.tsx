/* eslint-disable local/no-japanese-literal -- テスト: 作る小窓の日時の 1 行が Google と同じ日本語で出ることを検証する（ADR-027・precedent: CalendarView.test.tsx） */
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { queryClient } from "../../lib/query/apiQuery";
import { TOPICS } from "../../lib/realtime/topics";
import SchedulePage from "./SchedulePageImpl";
import { formatTimeRange } from "../../components/calendarView.utils";
import { formatDateInput, formatDayLabel, formatDraftDateLine, formatTimeInput, getWeekDays } from "./schedule-utils";

/** 編集の画面（金型 EditorPage の dialog・名前は予定の編集） */
const editorDialog = () => screen.findByRole("dialog", { name: i18n.t("schedule.fullEditLabel") });

const realtimeRefresh = vi.hoisted(() => vi.fn());
vi.mock("../../hooks/useRealtimeRefresh", () => ({
  useRealtimeRefresh: realtimeRefresh,
}));

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: { uid: "user-a" } }),
}));

// FullCalendar は jsdom で描かない。金型を差し替え、渡された props を取り出せるようにする
const calendarProps = vi.hoisted(() => ({ current: null as null | Record<string, any> }));
vi.mock("../../components/CalendarView", () => ({
  CalendarView: (props: Record<string, any>) => {
    calendarProps.current = props;
    return (
      <div data-testid="calendar-view">
        {props.events.map((ev: { id: string; title: string }) => (
          <button key={ev.id} type="button" onClick={(e) => props.onEventClick?.(ev.id, e.currentTarget.getBoundingClientRect())}>
            {ev.title}
          </button>
        ))}
      </div>
    );
  },
}));

const answers = vi.hoisted(() => ({
  isTenantAdmin: false,
  connected: false,
  meetAvailable: false,
  events: [] as Array<Record<string, unknown>>,
  searchEvents: [] as Array<Record<string, unknown>>,
  shifts: [] as Array<Record<string, unknown>>,
  holidays: [] as Array<Record<string, unknown>>,
  canManageOthers: false,
  selfMissing: false,
  ownerColorKey: null as string | null,
  categories: [] as Array<Record<string, unknown>>,
  teams: [] as Array<{ id: number; name: string }>,
  /** GET /calendar/preferences の応答。null は「行が無い」（既定値の応答） */
  prefs: null as Record<string, unknown> | null,
  /** true の間、初期値の読み込みは失敗する */
  prefsFail: false as boolean,
  /** 名簿の team_ids（自分・ほかの人） */
  selfTeamIds: [] as number[],
  otherTeamIds: [] as number[],
  /** 入れた Promise が終わるまで、その応答を返さない（読み込みの順番の試験用） */
  gate: { perms: null as Promise<void> | null, prefs: null as Promise<void> | null, teams: null as Promise<void> | null },
}));

const DEFAULT_PREFS = {
  default_view: "week", week_start: 0, event_minutes: 60, auto_meet: false, open_owners: "self", open_team_id: null,
};

/** 種類の表の応答（GET /calendar/categories）。必要な行だけ並べる */
function categoryRow(key: string, over: Record<string, unknown> = {}) {
  return { key, name: null, color_key: null, default_share: "all", default_team_ids: [], sort_order: 1, is_active: true, ...over };
}

vi.mock("../../lib/api", () => ({
  api: {
    get: vi.fn(async (path: string) => {
      if (path === "/calendar/categories") return answers.categories;
      if (path === "/calendar/teams") {
        await answers.gate.teams;
        return answers.teams;
      }
      if (path === "/calendar/preferences") {
        if (answers.prefsFail) throw new Error("prefs failed");
        await answers.gate.prefs;
        return answers.prefs ?? DEFAULT_PREFS;
      }
      if (path === "/me/permissions") {
        await answers.gate.perms;
        return { permissions: answers.canManageOthers ? ["staff.view"] : [], is_tenant_admin: answers.isTenantAdmin };
      }
      if (path === "/google-calendar/status") return { connected: answers.connected, meet_available: answers.meetAvailable };
      if (path === "/calendar/owners") {
        return {
          can_manage_others: answers.canManageOthers,
          current_staff_id: 7,
          current_user_id: 101,
          owners: [
            { staff_id: 7, user_id: 101, staff_code: "A01", name: "Owner Self", primary_email: null, color_key: answers.ownerColorKey, is_self: true, team_ids: answers.selfTeamIds },
            { staff_id: 8, user_id: 202, staff_code: "B02", name: "Owner Other", primary_email: null, color_key: null, is_self: false, team_ids: answers.otherTeamIds },
          ].filter((o) => !(answers.selfMissing && o.is_self)),
        };
      }
      if (path.startsWith("/calendar/holidays")) return { holidays: answers.holidays };
      if (path.startsWith("/calendar/events/search")) return { events: answers.searchEvents };
      if (path.startsWith("/calendar/events")) return { events: answers.events };
      if (path === "/google-calendar/connect/start") return { auth_url: "https://accounts.example/auth" };
      if (path.startsWith("/shifts")) return answers.shifts;
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
  answers.searchEvents = [];
  answers.shifts = [];
  answers.holidays = [];
  answers.canManageOthers = false;
  answers.selfMissing = false;
  answers.ownerColorKey = null;
  answers.categories = [];
  answers.teams = [];
  answers.prefs = null;
  answers.prefsFail = false;
  answers.selfTeamIds = [];
  answers.otherTeamIds = [];
  answers.gate = { perms: null, prefs: null, teams: null };
  calendarProps.current = null;
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

describe("SchedulePage realtime refresh", () => {
  it("rereads the events cache when calendar.events arrives", async () => {
    view();
    await waitFor(() => expect(realtimeRefresh).toHaveBeenCalled());
    const [topics, reload] = realtimeRefresh.mock.calls[0] as [string[], () => void];
    expect(topics).toEqual([TOPICS.calendarEvents]);
    const spy = vi.spyOn(queryClient, "invalidateQueries");
    reload();
    expect(spy).toHaveBeenCalledWith({ queryKey: ["api", "user-a", "calendar", "events"] });
  });
});

describe("SchedulePage header (settings page owns the Google connection)", () => {
  it("has no Google connect button in the header, for an admin either", async () => {
    answers.isTenantAdmin = true;
    view();
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith("/google-calendar/status"));
    await screen.findByRole("button", { name: i18n.t("schedule.create") });
    expect(screen.queryByRole("button", { name: /Googleカレンダー連携|連携済/ })).toBeNull();
    expect(mockGet).not.toHaveBeenCalledWith("/google-calendar/connect/start");
  });

  it("shows the settings gear to a tenant admin without staff.view", async () => {
    answers.isTenantAdmin = true;
    answers.canManageOthers = false;
    view();
    expect(await screen.findByRole("button", { name: i18n.t("schedule.settings") })).toBeTruthy();
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

describe("SchedulePage share select (self / all / team)", () => {
  const label = () => i18n.t("schedule.shareLabel");

  it("shows the share select on create, default all, and sends personal when set to self", async () => {
    view();
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("schedule.create") }));
    const toggle = (await screen.findByRole("combobox", { name: label() })) as HTMLSelectElement;
    expect(toggle.value).toBe("all");
    fireEvent.change(toggle, { target: { value: "self" } });
    expect(toggle.value).toBe("self");
    fireEvent.change(screen.getByLabelText(i18n.t("schedule.eventTitle")), { target: { value: "Secret" } });
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const [path, body] = vi.mocked(api.post).mock.calls[0] as [string, Record<string, unknown>];
    expect(path).toBe("/calendar/events");
    expect(body.calendar_type).toBe("personal");
  });

  it("shows the share select when editing own event and sends calendar_type", async () => {
    answers.events = [apiEvent({})];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    const dialog = await editorDialog();
    expect(await within(dialog).findByRole("combobox", { name: label() })).toBeTruthy();
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    const body = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect(body.calendar_type).toBe("shared");
  });

  it("hides the share select and omits calendar_type when editing someone else's event", async () => {
    answers.canManageOthers = true;
    answers.events = [apiEvent({ id: 2, user_id: 202, created_by_user_id: 202, title: "Other Event" })];
    view();
    fireEvent.click(await screen.findByRole("checkbox", { name: "Owner Other" }));
    fireEvent.click(await screen.findByText("Other Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    const dialog = await editorDialog();
    await within(dialog).findByLabelText(i18n.t("schedule.eventTitle"));
    expect(within(dialog).queryByRole("combobox", { name: label() })).toBeNull();
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    const body = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect("calendar_type" in body).toBe(false);
  });
});

describe("SchedulePage clearing description and location (design §11)", () => {
  it("K18: sends empty strings when an existing description and location are cleared", async () => {
    answers.events = [apiEvent({ description: "Old note", location: "Room A" })];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    const dialog = await editorDialog();
    fireEvent.change(within(dialog).getByLabelText(i18n.t("schedule.eventDescription")), { target: { value: "" } });
    fireEvent.change(within(dialog).getByLabelText(i18n.t("schedule.eventLocation")), { target: { value: "" } });
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    const body = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect(body.description).toBe("");
    expect(body.location).toBe("");
  });

  it("K18: keeps sending the text when it is not cleared", async () => {
    answers.events = [apiEvent({ description: "Old note", location: "Room A" })];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    const dialog = await editorDialog();
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    const body = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect(body.description).toBe("Old note");
    expect(body.location).toBe("Room A");
  });

  it("K19: does not send them when the event had none", async () => {
    answers.events = [apiEvent({})];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    const dialog = await editorDialog();
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    const body = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    const sent = JSON.parse(JSON.stringify(body)) as Record<string, unknown>;
    expect(sent).not.toHaveProperty("description");
    expect(sent).not.toHaveProperty("location");
  });

  it("K19: does not send them when creating", async () => {
    view();
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("schedule.create") }));
    fireEvent.change(await screen.findByLabelText(i18n.t("schedule.eventTitle")), { target: { value: "New" } });
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const body = vi.mocked(api.post).mock.calls[0][1] as Record<string, unknown>;
    const sent = JSON.parse(JSON.stringify(body)) as Record<string, unknown>;
    expect(sent).not.toHaveProperty("description");
    expect(sent).not.toHaveProperty("location");
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
  const viewSwitch = () => {
    const el = document.querySelector('button[aria-haspopup="menu"]');
    if (!el) throw new Error("view switch button is missing");
    return el;
  };
  const pressed = (name: string) => viewSwitch().textContent === name;
  const press = (key: string, init: Record<string, unknown> = {}, target: Element = document.body) =>
    fireEvent.keyDown(target, { key, ...init });
  const ready = async () => {
    view();
    await screen.findByRole("button", { name: i18n.t("schedule.create") });
  };
  const titleInput = () => screen.queryByLabelText(i18n.t("schedule.eventTitle"));

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

    it("X switches to the 3-day view", async () => {
      await ready();
      press("x");
      expect(pressed(i18n.t("schedule.threeDayView"))).toBe(true);
    });

    it("the menu button hides and shows the left panel, and the header has no subtitle", async () => {
      await ready();
      const toggle = screen.getByRole("button", { name: i18n.t("schedule.togglePanel") });
      expect(toggle.getAttribute("aria-expanded")).toBe("true");
      fireEvent.click(toggle);
      expect(toggle.getAttribute("aria-expanded")).toBe("false");
      expect(screen.queryByRole("button", { name: i18n.t("schedule.create") })).toBeNull();
      fireEvent.click(toggle);
      expect(toggle.getAttribute("aria-expanded")).toBe("true");
      expect(screen.getByRole("button", { name: i18n.t("schedule.create") })).toBeTruthy();
      expect(document.querySelectorAll(".page-subtitle")).toHaveLength(0);
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
      expect(await screen.findByLabelText(i18n.t("schedule.eventTitle"))).toBeTruthy();
    });

    it("Escape closes the popover", async () => {
      await ready();
      press("c");
      await screen.findByLabelText(i18n.t("schedule.eventTitle"));
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
      const input = await screen.findByLabelText(i18n.t("schedule.eventTitle"));
      press("Escape", {}, input);
      expect(titleInput()).toBeNull();
    });

    it("Escape during IME composition does not close the popover", async () => {
      await ready();
      press("c");
      const input = await screen.findByLabelText(i18n.t("schedule.eventTitle"));
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
      await screen.findByLabelText(i18n.t("schedule.eventTitle"));
      press("m");
      expect(pressed(i18n.t("schedule.monthView"))).toBe(false);
      expect(pressed(i18n.t("schedule.weekView"))).toBe(true);
    });

    it("ignores letter keys while the shortcut list is open", async () => {
      await ready();
      press("?", { shiftKey: true });
      await screen.findByRole("dialog", { name: i18n.t("schedule.shortcuts.title") });
      press("m");
      expect(pressed(i18n.t("schedule.monthView"))).toBe(false);
      expect(pressed(i18n.t("schedule.weekView"))).toBe(true);
    });
  });
});

describe("SchedulePage Google Meet (K12)", () => {
  const addMeetLabel = () => i18n.t("schedule.addMeet");
  const joinLabel = () => i18n.t("schedule.joinMeet");
  const MEET = "https://meet.google.com/abc-defg-hij";
  const openCreate = async () => {
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("schedule.create") }));
    await screen.findByLabelText(i18n.t("schedule.eventTitle"));
  };
  const save = () => {
    fireEvent.change(screen.getByLabelText(i18n.t("schedule.eventTitle")), { target: { value: "Meet Meeting" } });
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
  };
  const enableMeet = () => {
    answers.isTenantAdmin = true;
    answers.connected = true;
    answers.meetAvailable = true;
  };

  it("hides the Meet row when meet_available is false", async () => {
    answers.isTenantAdmin = true;
    answers.connected = true;
    answers.meetAvailable = false;
    view();
    await openCreate();
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith("/google-calendar/status"));
    expect(screen.queryByRole("button", { name: addMeetLabel() })).toBeNull();
    save();
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const body = vi.mocked(api.post).mock.calls[0][1] as Record<string, unknown>;
    expect("add_meet" in body).toBe(false);
  });

  it("sends add_meet only when the Meet row is on", async () => {
    enableMeet();
    view();
    await openCreate();
    const row = await screen.findByRole("button", { name: addMeetLabel() });
    fireEvent.click(row);
    expect(screen.getByText(i18n.t("schedule.meetPending"))).toBeTruthy();
    expect(screen.getByRole("button", { name: i18n.t("schedule.removeMeet") })).toBeTruthy();
    vi.mocked(api.post).mockResolvedValueOnce({ id: 1, meet_url: MEET });
    save();
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const body = vi.mocked(api.post).mock.calls[0][1] as Record<string, unknown>;
    expect(body.add_meet).toBe(true);
    expect(screen.queryByText(i18n.t("schedule.meetFailed"))).toBeNull();
  });

  it("does not send add_meet when the Meet row is left off", async () => {
    enableMeet();
    view();
    await openCreate();
    await screen.findByRole("button", { name: addMeetLabel() });
    save();
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const body = vi.mocked(api.post).mock.calls[0][1] as Record<string, unknown>;
    expect("add_meet" in body).toBe(false);
  });

  it("shows the failure banner when the reply has no meet_url", async () => {
    enableMeet();
    view();
    await openCreate();
    fireEvent.click(await screen.findByRole("button", { name: addMeetLabel() }));
    vi.mocked(api.post).mockResolvedValueOnce({ id: 1, meet_url: null });
    save();
    expect(await screen.findByText(i18n.t("schedule.meetFailed"))).toBeTruthy();
    // 予定は保存済みなので小窓は閉じる
    await waitFor(() => expect(screen.queryByLabelText(i18n.t("schedule.eventTitle"))).toBeNull());
  });

  it("G28: the banner close is a mold Button with an svg icon and dismisses the banner", async () => {
    enableMeet();
    view();
    await openCreate();
    fireEvent.click(await screen.findByRole("button", { name: addMeetLabel() }));
    vi.mocked(api.post).mockResolvedValueOnce({ id: 1, meet_url: null });
    save();
    const message = i18n.t("schedule.meetFailed");
    expect(await screen.findByText(message)).toBeTruthy();
    const banner = screen.getByText(message).closest("div");
    if (!banner) throw new Error("banner is missing");
    const close = Array.from(banner.querySelectorAll("button")).find(
      (b) => b.getAttribute("aria-label") === i18n.t("common.close"),
    );
    if (!close) throw new Error("close button is missing");
    expect(close.className).toContain("comp-btn--sm");
    expect(close.className).toContain("comp-btn--icon-only");
    expect(close.className).toContain("schedule-banner__close");
    expect(close.querySelector("svg")).not.toBeNull();
    fireEvent.click(close);
    await waitFor(() => expect(screen.queryByText(message)).toBeNull());
  });

  it("shows the join link for an event with meet_url and no Meet row on edit", async () => {
    enableMeet();
    answers.events = [apiEvent({ meet_url: MEET })];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    const link = (await screen.findByRole("link", { name: joinLabel() })) as HTMLAnchorElement;
    expect(link.getAttribute("href")).toBe(MEET);
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    const dialog = await editorDialog();
    await within(dialog).findByLabelText(i18n.t("schedule.eventTitle"));
    expect(within(dialog).queryByRole("button", { name: addMeetLabel() })).toBeNull();
    expect(within(dialog).getByRole("link", { name: joinLabel() })).toBeTruthy();
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    const body = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect("add_meet" in body).toBe(false);
  });

  it("shows the Meet row when editing an own event that has no Meet yet", async () => {
    enableMeet();
    answers.events = [apiEvent({ google_event_id: "g1" })];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    const dialog = await editorDialog();
    fireEvent.click(await within(dialog).findByRole("button", { name: addMeetLabel() }));
    vi.mocked(api.patch).mockResolvedValueOnce({ id: 1, meet_url: MEET });
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    expect((vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>).add_meet).toBe(true);
  });

  it("hides the Meet row when editing an own event that was never sent to Google", async () => {
    enableMeet();
    answers.events = [apiEvent({ google_event_id: null })];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    const dialog = await editorDialog();
    await within(dialog).findByLabelText(i18n.t("schedule.eventTitle"));
    expect(within(dialog).queryByRole("button", { name: addMeetLabel() })).toBeNull();
  });

  it("does not show a join link for a URL outside meet.google.com", async () => {
    enableMeet();
    answers.events = [apiEvent({ meet_url: "https://evil.example.com/abc" })];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") });
    expect(screen.queryByRole("link", { name: joinLabel() })).toBeNull();
  });

  it("pressing the Meet row then the remove button restores the row and sends no add_meet", async () => {
    enableMeet();
    view();
    await openCreate();
    fireEvent.click(await screen.findByRole("button", { name: addMeetLabel() }));
    fireEvent.click(screen.getByRole("button", { name: i18n.t("schedule.removeMeet") }));
    expect(screen.getByRole("button", { name: addMeetLabel() })).toBeTruthy();
    save();
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const body = vi.mocked(api.post).mock.calls[0][1] as Record<string, unknown>;
    expect("add_meet" in body).toBe(false);
  });

  it("has no Meet switch in the create popover, the edit popover or the full editor", async () => {
    enableMeet();
    answers.events = [apiEvent({ google_event_id: "g1" })];
    view();
    await openCreate();
    await screen.findByRole("button", { name: addMeetLabel() });
    expect(screen.queryByRole("switch", { name: /Google Meet/ })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: i18n.t("schedule.moreOptions") }));
    await screen.findByRole("dialog", { name: i18n.t("schedule.fullEditLabel") });
    expect(screen.queryByRole("switch", { name: /Google Meet/ })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.close") }));
    fireEvent.keyDown(document.body, { key: "Escape" });
    await waitFor(() => expect(screen.queryByLabelText(i18n.t("schedule.eventTitle"))).toBeNull());
    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    const editDialog = await editorDialog();
    await within(editDialog).findByRole("button", { name: addMeetLabel() });
    expect(screen.queryByRole("switch", { name: /Google Meet/ })).toBeNull();
  });
});

describe("SchedulePage on CalendarView", () => {
  const ready = async () => {
    view();
    await screen.findByRole("button", { name: i18n.t("schedule.create") });
    await waitFor(() => expect(calendarProps.current).not.toBeNull());
  };
  const selectRange = (start: Date, end: Date, allDay: boolean) => {
    act(() => {
      calendarProps.current?.onSelectRange(start, end, allDay, null);
    });
  };
  const pendingOf = () =>
    (calendarProps.current?.events as Array<Record<string, any>>).find((ev) => ev.id === "pending");
  const eventOf = (id: string) =>
    (calendarProps.current?.events as Array<Record<string, any>>).find((ev) => ev.id === id);

  it.each([
    [10, "10:00", "11:00", "午前10時～午前11時"],
    [4, "04:00", "05:00", "午前4時～午前5時"],
    [15, "15:00", "16:00", "午後3時～午後4時"],
  ])("T1: a selected range at %i o'clock opens at %s-%s", async (hour, start, end, lineText) => {
    await ready();
    selectRange(new Date(2026, 10, 10, hour, 0), new Date(2026, 10, 10, hour + 1, 0), false);
    const line = await screen.findByRole("button", { name: new RegExp(lineText) });
    fireEvent.click(line);
    const inputs = (await screen.findAllByLabelText(i18n.t("schedule.time"))) as HTMLInputElement[];
    expect(inputs[0].value).toBe(start);
    expect(inputs[1].value).toBe(end);
  });

  it("C1: selecting a range focuses the title field and shows no header label", async () => {
    await ready();
    selectRange(new Date(2026, 10, 10, 10, 0), new Date(2026, 10, 10, 11, 0), false);
    await waitFor(() =>
      expect(document.activeElement).toBe(screen.getByLabelText(i18n.t("schedule.eventTitle"))),
    );
    expect(screen.queryByText(i18n.t("schedule.addEvent"))).toBeNull();
  });

  it("C2: location and description are closed lines that open on click and take focus", async () => {
    await ready();
    selectRange(new Date(2026, 10, 10, 10, 0), new Date(2026, 10, 10, 11, 0), false);
    await screen.findByLabelText(i18n.t("schedule.eventTitle"));
    expect(screen.queryByPlaceholderText(i18n.t("schedule.locationPlaceholder"))).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: i18n.t("schedule.locationPlaceholder") }));
    const location = await screen.findByPlaceholderText(i18n.t("schedule.locationPlaceholder"));
    await waitFor(() => expect(document.activeElement).toBe(location));
    expect(screen.queryByPlaceholderText(i18n.t("schedule.descriptionPlaceholder"))).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: i18n.t("schedule.descriptionPlaceholder") }));
    const description = await screen.findByPlaceholderText(i18n.t("schedule.descriptionPlaceholder"));
    await waitFor(() => expect(document.activeElement).toBe(description));
  });

  describe("便12: 作る小窓と仮の箱（G42〜G50）", () => {
    const D = (day: number, h = 0, mi = 0) => new Date(2026, 10, day, h, mi);
    const openTimed = async () => {
      await ready();
      selectRange(D(10, 10), D(10, 11), false);
      await screen.findByLabelText(i18n.t("schedule.eventTitle"));
    };
    const draftLine = (s: Date, e: Date, allDay = false) =>
      formatDraftDateLine(
        {
          startDate: formatDateInput(s),
          startTime: formatTimeInput(s),
          endDate: formatDateInput(e),
          endTime: formatTimeInput(e),
          allDay,
        },
        i18n.t.bind(i18n) as never,
        i18n.language,
      );
    const openDateRow = async (lineText: RegExp) => {
      fireEvent.click(await screen.findByRole("button", { name: lineText }));
      return (await screen.findAllByLabelText(i18n.t("schedule.time"))) as HTMLInputElement[];
    };

    it("the create popover has no backdrop, the detail popover has one", async () => {
      answers.events = [apiEvent({})];
      view();
      await screen.findByText("Own Event");
      await waitFor(() => expect(calendarProps.current).not.toBeNull());
      selectRange(D(10, 10), D(10, 11), false);
      await screen.findByLabelText(i18n.t("schedule.eventTitle"));
      expect(document.querySelectorAll(".schedule-popover-backdrop")).toHaveLength(0);
      fireEvent.keyDown(document.body, { key: "Escape" });
      await waitFor(() => expect(document.querySelector(".schedule-popover")).toBeNull());
      fireEvent.click(await screen.findByText("Own Event"));
      await waitFor(() => expect(document.querySelectorAll(".schedule-popover-backdrop")).toHaveLength(1));
    });

    it("the pending box is editable and follows the title", async () => {
      await openTimed();
      expect(pendingOf()?.editable).toBe(true);
      expect(pendingOf()?.title).toBe(i18n.t("schedule.noTitle"));
      fireEvent.change(screen.getByLabelText(i18n.t("schedule.eventTitle")), { target: { value: "試し" } });
      await waitFor(() => expect(pendingOf()?.title).toBe("試し"));
    });

    it("changing only the start time moves the end too (10:00-11:00 to 15:00-16:00)", async () => {
      await openTimed();
      const inputs = await openDateRow(/午前10時/);
      fireEvent.change(inputs[0], { target: { value: "15:00" } });
      await waitFor(() => expect(pendingOf()?.start).toEqual(D(10, 15)));
      expect(pendingOf()?.end).toEqual(D(10, 16));
    });

    it("moving the pending box changes only the draft and saves the moved time", async () => {
      await openTimed();
      const revert = vi.fn();
      act(() => {
        calendarProps.current?.onEventMove("pending", D(11, 14), D(11, 15), false, revert);
      });
      const line = await screen.findByRole("button", { name: draftLine(D(11, 14), D(11, 15)) });
      expect(line).toBeTruthy();
      expect(api.patch).not.toHaveBeenCalled();
      expect(api.post).not.toHaveBeenCalled();
      expect(revert).not.toHaveBeenCalled();
      fireEvent.change(screen.getByLabelText(i18n.t("schedule.eventTitle")), { target: { value: "Moved" } });
      fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
      await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));
      const body = vi.mocked(api.post).mock.calls[0][1] as Record<string, unknown>;
      expect(body.start_datetime).toBe(D(11, 14).toISOString());
      expect(body.end_datetime).toBe(D(11, 15).toISOString());
      expect(api.patch).not.toHaveBeenCalled();
    });

    it("resizing the pending box changes the end time in the draft", async () => {
      await openTimed();
      act(() => {
        calendarProps.current?.onEventResize("pending", D(10, 10), D(10, 11, 30), vi.fn());
      });
      const inputs = await openDateRow(/午前10時/);
      await waitFor(() => expect(inputs[1].value).toBe("11:30"));
    });

    it("resizing an all-day pending box keeps it all-day", async () => {
      await ready();
      selectRange(D(10), D(12), true);
      await screen.findByLabelText(i18n.t("schedule.eventTitle"));
      act(() => {
        calendarProps.current?.onEventResize("pending", D(10), D(13), vi.fn());
      });
      await waitFor(() => expect(pendingOf()?.end).toEqual(D(13)));
      expect(pendingOf()?.allDay).toBe(true);
    });

    it("moving an all-day pending box one week later moves the box", async () => {
      await ready();
      selectRange(D(10), D(12), true);
      await screen.findByLabelText(i18n.t("schedule.eventTitle"));
      act(() => {
        calendarProps.current?.onEventMove("pending", D(17), D(19), true, vi.fn());
      });
      await waitFor(() => expect(pendingOf()?.start).toEqual(D(17)));
      expect(pendingOf()?.end).toEqual(D(19));
    });

    it("pressing outside closes the popover and the box; pressing inside the calendar or popover does not", async () => {
      await openTimed();
      fireEvent.pointerDown(screen.getByTestId("calendar-view"));
      fireEvent.pointerDown(screen.getByLabelText(i18n.t("schedule.eventTitle")));
      expect(document.querySelector(".schedule-popover")).not.toBeNull();
      expect(pendingOf()).toBeDefined();
      fireEvent.pointerDown(document.body);
      await waitFor(() => expect(document.querySelector(".schedule-popover")).toBeNull());
      await waitFor(() => expect(pendingOf()).toBeUndefined());
    });

    it("the footer has more options then save and no cancel; more options opens the full editor", async () => {
      await openTimed();
      const footer = document.querySelector(".schedule-popover__footer") as HTMLElement;
      const labels = Array.from(footer.querySelectorAll("button")).map((b) => b.textContent);
      expect(labels).toEqual([i18n.t("schedule.moreOptions"), i18n.t("common.save")]);
      expect(screen.queryByRole("button", { name: i18n.t("common.cancel") })).toBeNull();
      fireEvent.change(screen.getByLabelText(i18n.t("schedule.eventTitle")), { target: { value: "試し" } });
      fireEvent.click(screen.getByRole("button", { name: i18n.t("schedule.moreOptions") }));
      const dialog = await screen.findByRole("dialog", { name: i18n.t("schedule.fullEditLabel") });
      expect((within(dialog).getByLabelText(i18n.t("schedule.eventTitle")) as HTMLInputElement).value).toBe("試し");
      const startTime = within(dialog).getByLabelText(`${i18n.t("schedule.eventStart")} ${i18n.t("schedule.time")}`) as HTMLInputElement;
      const endTime = within(dialog).getByLabelText(`${i18n.t("schedule.eventEnd")} ${i18n.t("schedule.time")}`) as HTMLInputElement;
      expect(startTime.value).toBe("10:00");
      expect(endTime.value).toBe("11:00");
      expect((within(dialog).getAllByDisplayValue("2026-11-10") as HTMLInputElement[]).length).toBeGreaterThan(0);
      expect(within(dialog).getByPlaceholderText(i18n.t("schedule.locationPlaceholder"))).toBeTruthy();
      expect(within(dialog).getByPlaceholderText(i18n.t("schedule.descriptionPlaceholder"))).toBeTruthy();
      expect(document.querySelector(".schedule-popover")).toBeNull();
    });

    it("places the create popover beside the box rect reported by the calendar", async () => {
      await openTimed();
      act(() => {
        calendarProps.current?.onEventRect("pending", { top: 100, left: 200, right: 300, bottom: 140, width: 100, height: 40 });
      });
      await waitFor(() => {
        const el = document.querySelector(".schedule-popover--create") as HTMLElement;
        expect(el.style.left).toBe("308px");
      });
    });
  });

  describe("SchedulePage full editor (G53-G56)", () => {
    const D = (day: number, h = 0, mi = 0) => new Date(2026, 10, day, h, mi);
    const openTimed = async () => {
      await ready();
      selectRange(D(10, 10), D(10, 11), false);
      await screen.findByLabelText(i18n.t("schedule.eventTitle"));
    };
    const openFull = async () => {
      await openTimed();
      fireEvent.change(screen.getByLabelText(i18n.t("schedule.eventTitle")), { target: { value: "試し" } });
      fireEvent.click(screen.getByRole("button", { name: i18n.t("schedule.moreOptions") }));
      return screen.findByRole("dialog", { name: i18n.t("schedule.fullEditLabel") });
    };
    const titleValue = () => (screen.getByLabelText(i18n.t("schedule.eventTitle")) as HTMLInputElement).value;

    it("1: the close button returns to the popover with the title and the pending box, no save call", async () => {
      await openFull();
      fireEvent.click(screen.getByRole("button", { name: i18n.t("common.close") }));
      await waitFor(() => expect(screen.queryByRole("dialog", { name: i18n.t("schedule.fullEditLabel") })).toBeNull());
      expect(document.querySelector(".schedule-popover")).not.toBeNull();
      expect(titleValue()).toBe("試し");
      expect(pendingOf()).toBeDefined();
      expect(api.post).not.toHaveBeenCalled();
      expect(api.patch).not.toHaveBeenCalled();
    });

    it("2: Escape does the same as the close button", async () => {
      await openFull();
      fireEvent.keyDown(document, { key: "Escape" });
      await waitFor(() => expect(screen.queryByRole("dialog", { name: i18n.t("schedule.fullEditLabel") })).toBeNull());
      expect(document.querySelector(".schedule-popover")).not.toBeNull();
      expect(titleValue()).toBe("試し");
      expect(pendingOf()).toBeDefined();
      expect(api.post).not.toHaveBeenCalled();
      expect(api.patch).not.toHaveBeenCalled();
    });

    it("3: saving from the dialog sends the same body as saving from the popover", async () => {
      const dialog = await openFull();
      fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.save") }));
      await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));
      const pick = (b: Record<string, unknown>) => ({
        title: b.title,
        start_datetime: b.start_datetime,
        end_datetime: b.end_datetime,
        is_all_day: b.is_all_day,
        category: b.category,
      });
      const fromDialog = pick(vi.mocked(api.post).mock.calls[0][1] as Record<string, unknown>);
      await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
      await waitFor(() => expect(document.querySelector(".schedule-popover")).toBeNull());

      cleanup();
      queryClient.clear();
      vi.mocked(api.post).mockClear();
      calendarProps.current = null;
      await openTimed();
      fireEvent.change(screen.getByLabelText(i18n.t("schedule.eventTitle")), { target: { value: "試し" } });
      fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
      await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));
      const fromPopover = pick(vi.mocked(api.post).mock.calls[0][1] as Record<string, unknown>);
      expect(fromDialog).toEqual(fromPopover);
    });

    it("4: a failed save keeps the dialog with the error, and closing clears the error", async () => {
      const dialog = await openFull();
      vi.mocked(api.post).mockRejectedValueOnce(new Error("boom"));
      fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.save") }));
      const still = await screen.findByRole("dialog", { name: i18n.t("schedule.fullEditLabel") });
      expect(await within(still).findByText("boom")).toBeTruthy();
      fireEvent.click(screen.getByRole("button", { name: i18n.t("common.close") }));
      await waitFor(() => expect(screen.queryByRole("dialog", { name: i18n.t("schedule.fullEditLabel") })).toBeNull());
      expect(document.querySelector(".schedule-error")?.textContent ?? "").not.toContain("boom");
    });

    it("5: letter shortcuts do nothing while the dialog is open", async () => {
      await openFull();
      expect(calendarProps.current?.mode).not.toBe("month");
      fireEvent.keyDown(document.body, { key: "m" });
      expect(calendarProps.current?.mode).not.toBe("month");
    });

    it("6: closing returns the focus to the title field of the popover", async () => {
      await openFull();
      fireEvent.click(screen.getByRole("button", { name: i18n.t("common.close") }));
      await waitFor(() =>
        expect(document.activeElement).toBe(screen.getByLabelText(i18n.t("schedule.eventTitle"))),
      );
    });

    it("7: Escape during IME composition keeps the dialog", async () => {
      await openFull();
      fireEvent.keyDown(document, { key: "Escape", isComposing: true });
      expect(screen.getByRole("dialog", { name: i18n.t("schedule.fullEditLabel") })).toBeTruthy();
    });
  });

  describe("SchedulePage edit page (EP1-EP6)", () => {
    const openEdit = async (events: Array<Record<string, unknown>> = [apiEvent({})]) => {
      answers.events = events;
      view();
      fireEvent.click(await screen.findByText("Own Event"));
      fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
      return editorDialog();
    };

    it("EP1: editing opens the dialog with the event title and no small popover", async () => {
      const dialog = await openEdit();
      expect((within(dialog).getByLabelText(i18n.t("schedule.eventTitle")) as HTMLInputElement).value).toBe("Own Event");
      expect(document.querySelector(".schedule-popover")).toBeNull();
    });

    it("EP2: closing with the close button or Escape leaves no dialog, no popover and no save call", async () => {
      const dialog = await openEdit();
      fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.close") }));
      await waitFor(() => expect(screen.queryByRole("dialog", { name: i18n.t("schedule.fullEditLabel") })).toBeNull());
      expect(document.querySelector(".schedule-popover")).toBeNull();
      expect(api.patch).not.toHaveBeenCalled();
      expect(api.post).not.toHaveBeenCalled();

      fireEvent.click(await screen.findByText("Own Event"));
      fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
      await editorDialog();
      fireEvent.keyDown(document, { key: "Escape" });
      await waitFor(() => expect(screen.queryByRole("dialog", { name: i18n.t("schedule.fullEditLabel") })).toBeNull());
      expect(document.querySelector(".schedule-popover")).toBeNull();
      expect(api.patch).not.toHaveBeenCalled();
      expect(api.post).not.toHaveBeenCalled();
    });

    it("EP3: saving sends one PATCH and closes; a failed save keeps the dialog open with the alert inside", async () => {
      const dialog = await openEdit();
      vi.mocked(api.patch).mockRejectedValueOnce(new Error("boom"));
      fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.save") }));
      const still = await editorDialog();
      const alert = await within(still).findByRole("alert");
      expect(alert.textContent).toContain("boom");
      expect(api.patch).toHaveBeenCalledTimes(1);

      fireEvent.click(within(still).getByRole("button", { name: i18n.t("common.save") }));
      await waitFor(() => expect(api.patch).toHaveBeenCalledTimes(2));
      expect(vi.mocked(api.patch).mock.calls[1][0]).toMatch(/^\/calendar\/events\/\d+$/);
      await waitFor(() => expect(screen.queryByRole("dialog", { name: i18n.t("schedule.fullEditLabel") })).toBeNull());
    });

    it("EP4: the card lists Meet, location, category, share, description in this order", async () => {
      answers.isTenantAdmin = true;
      answers.connected = true;
      answers.meetAvailable = true;
      const dialog = await openEdit([apiEvent({ google_event_id: "g1" })]);
      const meet = await within(dialog).findByRole("button", { name: i18n.t("schedule.addMeet") });
      const location = within(dialog).getByLabelText(i18n.t("schedule.eventLocation"));
      const category = within(dialog).getByLabelText(i18n.t("schedule.category"));
      const share = within(dialog).getByRole("combobox", { name: i18n.t("schedule.shareLabel") });
      const description = within(dialog).getByLabelText(i18n.t("schedule.eventDescription"));
      const follows = (a: Node, b: Node) => Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
      expect(follows(meet, location)).toBe(true);
      expect(follows(location, category)).toBe(true);
      expect(follows(category, share)).toBe(true);
      expect(follows(share, description)).toBe(true);
    });

    it("EP5: all day is a checkbox in the edit page and a switch in the create popover", async () => {
      const dialog = await openEdit();
      expect(within(dialog).getByRole("checkbox", { name: i18n.t("schedule.allDay") })).toBeTruthy();
      expect(within(dialog).queryByRole("switch", { name: i18n.t("schedule.allDay") })).toBeNull();
      fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.close") }));
      await waitFor(() => expect(screen.queryByRole("dialog", { name: i18n.t("schedule.fullEditLabel") })).toBeNull());

      cleanup();
      calendarProps.current = null;
      view();
      fireEvent.click(await screen.findByRole("button", { name: i18n.t("schedule.create") }));
      await screen.findByLabelText(i18n.t("schedule.eventTitle"));
      fireEvent.click(document.querySelector(".schedule-popover__line") as HTMLElement);
      expect(await screen.findByRole("switch", { name: i18n.t("schedule.allDay") })).toBeTruthy();
    });

    it("EP6: the schedule page root and the edit dialog carry the gcal-colors class", async () => {
      const dialog = await openEdit();
      expect(document.querySelector(".schedule-page")?.classList.contains("gcal-colors")).toBe(true);
      expect(dialog.classList.contains("gcal-colors")).toBe(true);
    });
  });

  it("C3: the single view button opens a menu of four views and picks one", async () => {
    await ready();
    const button = screen.getByRole("button", { name: i18n.t("schedule.weekView") });
    fireEvent.click(button);
    const menu = await screen.findByRole("menu");
    expect(menu).toBeTruthy();
    expect(screen.getAllByRole("menuitem")).toHaveLength(5);
    fireEvent.click(screen.getByRole("menuitem", { name: i18n.t("schedule.monthView") }));
    await waitFor(() => expect(calendarProps.current?.mode).toBe("month"));
    await waitFor(() => expect(screen.queryByRole("menu")).toBeNull());
  });

  it("C4: letter shortcuts are ignored while the view menu is open", async () => {
    await ready();
    fireEvent.click(screen.getByRole("button", { name: i18n.t("schedule.weekView") }));
    await screen.findByRole("menu");
    fireEvent.keyDown(document.body, { key: "d" });
    expect(document.querySelector('button[aria-haspopup="menu"]')?.textContent).toBe(i18n.t("schedule.weekView"));
    fireEvent.keyDown(document.body, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("menu")).toBeNull());
    fireEvent.keyDown(document.body, { key: "d" });
    await waitFor(() =>
      expect(document.querySelector('button[aria-haspopup="menu"]')?.textContent).toBe(i18n.t("schedule.dayView")),
    );
  });

  it("T2: a pending box shows while creating and goes away when the popover closes", async () => {
    await ready();
    expect(pendingOf()).toBeUndefined();
    selectRange(new Date(2026, 10, 10, 10, 0), new Date(2026, 10, 10, 11, 0), false);
    await screen.findByLabelText(i18n.t("schedule.eventTitle"));
    const pending = pendingOf();
    expect(pending?.id).toBe("pending");
    expect(pending?.title).toBe(i18n.t("schedule.noTitle"));
    expect(pending?.editable).toBe(true);
    fireEvent.keyDown(document.body, { key: "Escape" });
    await waitFor(() => expect(pendingOf()).toBeUndefined());
  });

  it("T3: a one-day click in the month view keeps the 07:00-08:00 default", async () => {
    await ready();
    fireEvent.keyDown(document.body, { key: "m" });
    await waitFor(() => expect(calendarProps.current?.mode).toBe("month"));
    selectRange(new Date(2026, 10, 10), new Date(2026, 10, 11), true);
    fireEvent.click(await screen.findByRole("button", { name: /午前7時～午前8時/ }));
    const inputs = (await screen.findAllByLabelText(i18n.t("schedule.time"))) as HTMLInputElement[];
    expect(inputs[0].value).toBe("07:00");
    expect(inputs[1].value).toBe("08:00");
    expect(pendingOf()).toBeUndefined();
  });

  it("T4: dragging several days in the month view opens an all-day event", async () => {
    await ready();
    fireEvent.keyDown(document.body, { key: "m" });
    await waitFor(() => expect(calendarProps.current?.mode).toBe("month"));
    selectRange(new Date(2026, 10, 10), new Date(2026, 10, 13), true);
    fireEvent.click(await screen.findByRole("button", { name: /11月10日\(火\)～11月12日\(木\)/ }));
    const toggle = (await screen.findByRole("switch", { name: i18n.t("schedule.allDay") })) as HTMLInputElement;
    expect(toggle.checked).toBe(true);
    const dates = screen.getAllByDisplayValue(/^2026-11-/) as HTMLInputElement[];
    expect(dates[0].value).toBe("2026-11-10");
    expect(dates[1].value).toBe("2026-11-12");
  });

  it("T5: only events the user can move are editable", async () => {
    answers.events = [
      apiEvent({}),
      apiEvent({ id: 5, title: "Imported All Day", source: "google", is_all_day: true }),
      apiEvent({ id: 6, title: "Imported Timed", source: "google" }),
    ];
    answers.shifts = [{
      id: 3, user_id: 101, shift_date: new Date().toISOString().slice(0, 10), start_time: "09:00:00",
      end_time: "18:00:00", shift_type: "work", notes: null, created_at: "2026-10-01T00:00:00Z",
    }];
    await ready();
    await screen.findByText("Own Event");
    expect(eventOf("event-1")?.editable).toBe(true);
    expect(eventOf("event-6")?.editable).toBe(true);
    expect(eventOf("event-5")?.editable).toBe(false);
    expect(eventOf("shift-3")?.editable).toBe(false);
  });

  it("T5: another owner's event is not editable for a non-admin", async () => {
    answers.canManageOthers = false;
    answers.selfMissing = true;
    answers.events = [apiEvent({ id: 2, user_id: 202, created_by_user_id: 202, title: "Other Event" })];
    await ready();
    await screen.findByText("Other Event");
    expect(eventOf("event-2")?.editable).toBe(false);
  });

  it("T6: moving an event patches it with the numeric id and reverts on failure", async () => {
    answers.events = [apiEvent({})];
    await ready();
    await screen.findByText("Own Event");
    const start = new Date(2026, 10, 12, 14, 0);
    const end = new Date(2026, 10, 12, 15, 0);
    const revert = vi.fn();
    await act(async () => {
      await calendarProps.current?.onEventMove("event-1", start, end, false, revert);
    });
    expect(api.patch).toHaveBeenCalledTimes(1);
    const [path, body] = vi.mocked(api.patch).mock.calls[0] as [string, Record<string, unknown>];
    expect(path).toBe("/calendar/events/1");
    expect(body).toEqual({
      title: "Own Event",
      start_datetime: start.toISOString(),
      end_datetime: end.toISOString(),
      is_all_day: false,
    });
    expect("category" in body).toBe(false);
    expect(revert).not.toHaveBeenCalled();

    vi.mocked(api.patch).mockRejectedValueOnce(new Error("move failed"));
    await act(async () => {
      await calendarProps.current?.onEventMove("event-1", start, end, false, revert);
    });
    expect(revert).toHaveBeenCalledTimes(1);
    expect(await screen.findByText("move failed")).toBeTruthy();
  });

  it("T7: editing and deleting send the numeric id, not event-1", async () => {
    answers.events = [apiEvent({})];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    fireEvent.click(within(await editorDialog()).getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    expect(vi.mocked(api.patch).mock.calls[0][0]).toBe("/calendar/events/1");

    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.deleteEvent") }))[0]);
    await waitFor(() => expect(api.delete).toHaveBeenCalled());
    expect(vi.mocked(api.delete).mock.calls[0][0]).toBe("/calendar/events/1");
  });

  it("T8: moving an all-day event sends the last day at 23:59", async () => {
    answers.events = [apiEvent({ id: 3, title: "Trip", is_all_day: true })];
    await ready();
    await screen.findByText("Trip");
    await act(async () => {
      await calendarProps.current?.onEventMove("event-3", new Date(2026, 10, 10), new Date(2026, 10, 12), true, vi.fn());
    });
    const body = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect(body.start_datetime).toBe(new Date(2026, 10, 10, 0, 0).toISOString());
    expect(body.end_datetime).toBe(new Date(2026, 10, 11, 23, 59).toISOString());
    expect(body.is_all_day).toBe(true);
  });

  it("H1: a holiday reaches the calendar as an all-day, immovable holiday event", async () => {
    answers.holidays = [{ date: "2026-11-03", name: "文化の日" }];
    await ready();
    await waitFor(() => expect(eventOf("holiday-2026-11-03")).toBeTruthy());
    const holiday = eventOf("holiday-2026-11-03")!;
    expect(holiday.title).toBe("文化の日");
    expect(holiday.tone).toBe("holiday");
    expect(holiday.allDay).toBe(true);
    expect(holiday.editable).toBe(false);
  });

  it("H2: clicking a holiday opens no dialog", async () => {
    answers.holidays = [{ date: "2026-11-03", name: "文化の日" }];
    await ready();
    fireEvent.click(await screen.findByText("文化の日"));
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.queryByRole("button", { name: i18n.t("schedule.editEvent") })).toBeNull();
  });

  it("H3: the holiday request carries lang=ja and the current range", async () => {
    await ready();
    await waitFor(() => {
      const paths = mockGet.mock.calls.map((call) => String(call[0]));
      expect(paths.some((p) => /^\/calendar\/holidays\?start=\d{4}-\d{2}-\d{2}&end=\d{4}-\d{2}-\d{2}&lang=ja$/.test(p))).toBe(true);
    });
  });

  it("T9: week view passes Sunday, 7 days and weekStart 0; day view passes today and 1", async () => {
    await ready();
    const weekDate = calendarProps.current?.date as Date;
    expect(weekDate.getDay()).toBe(0);
    expect(calendarProps.current?.dayCount).toBe(7);
    expect(calendarProps.current?.weekStart).toBe(0);
    expect(calendarProps.current?.mode).toBe("days");
    fireEvent.keyDown(document.body, { key: "d" });
    await waitFor(() => expect(calendarProps.current?.dayCount).toBe(1));
    const dayDate = calendarProps.current?.date as Date;
    const today = new Date();
    expect(dayDate.getFullYear()).toBe(today.getFullYear());
    expect(dayDate.getMonth()).toBe(today.getMonth());
    expect(dayDate.getDate()).toBe(today.getDate());
    expect(calendarProps.current?.dayCount).toBe(1);
  });
});

describe("SchedulePage search by title (G12)", () => {
  const rangeText = () => document.querySelector(".schedule-shell__range")?.textContent ?? "";
  const searchName = () => i18n.t("common.search");
  const ready = async () => {
    view();
    await screen.findByRole("button", { name: i18n.t("schedule.create") });
  };
  const searchButton = () => screen.getByRole("button", { name: searchName() });
  const searchField = () =>
    (screen.queryByRole("searchbox", { name: searchName() }) ?? screen.queryByRole("textbox", { name: searchName() })) as HTMLInputElement | null;
  const search = (text: string) => {
    const field = searchField();
    if (!field) throw new Error("search field is missing");
    fireEvent.change(field, { target: { value: text } });
    fireEvent.keyDown(field, { key: "Enter" });
  };

  it("F1: the magnifier opens a focused search field", async () => {
    await ready();
    fireEvent.click(searchButton());
    const field = searchField();
    expect(field).not.toBeNull();
    expect(document.activeElement).toBe(field);
  });

  it("F2: Enter asks the search path with the encoded query and lists the hit", async () => {
    answers.searchEvents = [
      apiEvent({ id: 11, title: "商談A", start_datetime: "2026-12-15T10:00:00", end_datetime: "2026-12-15T11:00:00" }),
    ];
    await ready();
    fireEvent.click(searchButton());
    search("商談");
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith("/calendar/events/search?q=%E5%95%86%E8%AB%87"));
    expect(await screen.findByText("商談A")).toBeTruthy();
  });

  it("F3: clicking a hit jumps to its week and closes the field", async () => {
    answers.searchEvents = [
      apiEvent({ id: 11, title: "商談A", start_datetime: "2026-12-15T10:00:00", end_datetime: "2026-12-15T11:00:00" }),
    ];
    await ready();
    fireEvent.click(searchButton());
    search("商談");
    fireEvent.click(await screen.findByText("商談A"));
    const days = getWeekDays(new Date(2026, 11, 15));
    const expected = `${formatDayLabel(days[0])} - ${formatDayLabel(days[6])}`;
    await waitFor(() => expect(rangeText()).toBe(expected));
    expect(searchField()).toBeNull();
    expect(screen.getByRole("button", { name: searchName() })).toBeTruthy();
  });

  it("F4: no hit shows the no-results text", async () => {
    answers.searchEvents = [];
    await ready();
    fireEvent.click(searchButton());
    search("商談");
    expect(await screen.findByText(i18n.t("schedule.searchNoResults"))).toBeTruthy();
  });

  it("F5: Esc closes the field and the t shortcut still goes back to today", async () => {
    await ready();
    const initial = rangeText();
    fireEvent.click(searchButton());
    const field = searchField();
    if (!field) throw new Error("search field is missing");
    fireEvent.keyDown(field, { key: "Escape" });
    expect(searchField()).toBeNull();
    expect(screen.getByRole("button", { name: searchName() })).toBeTruthy();
    fireEvent.keyDown(document.body, { key: "j" });
    expect(rangeText()).not.toBe(initial);
    fireEvent.keyDown(document.body, { key: "t" });
    expect(rangeText()).toBe(initial);
  });
});

describe("SchedulePage on component molds (G26-G28)", () => {
  it("G26: detail popover buttons are mold Buttons and no .modal-icon-btn remains", async () => {
    answers.events = [apiEvent({})];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    for (const key of ["schedule.editEvent", "schedule.deleteEvent", "common.close"]) {
      const button = (await screen.findAllByRole("button", { name: i18n.t(key) }))[0];
      expect(button.className).toContain("comp-btn--ghost");
      expect(button.className).toContain("comp-btn--icon-only");
    }
    expect(document.querySelectorAll(".modal-icon-btn").length).toBe(0);
  });

  it("G27: the category chip is a mold Badge without inline style", async () => {
    answers.events = [apiEvent({})];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") });
    const badge = document.querySelector(".schedule-popover .comp-badge");
    if (!badge) throw new Error("badge is missing");
    expect(badge.className).toContain("comp-badge--neutral");
    expect(badge.className).toContain("comp-badge--soft");
    expect(badge.hasAttribute("style")).toBe(false);
    // 種類に色が無ければ点は出ない・名前は 7 種の i18n の名前
    expect(badge.querySelector(".schedule-month__dot")).toBeNull();
    expect(badge.textContent).toBe(i18n.t("schedule.calendarLabels.meeting"));
  });

  it("G27b: a category with a color shows the existing dot before its own name", async () => {
    answers.categories = [categoryRow("meeting", { name: "商談", color_key: "tomato" })];
    answers.events = [apiEvent({})];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") });
    await waitFor(() => expect(document.querySelector(".schedule-popover .comp-badge")?.textContent).toBe("商談"));
    const dot = document.querySelector(".schedule-popover .comp-badge .schedule-month__dot") as HTMLElement | null;
    expect(dot).not.toBeNull();
    expect(dot?.style.background).toContain("--event-color-tomato");
  });
});

describe("SchedulePage category defaults (schedule-settings bin2a)", () => {
  const categoryLabelOf = () => i18n.t("schedule.category");

  it("A6: picking a category on create fills its color and share default", async () => {
    answers.categories = [
      categoryRow("meeting", { sort_order: 1 }),
      categoryRow("personal", { sort_order: 2, default_share: "self" }),
      categoryRow("shipping", { sort_order: 3, color_key: "tomato" }),
    ];
    view();
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("schedule.create") }));
    const select = (await screen.findByLabelText(categoryLabelOf())) as HTMLSelectElement;
    await waitFor(() => expect(select.options.length).toBe(3));
    const share = (await screen.findByRole("combobox", { name: i18n.t("schedule.shareLabel") })) as HTMLSelectElement;
    expect(share.value).toBe("all");
    fireEvent.change(select, { target: { value: "personal" } });
    expect(share.value).toBe("self");
    fireEvent.change(select, { target: { value: "shipping" } });
    expect(share.value).toBe("all");
    const colorButton = screen.getByRole("button", { name: new RegExp(`^${i18n.t("schedule.eventColor")}`) });
    expect(colorButton.getAttribute("aria-label")).toContain(i18n.t("schedule.eventColors.tomato"));
    fireEvent.change(screen.getByLabelText(i18n.t("schedule.eventTitle")), { target: { value: "Ship it" } });
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const body = vi.mocked(api.post).mock.calls[0][1] as Record<string, unknown>;
    expect(body.category).toBe("shipping");
    expect(body.color_key).toBe("tomato");
    expect(body.calendar_type).toBe("shared");
  });

  it("A6: changing the category on edit changes only the category (color and share stay)", async () => {
    answers.categories = [
      categoryRow("meeting", { sort_order: 1 }),
      categoryRow("personal", { sort_order: 2, default_share: "self" }),
      categoryRow("shipping", { sort_order: 3, color_key: "tomato" }),
    ];
    answers.events = [apiEvent({ color_key: "basil" })];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    const dialog = await editorDialog();
    const select = (await within(dialog).findByLabelText(categoryLabelOf())) as HTMLSelectElement;
    await waitFor(() => expect(select.options.length).toBe(3));
    const share = within(dialog).getByRole("combobox", { name: i18n.t("schedule.shareLabel") }) as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "personal" } });
    expect(share.value).toBe("all");
    fireEvent.change(select, { target: { value: "shipping" } });
    expect(share.value).toBe("all");
    const colorButton = within(dialog).getByRole("button", { name: new RegExp(`^${i18n.t("schedule.eventColor")}`) });
    expect(colorButton.getAttribute("aria-label")).toContain(i18n.t("schedule.eventColors.basil"));
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    const body = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect(body.category).toBe("shipping");
    expect(body.color_key).toBe("basil");
    expect(body.calendar_type).toBe("shared");
  });

  it("edit without changing the category does not send it", async () => {
    answers.categories = [categoryRow("meeting")];
    answers.events = [apiEvent({})];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    const dialog = await editorDialog();
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    expect("category" in (vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>)).toBe(false);
  });

  it("A7: the picker lists active categories only, plus the event's own category when it is inactive", async () => {
    answers.categories = [
      categoryRow("meeting", { sort_order: 1 }),
      categoryRow("shipping", { sort_order: 2, is_active: false }),
      categoryRow("billing", { sort_order: 3, is_active: false }),
      categoryRow("custom_1", { sort_order: 4, name: "見積り" }),
    ];
    answers.events = [apiEvent({ category: "shipping" })];
    view();
    // 作るとき: 使っている種類だけ（meeting と custom_1）
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("schedule.create") }));
    const createSelect = (await screen.findByLabelText(categoryLabelOf())) as HTMLSelectElement;
    await waitFor(() => expect(Array.from(createSelect.options).map((o) => o.value)).toEqual(["meeting", "custom_1"]));
    expect(Array.from(createSelect.options).map((o) => o.textContent)).toContain("見積り");
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.close") }));
    // 直すとき: 今の予定の種類（使わなくした shipping）も出る。billing は出ない
    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    const dialog = await editorDialog();
    const editSelect = (await within(dialog).findByLabelText(categoryLabelOf())) as HTMLSelectElement;
    await waitFor(() => expect(Array.from(editSelect.options).map((o) => o.value)).toEqual(["meeting", "shipping", "custom_1"]));
    expect(editSelect.value).toBe("shipping");
  });
});

describe("SchedulePage time lines (G34-G35)", () => {
  const range = () => {
    const s = new Date(todayAt(10));
    const e = new Date(todayAt(11));
    return { s, e };
  };

  it("shows the Google-style time line in the detail popover and no date line (G34)", async () => {
    answers.events = [apiEvent({})];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    const { s, e } = range();
    const expected = formatDraftDateLine(
      {
        startDate: formatDateInput(s),
        startTime: formatTimeInput(s),
        endDate: formatDateInput(e),
        endTime: formatTimeInput(e),
        allDay: false,
      },
      i18n.t.bind(i18n) as never,
      i18n.language,
    );
    await waitFor(() => expect(document.querySelector(".schedule-popover__time")).not.toBeNull());
    expect(document.querySelector(".schedule-popover__time")?.textContent).toBe(expected);
    expect(document.querySelectorAll(".schedule-popover__date")).toHaveLength(0);
  });

  it("shows the meridiem time range in the list view (G35)", async () => {
    answers.events = [apiEvent({})];
    view();
    await screen.findByText("Own Event");
    fireEvent.keyDown(document.body, { key: "a" });
    await waitFor(() => expect(document.querySelector(".schedule-list__time")).not.toBeNull());
    const { s, e } = range();
    const text = document.querySelector(".schedule-list__time")?.textContent ?? "";
    expect(text).toBe(formatTimeRange(s, e, i18n.t.bind(i18n) as never, false));
    expect(text).not.toMatch(/\d{2}:\d{2} - \d{2}:\d{2}/);
  });
});

describe("SchedulePage recurring events (G69-G79)", () => {
  const occurrence = (over: Record<string, unknown> = {}) =>
    apiEvent({
      recurrence_rule: "FREQ=WEEKLY;BYDAY=TH",
      recurrence: "weekly",
      recurring_event_id: 1,
      occurrence_start: todayAt(10),
      is_first_occurrence: false,
      ...over,
    });
  const scopeDialog = (kind: "editTitle" | "deleteTitle" = "editTitle") =>
    screen.findByRole("dialog", { name: i18n.t(`schedule.recurrence.${kind}`) });
  const openEditor = async () => {
    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    return editorDialog();
  };
  const clickSave = (dialog: HTMLElement) =>
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.save") }));
  const repeatSelect = (dialog: HTMLElement) =>
    within(dialog).getByRole("combobox", { name: i18n.t("schedule.recurrence.label") }) as HTMLSelectElement;
  const radioNames = (dialog: HTMLElement) => within(dialog).getAllByRole("radio").map((r) => r.closest("label")?.textContent);

  it("shows the repeat line under the time in the detail popover", async () => {
    answers.events = [occurrence()];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    const weekday = new Intl.DateTimeFormat("ja", { weekday: "long" }).format(new Date(todayAt(10)));
    expect(await screen.findByText(i18n.t("schedule.recurrence.weekly", { weekday }))).toBeTruthy();
  });

  it("asks this/following/all on save and sends nothing on cancel", async () => {
    answers.events = [occurrence()];
    view();
    clickSave(await openEditor());
    const scope = await scopeDialog();
    expect(within(scope).getAllByRole("radio")).toHaveLength(3);
    expect((within(scope).getByRole("radio", { name: i18n.t("schedule.recurrence.scopeThis") }) as HTMLInputElement).checked).toBe(true);
    fireEvent.click(within(scope).getByRole("button", { name: i18n.t("common.cancel") }));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: i18n.t("schedule.recurrence.editTitle") })).toBeNull());
    expect(api.patch).not.toHaveBeenCalled();
  });

  it("sends scope this with the occurrence start on OK", async () => {
    answers.events = [occurrence()];
    view();
    clickSave(await openEditor());
    const scope = await scopeDialog();
    fireEvent.click(within(scope).getByRole("button", { name: i18n.t("common.ok") }));
    await waitFor(() => expect(api.patch).toHaveBeenCalledTimes(1));
    const [path, body] = vi.mocked(api.patch).mock.calls[0] as [string, Record<string, unknown>];
    expect(path).toBe("/calendar/events/1");
    expect(body.scope).toBe("this");
    expect(body.occurrence_start).toBe(new Date(todayAt(10)).toISOString());
    expect("recurrence" in body).toBe(false);
  });

  it("hides following on the first occurrence", async () => {
    answers.events = [occurrence({ is_first_occurrence: true })];
    view();
    clickSave(await openEditor());
    const scope = await scopeDialog();
    expect(radioNames(scope)).toEqual([i18n.t("schedule.recurrence.scopeThis"), i18n.t("schedule.recurrence.scopeAll")]);
  });

  it("drops this when the repeat changes and skips the dialog on the first occurrence", async () => {
    answers.events = [occurrence()];
    view();
    let dialog = await openEditor();
    fireEvent.change(repeatSelect(dialog), { target: { value: "daily" } });
    clickSave(dialog);
    const scope = await scopeDialog();
    expect(radioNames(scope)).toEqual([
      i18n.t("schedule.recurrence.scopeFollowing"),
      i18n.t("schedule.recurrence.scopeAll"),
    ]);
    expect(api.patch).not.toHaveBeenCalled();

    cleanup();
    vi.clearAllMocks();
    queryClient.clear();
    answers.events = [occurrence({ is_first_occurrence: true })];
    view();
    dialog = await openEditor();
    fireEvent.change(repeatSelect(dialog), { target: { value: "daily" } });
    clickSave(dialog);
    await waitFor(() => expect(api.patch).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("dialog", { name: i18n.t("schedule.recurrence.editTitle") })).toBeNull();
    const body = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect(body.scope).toBe("all");
    expect(body.recurrence).toBe("daily");
  });

  it("deletes with scope and occurrence start in the query", async () => {
    answers.events = [occurrence()];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.deleteEvent") }))[0]);
    const scope = await scopeDialog("deleteTitle");
    fireEvent.click(within(scope).getByRole("button", { name: i18n.t("common.ok") }));
    await waitFor(() => expect(api.delete).toHaveBeenCalledTimes(1));
    expect(vi.mocked(api.delete).mock.calls[0][0]).toBe(
      `/calendar/events/1?${new URLSearchParams({ scope: "this", occurrence_start: new Date(todayAt(10)).toISOString() })}`,
    );
  });

  it("asks two choices on move and reverts on cancel", async () => {
    answers.events = [occurrence()];
    view();
    await screen.findByText("Own Event");
    await waitFor(() => expect(calendarProps.current).not.toBeNull());
    const revert = vi.fn();
    const start = new Date(2026, 10, 12, 14, 0);
    const end = new Date(2026, 10, 12, 15, 0);
    await act(async () => {
      await calendarProps.current?.onEventMove(`event-1-${new Date(todayAt(10)).getTime()}`, start, end, false, revert);
    });
    const scope = await scopeDialog();
    expect(radioNames(scope)).toEqual([
      i18n.t("schedule.recurrence.scopeThis"),
      i18n.t("schedule.recurrence.scopeFollowing"),
    ]);
    fireEvent.click(within(scope).getByRole("button", { name: i18n.t("common.cancel") }));
    expect(revert).toHaveBeenCalledTimes(1);
    expect(api.patch).not.toHaveBeenCalled();
  });

  it("closes only the scope dialog on Escape", async () => {
    answers.events = [occurrence()];
    view();
    clickSave(await openEditor());
    await scopeDialog();
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: i18n.t("schedule.recurrence.editTitle") })).toBeNull());
    expect(await editorDialog()).toBeTruthy();
  });

  it("has no repeat select for a Google event or a Meet event", async () => {
    answers.events = [apiEvent({ source: "google", google_event_id: "g1" })];
    view();
    let dialog = await openEditor();
    await within(dialog).findByLabelText(i18n.t("schedule.eventTitle"));
    expect(within(dialog).queryByRole("combobox", { name: i18n.t("schedule.recurrence.label") })).toBeNull();

    cleanup();
    vi.clearAllMocks();
    queryClient.clear();
    answers.events = [apiEvent({ meet_url: "https://meet.google.com/abc-defg-hij" })];
    view();
    dialog = await openEditor();
    await within(dialog).findByLabelText(i18n.t("schedule.eventTitle"));
    expect(within(dialog).queryByRole("combobox", { name: i18n.t("schedule.recurrence.label") })).toBeNull();
  });

  it("shows the repeat select right of all-day with does-not-repeat first", async () => {
    answers.events = [apiEvent({})];
    view();
    const dialog = await openEditor();
    const select = repeatSelect(dialog);
    expect(select.value).toBe("none");
    expect(select.options[0].value).toBe("none");
    expect(select.closest(".schedule-editor-all-day-row")).not.toBeNull();
  });

  it("hides the Meet row when a repeat is chosen and sends no add_meet", async () => {
    answers.isTenantAdmin = true;
    answers.connected = true;
    answers.meetAvailable = true;
    answers.events = [apiEvent({ google_event_id: "g1" })];
    view();
    const dialog = await openEditor();
    fireEvent.click(await within(dialog).findByRole("button", { name: i18n.t("schedule.addMeet") }));
    fireEvent.change(repeatSelect(dialog), { target: { value: "weekly" } });
    expect(within(dialog).queryByRole("button", { name: i18n.t("schedule.addMeet") })).toBeNull();
    expect(within(dialog).queryByRole("button", { name: i18n.t("schedule.removeMeet") })).toBeNull();
    clickSave(dialog);
    await waitFor(() => expect(api.patch).toHaveBeenCalledTimes(1));
    const body = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect("add_meet" in body).toBe(false);
    expect(body.recurrence).toBe("weekly");
  });

  it("shows no dialog for a single event", async () => {
    answers.events = [apiEvent({})];
    view();
    clickSave(await openEditor());
    await waitFor(() => expect(api.patch).toHaveBeenCalledTimes(1));
    expect("scope" in (vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>)).toBe(false);
    expect(screen.queryByRole("dialog", { name: i18n.t("schedule.recurrence.editTitle") })).toBeNull();

    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.deleteEvent") }))[0]);
    await waitFor(() => expect(api.delete).toHaveBeenCalledTimes(1));
    expect(vi.mocked(api.delete).mock.calls[0]).toEqual(["/calendar/events/1"]);
    expect(screen.queryByRole("dialog", { name: i18n.t("schedule.recurrence.deleteTitle") })).toBeNull();
  });
});

describe("SchedulePage event colors (ADR-1081)", () => {
  const eventsOf = () => calendarProps.current?.events as Array<Record<string, any>>;
  const boxOf = (id: string) => eventsOf().find((ev) => ev.id === id);
  const pendingOf = () => boxOf("pending");
  const colorLabel = (key: string) => i18n.t(`schedule.eventColors.${key}`);
  const openPicker = (scope: HTMLElement | Document = document) => {
    const root = scope instanceof Document ? within(document.body) : within(scope);
    fireEvent.click(root.getByRole("button", { name: new RegExp(i18n.t("schedule.eventColor")) }));
  };
  const openCreate = async () => {
    view();
    await screen.findByRole("button", { name: i18n.t("schedule.create") });
    await waitFor(() => expect(calendarProps.current).not.toBeNull());
    act(() => {
      calendarProps.current?.onSelectRange(new Date(2026, 10, 10, 10, 0), new Date(2026, 10, 10, 11, 0), false, null);
    });
    await screen.findByLabelText(i18n.t("schedule.eventTitle"));
  };
  const openEditor = async () => {
    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    return editorDialog();
  };

  it("C1: a box without a color keeps the owner color", async () => {
    answers.events = [apiEvent({})];
    view();
    await screen.findByText("Own Event");
    const color = boxOf("event-1")?.color;
    expect(color).toBeTruthy();
    expect(String(color)).not.toContain("--event-color-");
  });

  it("C1b: a box without a color uses the owner's chosen color token", async () => {
    answers.ownerColorKey = "basil";
    answers.events = [apiEvent({})];
    view();
    await screen.findByText("Own Event");
    expect(boxOf("event-1")?.color).toBe("var(--event-color-basil)");
  });

  it("C2: a box with color_key uses the event color token", async () => {
    answers.events = [apiEvent({ color_key: "tomato" })];
    view();
    await screen.findByText("Own Event");
    expect(boxOf("event-1")?.color).toBe("var(--event-color-tomato)");
  });

  it("C3: the list view dot uses the event color token", async () => {
    answers.events = [apiEvent({ color_key: "tomato" })];
    view();
    await screen.findByText("Own Event");
    fireEvent.keyDown(document.body, { key: "a" });
    await waitFor(() => expect(document.querySelector(".schedule-list__items")).not.toBeNull());
    const dot = document.querySelector(".schedule-list__items .schedule-month__dot") as HTMLElement | null;
    expect(dot).not.toBeNull();
    expect(dot?.style.background).toBe("var(--event-color-tomato)");
  });

  it("C4: choosing a swatch in the create popover sends that color_key", async () => {
    await openCreate();
    fireEvent.change(screen.getByLabelText(i18n.t("schedule.eventTitle")), { target: { value: "Colored" } });
    openPicker();
    expect(screen.getAllByRole("radio", { name: /./ }).filter((r) => (r as HTMLInputElement).name === "schedule-event-color-popover")).toHaveLength(25);
    fireEvent.click(screen.getByRole("radio", { name: colorLabel("tomato") }));
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const body = vi.mocked(api.post).mock.calls[0][1] as Record<string, unknown>;
    expect(body.color_key).toBe("tomato");
  });

  it("C5: saving without touching the color sends an empty color_key", async () => {
    await openCreate();
    fireEvent.change(screen.getByLabelText(i18n.t("schedule.eventTitle")), { target: { value: "Plain" } });
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const body = vi.mocked(api.post).mock.calls[0][1] as Record<string, unknown>;
    expect(body.color_key).toBe("");
  });

  it("C6: the edit page checks the radio of the event's color", async () => {
    answers.events = [apiEvent({ color_key: "tomato" })];
    view();
    const dialog = await openEditor();
    openPicker(dialog);
    expect((within(dialog).getByRole("radio", { name: colorLabel("tomato") }) as HTMLInputElement).checked).toBe(true);
    expect((within(dialog).getByRole("radio", { name: colorLabel("default") }) as HTMLInputElement).checked).toBe(false);
  });

  it("C7: choosing a color in the create popover colors the pending box", async () => {
    await openCreate();
    openPicker();
    fireEvent.click(screen.getByRole("radio", { name: colorLabel("basil") }));
    await waitFor(() => expect(pendingOf()?.color).toBe("var(--event-color-basil)"));
  });

  it("C8: changing only the color of a repeating event still asks the three choices", async () => {
    answers.events = [
      apiEvent({
        recurrence_rule: "FREQ=WEEKLY;BYDAY=TH",
        recurrence: "weekly",
        recurring_event_id: 1,
        occurrence_start: todayAt(10),
        is_first_occurrence: false,
      }),
    ];
    view();
    const dialog = await openEditor();
    openPicker(dialog);
    fireEvent.click(within(dialog).getByRole("radio", { name: colorLabel("cobalt") }));
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.save") }));
    const scope = await screen.findByRole("dialog", { name: i18n.t("schedule.recurrence.editTitle") });
    expect(within(scope).getAllByRole("radio")).toHaveLength(3);
  });

  it("C9: moving a box sends no color_key", async () => {
    answers.events = [apiEvent({ color_key: "tomato" })];
    view();
    await screen.findByText("Own Event");
    const revert = vi.fn();
    await act(async () => {
      await calendarProps.current?.onEventMove("event-1", new Date(2026, 10, 12, 14, 0), new Date(2026, 10, 12, 15, 0), false, revert);
    });
    expect(api.patch).toHaveBeenCalledTimes(1);
    const body = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect("color_key" in body).toBe(false);
  });

  it("C10: pressing a swatch does not close the create popover", async () => {
    await openCreate();
    openPicker();
    const radio = screen.getByRole("radio", { name: colorLabel("grape") });
    fireEvent.pointerDown(radio);
    fireEvent.click(radio);
    expect(document.querySelector(".schedule-popover")).not.toBeNull();
    expect(pendingOf()).toBeDefined();
  });
});

describe("SchedulePage team share (schedule-settings bin2b)", () => {
  const shareLabel = () => i18n.t("schedule.shareLabel");
  const teams = [
    { id: 1, name: "Team One" },
    { id: 2, name: "Team Two" },
  ];
  const openCreateForm = async () => {
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("schedule.create") }));
    return (await screen.findByRole("combobox", { name: shareLabel() })) as HTMLSelectElement;
  };
  const openEditor = async () => {
    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    return editorDialog();
  };

  it("lists self / all / team, shows the team picker for team, and sends team_ids", async () => {
    answers.teams = teams;
    view();
    const share = await openCreateForm();
    expect(Array.from(share.options).map((option) => option.value)).toEqual(["self", "all", "team"]);
    expect(screen.queryByTestId("schedule-share-teams-option-1")).toBeNull();
    fireEvent.change(share, { target: { value: "team" } });
    fireEvent.click(await screen.findByTestId("schedule-share-teams-option-1"));
    fireEvent.click(screen.getByTestId("schedule-share-teams-option-2"));
    fireEvent.change(screen.getByLabelText(i18n.t("schedule.eventTitle")), { target: { value: "Team plan" } });
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const body = vi.mocked(api.post).mock.calls[0][1] as Record<string, unknown>;
    expect(body.calendar_type).toBe("team");
    expect(body.team_ids).toEqual([1, 2]);
  });

  it("cannot save with team selected and no team chosen, and says why", async () => {
    answers.teams = teams;
    view();
    const share = await openCreateForm();
    fireEvent.change(screen.getByLabelText(i18n.t("schedule.eventTitle")), { target: { value: "Team plan" } });
    fireEvent.change(share, { target: { value: "team" } });
    expect(await screen.findByText(i18n.t("schedule.shareTeamsRequired"))).toBeTruthy();
    const save = screen.getByRole("button", { name: i18n.t("common.save") }) as HTMLButtonElement;
    expect(save.disabled).toBe(true);
    fireEvent.click(await screen.findByTestId("schedule-share-teams-option-2"));
    expect(save.disabled).toBe(false);
    expect(screen.queryByText(i18n.t("schedule.shareTeamsRequired"))).toBeNull();
  });

  it("shows the empty label when there is no active team", async () => {
    view();
    const share = await openCreateForm();
    fireEvent.change(share, { target: { value: "team" } });
    expect(await screen.findByText(i18n.t("schedule.noActiveTeams"))).toBeTruthy();
  });

  it("a category whose default share is team fills the share and the teams on create", async () => {
    answers.teams = teams;
    answers.categories = [
      categoryRow("meeting", { sort_order: 1 }),
      categoryRow("shipping", { sort_order: 2, default_share: "team", default_team_ids: [2] }),
    ];
    view();
    const share = await openCreateForm();
    const select = (await screen.findByLabelText(i18n.t("schedule.category"))) as HTMLSelectElement;
    await waitFor(() => expect(select.options.length).toBe(2));
    expect(share.value).toBe("all");
    fireEvent.change(select, { target: { value: "shipping" } });
    expect(share.value).toBe("team");
    fireEvent.change(screen.getByLabelText(i18n.t("schedule.eventTitle")), { target: { value: "Ship it" } });
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const body = vi.mocked(api.post).mock.calls[0][1] as Record<string, unknown>;
    expect(body.calendar_type).toBe("team");
    expect(body.team_ids).toEqual([2]);
  });

  it("the detail popover has a share row with the team names", async () => {
    answers.teams = teams;
    answers.events = [apiEvent({ calendar_type: "team", team_ids: [1, 2] })];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    expect(await screen.findByText(i18n.t("schedule.shareLabel"))).toBeTruthy();
    expect(await screen.findByText(i18n.t("schedule.shareTeamWithNames", { names: ["Team One", "Team Two"].join(i18n.t("schedule.nameListSeparator")) }))).toBeTruthy();
  });

  it("the detail popover says Only me for a personal event", async () => {
    answers.events = [apiEvent({ calendar_type: "personal" })];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    expect(await screen.findByText(i18n.t("schedule.shareSelf"))).toBeTruthy();
  });

  it("editing a team event keeps the share and sends the same team_ids", async () => {
    answers.teams = teams;
    answers.events = [apiEvent({ calendar_type: "team", team_ids: [2] })];
    view();
    const dialog = await openEditor();
    const share = (await within(dialog).findByRole("combobox", { name: shareLabel() })) as HTMLSelectElement;
    expect(share.value).toBe("team");
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    const body = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect(body.calendar_type).toBe("team");
    expect(body.team_ids).toEqual([2]);
  });

  it("recurring event: this-only sends no team_ids, all sends them", async () => {
    answers.teams = teams;
    answers.events = [
      apiEvent({
        calendar_type: "team",
        team_ids: [1],
        recurrence_rule: "FREQ=WEEKLY;BYDAY=TH",
        recurrence: "weekly",
        recurring_event_id: 1,
        occurrence_start: todayAt(10),
        is_first_occurrence: false,
      }),
    ];
    view();
    let dialog = await openEditor();
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.save") }));
    let scope = await screen.findByRole("dialog", { name: i18n.t("schedule.recurrence.editTitle") });
    fireEvent.click(within(scope).getByRole("button", { name: i18n.t("common.ok") }));
    await waitFor(() => expect(api.patch).toHaveBeenCalledTimes(1));
    const thisBody = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect(thisBody.scope).toBe("this");
    expect(thisBody.calendar_type).toBe("team");
    expect("team_ids" in thisBody).toBe(false);

    cleanup();
    queryClient.clear();
    vi.mocked(api.patch).mockClear();
    view();
    dialog = await openEditor();
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.save") }));
    scope = await screen.findByRole("dialog", { name: i18n.t("schedule.recurrence.editTitle") });
    fireEvent.click(within(scope).getByRole("radio", { name: i18n.t("schedule.recurrence.scopeAll") }));
    fireEvent.click(within(scope).getByRole("button", { name: i18n.t("common.ok") }));
    await waitFor(() => expect(api.patch).toHaveBeenCalledTimes(1));
    const allBody = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect(allBody.scope).toBe("all");
    expect(allBody.team_ids).toEqual([1]);
  });
});

/** 入れた Promise を、あとで終わらせられる形で作る（応答を止めておく試験用） */
function makeGate() {
  let release = () => {};
  const promise = new Promise<void>((resolve) => { release = resolve; });
  return { promise, release };
}

/** 画面が今の初期値で組み直されるまで待つ（時間割へ渡る長さの値を目印にする。試験は event_minutes に 60 以外を入れる） */
const waitForPrefsApplied = (minutes: number) => waitFor(() => expect(calendarProps.current?.clickMinutes).toBe(minutes));
const flush = () => act(async () => { await new Promise((resolve) => setTimeout(resolve, 30)); });
const ownerBox = (name: string) => screen.queryByRole("checkbox", { name }) as HTMLInputElement | null;

describe("SchedulePage personal defaults (schedule-settings bin3b)", () => {
  it("B7: shows the settings gear to a user who is neither admin nor staff.view", async () => {
    answers.isTenantAdmin = false;
    answers.canManageOthers = false;
    view();
    expect(await screen.findByRole("button", { name: i18n.t("schedule.settings") })).toBeTruthy();
  });

  it("B2: with no saved row it behaves as today (week, Sunday, 60 minutes, only me)", async () => {
    answers.canManageOthers = true;
    view();
    await screen.findByRole("button", { name: i18n.t("schedule.create") });
    await flush();
    expect(calendarProps.current?.mode).toBe("days");
    expect(calendarProps.current?.dayCount).toBe(7);
    expect(calendarProps.current?.weekStart).toBe(0);
    expect(calendarProps.current?.clickMinutes).toBe(60);
    expect(ownerBox("Owner Self")?.checked).toBe(true);
    expect(ownerBox("Owner Other")?.checked).toBe(false);
  });

  it.each([
    ["month", "month", 7],
    ["threeDay", "days", 3],
    ["day", "days", 1],
    ["week", "days", 7],
  ])("B1: opens in the saved view %s", async (saved, mode, dayCount) => {
    answers.prefs = { ...DEFAULT_PREFS, default_view: saved, event_minutes: 30 };
    view();
    await waitForPrefsApplied(30);
    await waitFor(() => {
      expect(calendarProps.current?.mode).toBe(mode);
      if (mode === "days") expect(calendarProps.current?.dayCount).toBe(dayCount);
    });
  });

  it("B1: opens in the list view when saved", async () => {
    answers.prefs = { ...DEFAULT_PREFS, default_view: "list" };
    view();
    expect(await screen.findByRole("button", { name: i18n.t("schedule.listView") })).toBeTruthy();
    await waitFor(() => expect(screen.queryByTestId("calendar-view")).toBeNull());
    await flush();
    expect(screen.queryByTestId("calendar-view")).toBeNull();
  });

  it("does not override a view the person changed by hand before the preferences arrived", async () => {
    const gate = makeGate();
    answers.gate.prefs = gate.promise;
    answers.prefs = { ...DEFAULT_PREFS, default_view: "month", event_minutes: 30 };
    view();
    await screen.findByRole("button", { name: i18n.t("schedule.create") });
    fireEvent.keyDown(window, { key: "d" });
    await waitFor(() => expect(calendarProps.current?.dayCount).toBe(1));
    gate.release();
    await waitForPrefsApplied(30);
    await flush();
    expect(calendarProps.current?.mode).toBe("days");
    expect(calendarProps.current?.dayCount).toBe(1);
  });

  it("B1: week start Monday reaches the calendar, and the week's events are asked for from a Monday", async () => {
    answers.prefs = { ...DEFAULT_PREFS, week_start: 1 };
    view();
    await waitFor(() => expect(calendarProps.current?.weekStart).toBe(1));
    await waitFor(() => {
      const calls = mockGet.mock.calls.map((c) => String(c[0])).filter((path) => path.startsWith("/calendar/events?"));
      const last = calls[calls.length - 1];
      const start = new Date(new URL(`http://x${last}`).searchParams.get("start") as string);
      const end = new Date(new URL(`http://x${last}`).searchParams.get("end") as string);
      expect(start.getDay()).toBe(1);
      expect(Math.round((end.getTime() - start.getTime()) / 86400000)).toBe(7);
    });
  });

  it("K2: the mini calendar starts on Monday when week_start is 1", async () => {
    answers.prefs = { ...DEFAULT_PREFS, week_start: 1 };
    const { container } = view();
    await waitFor(() => {
      expect(container.querySelectorAll(".schedule-mini-calendar__weekdays span")[0]?.textContent).toBe("月");
    });
    const now = new Date();
    const first = new Date(now.getFullYear(), now.getMonth(), 1);
    const back = (first.getDay() + 6) % 7;
    const expected = String(new Date(now.getFullYear(), now.getMonth(), 1 - back).getDate());
    expect(container.querySelectorAll(".schedule-mini-calendar__day")[0]?.textContent).toBe(expected);
  });

  it("K2: the mini calendar starts on Sunday when there is no saved preference", async () => {
    const { container } = view();
    await screen.findByRole("button", { name: i18n.t("schedule.create") });
    expect(container.querySelectorAll(".schedule-mini-calendar__weekdays span")[0]?.textContent).toBe("日");
    const now = new Date();
    const first = new Date(now.getFullYear(), now.getMonth(), 1);
    const expected = String(new Date(now.getFullYear(), now.getMonth(), 1 - first.getDay()).getDate());
    expect(container.querySelectorAll(".schedule-mini-calendar__day")[0]?.textContent).toBe(expected);
  });

  it("K4: shows the preference load failure sentence while events still show", async () => {
    answers.prefsFail = true;
    answers.events = [apiEvent({})];
    view();
    expect(await screen.findByText(i18n.t("schedule.prefsLoadErrorSchedule"))).toBeTruthy();
    expect(await screen.findByText("Own Event")).toBeTruthy();
  });

  it("K4: does not show the preference load failure sentence when the preferences load", async () => {
    answers.events = [apiEvent({})];
    view();
    expect(await screen.findByText("Own Event")).toBeTruthy();
    await flush();
    expect(screen.queryByText(i18n.t("schedule.prefsLoadErrorSchedule"))).toBeNull();
  });

  it("B1: the saved length is used for a new event (30 minutes) and for a click in the grid", async () => {
    answers.prefs = { ...DEFAULT_PREFS, event_minutes: 30 };
    view();
    await waitForPrefsApplied(30);
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("schedule.create") }));
    await screen.findByLabelText(i18n.t("schedule.eventTitle"));
    fireEvent.change(screen.getByLabelText(i18n.t("schedule.eventTitle")), { target: { value: "Half hour" } });
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const body = vi.mocked(api.post).mock.calls[0][1] as Record<string, string>;
    expect((new Date(body.end_datetime).getTime() - new Date(body.start_datetime).getTime()) / 60000).toBe(30);
  });

  it("B2: a new event is 60 minutes with no saved row", async () => {
    view();
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("schedule.create") }));
    await screen.findByLabelText(i18n.t("schedule.eventTitle"));
    fireEvent.change(screen.getByLabelText(i18n.t("schedule.eventTitle")), { target: { value: "One hour" } });
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const body = vi.mocked(api.post).mock.calls[0][1] as Record<string, string>;
    expect((new Date(body.end_datetime).getTime() - new Date(body.start_datetime).getTime()) / 60000).toBe(60);
  });

  it("B8: auto_meet turns Meet on for a new event only when Meet is available", async () => {
    answers.isTenantAdmin = true;
    answers.connected = true;
    answers.meetAvailable = true;
    answers.prefs = { ...DEFAULT_PREFS, auto_meet: true, event_minutes: 30 };
    view();
    await waitForPrefsApplied(30);
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith("/google-calendar/status"));
    await flush();
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("schedule.create") }));
    expect(await screen.findByText(i18n.t("schedule.meetPending"))).toBeTruthy();
  });

  it("B8: auto_meet with Meet unavailable leaves the new event without Meet", async () => {
    answers.isTenantAdmin = true;
    answers.connected = true;
    answers.meetAvailable = false;
    answers.prefs = { ...DEFAULT_PREFS, auto_meet: true, event_minutes: 30 };
    view();
    await waitForPrefsApplied(30);
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith("/google-calendar/status"));
    await flush();
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("schedule.create") }));
    await screen.findByLabelText(i18n.t("schedule.eventTitle"));
    expect(screen.queryByText(i18n.t("schedule.meetPending"))).toBeNull();
    fireEvent.change(screen.getByLabelText(i18n.t("schedule.eventTitle")), { target: { value: "No Meet" } });
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    expect("add_meet" in (vi.mocked(api.post).mock.calls[0][1] as Record<string, unknown>)).toBe(false);
  });

  it("B1: opens with everyone checked when 'everyone' is saved and the person may see others", async () => {
    answers.canManageOthers = true;
    answers.prefs = { ...DEFAULT_PREFS, open_owners: "all" };
    view();
    await waitFor(() => expect(ownerBox("Owner Other")?.checked).toBe(true));
    expect(ownerBox("Owner Self")?.checked).toBe(true);
  });

  it("falls back to only me when 'everyone' is saved but the person lost staff.view", async () => {
    answers.canManageOthers = false;
    answers.prefs = { ...DEFAULT_PREFS, open_owners: "all", event_minutes: 30 };
    view();
    await waitForPrefsApplied(30);
    await flush();
    expect(ownerBox("Owner Self")?.checked).toBe(true);
    expect(ownerBox("Owner Other")).toBeNull();
  });

  it("B1: opens with the team's people and me checked when 'one team' is saved", async () => {
    answers.canManageOthers = true;
    answers.teams = [{ id: 3, name: "Team Three" }];
    answers.otherTeamIds = [3];
    answers.prefs = { ...DEFAULT_PREFS, open_owners: "team", open_team_id: 3 };
    view();
    await waitFor(() => expect(ownerBox("Owner Other")?.checked).toBe(true));
    expect(ownerBox("Owner Self")?.checked).toBe(true);
  });

  it("B6 (a): a saved team that is not in the active team list falls back to only me", async () => {
    answers.canManageOthers = true;
    answers.teams = [{ id: 1, name: "Team One" }];
    answers.otherTeamIds = [9];
    answers.prefs = { ...DEFAULT_PREFS, open_owners: "team", open_team_id: 9, event_minutes: 30 };
    view();
    await waitForPrefsApplied(30);
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith("/calendar/teams"));
    await flush();
    expect(ownerBox("Owner Self")?.checked).toBe(true);
    expect(ownerBox("Owner Other")?.checked).toBe(false);
  });

  it("B6 (b): a team list that arrives after the owners and preferences still applies 'one team'", async () => {
    const gate = makeGate();
    answers.gate.teams = gate.promise;
    answers.canManageOthers = true;
    answers.teams = [{ id: 3, name: "Team Three" }];
    answers.otherTeamIds = [3];
    answers.prefs = { ...DEFAULT_PREFS, open_owners: "team", open_team_id: 3, event_minutes: 30 };
    view();
    await waitForPrefsApplied(30);
    await waitFor(() => expect(ownerBox("Owner Other")).not.toBeNull());
    await flush();
    expect(ownerBox("Owner Other")?.checked).toBe(false); // まだ当てない（チーム一覧が無い）
    gate.release();
    await waitFor(() => expect(ownerBox("Owner Other")?.checked).toBe(true));
    expect(ownerBox("Owner Self")?.checked).toBe(true);
  });

  it("B6 (c): nothing is applied until the permissions have loaded", async () => {
    const gate = makeGate();
    answers.gate.perms = gate.promise;
    answers.canManageOthers = true;
    answers.prefs = { ...DEFAULT_PREFS, open_owners: "all", event_minutes: 30 };
    view();
    await waitForPrefsApplied(30);
    await flush();
    expect(ownerBox("Owner Other")).toBeNull();
    expect(ownerBox("Owner Self")?.checked).toBe(true);
    gate.release();
    await waitFor(() => expect(ownerBox("Owner Other")?.checked).toBe(true));
    expect(ownerBox("Owner Self")?.checked).toBe(true);
  });

  it("does not apply the saved people after the person chose people by hand", async () => {
    const gate = makeGate();
    answers.gate.prefs = gate.promise;
    answers.canManageOthers = true;
    answers.prefs = { ...DEFAULT_PREFS, open_owners: "all", event_minutes: 30 };
    view();
    fireEvent.click(await screen.findByRole("checkbox", { name: "Owner Other" }));
    expect(ownerBox("Owner Other")?.checked).toBe(true);
    fireEvent.click(ownerBox("Owner Other") as HTMLInputElement); // 外す
    expect(ownerBox("Owner Other")?.checked).toBe(false);
    gate.release();
    await waitForPrefsApplied(30);
    await flush();
    expect(ownerBox("Owner Other")?.checked).toBe(false);
  });
});
