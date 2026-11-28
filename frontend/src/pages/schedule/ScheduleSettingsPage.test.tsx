/* eslint-disable local/no-japanese-literal -- テスト: 管理者が付けた種類の名前（DB の値）が画面にそのまま出ることを検証する（ADR-027・precedent: SchedulePageImpl.test.tsx） */
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { queryClient } from "../../lib/query/apiQuery";
import ScheduleSettingsPage from "./ScheduleSettingsPage";
import { eventColorLabelKey } from "./eventColors";

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: { uid: "user-a" } }),
}));

const perms = vi.hoisted(() => ({
  isTenantAdmin: false,
  staffView: false,
  loading: false,
}));

vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({
    loading: perms.loading,
    isTenantAdmin: perms.isTenantAdmin,
    hasPermission: (key: string) => key === "staff.view" && perms.staffView,
  }),
}));

const answers = vi.hoisted(() => ({
  connected: false,
  connectedAt: null as string | null,
  categories: [] as Array<Record<string, unknown>>,
  teams: [] as Array<{ id: number; name: string }>,
  meetAvailable: false,
  /** GET /calendar/preferences の応答。null は「行が無い」（既定値の応答） */
  prefs: null as Record<string, unknown> | null,
  /** true の間、初期値の読み込みを終わらせない */
  prefsPending: false,
  /** true の間、初期値の読み込みは失敗する */
  prefsFail: false as boolean,
}));

const DEFAULT_PREFS = {
  default_view: "week", week_start: 0, event_minutes: 60, auto_meet: false, open_owners: "self", open_team_id: null,
};

/** 種類の表の応答（GET /calendar/categories）の 1 行 */
function categoryRow(key: string, over: Record<string, unknown> = {}) {
  return { key, name: null, color_key: null, default_share: "all", default_team_ids: [], sort_order: 1, is_active: true, ...over };
}

vi.mock("../../lib/api", () => ({
  api: {
    get: vi.fn(async (path: string) => {
      if (path === "/calendar/categories") return answers.categories;
      if (path === "/calendar/teams") return answers.teams;
      if (path === "/google-calendar/status") {
        return { connected: answers.connected, connected_at: answers.connectedAt, meet_available: answers.meetAvailable };
      }
      if (path === "/calendar/preferences") {
        if (answers.prefsFail) throw new Error("prefs failed");
        if (answers.prefsPending) return new Promise(() => {});
        return answers.prefs ?? DEFAULT_PREFS;
      }
      if (path === "/google-calendar/connect/start") return { auth_url: "https://accounts.example/auth" };
      if (path === "/calendar/owners") {
        return {
          can_manage_others: true,
          current_staff_id: 7,
          current_user_id: 101,
          owners: [
            { staff_id: 7, user_id: 101, staff_code: "A01", name: "Owner Self", primary_email: null, color_key: "tomato", is_self: true },
            { staff_id: 8, user_id: 202, staff_code: "B02", name: "Owner Other", primary_email: null, color_key: null, is_self: false },
          ],
        };
      }
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
  perms.isTenantAdmin = false;
  perms.staffView = false;
  perms.loading = false;
  answers.connected = false;
  answers.connectedAt = null;
  answers.categories = [];
  answers.teams = [];
  answers.meetAvailable = false;
  answers.prefs = null;
  answers.prefsPending = false;
  answers.prefsFail = false;
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

const view = (url = "/schedule/settings") =>
  render(<MemoryRouter initialEntries={[url]}><ScheduleSettingsPage /></MemoryRouter>);

const googleTitle = () => i18n.t("schedule.settingsGoogleTitle");
const personalTitle = () => i18n.t("schedule.prefsTitle");

describe("ScheduleSettingsPage Google section (K1)", () => {
  it("shows the Google section to a tenant admin", async () => {
    perms.isTenantAdmin = true;
    perms.staffView = true;
    view();
    expect(await screen.findByRole("region", { name: googleTitle() })).toBeTruthy();
  });

  it("hides the Google section from a user with only staff.view and never asks for status", async () => {
    perms.staffView = true;
    view();
    expect(await screen.findByText("Owner Self")).toBeTruthy();
    expect(screen.queryByRole("region", { name: googleTitle() })).toBeNull();
    expect(mockGet).not.toHaveBeenCalledWith("/google-calendar/status");
  });

  it("shows the Google section to an admin without staff.view, no spinner left, no owners request", async () => {
    perms.isTenantAdmin = true;
    perms.staffView = false;
    view();
    expect(await screen.findByRole("region", { name: googleTitle() })).toBeTruthy();
    expect(document.querySelector('[aria-busy="true"]')).toBeNull();
    expect(screen.queryByRole("status", { name: /./ })).toBeNull();
    expect(mockGet).not.toHaveBeenCalledWith("/calendar/owners");
    expect(screen.queryByText(i18n.t("schedule.myCalendars"))).toBeNull();
  });

  it("shows only the personal section to a user with neither (no admin sections, no owners request)", async () => {
    view();
    expect(await screen.findByRole("region", { name: personalTitle() })).toBeTruthy();
    expect(screen.queryByRole("region", { name: googleTitle() })).toBeNull();
    expect(screen.queryByRole("region", { name: i18n.t("schedule.categoriesTitle") })).toBeNull();
    expect(screen.queryByText(i18n.t("schedule.myCalendars"))).toBeNull();
    expect(mockGet).not.toHaveBeenCalledWith("/calendar/owners");
    expect(mockGet).not.toHaveBeenCalledWith("/google-calendar/status");
  });
});

describe("ScheduleSettingsPage connect flow (K2)", () => {
  it("opens the notice first and calls connect/start only after confirming", async () => {
    perms.isTenantAdmin = true;
    view();
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("schedule.connect") }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(i18n.t("schedule.connectNoticeTitle"))).toBeTruthy();
    expect(within(dialog).getByText(i18n.t("schedule.connectNoticeItemEvents"))).toBeTruthy();
    expect(mockGet).not.toHaveBeenCalledWith("/google-calendar/connect/start");
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("schedule.connectNoticeConfirm") }));
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith("/google-calendar/connect/start"));
    await waitFor(() => expect(hrefSetter).toHaveBeenCalledWith("https://accounts.example/auth"));
  });

  it("does not call connect/start when the notice is cancelled", async () => {
    perms.isTenantAdmin = true;
    view();
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("schedule.connect") }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("confirmModal.defaultCancel") }));
    expect(mockGet).not.toHaveBeenCalledWith("/google-calendar/connect/start");
  });
});

