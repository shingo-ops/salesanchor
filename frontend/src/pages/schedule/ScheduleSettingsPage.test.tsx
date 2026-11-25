/* eslint-disable local/no-japanese-literal -- テスト: 管理者が付けた種類の名前（DB の値）が画面にそのまま出ることを検証する（ADR-027・precedent: SchedulePageImpl.test.tsx） */
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { queryClient } from "../../lib/query/apiQuery";
import ScheduleSettingsPage from "./ScheduleSettingsPage";

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
}));

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
        return { connected: answers.connected, connected_at: answers.connectedAt };
      }
      if (path === "/google-calendar/connect/start") return { auth_url: "https://accounts.example/auth" };
      if (path === "/calendar/owners") {
        return {
          can_manage_others: true,
          current_staff_id: 7,
          current_user_id: 101,
          owners: [
            { staff_id: 7, user_id: 101, staff_code: "A01", name: "Owner Self", primary_email: null, color: "rgb(17, 34, 51)", is_visible: true, share_mode: "self", is_self: true },
            { staff_id: 8, user_id: 202, staff_code: "B02", name: "Owner Other", primary_email: null, color: "rgb(68, 85, 102)", is_visible: true, share_mode: "view", is_self: false },
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

  it("shows the permission message to a user with neither", async () => {
    view();
    expect(await screen.findByText(i18n.t("schedule.settingsPermissionRequired"))).toBeTruthy();
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
    expect(screen.queryAllByRole("switch")).toHaveLength(0);
    expect(screen.queryAllByRole("combobox")).toHaveLength(0);
    fireEvent.click(screen.getAllByRole("button", { name: i18n.t("schedule.settingsSave") })[0]);
    await waitFor(() => expect(api.patch).toHaveBeenCalledWith("/calendar/owners/101", { color: "rgb(17, 34, 51)" }));
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
