/**
 * ADR-1054 段 3 の 2 回目: 本物の画面の試験（Q1）。
 * Q1 戻った時に写しを先に出す（読み込み中の印を出さない）・一覧と詳しい画面は見出しの横に回る印・裏で取り直す。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import type { ComponentType } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ContactsPage from "../../pages/contacts/ContactsPage";
import FunnelLeadsPage from "../../pages/dashboard/FunnelLeadsPage";
import GoalSettingPage from "../../pages/goal-setting/GoalSettingPage";
import QuoteDetailPage from "../../pages/quote-detail/QuoteDetailPage";
import QuotesPage from "../../pages/quotes/QuotesPage";
import ScheduleSettingsPage from "../../pages/schedule/ScheduleSettingsPage";
import StatusMasterPage from "../../pages/status-master/StatusMasterPage";
import TeamsPage from "../../pages/teams/TeamsPage";
import UnitsPage from "../../pages/units/UnitsPage";
import { api } from "../api";
import { QueryAuthSync } from "./QueryAuthSync";
import { queryClient } from "./apiQuery";

const auth = vi.hoisted(() => ({ user: { uid: "uid-A" } as { uid: string } | null }));

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: auth.user, loading: false }),
}));
vi.mock("../auth/provider", () => ({ isSelfAuth: () => false }));
vi.mock("../auth/selfAuth", () => ({
  getAccessToken: async () => "test-token",
  expireSession: vi.fn(),
  selfRefresh: vi.fn(),
}));
vi.mock("../../hooks/usePermissions", () => ({ usePermissions: () => ({ hasPermission: () => true, loading: false }) }));
vi.mock("../../hooks/useSSE", () => ({ useSSE: vi.fn() }));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
  // api.ts が i18n.ts を読み、i18n.ts が initReactI18next を使う（同じ書き方: src/lib/query/batch3aPages.test.tsx）
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

// 中身は画面の型（UnitsPage.tsx:25-33・StatusMasterPage.tsx:26-39・ContactsPage.tsx:38-・QuotesPage.tsx:23-・
// QuoteDetailPage.tsx:26-53・TeamsPage.tsx:29-38・schedule-owner.ts:3-19）の欄から画面が使う物だけ。
// チームは TeamFormButtonMigration.test.tsx:14 の写し
const unit = { id: 1, code: "FX", canonical: "Fixture Unit", kubun: null, is_active: true, created_at: "", updated_at: "" };
const status = { id: 1, status_id: "FX", canonical: "Fixture Status", search_pattern: "", exclude_pattern: "", priority: 1, enabled: true, note: "", match_type: "contains", effect: "OUTPUT", created_at: "", updated_at: "" };
const contact = { id: 52, tenant_id: 1, company_id: 41, contact_code: "C52", lead_id: null, surname: "Fixture contact", given_name: null, display_name: null, job_title: null, department: null, is_primary_contact: false, primary_email: null, primary_phone: null, status: "active", notes: null, emails: [], discord: null, contact_channels: [], created_at: "", updated_at: "" };
const quote = { id: 7, quote_code: "Q-7", company_id: 4, contact_id: null, currency: "USD", subtotal: 10, total_amount: 10, status: "approved", validity_date: null, created_at: "" };
const quoteDetail = { ...quote, shipping_fee: 0, tax_amount: 0, notes: null, items: [] };
const team = { id: 7, name: "Fixture Team", leader_id: null, description: null, is_active: true, member_count: 0, created_at: "", updated_at: "" };
const owners = { can_manage_others: true, current_staff_id: 1, current_user_id: 1, owners: [{ staff_id: 1, user_id: 1, staff_code: "S1", name: "Fixture Owner", primary_email: null, color: "", is_visible: true, share_mode: "self", is_self: true }] };

const fixtures: Record<string, unknown> = {
  "/units?page=1&per_page=100": [unit],
  "/status-master?page=1&per_page=100": [status],
  "/contacts?per_page=100": [contact],
  "/companies?per_page=100": [],
  "/quotes": [quote],
  "/quotes/7": quoteDetail,
  "/teams": [team],
  "/me/permissions": { user_id: 1, is_tenant_admin: true, permissions: [] },
  "/calendar/owners": owners,
  "/analytics/summary?period=1m&tab=team": { leads: { excluded: 37 } },
};
// チャネル別の表は月で path が変わるので頭で見分ける。画面の中の部品が別に取る物（目標の値など）は空の一覧で返す
const answer = (path: string) =>
  (path in fixtures ? fixtures[path] : path.startsWith("/analytics/channels?") ? { rows: [] } : []) as never;

type Case = { name: string; Page: ComponentType; route: string; at: string; path: string; text: string | RegExp; spinner: boolean };
const cases: Case[] = [
  { name: "funnel leads", Page: FunnelLeadsPage, route: "/dashboard/leads", at: "/dashboard/leads", path: "/analytics/summary?period=1m&tab=team", text: "37", spinner: true },
  { name: "units", Page: UnitsPage, route: "/management-center/units", at: "/management-center/units", path: "/units?page=1&per_page=100", text: "Fixture Unit", spinner: true },
  { name: "status master", Page: StatusMasterPage, route: "/management-center/status-master", at: "/management-center/status-master", path: "/status-master?page=1&per_page=100", text: "Fixture Status", spinner: true },
  { name: "contacts", Page: ContactsPage, route: "/crm/contacts", at: "/crm/contacts", path: "/contacts?per_page=100", text: "Fixture contact", spinner: true },
  { name: "schedule settings", Page: ScheduleSettingsPage, route: "/schedule/settings", at: "/schedule/settings", path: "/calendar/owners", text: "Fixture Owner", spinner: false },
  { name: "quotes", Page: QuotesPage, route: "/quotes", at: "/quotes", path: "/quotes", text: "Q-7", spinner: true },
  { name: "goal settings", Page: GoalSettingPage, route: "/goals/settings", at: "/goals/settings", path: "/teams", text: "Fixture Team", spinner: false },
  { name: "teams", Page: TeamsPage, route: "/teams", at: "/teams", path: "/teams", text: "Fixture Team", spinner: true },
  { name: "quote detail", Page: QuoteDetailPage, route: "/quotes/:id", at: "/quotes/7", path: "/quotes/7", text: /Q-7/, spinner: true },
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

const shown = (c: Case) => screen.queryAllByText(c.text);
const found = (c: Case) => screen.findAllByText(c.text);

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
    await waitFor(() => expect(spy).toHaveBeenCalledWith(c.path));
  });

  it("funnel leads fetches the channel table through the one path builder", async () => {
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) => answer(path));
    render(<Tree c={cases[0]} />);
    await found(cases[0]);
    expect(spy).toHaveBeenCalledWith(expect.stringMatching(/^\/analytics\/channels\?month=\d{4}-\d{2}$/));
  });
});