describe("ScheduleSettingsPage disconnect (K3・K5)", () => {
  const openDisconnect = async () => {
    perms.isTenantAdmin = true;
    answers.connected = true;
    answers.connectedAt = "2026-11-01T03:00:00Z";
    view();
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("schedule.disconnect") }));
    return screen.findByRole("dialog");
  };

  it("deletes the connection and shows the success message", async () => {
    const dialog = await openDisconnect();
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("schedule.disconnect") }));
    await waitFor(() => expect(api.delete).toHaveBeenCalledWith("/google-calendar/connect"));
    expect(await screen.findByText(i18n.t("schedule.disconnectSuccess"))).toBeTruthy();
  });

  it("shows the failure message when the disconnect fails", async () => {
    vi.mocked(api.delete).mockRejectedValueOnce(new Error("502"));
    const dialog = await openDisconnect();
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("schedule.disconnect") }));
    expect(await screen.findByText(i18n.t("schedule.disconnectError"))).toBeTruthy();
    expect(screen.queryByText(i18n.t("schedule.disconnectSuccess"))).toBeNull();
  });
});

describe("ScheduleSettingsPage result banner (K7)", () => {
  it("shows success for ?connected=true", async () => {
    perms.isTenantAdmin = true;
    view("/schedule/settings?connected=true");
    expect(await screen.findByText(i18n.t("schedule.connectSuccess"))).toBeTruthy();
  });

  it("shows the scope-missing message for ?connected=false&error=scope_missing", async () => {
    perms.isTenantAdmin = true;
    view("/schedule/settings?connected=false&error=scope_missing");
    expect(await screen.findByText(i18n.t("schedule.connectScopeMissing"))).toBeTruthy();
    expect(screen.queryByText(i18n.t("schedule.connectError"))).toBeNull();
  });

  it("shows the generic error for ?connected=false alone", async () => {
    perms.isTenantAdmin = true;
    view("/schedule/settings?connected=false");
    expect(await screen.findByText(i18n.t("schedule.connectError"))).toBeTruthy();
    expect(screen.queryByText(i18n.t("schedule.connectScopeMissing"))).toBeNull();
  });
});

