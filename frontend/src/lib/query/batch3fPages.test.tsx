/**
 * ADR-1054 段 3 の 6 回目: 本物の画面の試験。
 * Q1 戻った時に写しを先に出す（読み込み中の印を出さない）・裏で取り直す。
 * Q2 読めなかった時はフォームを出さない（空の値で上書きしない）。
 * Q3 Discord の設定はチャネルの画面と Discord の設定の画面で 1 つの写し。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import type { ComponentType } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import DiscordConfigPage from "../../pages/admin/DiscordConfigPage";
import TenantPolicyPage from "../../pages/admin/TenantPolicyPage";
import TenantProfilePage from "../../pages/admin/TenantProfilePage";
import ChannelsPage from "../../pages/channels/ChannelsPage";
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
  // api.ts が i18n.ts を読み、i18n.ts が initReactI18next を使う（同じ書き方: src/lib/query/batch3ePages.test.tsx）
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

// 中身は画面の型（TenantProfilePage.tsx:27-39・TenantPolicyPage.tsx:25-34・DiscordConfigPage.tsx:27-42・
// ChannelsPage.tsx の DiscordGuildConfig）と backend の返事（discord_guild_config.py:37-42）の欄
const GUILD = "1288437029213835356";
const profile = {
  id: 1, company_name: "Fixture Company", company_name_en: null, address: null, phone: null, email: null,
  website: null, seal_image_url: null, default_language: "ja", created_at: "", updated_at: "",
};
const policy = {
  inventory_agg_filter: "none", agg_price_threshold_jpy: 12345, agg_qty_threshold: 0, quote_validity_days: 7,
  default_currency: "JPY", document_language: "en", duty_incoterms: "DAP", issue_mode: "pdf",
};
const discordConfig = {
  guild_id: GUILD, connected_at: "2026-11-01T00:00:00Z", connected_by_staff_name: "Fixture Staff",
  role_member: "Member", role_partner: "Partner",
};
const ticket = {
  ticket_category_id: "1288437029213835357", ticket_button_channel_id: "1288437029213835358", staff_role_id: null,
  welcome_template: "Hello", small_channel_id: null, large_channel_id: null,
  small_role_name: "Member", large_role_name: "Partner",
};
const fixtures: Record<string, unknown> = {
  "/admin/tenant-profile": profile,
  "/admin/tenant-policy": policy,
  "/admin/discord-config": discordConfig,
  "/admin/discord-ticket-config": ticket,
  "/meta/channels": { channels: [] },
};
const answer = (path: string) => {
  if (!(path in fixtures)) throw new Error(`Unexpected GET ${path}`);
  return fixtures[path] as never;
};

type Case = {
  name: string; Page: ComponentType; route: string;
  path: string; text: string; value: boolean;
};
const cases: Case[] = [
  { name: "tenant profile", Page: TenantProfilePage, route: "/admin/tenant-profile", path: "/admin/tenant-profile", text: "Fixture Company", value: true },
  { name: "tenant policy", Page: TenantPolicyPage, route: "/admin/tenant-policy", path: "/admin/tenant-policy", text: "12345", value: true },
  { name: "discord config", Page: DiscordConfigPage, route: "/admin/discord-config", path: "/admin/discord-config", text: GUILD, value: false },
  { name: "channels discord section", Page: ChannelsPage, route: "/channels", path: "/admin/discord-config", text: GUILD, value: false },
];

function Tree({ c }: { c: Pick<Case, "Page" | "route"> }) {
  const Page = c.Page;
  return (
    <QueryClientProvider client={queryClient}>
      <QueryAuthSync />
      <MemoryRouter initialEntries={[c.route]}>
        <Routes><Route path={c.route} element={<Page />} /></Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// フォームの画面は欄の中の値で、ほかは文字で見分ける
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
    if (c.Page !== ChannelsPage) {
      expect(container.querySelector(".sa-loading-block")).toBeNull();
    }
    await waitFor(() => expect(spy).toHaveBeenCalledWith(c.path));
  });
});

describe("forms wait until the record is read (Q2)", () => {
  it("does not show the tenant profile form when the profile could not be read", async () => {
    vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === "/admin/tenant-profile") throw new Error("Fixture read failure");
      return answer(path);
    });
    const { container } = render(<Tree c={{ Page: TenantProfilePage, route: "/admin/tenant-profile" }} />);
    await screen.findByText("Fixture read failure");
    expect(container.querySelector("form")).toBeNull();
  });

  it("does not show the tenant policy form when the policy could not be read", async () => {
    vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === "/admin/tenant-policy") throw new Error("Fixture read failure");
      return answer(path);
    });
    const { container } = render(<Tree c={{ Page: TenantPolicyPage, route: "/admin/tenant-policy" }} />);
    await screen.findByText("Fixture read failure");
    expect(container.querySelector("form")).toBeNull();
  });

  it("does not show the discord forms when the ticket settings could not be read", async () => {
    vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === "/admin/discord-ticket-config") throw new Error("Fixture read failure");
      return answer(path);
    });
    render(<Tree c={{ Page: DiscordConfigPage, route: "/admin/discord-config" }} />);
    await screen.findByText("discordConfig.loadError");
    expect(screen.queryByText("discordConfig.connectionTitle")).toBeNull();
  });
});

describe("one copy of the discord settings (Q3)", () => {
  it("shows the server read on the discord settings page at once on the channels page", async () => {
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) => answer(path));
    const first = render(<Tree c={{ Page: DiscordConfigPage, route: "/admin/discord-config" }} />);
    await screen.findAllByText(GUILD);
    first.unmount();
    spy.mockClear();
    spy.mockImplementation(() => new Promise<never>(() => {}));
    render(<Tree c={{ Page: ChannelsPage, route: "/channels" }} />);
    expect(screen.queryAllByText(GUILD).length).toBeGreaterThan(0);
    await waitFor(() => expect(spy).toHaveBeenCalledWith("/admin/discord-config"));
  });
});
