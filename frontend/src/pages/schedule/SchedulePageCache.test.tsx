/**
 * ADR-1054 段 3 の 7 回目: 予定表の写し。
 * R1 戻った時に前の予定をすぐ出す（読み込み中の印を出さない）・裏で 3 本を取り直す。
 * R2 予定を保存した後は予定の写しだけを取り直す（読み込み中の印を出さない・持ち主とシフトは取り直さない）。
 * R3 写しを出したまま裏の取り直しが失敗したら、前の予定を出したまま取れなかった文を出す。写しが無い時の失敗は今と同じく文を出さない。
 * R4 見本の状態（demoState=empty）では 3 本を取りに行かない。
 * R5 前に見た週へ戻った時はすぐ出す。写しの無い週へ移った時は今と同じく読み込み中の印を出す。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { queryClient } from "../../lib/query/apiQuery";
import SchedulePage from "./SchedulePageImpl";

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: { uid: "user-a" } }),
}));

// mode: ok = 答える・hang = 3 本は返事を返さない・fail = 3 本は失敗する（権限など 3 本以外はいつも答える）
const answers = vi.hoisted(() => ({ mode: "ok" as "ok" | "hang" | "fail" }));

function todayAt(hour: number) {
  const d = new Date();
  d.setHours(hour, 0, 0, 0);
  return d.toISOString();
}

// 中身は SchedulePageImpl.test.tsx の答えと同じ形（schedule-owner.ts の ApiCalendarOwnersResponse・schedule-utils.ts の ApiCalendarEvent）
const OWNERS = {
  can_manage_others: false,
  current_staff_id: 7,
  current_user_id: 101,
  owners: [
    { staff_id: 7, user_id: 101, staff_code: "A01", name: "Owner Self", primary_email: null, color: null, is_visible: true, share_mode: "self", is_self: true },
  ],
};
const eventsAnswer = () => ({
  events: [{
    id: 1, user_id: 101, calendar_type: "shared", category: "meeting", title: "Cached Event",
    description: null, location: null, start_datetime: todayAt(10), end_datetime: todayAt(11),
    is_all_day: false, google_event_id: null, source: "app", sync_status: "synced",
    created_by_user_id: 101, created_at: null, updated_at: null, owner_name: null, created_by_name: null,
  }],
});
const isScheduleRead = (path: string) =>
  path === "/calendar/owners" || path.startsWith("/calendar/events?") || path.startsWith("/shifts?");

vi.mock("../../lib/api", () => ({
  api: {
    get: vi.fn(async (path: string) => {
      if (path === "/me/permissions") return { permissions: [], is_tenant_admin: false };
      if (isScheduleRead(path) && answers.mode === "hang") return new Promise<never>(() => {});
      if (isScheduleRead(path) && answers.mode === "fail") throw new Error("read failed");
      if (path === "/calendar/owners") return OWNERS;
      if (path.startsWith("/calendar/events?")) return eventsAnswer();
      if (path.startsWith("/shifts?")) return [];
      throw new Error(`Unexpected GET ${path}`);
    }),
    post: vi.fn(async () => ({})),
    patch: vi.fn(async () => ({})),
    put: vi.fn(async () => ({})),
    delete: vi.fn(async () => ({})),
  },
}));

import { api } from "../../lib/api";
const mockGet = vi.mocked(api.get);
const readsOf = (head: string) => mockGet.mock.calls.filter(([path]) => String(path).startsWith(head)).length;
const view = (url = "/schedule") => render(<MemoryRouter initialEntries={[url]}><SchedulePage /></MemoryRouter>);
const loadingMark = () => document.querySelector(".schedule-loading");

beforeEach(async () => {
  await i18n.changeLanguage("ja");
  answers.mode = "ok";
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  queryClient.clear();
});

describe("schedule revisit shows the copy first (R1)", () => {
  it("shows the previous events at once on revisit and refetches the three reads", async () => {
    const first = view();
    await screen.findByText("Cached Event");
    first.unmount();
    mockGet.mockClear();
    answers.mode = "hang";
    view();
    expect(screen.queryAllByText("Cached Event").length).toBeGreaterThan(0);
    expect(loadingMark()).toBeNull();
    await waitFor(() => expect(readsOf("/calendar/owners")).toBe(1));
    expect(readsOf("/calendar/events?")).toBe(1);
    expect(readsOf("/shifts?")).toBe(1);
  });
});

describe("schedule save refetches only the events (R2)", () => {
  it("refetches only the events after saving, without the loading mark", async () => {
    view();
    await screen.findByText("Cached Event");
    await waitFor(() => expect(readsOf("/shifts?")).toBe(1));
    mockGet.mockClear();
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("schedule.create") }));
    fireEvent.change(screen.getByPlaceholderText(i18n.t("schedule.eventTitle")), { target: { value: "New Event" } });
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    await waitFor(() => expect(readsOf("/calendar/events?")).toBe(1));
    expect(loadingMark()).toBeNull();
    expect(screen.queryAllByText("Cached Event").length).toBeGreaterThan(0);
    expect(readsOf("/calendar/owners")).toBe(0);
    expect(readsOf("/shifts?")).toBe(0);
  });
});

describe("schedule read failure (R3)", () => {
  it("keeps the previous events and shows the fetch error when the refetch fails", async () => {
    const first = view();
    await screen.findByText("Cached Event");
    first.unmount();
    answers.mode = "fail";
    view();
    expect(screen.queryAllByText("Cached Event").length).toBeGreaterThan(0);
    expect(await screen.findByText(i18n.t("schedule.errorFetch"))).toBeTruthy();
    expect(screen.queryAllByText("Cached Event").length).toBeGreaterThan(0);
  });

  it("shows the grid without the error text when the first read fails (as today)", async () => {
    answers.mode = "fail";
    const { container } = view();
    await waitFor(() => expect(container.querySelector(".schedule-main__surface")).not.toBeNull());
    expect(loadingMark()).toBeNull();
    expect(screen.queryByText(i18n.t("schedule.errorFetch"))).toBeNull();
  });
});

describe("schedule demo state (R4)", () => {
  it("does not read the three paths in the empty demo state", async () => {
    const { container } = view("/schedule?demoState=empty");
    await waitFor(() => expect(container.querySelector(".schedule-main__surface")).not.toBeNull());
    expect(readsOf("/calendar/owners") + readsOf("/calendar/events?") + readsOf("/shifts?")).toBe(0);
  });
});

describe("schedule period change (R5)", () => {
  it("shows the earlier week at once when going back, and the loading mark for an unread week", async () => {
    view();
    await screen.findByText("Cached Event");
    answers.mode = "hang";
    fireEvent.click(screen.getByRole("button", { name: i18n.t("schedule.nextPeriod") }));
    await waitFor(() => expect(loadingMark()).not.toBeNull());
    fireEvent.click(screen.getByRole("button", { name: i18n.t("schedule.prevPeriod") }));
    expect(loadingMark()).toBeNull();
    expect(screen.queryAllByText("Cached Event").length).toBeGreaterThan(0);
  });
});