describe("ScheduleSettingsPage categories section (schedule-settings bin2a A8)", () => {
  const categoriesTitle = () => i18n.t("schedule.categoriesTitle");

  it("shows the categories section to a tenant admin (with and without staff.view)", async () => {
    for (const staffView of [true, false]) {
      perms.isTenantAdmin = true;
      perms.staffView = staffView;
      const { unmount } = view();
      expect(await screen.findByRole("region", { name: categoriesTitle() })).toBeTruthy();
      unmount();
      queryClient.clear();
    }
  });

  it("hides the categories section from a user with only staff.view", async () => {
    perms.staffView = true;
    view();
    expect(await screen.findByText("Owner Self")).toBeTruthy();
    expect(screen.queryByRole("region", { name: categoriesTitle() })).toBeNull();
  });

  it("saves one category with its name, color, share and use", async () => {
    perms.isTenantAdmin = true;
    answers.categories = [categoryRow("meeting"), categoryRow("shipping", { sort_order: 2 })];
    view();
    const region = await screen.findByRole("region", { name: categoriesTitle() });
    const names = await within(region).findAllByLabelText(i18n.t("schedule.categoryName"));
    expect(names).toHaveLength(2);
    // 7 種は名前が空で、i18n の名前が見本として出る
    expect((names[1] as HTMLInputElement).placeholder).toBe(i18n.t("schedule.calendarLabels.shipping"));
    fireEvent.change(names[1], { target: { value: "出荷便" } });
    const shares = within(region).getAllByLabelText(i18n.t("schedule.categoryDefaultShare"));
    fireEvent.change(shares[1], { target: { value: "self" } });
    // meeting の「使う」は切れない
    const uses = within(region).getAllByRole("switch", { name: i18n.t("schedule.categoryActive") }) as HTMLInputElement[];
    expect(uses[0].disabled).toBe(true);
    expect(uses[1].disabled).toBe(false);
    fireEvent.click(uses[1]);
    fireEvent.click(within(region).getAllByRole("button", { name: i18n.t("schedule.settingsSave") })[1]);
    await waitFor(() =>
      expect(api.patch).toHaveBeenCalledWith("/calendar/categories/shipping", {
        name: "出荷便",
        color_key: "",
        default_share: "self",
        is_active: false,
      }),
    );
  });

  it("team default share: needs a team, then sends default_team_ids", async () => {
    perms.isTenantAdmin = true;
    answers.teams = [
      { id: 1, name: "Team One" },
      { id: 2, name: "Team Two" },
    ];
    answers.categories = [categoryRow("meeting"), categoryRow("shipping", { sort_order: 2 })];
    view();
    const region = await screen.findByRole("region", { name: categoriesTitle() });
    const shares = (await within(region).findAllByLabelText(i18n.t("schedule.categoryDefaultShare"))) as HTMLSelectElement[];
    expect(Array.from(shares[1].options).map((option) => option.value)).toEqual(["self", "all", "team"]);
    fireEvent.change(shares[1], { target: { value: "team" } });
    // 0 個のままでは送らず、文を出す
    expect(await within(region).findByText(i18n.t("schedule.shareTeamsRequired"))).toBeTruthy();
    fireEvent.click(within(region).getAllByRole("button", { name: i18n.t("schedule.settingsSave") })[1]);
    expect(api.patch).not.toHaveBeenCalled();
    fireEvent.click(await within(region).findByTestId("schedule-category-teams-shipping-button"));
    fireEvent.click(await screen.findByTestId("schedule-category-teams-shipping-option-2"));
    fireEvent.click(within(region).getAllByRole("button", { name: i18n.t("schedule.settingsSave") })[1]);
    await waitFor(() =>
      expect(api.patch).toHaveBeenCalledWith("/calendar/categories/shipping", {
        name: "",
        color_key: "",
        default_share: "team",
        default_team_ids: [2],
        is_active: true,
      }),
    );
  });

  it("shows the saved default teams of a team category", async () => {
    perms.isTenantAdmin = true;
    answers.teams = [
      { id: 1, name: "Team One" },
      { id: 2, name: "Team Two" },
    ];
    answers.categories = [categoryRow("meeting"), categoryRow("shipping", { sort_order: 2, default_share: "team", default_team_ids: [1] })];
    view();
    const region = await screen.findByRole("region", { name: categoriesTitle() });
    const button = await within(region).findByTestId("schedule-category-teams-shipping-button");
    expect(button.textContent).toContain("Team One");
    expect(within(region).queryByText(i18n.t("schedule.shareTeamsRequired"))).toBeNull();
  });

  it("adds a category with a name and posts it", async () => {
    perms.isTenantAdmin = true;
    answers.categories = [categoryRow("meeting")];
    vi.mocked(api.post).mockResolvedValueOnce(categoryRow("custom_1", { name: "見積り", sort_order: 8 }));
    view();
    const region = await screen.findByRole("region", { name: categoriesTitle() });
    fireEvent.click(within(region).getByRole("button", { name: i18n.t("schedule.categoryAdd") }));
    const names = within(region).getAllByLabelText(i18n.t("schedule.categoryName"));
    expect(names).toHaveLength(2);
    // 名前が空のままでは送らず、文を出す
    fireEvent.click(within(region).getAllByRole("button", { name: i18n.t("schedule.settingsSave") })[1]);
    expect(await within(region).findByText(i18n.t("schedule.categoryErrorNameRequired"))).toBeTruthy();
    expect(api.post).not.toHaveBeenCalled();
    fireEvent.change(names[1], { target: { value: "見積り" } });
    fireEvent.click(within(region).getAllByRole("button", { name: i18n.t("schedule.settingsSave") })[1]);
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/calendar/categories", {
        name: "見積り",
        color_key: "",
        default_share: "all",
      }),
    );
  });

  it("shows the conflict sentence on 409 and the generic sentence on other failures", async () => {
    perms.isTenantAdmin = true;
    answers.categories = [categoryRow("meeting")];
    view();
    const region = await screen.findByRole("region", { name: categoriesTitle() });
    fireEvent.click(within(region).getByRole("button", { name: i18n.t("schedule.categoryAdd") }));
    const names = within(region).getAllByLabelText(i18n.t("schedule.categoryName"));
    fireEvent.change(names[1], { target: { value: "契約" } });
    vi.mocked(api.post).mockRejectedValueOnce(Object.assign(new Error("category_conflict"), { status: 409 }));
    fireEvent.click(within(region).getAllByRole("button", { name: i18n.t("schedule.settingsSave") })[1]);
    expect(await within(region).findByText(i18n.t("schedule.categoryErrorConflict"))).toBeTruthy();
    vi.mocked(api.post).mockRejectedValueOnce(new Error("boom"));
    fireEvent.click(within(region).getAllByRole("button", { name: i18n.t("schedule.settingsSave") })[1]);
    expect(await within(region).findByText(i18n.t("schedule.categoryErrorSave"))).toBeTruthy();
  });
});

