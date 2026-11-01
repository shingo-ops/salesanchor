/**
 * ADR-1054 段 2: 本物の 3 画面の試験（P1〜P4）。
 * P1 戻った時に写しを先に出す・P2 利用者が変わっても前の人の中身を出さない（K5）・
 * P3 書いた後に取り直す・P4 検索を変えた時は前の行を出したまま取る。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ChannelMastersPage from "../../pages/admin/ChannelMastersPage";
import CompaniesPage from "../../pages/companies/CompaniesPage";
import SuppliersPage from "../../pages/suppliers/SuppliersPage";
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
  useTranslation: () => ({ t: (key: string) => key }),
  // api.ts が i18n.ts を読み、i18n.ts が initReactI18next を使う（同じ書き方: src/pages/leads/LeadFormFields.test.tsx:6）
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

const supplier = { id: 63, name: "Fixture supplier", supplier_code: "S63", contact_name: null, email: null, phone: null, address: null, notes: null, is_active: true, created_at: "2026-11-01T00:00:00Z" };
const company = { id: 41, company_code: "C41", name: "Fixture company", status: "active", addresses: [], industry: null, priority_focus: null, notes: null };
const channel = { id: 1, platform: "line", display_name: "Fixture channel", connection_type: "manual", is_active: true };
const added = { id: 2, platform: "fixture_new", display_name: "Fixture new", connection_type: "manual", is_active: true };

const pages = {
  suppliers: { Page: SuppliersPage, path: "/suppliers?page=1&per_page=100", rows: [supplier], text: "Fixture supplier" },
  companies: { Page: CompaniesPage, path: "/companies?per_page=100", rows: [company], text: "Fixture company" },
  channels: { Page: ChannelMastersPage, path: "/channel-masters", rows: [channel], text: "Fixture channel" },
};
type Kind = keyof typeof pages;

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

describe("revisit shows the copy first (P1)", () => {
  it.each(Object.keys(pages) as Kind[])("%s shows the previous rows at once on revisit", async (kind) => {
    const c = pages[kind], Page = c.Page;
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === c.path) return c.rows as never;
      throw new Error("Unexpected GET " + path);
    });
    const first = render(<Tree><Page /></Tree>);
    await screen.findByText(c.text);
    first.unmount();

    spy.mockClear();
    spy.mockImplementation(() => new Promise<never>(() => {}));
    const { container } = render(<Tree><Page /></Tree>);
    expect(screen.getByText(c.text)).toBeTruthy();
    expect(container.querySelector(".sa-loading-block")).toBeNull();
    await waitFor(() => expect(container.querySelector(".page-layout-title-row .sa-spinner")).not.toBeNull());
    expect(spy).toHaveBeenCalledWith(c.path);
  });
});

describe("K5 on the real supplier screen (P2)", () => {
  // P2a: 写しを消す部品（QueryAuthSync）を置かずに人を変える。前の人の行を出さないのは keepSameUser の守りだけになる。
  // 守りを外す（previousData をそのまま返す）と、B の取り直しを待つ間に A の行が出てこの試験が落ちる。
  it("without the cache clear, the uid guard alone hides A's rows (P2a)", async () => {
    let releaseB: (rows: unknown) => void = () => {};
    vi.spyOn(api, "get").mockImplementation(async () => {
      const uid = auth.user?.uid;
      if (uid === "uid-B") return new Promise((resolve) => { releaseB = resolve; }) as never;
      return [{ ...supplier, name: `secret-${uid}` }] as never;
    });
    const bare = () => (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter><SuppliersPage /></MemoryRouter>
      </QueryClientProvider>
    );
    const { rerender, container } = render(bare());
    await screen.findByText("secret-uid-A");

    auth.user = { uid: "uid-B" };
    rerender(bare());
    expect(screen.queryByText("secret-uid-A")).toBeNull();
    expect(container.querySelector(".sa-loading-block")).not.toBeNull();

    await act(async () => {
      releaseB([{ ...supplier, id: 64, name: "secret-uid-B" }]);
    });
    await screen.findByText("secret-uid-B");
    expect(screen.queryByText("secret-uid-A")).toBeNull();
  });

  it("A -> B never shows A's rows on SuppliersPage", async () => {
    let releaseB: (rows: unknown) => void = () => {};
    vi.spyOn(api, "get").mockImplementation(async () => {
      const uid = auth.user?.uid;
      if (uid === "uid-B") return new Promise((resolve) => { releaseB = resolve; }) as never;
      return [{ ...supplier, name: `secret-${uid}` }] as never;
    });
    const tree = () => <Tree><SuppliersPage /></Tree>;
    const { rerender, container } = render(tree());
    await screen.findByText("secret-uid-A");

    auth.user = { uid: "uid-B" };
    rerender(tree());
    expect(screen.queryByText("secret-uid-A")).toBeNull();
    expect(container.querySelector(".sa-loading-block")).not.toBeNull();

    await act(async () => {
      releaseB([{ ...supplier, id: 64, name: "secret-uid-B" }]);
    });
    await screen.findByText("secret-uid-B");
    expect(screen.queryByText("secret-uid-A")).toBeNull();
    expect(queryClient.getQueryCache().getAll().filter((query) => query.queryKey[1] === "uid-A").length).toBe(0);
  });
});

describe("channel screen refetches after a write (P3)", () => {
  it("add and delete show the server rows again", async () => {
    let rows: unknown[] = [channel];
    const get = vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === "/channel-masters") return rows as never;
      throw new Error("Unexpected GET " + path);
    });
    const post = vi.spyOn(api, "post").mockImplementation(async () => {
      rows = [channel, added];
      return {} as never;
    });
    const del = vi.spyOn(api, "delete").mockImplementation(async () => {
      rows = [channel];
      return {} as never;
    });
    render(<Tree><ChannelMastersPage /></Tree>);
    await screen.findByText("Fixture channel");

    fireEvent.change(screen.getByRole("textbox", { name: "channelMasters.platform" }), { target: { value: "fixture_new" } });
    fireEvent.change(screen.getByRole("textbox", { name: "channelMasters.displayName" }), { target: { value: "Fixture new" } });
    const readCount = get.mock.calls.length;
    fireEvent.click(screen.getByRole("button", { name: "channelMasters.add" }));
    await screen.findByText("Fixture new");
    expect(post).toHaveBeenCalledExactlyOnceWith("/admin/channel-masters", { platform: "fixture_new", display_name: "Fixture new" });
    expect(get.mock.calls.length).toBeGreaterThan(readCount);

    fireEvent.click(screen.getAllByRole("button", { name: "channelMasters.deleteAriaLabel" })[1]);
    await waitFor(() => expect(screen.queryByText("Fixture new")).toBeNull());
    expect(del).toHaveBeenCalledExactlyOnceWith("/admin/channel-masters/2");
    expect(screen.getByText("Fixture channel")).toBeTruthy();
  });
});

describe("company search keeps the previous rows while the next ones load (P4)", () => {
  it("old rows stay with the small spinner, then the new rows replace them", async () => {
    let release: (rows: unknown) => void = () => {};
    vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === "/companies?per_page=100") return [company] as never;
      if (path === "/companies?per_page=100&search=Z") return new Promise((resolve) => { release = resolve; }) as never;
      throw new Error("Unexpected GET " + path);
    });
    const { container } = render(<Tree><CompaniesPage /></Tree>);
    await screen.findByText("Fixture company");

    fireEvent.change(screen.getByPlaceholderText("companies.searchPlaceholder"), { target: { value: "Z" } });
    expect(screen.getByText("Fixture company")).toBeTruthy();
    expect(container.querySelector(".sa-loading-block")).toBeNull();
    await waitFor(() => expect(container.querySelector(".page-layout-title-row .sa-spinner")).not.toBeNull());

    await act(async () => {
      release([{ ...company, id: 42, company_code: "C42", name: "Zeta company" }]);
    });
    await screen.findByText("Zeta company");
    expect(screen.queryByText("Fixture company")).toBeNull();
  });
});
