/**
 * ADR-1054 段 3 の 4 回目: 本物の画面の試験。
 * Q1 戻った時に写しを先に出す（読み込み中の印を出さない）・一覧の画面は見出しの横に回る印・裏で取り直す。
 * Q2 報酬の設定を読めなかった時は保存のボタンを押せない（既定の値で本物の設定を上書きしない）。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import type { ComponentType } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ArchivesPage from "../../pages/archives/ArchivesPage";
import CommissionSettingsPage from "../../pages/commission-settings/CommissionSettingsPage";
import CommissionsPage from "../../pages/commissions/CommissionsPage";
import ERPPage from "../../pages/erp/ERPPage";
import NotificationsPage from "../../pages/notifications/NotificationsPage";
import SalesPage from "../../pages/sales/SalesPage";
import ShiftsPage from "../../pages/shifts/ShiftsPage";
import StaffReportsPage from "../../pages/staff-reports/StaffReportsPage";
import { api } from "../api";
import { QueryAuthSync } from "./QueryAuthSync";
import { queryClient } from "./apiQuery";

const auth = vi.hoisted(() => ({ user: { uid: "uid-A" } as { uid: string } | null }));

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: auth.user, loading: false }),
}));
vi.mock("../auth/selfAuth", () => ({
  getAccessToken: async () => "test-token",
  expireSession: vi.fn(),
  selfRefresh: vi.fn(),
}));
vi.mock("../../hooks/usePermissions", () => ({ usePermissions: () => ({ hasPermission: () => true, loading: false }) }));
vi.mock("../../hooks/useSSE", () => ({ useSSE: vi.fn() }));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
  // api.ts が i18n.ts を読み、i18n.ts が initReactI18next を使う（同じ書き方: src/lib/query/batch3cPages.test.tsx）
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

// 中身は画面の型（ArchivesPage.tsx:11・ERPPage.tsx:14・ShiftsPage.tsx:15・StaffReportsPage.tsx:14-18・
// NotificationsPage.tsx:18-19・SalesPage.tsx:24-45・CommissionsPage.tsx:44-61・CommissionSettingsPage.tsx:29-35）の欄
const archive = { id: 1, source_table: "Fixture Table", source_id: 9, archived_by: null, archived_at: "2026-11-01T00:00:00Z", restored_at: null };
const syncLog = { id: 1, sync_type: "Fixture Sync", direction: "export", record_count: 1, status: "success", error_message: null, started_at: "2026-11-01T00:00:00Z", completed_at: null };
const shift = { id: 1, user_id: 5, shift_date: "2026-11-01", start_time: "09:00", end_time: "18:00", shift_type: "Fixture Shift", notes: null, created_at: "" };
const report = { id: 1, report_code: "SR-FIX", report_type: "daily", user_id: 5, period: "2026-11", review: null, goals: null, challenges: null, reviewer_comment: null, reviewed_at: null, submitted_at: null, created_at: "" };
const channel = { id: 1, channel_name: "Fixture Channel", webhook_url: "https://example.invalid/hook", event_types: "", is_active: true, created_at: "" };
const sales = {
  items: [{ order_id: 1, order_number: "ORD-FIX", company_name: null, contact_display_name: null, currency: "JPY", created_at: "2026-11-01T00:00:00Z", revenue_amount: null, cost_total: null, gross_profit: null, gross_profit_rate: null }],
  count: 1, revenue_total: 0, cost_total: 0, gross_profit_total: 0, gross_profit_rate: null,
};
const monthly = { year: 2026, month: 11, by_staff: [{ staff_id: 5, staff_name: "Fixture Staff", total: 100 }], by_role: [], total: 100 };
const settings = {
  id: 1, tenant_id: 1, created_at: "", updated_at: "2026-11-01T00:00:00Z",
  commission_rates: {
    sales: { type: "rate", value: 0.37 }, order: { type: "rate", value: 0.1 }, ship: { type: "fixed", value: 200 },
    purchase: { type: "fixed", value: 100 }, trouble: { type: "fixed", value: 500 },
  },
};

const fixtures: Record<string, unknown> = {
  "/archives": [archive],
  "/erp/sync-logs": [syncLog],
  "/shifts": [shift],
  "/staff-reports": [report],
  "/notification-channels": [channel],
  "/notification-event-types": [],
  "/financials/orders": sales,
  "/tenant-commission-settings": settings,
};
// 報酬の月の集計は年と月で path が変わるので頭で見分ける
const answer = (path: string) =>
  (path in fixtures ? fixtures[path] : path.startsWith("/commissions/monthly?") ? monthly : []) as never;

type Case = {
  name: string; Page: ComponentType; route: string; at: string;
  path: string | RegExp; text: string; value: boolean; spinner: boolean;
};
const cases: Case[] = [
  { name: "archives", Page: ArchivesPage, route: "/crm/archive", at: "/crm/archive", path: "/archives", text: "Fixture Table", value: false, spinner: true },
  { name: "erp", Page: ERPPage, route: "/data", at: "/data", path: "/erp/sync-logs", text: "Fixture Sync", value: false, spinner: true },
  { name: "shifts", Page: ShiftsPage, route: "/shifts", at: "/shifts", path: "/shifts", text: "Fixture Shift", value: false, spinner: true },
  { name: "staff reports", Page: StaffReportsPage, route: "/reports", at: "/reports", path: "/staff-reports", text: "SR-FIX", value: false, spinner: true },
  { name: "notifications", Page: NotificationsPage, route: "/management-center/notifications", at: "/management-center/notifications", path: "/notification-channels", text: "Fixture Channel", value: false, spinner: true },
  { name: "sales", Page: SalesPage, route: "/sales", at: "/sales", path: "/financials/orders", text: "ORD-FIX", value: false, spinner: true },
  { name: "commissions", Page: CommissionsPage, route: "/commissions", at: "/commissions", path: /^\/commissions\/monthly\?year=\d{4}&month=\d{1,2}$/, text: "Fixture Staff", value: false, spinner: true },
  { name: "commission settings", Page: CommissionSettingsPage, route: "/commission-settings", at: "/commission-settings", path: "/tenant-commission-settings", text: "0.37", value: true, spinner: false },
];

function Tree({ c }: { c: Pick<Case, "Page" | "route" | "at"> }) {
  const Page = c.Page;
  return (
    <QueryClientProvider client={queryClient}>
      <QueryAuthSync />
      <MemoryRouter initialEntries={[c.at]}>
        <Routes><Route path={c.route} element={<Page />} /></Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// 設定の画面は欄の中の値で、ほかは文字で見分ける
const shown = (c: Case) => (c.value ? screen.queryAllByDisplayValue(c.text) : screen.queryAllByText(c.text));
const found = (c: Case) => (c.value ? screen.findAllByDisplayValue(c.text) : screen.findAllByText(c.text));
const calledPath = (c: Case) => (typeof c.path === "string" ? c.path : expect.stringMatching(c.path));

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(() => { throw new Error("Unexpected real network request"); }));
});

afterEach(() => {
  cleanup();
  queryClient.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  auth.user = { uid: "uid-A" };
});

describe("revisit shows the copy first (Q1)", () => {
  it.each(cases)("$name shows the previous content at once on revisit", async (c) => {
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) => answer(path));
    const first = render(<Tree c={c} />);
    await found(c);
    first.unmount();

    spy.mockClear();
    spy.mockImplementation(() => new Promise<never>(() => {}));
    const { container } = render(<Tree c={c} />);
    expect(shown(c).length).toBeGreaterThan(0);
    expect(container.querySelector(".sa-loading-block")).toBeNull();
    if (c.spinner) {
      await waitFor(() => expect(container.querySelector(".page-layout-title-row .sa-spinner")).not.toBeNull());
    }
    await waitFor(() => expect(spy).toHaveBeenCalledWith(calledPath(c)));
  });
});

describe("commission settings save is blocked until the settings are read (Q2)", () => {
  it("disables save when the settings could not be read", async () => {
    vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === "/tenant-commission-settings") throw new Error("Fixture read failure");
      return answer(path);
    });
    render(<Tree c={{ Page: CommissionSettingsPage, route: "/commission-settings", at: "/commission-settings" }} />);
    await screen.findByText("Fixture read failure");
    expect((screen.getByTestId("settings-save") as HTMLButtonElement).disabled).toBe(true);
  });

  it("enables save once the settings are read", async () => {
    vi.spyOn(api, "get").mockImplementation(async (path: string) => answer(path));
    render(<Tree c={{ Page: CommissionSettingsPage, route: "/commission-settings", at: "/commission-settings" }} />);
    await screen.findAllByDisplayValue("0.37");
    expect((screen.getByTestId("settings-save") as HTMLButtonElement).disabled).toBe(false);
  });
});