describe("ScheduleSettingsPage owners and nav (K9・K10)", () => {
  it("has no visibility switch or share-permission select, and saves only the color", async () => {
    perms.staffView = true;
    view();
    await screen.findByText("Owner Self");
    // 人の色の区画には切り替えも共有権限の選択も無い（あるのは自分の初期値の選択 4 つだけ。Meet の行は隠れている）
    expect(screen.queryAllByRole("switch")).toHaveLength(0);
    expect(screen.queryAllByRole("combobox")).toHaveLength(4);
    expect(screen.queryByRole("combobox", { name: i18n.t("schedule.shareLabel") })).toBeNull();
    fireEvent.click(screen.getAllByRole("button", { name: i18n.t("schedule.settingsSave") })[1]);
    await waitFor(() => expect(api.patch).toHaveBeenCalledWith("/calendar/owners/101", { color_key: "tomato" }));
  });

  it("A1: person colors use the swatch picker, with no free color input", async () => {
    perms.staffView = true;
    view();
    await screen.findByText("Owner Self");
    expect(document.querySelector("input[type=color]")).toBeNull();
    const pickers = document.querySelectorAll(".comp-color-swatch-picker");
    expect(pickers.length).toBeGreaterThanOrEqual(2);
  });

  it("A2: choosing a color sends its color_key, and the default color sends null", async () => {
    perms.staffView = true;
    view();
    await screen.findByText("Owner Self");
    const colorLabel = i18n.t("schedule.settingsCalendarColor");
    const openButton = (index: number) =>
      screen.getAllByRole("button", { name: new RegExp(`^${colorLabel}:`) })[index];

    const radio = (group: string, label: string) =>
      screen.getAllByRole("radio", { name: label }).find((r) => (r as HTMLInputElement).name === group) as HTMLElement;

    fireEvent.click(openButton(1));
    fireEvent.click(radio("owner-color-8", i18n.t(eventColorLabelKey("basil"))));
    fireEvent.click(screen.getAllByRole("button", { name: i18n.t("schedule.settingsSave") })[2]);
    await waitFor(() => expect(api.patch).toHaveBeenCalledWith("/calendar/owners/202", { color_key: "basil" }));

    fireEvent.click(openButton(0));
    fireEvent.click(radio("owner-color-7", i18n.t("schedule.ownerColorDefault")));
    fireEvent.click(screen.getAllByRole("button", { name: i18n.t("schedule.settingsSave") })[1]);
    await waitFor(() => expect(api.patch).toHaveBeenCalledWith("/calendar/owners/101", { color_key: null }));
  });

  it("renders the side list as the SubMenu mold and moves to a section on click", async () => {
    perms.isTenantAdmin = true;
    perms.staffView = true;
    const scroll = vi.fn();
    const originalScrollIntoView = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = scroll;
    try {
      view();
      await screen.findByText("Owner Self");
      const nav = document.querySelector("nav.comp-subnav");
      expect(nav).not.toBeNull();
      expect(document.querySelector(".schedule-settings__nav-item")).toBeNull();
      const others = within(nav as HTMLElement).getByText(i18n.t("schedule.otherCalendars"));
      fireEvent.click(others);
      await waitFor(() => expect(scroll).toHaveBeenCalled());
    } finally {
      Element.prototype.scrollIntoView = originalScrollIntoView;
    }
  });
});

