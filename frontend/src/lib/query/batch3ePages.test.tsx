/**
 * ADR-1054 段 3 の 5 回目: 本物の画面の試験。
 * Q1 戻った時に写しを先に出す（読み込み中の印を出さない）・一覧の画面は見出しの横に回る印・裏で取り直す。
 * Q2 ロールの権限を読めていない間はチェックを押せない。スタッフを読めなかった時はフォームを出さない（空の値で上書きしない）。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import type { ComponentType } from "react";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ChannelsPage from "../../pages/channels/ChannelsPage";
import OrdersPage from "../../pages/orders/OrdersPage";
import RolesPage from "../../pages/roles/RolesPage";
import StaffEditPage from "../../pages/staff/StaffEditPage";
import StaffPage from "../../pages/staff/StaffPage";
import { rowMenuLabelKey } from "../../constants/menuPermissions";
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
  // api.ts が i18n.ts を読み、i18n.ts が initReactI18next を使う（同じ書き方: src/lib/query/batch3dPages.test.tsx）
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

// 中身は画面の型（ChannelsPage.tsx:33-49・RolesPage.tsx:33-52・StaffPage.tsx:43-63・StaffEditPage.tsx:32-50・
// orders.types.ts:5-24・:32-35）の欄
const channel = {
  page_id: "p1", page_name: "Fixture Page", instagram_business_account_id: null, instagram_username: null,
  is_active: true, connected_at: null, page_token_expires_at: null, connected_by_staff_id: null,
  connected_by_staff_name: null, granted_scopes: null, requires_reauth: false,
};
const role = { id: 1, name: "Fixture Role", color: null, priority: 500, is_system: false, description: null, created_at: "", updated_at: "" };
const permission = { id: 10, key: "customers.view", resource: "customers", action: "view", description: "Fixture Permission", category: "customers" };
const staff = {
  id: 7, tenant_id: 1, user_id: null, staff_code: "ST-FIX", surname_jp: "Fixture", given_name_jp: "Person",
  surname_kana: null, given_name_kana: null, surname_en: "Fixture", given_name_en: "Person",
  primary_email: "fixture@example.invalid", discord_user_id: null, role_id: 1, role_name: "Fixture Role",
  status: "active", emails: [], ui_preferences: null, created_at: "", updated_at: "",
};
const order = {
  id: 1, company_id: 1, contact_id: null, invoice_id: null, order_number: "ORD-FIX", total_amount: null,
  currency: "JPY", status: "awaiting_payment", paid_at: null, notes: null,
  created_at: "2026-11-01T00:00:00Z", updated_at: "2026-11-01T00:00:00Z",
  company_name: "Fixture Company", contact_display_name: null, shipping_city: null, shipping_country_code: null,
};

const fixtures: Record<string, unknown> = {
  "/meta/channels": { channels: [channel] },
  "/admin/discord-config": { guild_id: null, connected_at: null, connected_by_staff_name: null },
  "/roles": [role],
  "/permissions": [permission],
  "/roles/1/permissions": [permission],
  "/staff": [staff],
  "/staff/7": staff,
  "/orders?sort_by=updated_at&sort_order=desc": [order],
  "/orders/group-counts": { counts: {}, total: 1 },
  "/companies?per_page=100": [],
};
// ほかの path（受注の発送と仕入など）は取れない扱い（画面は null にする）
const answer = (path: string) => {
  if (!(path in fixtures)) throw new Error(`Unexpected GET ${path}`);
  return fixtures[path] as never;
};

type Case = {
  name: string; Page: ComponentType; route: string; at: string;
  path: string; text: string; value: boolean; spinner: boolean;
};
const cases: Case[] = [
  { name: "channels", Page: ChannelsPage, route: "/channels", at: "/channels", path: "/meta/channels", text: "Fixture Page", value: false, spinner: true },
  { name: "roles", Page: RolesPage, route: "/roles", at: "/roles", path: "/roles", text: "Fixture Role", value: false, spinner: false },
  { name: "staff", Page: StaffPage, route: "/staff", at: "/staff", path: "/staff", text: "Fixture Person", value: false, spinner: true },
  { name: "staff edit", Page: StaffEditPage, route: "/staff/:id/edit", at: "/staff/7/edit", path: "/staff/7", text: "Fixture", value: true, spinner: false },
  { name: "orders", Page: OrdersPage, route: "/orders", at: "/orders", path: "/orders?sort_by=updated_at&sort_order=desc", text: "ORD-FIX", value: false, spinner: true },
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

describe("edits wait until the record is read (Q2)", () => {
  const rowGroup = () => screen.findByRole("radiogroup", { name: rowMenuLabelKey("leads") });
  const permissionBox = () =>
    within(screen.getByRole("radiogroup", { name: rowMenuLabelKey("leads") })).getByRole("radio", { name: "roles.stateOff" }) as HTMLButtonElement;

  it("keeps the role permission boxes disabled until that role's permissions are read", async () => {
    let release: (value: unknown) => void = () => {};
    const held = new Promise((resolve) => { release = resolve; });
    vi.spyOn(api, "get").mockImplementation(async (path: string) =>
      (path === "/roles/1/permissions" ? held : answer(path)) as never,
    );
    render(<Tree c={{ Page: RolesPage, route: "/roles", at: "/roles" }} />);
    await rowGroup();
    expect(permissionBox().disabled).toBe(true);

    release([permission]);
    await waitFor(() => expect(permissionBox().disabled).toBe(false));
    const viewOnly = within(screen.getByRole("radiogroup", { name: rowMenuLabelKey("leads") })).getByRole("radio", { name: "roles.stateView" });
    expect(viewOnly.getAttribute("aria-checked")).toBe("true");
  });

  it("does not show the staff form when the staff could not be read", async () => {
    vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === "/staff/7") throw new Error("Fixture read failure");
      return answer(path);
    });
    const { container } = render(<Tree c={{ Page: StaffEditPage, route: "/staff/:id/edit", at: "/staff/7/edit" }} />);
    await screen.findByText("Fixture read failure");
    expect(container.querySelector("form")).toBeNull();
  });
});
