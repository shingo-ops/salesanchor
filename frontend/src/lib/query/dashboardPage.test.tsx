/**
 * ADR-1054 最初の画面の写し（dashboard-cache-card.md）の試験。
 * 1〜4 本目 戻った時に写しを先に出す（K1）・5 本目 利用者が変わっても前の人の中身を出さない（K5）・
 * 6 本目 次の行動を保存した後にその人の中身を取り直す。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DashboardPage from "../../pages/dashboard/DashboardPage";
import { FunnelSection } from "../../pages/dashboard/FunnelSection";
import { PriorityProspectsSection } from "../../pages/dashboard/PriorityProspectsSection";
import { MOCK_FOLLOW_UPS, MOCK_FUNNEL, MOCK_PRIORITY_PROSPECTS, MOCK_REVENUE_SUMMARY } from "../../mocks/funnelFixtures";
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
vi.mock("../../hooks/usePermissions", () => ({ usePermissions: () => ({ hasPermission: () => true }) }));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key, i18n: { language: "ja" } }),
  // api.ts が i18n.ts を読み、i18n.ts が initReactI18next を使う（同じ書き方: src/lib/query/stage2Pages.test.tsx:32-36）
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

const prospect = MOCK_PRIORITY_PROSPECTS.items[0];
const prospects = { scope: "mine", items: [prospect] };
const leadPath = `/leads/${prospect.lead_id}`;
const lead = (name: string, nextAction: string | null = null) => ({
  id: prospect.lead_id,
  customer_name: name,
  company_name: null,
  next_action: nextAction,
  next_action_date: null,
});
const kpi = { pct: null, direction: "flat" };
const pageRows: Record<string, unknown> = {
  "/goals/summary?tab=individual": { monthly: [], weekly: [] },
  "/analytics/forecast": { forecast_amount: 0, open_deal_count: 0, won_amount: 0, period_start: "2026-11-01", period_end: "2026-11-30" },
  "/analytics/followups": { overdue: [], due_today: [], upcoming: [] },
  "/analytics/summary?period=1m&tab=individual": {
    period: "1m",
    start_date: "2026-10-02",
    end_date: "2026-11-01",
    leads: { total: 7, converted: 2, excluded: 1, conversion_rate: 28.6 },
    orders: { total_revenue: 0, order_count: 7, active_count: 0 },
    comparison: { leads_total: kpi, leads_cv_rate: kpi, orders_revenue: kpi, orders_count: kpi },
  },
  "/analytics/monthly-revenue?period=1m": { granularity: "monthly", entries: [] },
  "/analytics/priority-prospects?scope=mine": prospects,
  "/analytics/weekly-advisor-defensive?scope=mine&period=3m": { period: "3m", scope: "mine", stale_days: 14, actions: [] },
  "/analytics/lead-conversion-factors": {
    status: "insufficient",
    included_count: 0,
    won_count: 0,
    lost_count: 0,
    required_per_item: 10,
    item_count: 6,
    excluded: { by_status: 0, other_values: 0, no_inbound: 0, no_outbound: 0, no_reply_pair: 0, no_sales_form: 0, missing_scale_or_type: 0 },
    items: [],
  },
  [leadPath]: lead("Fixture lead"),
};
const funnelRows: Record<string, unknown> = {
  "/analytics/funnel?month=2026-11": MOCK_FUNNEL,
  "/analytics/revenue-summary?month=2026-11": MOCK_REVENUE_SUMMARY,
  "/analytics/follow-ups?": MOCK_FOLLOW_UPS,
};

function answer(rows: Record<string, unknown>) {
  return async (path: string) => {
    if (path in rows) return rows[path] as never;
    throw new Error("Unexpected GET " + path);
  };
}

function Tree({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <QueryAuthSync />
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

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

describe("dashboard revisit shows the copy first (K1)", () => {
  it("1: the whole page shows the previous contents at once, with the small spinner", async () => {
    const spy = vi.spyOn(api, "get").mockImplementation(answer(pageRows));
    const first = render(<Tree><DashboardPage /></Tree>);
    await screen.findByText("Fixture lead");
    await waitFor(() => expect(first.container.querySelector(".sa-loading-block")).toBeNull());
    first.unmount();

    spy.mockClear();
    spy.mockImplementation(() => new Promise<never>(() => {}));
    const { container } = render(<Tree><DashboardPage /></Tree>);
    expect(screen.getByText("Fixture lead")).toBeTruthy();
    expect(screen.getByText("7")).toBeTruthy();
    expect(container.querySelector(".sa-loading-block")).toBeNull();
    await waitFor(() => expect(container.querySelector(".page-layout-title-row .sa-spinner")).not.toBeNull());
    expect(spy).toHaveBeenCalledWith("/analytics/summary?period=1m&tab=individual");
    expect(spy).toHaveBeenCalledWith(leadPath);
  });

  it("2: the first open sends the same paths as before", async () => {
    const spy = vi.spyOn(api, "get").mockImplementation(answer(pageRows));
    render(<Tree><DashboardPage /></Tree>);
    await screen.findByText("Fixture lead");
    const sent = new Set(spy.mock.calls.map((call) => call[0]));
    expect([...sent].sort()).toEqual(Object.keys(pageRows).sort());
  });

  it("3: the funnel section shows the previous contents at once", async () => {
    const spy = vi.spyOn(api, "get").mockImplementation(answer(funnelRows));
    const first = render(<Tree><FunnelSection month="2026-11" viewMode="management" /></Tree>);
    await waitFor(() => expect(first.container.querySelector(".fn-funnel-row")).not.toBeNull());
    first.unmount();

    spy.mockClear();
    spy.mockImplementation(() => new Promise<never>(() => {}));
    const { container } = render(<Tree><FunnelSection month="2026-11" viewMode="management" /></Tree>);
    expect(container.querySelector(".fn-funnel-row")).not.toBeNull();
    expect(container.querySelector(".sa-loading-block")).toBeNull();
    await waitFor(() => expect(spy).toHaveBeenCalledWith("/analytics/funnel?month=2026-11"));
  });

  it("4: the lead lookup that failed still shows the fallback label, not a loading mark", async () => {
    vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === "/analytics/priority-prospects?scope=mine") return prospects as never;
      throw new Error("lead lookup failed");
    });
    const { container } = render(<Tree><PriorityProspectsSection /></Tree>);
    await screen.findByText("dashboard.priorityFallbackLead");
    expect(container.querySelector(".sa-loading-block")).toBeNull();
  });
});

describe("K5 on the priority section", () => {
  it("5: A -> B never shows A's lead name", async () => {
    let releaseB: (rows: unknown) => void = () => {};
    vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      const uid = auth.user?.uid;
      if (uid === "uid-B" && path === "/analytics/priority-prospects?scope=mine") {
        return new Promise((resolve) => { releaseB = resolve; }) as never;
      }
      if (path === "/analytics/priority-prospects?scope=mine") return prospects as never;
      if (path === leadPath) return lead(`secret-${uid}`) as never;
      throw new Error("Unexpected GET " + path);
    });
    const tree = () => <Tree><PriorityProspectsSection /></Tree>;
    const { rerender, container } = render(tree());
    await screen.findByText("secret-uid-A");

    auth.user = { uid: "uid-B" };
    rerender(tree());
    expect(screen.queryByText("secret-uid-A")).toBeNull();
    expect(container.querySelector(".sa-loading-block")).not.toBeNull();

    await act(async () => {
      releaseB(prospects);
    });
    await screen.findByText("secret-uid-B");
    expect(screen.queryByText("secret-uid-A")).toBeNull();
    expect(queryClient.getQueryCache().getAll().filter((query) => query.queryKey[1] === "uid-A").length).toBe(0);
  });
});

describe("priority follow-up refetches the lead after saving", () => {
  it("6: save sends the patch, then the lead is read again", async () => {
    let current = lead("Fixture lead");
    const get = vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === "/analytics/priority-prospects?scope=mine") return prospects as never;
      if (path === leadPath) return current as never;
      throw new Error("Unexpected GET " + path);
    });
    const patch = vi.spyOn(api, "patch").mockImplementation(async () => {
      current = lead("Fixture lead renamed", prospect.suggested_action);
      return current as never;
    });
    render(<Tree><PriorityProspectsSection /></Tree>);
    await screen.findByText("Fixture lead");

    fireEvent.click(screen.getByRole("button", { name: "dashboard.weeklyAddFollowUp" }));
    const leadReads = get.mock.calls.filter((call) => call[0] === leadPath).length;
    fireEvent.click(screen.getByRole("button", { name: "common.add" }));
    await screen.findByText("Fixture lead renamed");
    expect(patch).toHaveBeenCalledTimes(1);
    expect(patch.mock.calls[0][0]).toBe(leadPath);
    expect(get.mock.calls.filter((call) => call[0] === leadPath).length).toBeGreaterThan(leadReads);
  });
});
