/* eslint-disable local/no-japanese-literal -- 試験の題名（画面の文字ではない） */
import { describe, expect, it } from "vitest";
import ja from "../locales/ja.json";
import en from "../locales/en.json";
import {
  MENUS,
  ROLE_ROWS,
  canSeeMenu,
  rowMenuLabelKey,
  type MenuId,
} from "./menuPermissions";

type Has = (key: string) => boolean;

// 置き換え前の条件の式（DesktopShell / MobileShell / ManagementCenterPage の実物を写したもの）
const LEGACY: Record<MenuId, (has: Has) => boolean> = {
  dashboard: (h) => h("dashboard.view"),
  inventory: (h) => h("products.view"),
  quotesInvoices: (h) => h("quotes.view") || h("invoices.view"),
  leads: (h) => h("leads.view") || h("customers.view"),
  orders: (h) => h("orders.view"),
  sales: (h) => h("orders.view"),
  commissions: (h) => h("orders.view"),
  commissionSettings: (h) => h("orders.view"),
  staff: (h) => h("staff.view"),
  roles: (h) => h("roles.view") || h("roles.create"),
  teams: (h) => h("teams.view"),
  shifts: (h) => h("shifts.view"),
  tenantPolicy: (h) => h("tenant.profile.edit") || h("tenant.profile.view"),
  tenantProfile: (h) => h("tenant.profile.edit") || h("tenant.profile.view"),
  discordConfig: (h) => h("tenant.profile.edit") || h("tenant.profile.view"),
  discordAnnounce: (h) => h("tenant.profile.edit") || h("tenant.profile.view"),
  suppliers: (h) => h("suppliers.view"),
  statusMaster: (h) => h("suppliers.view"),
  units: (h) => h("suppliers.view"),
  noteMaster: (h) => h("suppliers.view"),
  conditionsMaster: (h) => h("conditions.view"),
  productCategories: (h) => h("product_categories.view"),
  dataManagement: (h) => h("erp.view"),
  integrationGoogleDrive: (h) => h("erp.view"),
  integrationFedex: (h) => h("erp.view"),
  integrationDhl: (h) => h("erp.view"),
  integrationUps: (h) => h("erp.view"),
  integrationPaypal: (h) => h("erp.view"),
  channels: (h) => h("channels.view"),
  channelMasters: (h) => h("tenant.profile.edit"),
  bots: (h) => h("bots.view"),
  notifications: (h) => h("notifications.manage"),
};

const MENU_IDS = Object.keys(MENUS) as MenuId[];

// 許可の組み合わせ: 全部無し・1つずつ・全部
const ALL_KEYS = Array.from(new Set(MENU_IDS.flatMap((id) => [...MENUS[id].anyOf])));
const COMBOS: Set<string>[] = [
  new Set(),
  ...ALL_KEYS.map((k) => new Set([k])),
  new Set(ALL_KEYS),
];

describe("canSeeMenu", () => {
  it("旧い条件の式と、全メニュー・全組み合わせで同じ結果になる", () => {
    const mismatches: string[] = [];
    for (const held of COMBOS) {
      const has: Has = (k) => held.has(k);
      const hasAny = (...keys: string[]) => keys.some(has);
      for (const id of MENU_IDS) {
        if (canSeeMenu(id, hasAny) !== LEGACY[id](has)) {
          mismatches.push(`${id} with [${[...held].join(",")}]`);
        }
      }
    }
    expect(mismatches).toEqual([]);
  });

  it("許可が全部無いと、どのメニューも出ない", () => {
    const hasAny = () => false;
    expect(MENU_IDS.filter((id) => canSeeMenu(id, hasAny))).toEqual([]);
  });

  it("許可を全部持つと、どのメニューも出る", () => {
    const held = new Set(ALL_KEYS);
    const hasAny = (...keys: string[]) => keys.some((k) => held.has(k));
    expect(MENU_IDS.filter((id) => !canSeeMenu(id, hasAny))).toEqual([]);
  });
});

describe("メニュー名の鍵", () => {
  const navJa = (ja as unknown as { nav: Record<string, string> }).nav;
  const navEn = (en as unknown as { nav: Record<string, string> }).nav;

  it("MENUS の名前の鍵は nav.* で、ja と en の両方にある", () => {
    for (const id of MENU_IDS) {
      const key = MENUS[id].labelKey;
      expect(key.startsWith("nav.")).toBe(true);
      const name = key.slice("nav.".length);
      expect(navJa[name], `ja ${key}`).toBeTruthy();
      expect(navEn[name], `en ${key}`).toBeTruthy();
    }
  });

  it("行に並ぶメニューの名前の鍵も、左の列・管理センターと同じ nav.* で ja と en にある", () => {
    for (const row of ROLE_ROWS) {
      for (const m of row.menus ?? []) {
        const key = rowMenuLabelKey(m);
        expect(key.startsWith("nav.")).toBe(true);
        const name = key.slice("nav.".length);
        expect(navJa[name], `ja ${key}`).toBeTruthy();
        expect(navEn[name], `en ${key}`).toBeTruthy();
      }
    }
  });

  it("許可で出し分けるメニューは、全部どれかの行に入っている", () => {
    const inRows = new Set(ROLE_ROWS.flatMap((r) => r.menus ?? []));
    expect(MENU_IDS.filter((id) => !inRows.has(id))).toEqual([]);
  });
});

describe("ROLE_ROWS", () => {
  it("行の id は重ならない", () => {
    const ids = ROLE_ROWS.map((r) => r.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("同じ許可が2つの行に入らない", () => {
    const all = ROLE_ROWS.flatMap((r) => [...r.keys]);
    expect(new Set(all).size).toBe(all.length);
  });

  it("メニュー行の許可は、そのメニューを出す許可を含む", () => {
    // 一緒に出るメニューを出す許可は、同じ行の許可のどれかである（行を触るとメニューが変わる）
    for (const row of ROLE_ROWS) {
      for (const m of row.menus ?? []) {
        if (!(m in MENUS)) continue;
        const anyOf = MENUS[m as MenuId].anyOf;
        expect(anyOf.every((k) => row.keys.includes(k)), `${row.id}/${m}`).toBe(true);
      }
    }
  });
});
