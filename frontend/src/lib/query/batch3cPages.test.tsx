/**
 * ADR-1054 段 3 の 3 回目: 本物の画面の試験（Q1）。
 * Q1 戻った時に写しを先に出す（読み込み中の印を出さない）・一覧と詳しい画面は見出しの横に回る印・裏で取り直す。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import type { ComponentType } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import FollowUpsPage from "../../pages/dashboard/FollowUpsPage";
import FunnelReasonsPage from "../../pages/dashboard/FunnelReasonsPage";
import FunnelRevenuePage from "../../pages/dashboard/FunnelRevenuePage";
import OwnInventoryPage from "../../pages/inventory/OwnInventoryPage";
import InvoiceCreatePage from "../../pages/invoice-create/InvoiceCreatePage";
import InvoicesPage from "../../pages/invoices/InvoicesPage";
import SupplierEditPage from "../../pages/suppliers/SupplierEditPage";
import TeamEditPage from "../../pages/teams/TeamEditPage";
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
  // api.ts が i18n.ts を読み、i18n.ts が initReactI18next を使う（同じ書き方: src/lib/query/batch3bPages.test.tsx）
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

// 中身は画面の型（TeamEditPage・SupplierEditPage の型・backend/app/schemas/own_inventory.py:42-56・
// InvoicesPage.tsx:21-34・InvoiceCreatePage.tsx:30-38・api/funnel.ts:42-93）の欄
const team = { id: 7, name: "Fixture Team", leader_id: null, description: null };
const supplier = { id: 63, name: "Fixture supplier", contact_name: null, email: null, phone: null, address: null, notes: null };
const ownRow = { id: 1, tenant_id: 1, product_id: 77, physical_qty: 2, reserved_qty: 0, available_qty: 2, unit_price: null, condition: "Fixture Cond", status: "in_stock", note_ja: null, note_en: null, antique_ledger_id: null, created_at: "", updated_at: "" };
const invoice = { id: 7, invoice_number: "INV-7", company_id: 4, currency: "USD", total_amount: 10, amount_jpy: null, status: "draft", issued_at: null, due_date: null, paid_at: null, created_at: "" };
const quote = { id: 7, quote_code: "Q-7", company_id: 4, currency: "USD", total_amount: 10, status: "approved", created_at: "" };
const followUps = { items: [{ customer_id: 5, name: "Fixture Customer", segment: "order_stopped", days: 3, last_order_at: null, last_contact_at: null, assignee: "Fixture Assignee" }] };
const revenue = { revenue: { target: 2000000, actual: 1234567, pace: "on_track" }, split: { new: 1, repeat: 1 }, new_customers: { target: 1, actual: 1 }, active_existing_customers: 1, gross_margin: { amount: 1, uncosted_orders: 0 } };
const reasons = { reasons: [{ label: "Fixture Reason", primary_count: 1, secondary_count: 0 }], memos: [] };

const fixtures: Record<string, unknown> = {
  "/teams/7": team,
  "/suppliers/63": supplier,
  "/own-inventory?page=1&per_page=20": [ownRow],
  "/invoices": [invoice],
  "/quotes?status=approved": [quote],
  "/analytics/follow-ups?": followUps,
};
// 売上と理由は月で path が変わるので頭で見分ける。画面の中の部品が別に取る物（会社の選び欄など）は空の一覧で返す
const answer = (path: string) =>
  (path in fixtures
    ? fixtures[path]
    : path.startsWith("/analytics/revenue-summary?")
      ? revenue
      : path.startsWith("/analytics/reasons?")
        ? reasons
        : []) as never;

type Case = {
  name: string; Page: ComponentType; route: string; at: string;
  path: string | RegExp; text: string; value: boolean; spinner: boolean;
};
const cases: Case[] = [
  { name: "supplier edit", Page: SupplierEditPage, route: "/suppliers/:id/edit", at: "/suppliers/63/edit", path: "/suppliers/63", text: "Fixture supplier", value: true, spinner: false },
  { name: "own inventory", Page: OwnInventoryPage, route: "/own-inventory", at: "/own-inventory", path: "/own-inventory?page=1&per_page=20", text: "Fixture Cond", value: false, spinner: true },
  { name: "follow ups", Page: FollowUpsPage, route: "/dashboard/follow-ups", at: "/dashboard/follow-ups", path: "/analytics/follow-ups?", text: "Fixture Customer", value: false, spinner: true },
  { name: "invoice create", Page: InvoiceCreatePage, route: "/invoices/new", at: "/invoices/new", path: "/quotes?status=approved", text: "Q-7", value: false, spinner: false },
  { name: "invoices", Page: InvoicesPage, route: "/invoices", at: "/invoices", path: "/invoices", text: "INV-7", value: false, spinner: true },
  { name: "team edit", Page: TeamEditPage, route: "/teams/:id/edit", at: "/teams/7/edit", path: "/teams/7", text: "Fixture Team", value: true, spinner: false },
  { name: "revenue", Page: FunnelRevenuePage, route: "/dashboard/revenue", at: "/dashboard/revenue", path: /^\/analytics\/revenue-summary\?month=\d{4}-\d{2}$/, text: "¥1,234,567", value: false, spinner: true },
  { name: "reasons", Page: FunnelReasonsPage, route: "/dashboard/reasons", at: "/dashboard/reasons", path: /^\/analytics\/reasons\?type=won&month=\d{4}-\d{2}$/, text: "Fixture Reason", value: false, spinner: true },
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

// 編集の画面は欄の中の値で、ほかは文字で見分ける
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
