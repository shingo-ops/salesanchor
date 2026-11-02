/**
 * ADR-1054 段 3 の 1 回目: 本物の画面の試験（Q1・Q2）。
 * Q1 戻った時に写しを先に出す（読み込み中の印を出さない）・Q2 利用者が変わっても前の人のフォームを出さない（K5）。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import type { ComponentType } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BotEditPage from "../../pages/bots/BotEditPage";
import BotsPage from "../../pages/bots/BotsPage";
import CompanyDetailPage from "../../pages/company-detail/CompanyDetailPage";
import ContactEditPage from "../../pages/contacts/ContactEditPage";
import InvoiceDetailPage from "../../pages/invoice-detail/InvoiceDetailPage";
import LeadEditPage from "../../pages/leads/LeadEditPage";
import LeadsPage from "../../pages/leads/LeadsPage";
import NoteMasterPage from "../../pages/note-master/NoteMasterPage";
import ProductsPage from "../../pages/products/ProductsPage";
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
vi.mock("../../hooks/useSSE", () => ({ useSSE: vi.fn() }));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
  // api.ts が i18n.ts を読み、i18n.ts が initReactI18next を使う（同じ書き方: src/lib/query/stage2Pages.test.tsx）
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

// 中身は今ある画面の試験の写し（BotFormButtonMigration.test.tsx:14-15・LeadFormButtonMigration.test.tsx:15-16・
// AccountCompanySaveButtonMigration.test.tsx:18・AllLegacyButtonOperationMigration.test.tsx:80・FullPageFormButtonMigration.test.tsx:14-18）。
// 商品と注記は型（pages/products/products.types.ts:6-51・NoteMasterPage.tsx:27-40）の欄から画面が使う物だけ
const bot = { id: 7, tenant_id: 1, bot_code: "FIXTURE", display_name: "Fixture Bot", purpose: "invoice", status: "active", discord_user_id: null, sender_email: null, owner_staff_id: 9, owner_staff_name: "Fixture Staff", last_executed_at: null, execution_count: 0, created_at: "", updated_at: "" };
const staff = [{ id: 9, user_id: 9, surname_jp: "Fixture", given_name_jp: "Staff" }, { id: 10, user_id: 10, surname_jp: "Other", given_name_jp: "Staff" }];
const lead = { customer_name: "Fixture Lead", email: null, phone: null, status: "lead", type: null, notes: null, country: null, company_name: null, channel_type: null, initiative: null, temperature: null, estimated_scale: null, customer_type: null, response_speed: null, monthly_forecast: null, id: 7, lead_code: "FIXTURE", created_at: "", updated_at: "", close_reason_memo: "Existing memo", close_reasons: [{ reason_id: 42, is_primary: true }] };
const company = { id: 41, tenant_id: 1, company_code: "CO-41", lead_id: 2, sales_rep_id: null, name: "Old Co", name_en: null, normalized_name: null, industry: null, website: null, priority_focus: null, per_order_amount: null, monthly_frequency: null, monthly_forecast: null, monthly_forecast_source: null, monthly_forecast_updated_at: null, billing_display_name: null, payment_recipient_name: null, fedex_account: null, shipping_note: null, status: "active", notes: null, addresses: [], sales_channels: ["old"], discord: null, created_at: "", updated_at: "", conversation_count: 0, last_conversation_at: null };
const contact = { id: 52, company_id: 41, contact_code: "C52", surname: "Fixture contact", given_name: null, display_name: null, job_title: null, department: null, is_primary_contact: false, primary_email: null, primary_phone: null, status: "active", notes: null };
const product = { id: 5, product_code: "P-5", name_ja: "Fixture Product", name_en: null, product_kind: null, category: null, mark: null, status: "active", unit_price: null, quantity: 0, weight: null, notes: null, release_date: null, created_at: "", updated_at: "", is_archived: false, archived_at: null, work_code: null, set_type: null, boxes_per_case: null, packs_per_box: null, item: null, display_order: null };
const note = { id: 1, label_ja: "Fixture Note", label_en: "Fixture Note EN", enabled: true, search_keywords: "", exclude_keywords: "", category: "", priority: 1, match_type: "contains", search_pattern: null, label_template: null, label_template_en: null };
const invoice = { id: 3, invoice_number: "INV-3", quote_id: null, company_id: 1, currency: "USD", subtotal: 1, shipping_fee: 0, tax_amount: 0, total_amount: 1, exchange_rate_jpy: null, exchange_rate_usd: null, amount_jpy: null, amount_usd: null, payment_method: null, status: "draft", branch_number: null, erp_key: null, issued_at: null, due_date: null, paid_at: null, voided_at: null, void_reason: null, notes: null, created_at: "", items: [], ship_to_snapshot: null, bill_to_snapshot: null, duty_amount: null, fx_rate_snapshot: null, paypal_order_id: null, paypal_approval_url: null, payment_fee: null, paypal_invoicer_view_url: null, paypal_copy_pdf_at: "2026-01-01" };

const fixtures: Record<string, unknown> = {
  "/bots": [bot],
  "/bots/7": bot,
  "/staff": staff,
  "/leads": [lead],
  "/close-reasons?type=lost": [],
  "/companies/41": company,
  "/companies/41/contacts": [],
  "/invoices/3": invoice,
  "/invoices/3/paypal-disputes": [],
  "/leads/7": lead,
  "/contacts/52": contact,
  "/products?sort=release_date_desc&page=1&per_page=100": [product],
  "/note-master?page=1&per_page=100": [note],
};
// 画面の中の部品が別に取る物（一覧の選択肢など）は空の一覧で返す
const answer = (path: string) => (path in fixtures ? fixtures[path] : []) as never;

type Case = { name: string; Page: ComponentType; route: string; at: string; path: string; text: string | RegExp; value: boolean; spinner: boolean };
const cases: Case[] = [
  { name: "bots", Page: BotsPage, route: "/bots", at: "/bots", path: "/bots", text: "Fixture Bot", value: false, spinner: true },
  { name: "bot edit", Page: BotEditPage, route: "/bots/:id/edit", at: "/bots/7/edit", path: "/bots/7", text: "Fixture Bot", value: true, spinner: false },
  { name: "leads", Page: LeadsPage, route: "/crm/leads", at: "/crm/leads", path: "/leads", text: "Fixture Lead", value: false, spinner: true },
  { name: "company detail", Page: CompanyDetailPage, route: "/crm/companies/:id", at: "/crm/companies/41", path: "/companies/41", text: "Old Co", value: false, spinner: true },
  { name: "invoice detail", Page: InvoiceDetailPage, route: "/invoices/:id", at: "/invoices/3", path: "/invoices/3", text: /INV-3/, value: false, spinner: true },
  { name: "lead edit", Page: LeadEditPage, route: "/crm/leads/:id/edit", at: "/crm/leads/7/edit", path: "/leads/7", text: "Fixture Lead", value: true, spinner: false },
  { name: "contact edit", Page: ContactEditPage, route: "/contacts/:id/edit", at: "/contacts/52/edit", path: "/contacts/52", text: "Fixture contact", value: true, spinner: false },
  { name: "products", Page: ProductsPage, route: "/admin/products", at: "/admin/products", path: "/products?sort=release_date_desc&page=1&per_page=100", text: "Fixture Product", value: false, spinner: true },
  { name: "note master", Page: NoteMasterPage, route: "/management-center/note-master", at: "/management-center/note-master", path: "/note-master?page=1&per_page=100", text: "Fixture Note", value: false, spinner: true },
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

const shown = (c: Case) => (c.value ? screen.queryAllByDisplayValue(c.text) : screen.queryAllByText(c.text));
const found = (c: Case) => (c.value ? screen.findAllByDisplayValue(c.text) : screen.findAllByText(c.text));

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
});

describe("K5 on the real bot edit screen (Q2)", () => {
  it("after the user changes, the previous user's form is never shown", async () => {
    const c = cases[1];
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) =>
      (path === "/bots/7" ? { ...bot, display_name: "secret-uid-A" } : answer(path)) as never);
    const view = render(<Tree c={c} />);
    await screen.findByDisplayValue("secret-uid-A");

    spy.mockImplementation(() => new Promise<never>(() => {}));
    auth.user = { uid: "uid-B" };
    view.rerender(<Tree c={c} />);
    expect(screen.queryByDisplayValue("secret-uid-A")).toBeNull();
    expect(view.container.querySelector(".sa-loading-block")).not.toBeNull();
    await waitFor(() => expect(spy).toHaveBeenCalledWith("/bots/7"));
    expect(screen.queryByDisplayValue("secret-uid-A")).toBeNull();
  });
});