describe("ScheduleSettingsPage personal section (schedule-settings bin3b)", () => {
  const saveButton = () => within(screen.getByRole("region", { name: personalTitle() })).getByRole("button", { name: i18n.t("schedule.settingsSave") });
  const openOwners = () => screen.getByRole("combobox", { name: i18n.t("schedule.prefsOpenOwners") }) as HTMLSelectElement;
  const optionValues = (select: HTMLSelectElement) => Array.from(select.options).map((option) => option.value);

  it("is the first section in the side list and the one shown first, for a plain user", async () => {
    view();
    await screen.findByRole("region", { name: personalTitle() });
    const nav = document.querySelector("nav.comp-subnav") as HTMLElement;
    expect(within(nav).getAllByRole("button")[0].textContent).toContain(personalTitle());
  });

  it("shows the saved values and saves them all in one PUT", async () => {
    answers.prefs = { default_view: "month", week_start: 1, event_minutes: 30, auto_meet: false, open_owners: "self", open_team_id: null };
    view();
    const firstView = (await screen.findByRole("combobox", { name: i18n.t("schedule.prefsFirstView") })) as HTMLSelectElement;
    await waitFor(() => expect(firstView.value).toBe("month"));
    expect((screen.getByRole("combobox", { name: i18n.t("schedule.prefsWeekStart") }) as HTMLSelectElement).value).toBe("1");
    expect((screen.getByRole("combobox", { name: i18n.t("schedule.prefsEventMinutes") }) as HTMLSelectElement).value).toBe("30");
    fireEvent.change(firstView, { target: { value: "list" } });
    fireEvent.change(screen.getByRole("combobox", { name: i18n.t("schedule.prefsWeekStart") }), { target: { value: "0" } });
    fireEvent.change(screen.getByRole("combobox", { name: i18n.t("schedule.prefsEventMinutes") }), { target: { value: "90" } });
    fireEvent.click(saveButton());
    await waitFor(() =>
      expect(api.put).toHaveBeenCalledWith("/calendar/preferences", {
        default_view: "list", week_start: 0, event_minutes: 90, auto_meet: false, open_owners: "self", open_team_id: null,
      }),
    );
    expect(await screen.findByText(i18n.t("schedule.prefsSaved"))).toBeTruthy();
  });

  it("waits for the preferences cache to be reread before showing the saved sentence", async () => {
    view();
    await screen.findByRole("region", { name: personalTitle() });
    await waitFor(() => expect((saveButton() as HTMLButtonElement).disabled).toBe(false));
    const spy = vi.spyOn(queryClient, "invalidateQueries");
    fireEvent.click(saveButton());
    await waitFor(() => expect(api.put).toHaveBeenCalled());
    await screen.findByText(i18n.t("schedule.prefsSaved"));
    expect(spy).toHaveBeenCalledWith({ queryKey: ["api", "user-a", "calendar", "preferences"] });
  });

  it("shows the failure sentence when saving fails", async () => {
    vi.mocked(api.put).mockRejectedValueOnce(new Error("boom"));
    view();
    await screen.findByRole("region", { name: personalTitle() });
    await waitFor(() => expect((saveButton() as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(saveButton());
    expect(await screen.findByText(i18n.t("schedule.prefsSaveError"))).toBeTruthy();
    expect(screen.queryByText(i18n.t("schedule.prefsSaved"))).toBeNull();
  });

  it("keeps Save disabled until the preferences are read, so the defaults never overwrite saved values", async () => {
    answers.prefsPending = true;
    view();
    await screen.findByRole("region", { name: personalTitle() });
    expect((saveButton() as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(saveButton());
    expect(api.put).not.toHaveBeenCalled();
  });

  it("K3: shows the preference load failure sentence as an alert and keeps Save disabled", async () => {
    answers.prefsFail = true;
    view();
    const sentence = await screen.findByText(i18n.t("schedule.prefsLoadError"));
    expect(sentence.getAttribute("role")).toBe("alert");
    expect((saveButton() as HTMLButtonElement).disabled).toBe(true);
  });

  it("hides the Meet row without meet_available, and still sends the loaded auto_meet", async () => {
    answers.prefs = { default_view: "week", week_start: 0, event_minutes: 60, auto_meet: true, open_owners: "self", open_team_id: null };
    view();
    await screen.findByRole("region", { name: personalTitle() });
    expect(screen.queryByRole("switch", { name: i18n.t("schedule.prefsAutoMeet") })).toBeNull();
    await waitFor(() => expect((saveButton() as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(saveButton());
    await waitFor(() =>
      expect(api.put).toHaveBeenCalledWith("/calendar/preferences", expect.objectContaining({ auto_meet: true })),
    );
  });

  it("shows the Meet switch when Meet is available and saves the change", async () => {
    perms.isTenantAdmin = true;
    answers.connected = true;
    answers.meetAvailable = true;
    view();
    const toggle = (await screen.findByRole("switch", { name: i18n.t("schedule.prefsAutoMeet") })) as HTMLInputElement;
    expect(toggle.checked).toBe(false);
    fireEvent.click(toggle);
    fireEvent.click(saveButton());
    await waitFor(() =>
      expect(api.put).toHaveBeenCalledWith("/calendar/preferences", expect.objectContaining({ auto_meet: true })),
    );
  });

  it("offers only 'only me' to a user without staff.view", async () => {
    view();
    await screen.findByRole("region", { name: personalTitle() });
    expect(optionValues(openOwners())).toEqual(["self"]);
  });

  it("offers everyone and one team to a staff.view user (not admin), with the team choices", async () => {
    perms.staffView = true;
    answers.teams = [{ id: 1, name: "Team One" }, { id: 2, name: "Team Two" }];
    view();
    await screen.findByRole("region", { name: personalTitle() });
    await waitFor(() => expect(optionValues(openOwners())).toEqual(["self", "all", "team"]));
    fireEvent.change(openOwners(), { target: { value: "team" } });
    const team = (await screen.findByRole("combobox", { name: i18n.t("schedule.prefsTeam") })) as HTMLSelectElement;
    await waitFor(() => expect(optionValues(team)).toEqual(["", "1", "2"]));
    fireEvent.change(team, { target: { value: "2" } });
    fireEvent.click(saveButton());
    await waitFor(() =>
      expect(api.put).toHaveBeenCalledWith("/calendar/preferences", expect.objectContaining({ open_owners: "team", open_team_id: 2 })),
    );
  });

  it("sends a null team when the mode is not team", async () => {
    perms.staffView = true;
    answers.prefs = { default_view: "week", week_start: 0, event_minutes: 60, auto_meet: false, open_owners: "all", open_team_id: 5 };
    view();
    await screen.findByRole("region", { name: personalTitle() });
    await waitFor(() => expect((saveButton() as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(saveButton());
    await waitFor(() =>
      expect(api.put).toHaveBeenCalledWith("/calendar/preferences", expect.objectContaining({ open_owners: "all", open_team_id: null })),
    );
  });
});
