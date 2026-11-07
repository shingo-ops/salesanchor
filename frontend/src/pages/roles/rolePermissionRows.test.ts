/* eslint-disable local/no-japanese-literal -- 試験の題名と、本番の区分名（DB の値）の写し。画面の文字ではない */
import { describe, expect, it } from "vitest";
import { ROLE_ROWS } from "../../constants/menuPermissions";
import {
  applyState,
  buildRows,
  canSetEdit,
  canSetView,
  isViewKey,
  rowState,
  type PermLike,
} from "./rolePermissionRows";

// 本番の許可 135 件（鍵, 区分）。出どころ: docs/handoff/role-menu-permissions/perms-135.tsv
const PROD: ReadonlyArray<readonly [string, string]> = [
  ["analytics.customer_priority.override", "分析"],
  ["analytics.customer_priority.view", "分析"],
  ["archive.manage", "アーカイブ"],
  ["archive.view", "アーカイブ"],
  ["badges.manage", "バッジ"],
  ["badges.view", "バッジ"],
  ["bots.create", "Bot"],
  ["bots.delete", "Bot"],
  ["bots.update", "Bot"],
  ["bots.view", "Bot"],
  ["buddy.manage", "Buddy"],
  ["buddy.review", "Buddy"],
  ["buddy.view_own", "Buddy"],
  ["central.aliases.edit", "中央マスタ"],
  ["central.dex.edit", "中央マスタ"],
  ["central.knowledge.edit", "中央マスタ"],
  ["central.parse_review.approve", "中央マスタ"],
  ["central.parse_review.reject", "中央マスタ"],
  ["central.supplier_discord_routing.edit", "中央マスタ"],
  ["central.supplier.edit", "中央マスタ"],
  ["central.tcg.edit", "中央マスタ"],
  ["channels.manage", "メッセージ"],
  ["channels.view", "メッセージ"],
  ["conditions.create", "状態マスタ"],
  ["conditions.delete", "状態マスタ"],
  ["conditions.update", "状態マスタ"],
  ["conditions.view", "状態マスタ"],
  ["customers.create", "顧客"],
  ["customers.delete", "顧客"],
  ["customers.update", "顧客"],
  ["customers.view", "顧客"],
  ["dashboard.view", "レポート"],
  ["deals.create", "案件"],
  ["deals.delete", "案件"],
  ["deals.update", "案件"],
  ["deals.view", "案件"],
  ["erp.sync", "ERP"],
  ["erp.view", "ERP"],
  ["goals.edit", "目標管理"],
  ["goals.view", "目標管理"],
  ["inventory.visibility.full", "在庫"],
  ["inventory.visibility.staff", "在庫"],
  ["inventory.visibility.viewer", "在庫"],
  ["invoices.create", "請求"],
  ["invoices.update", "請求"],
  ["invoices.view", "請求"],
  ["invoices.void", "請求"],
  ["leads.convert", "リード"],
  ["leads.create", "リード"],
  ["leads.delete", "リード"],
  ["leads.discord_ban", "リード"],
  ["leads.discord_invite", "リード"],
  ["leads.discord_kick", "リード"],
  ["leads.discord_remove_channel", "リード"],
  ["leads.discord_resync", "リード"],
  ["leads.update", "リード"],
  ["leads.view", "リード"],
  ["menu.archive_chat", "メニュー"],
  ["menu.dashboard", "メニュー"],
  ["menu.data_management", "メニュー"],
  ["menu.deal_management", "メニュー"],
  ["menu.display_settings", "メニュー"],
  ["menu.faq", "メニュー"],
  ["menu.inventory", "メニュー"],
  ["menu.invoice_create", "メニュー"],
  ["menu.lead_chat", "メニュー"],
  ["menu.new_customer_chat", "メニュー"],
  ["menu.product_knowledge", "メニュー"],
  ["menu.quote_create", "メニュー"],
  ["menu.quote_history", "メニュー"],
  ["menu.report", "メニュー"],
  ["menu.role_management", "メニュー"],
  ["menu.route_customer_chat", "メニュー"],
  ["menu.staff_management", "メニュー"],
  ["menu.template_management", "メニュー"],
  ["menu.translation_prompt", "メニュー"],
  ["messaging.send", "メッセージ"],
  ["messaging.view", "メッセージ"],
  ["notifications.manage", "通知"],
  ["notifications.view", "通知"],
  ["orders.create", "注文"],
  ["orders.delete", "注文"],
  ["orders.update", "注文"],
  ["orders.view", "注文"],
  ["phase.switch", "在庫運用"],
  ["product_categories.delete", "商品カテゴリ"],
  ["product_categories.edit", "商品カテゴリ"],
  ["product_categories.view", "商品カテゴリ"],
  ["products.create", "在庫"],
  ["products.delete", "在庫"],
  ["products.update", "在庫"],
  ["products.view", "在庫"],
  ["purchase_orders.create", "仕入"],
  ["purchase_orders.receive", "仕入"],
  ["purchase_orders.update", "仕入"],
  ["purchase_orders.view", "仕入"],
  ["quotes.approve", "見積"],
  ["quotes.create", "見積"],
  ["quotes.delete", "見積"],
  ["quotes.update", "見積"],
  ["quotes.view", "見積"],
  ["reports.export", "レポート"],
  ["reports.view", "レポート"],
  ["roles.assign", "ロール"],
  ["roles.create", "ロール"],
  ["roles.delete", "ロール"],
  ["roles.update", "ロール"],
  ["roles.view", "ロール"],
  ["shifts.manage", "シフト"],
  ["shifts.view", "シフト"],
  ["shipping.calculate", "配送"],
  ["shipping.manage", "配送"],
  ["shipping.view", "配送"],
  ["staff.create", "スタッフ"],
  ["staff.delete", "スタッフ"],
  ["staff_reports.create", "レポート"],
  ["staff_reports.review", "レポート"],
  ["staff_reports.view_own", "レポート"],
  ["staff_reports.view_team", "レポート"],
  ["staff.update", "スタッフ"],
  ["staff.view", "スタッフ"],
  ["suppliers.create", "仕入"],
  ["suppliers.delete", "仕入"],
  ["suppliers.update", "仕入"],
  ["suppliers.view", "仕入"],
  ["system.audit_view", "システム"],
  ["system.manage", "システム"],
  ["teams.create", "チーム"],
  ["teams.delete", "チーム"],
  ["teams.manage_members", "チーム"],
  ["teams.update", "チーム"],
  ["teams.view", "チーム"],
  ["tenant.inventory_visibility.edit", "在庫"],
  ["tenant.profile.edit", "テナント設定"],
  ["tenant.profile.view", "テナント設定"],
];

const PERMS: PermLike[] = PROD.map(([key, category]) => ({ key, category }));
const MENU_KEYS = PERMS.map((p) => p.key).filter((k) => k.startsWith("menu."));
const NON_MENU_KEYS = PERMS.map((p) => p.key).filter((k) => !k.startsWith("menu."));
const rows = buildRows(PERMS, ROLE_ROWS);
const rowOf = (id: string) => {
  const r = rows.find((x) => x.id === id);
  if (!r) throw new Error(`row not found: ${id}`);
  return r;
};

describe("本番の許可 135 件", () => {
  it("写しは 135 件で、menu.* は 19 件", () => {
    expect(PERMS.length).toBe(135);
    expect(new Set(PERMS.map((p) => p.key)).size).toBe(135);
    expect(MENU_KEYS.length).toBe(19);
    expect(NON_MENU_KEYS.length).toBe(116);
  });

  it("menu.* を除く 116 件が、ちょうど 1 つの行に出る（漏れ 0・重なり 0）", () => {
    const counts = new Map<string, number>();
    for (const r of rows) for (const k of r.keys) counts.set(k, (counts.get(k) ?? 0) + 1);
    expect(NON_MENU_KEYS.filter((k) => counts.get(k) !== 1)).toEqual([]);
    expect([...counts.keys()].sort()).toEqual([...NON_MENU_KEYS].sort());
  });

  it("menu.* は、どの行にも出ない", () => {
    const shown = new Set(rows.flatMap((r) => r.keys));
    expect(MENU_KEYS.filter((k) => shown.has(k))).toEqual([]);
  });

  it("ROLE_ROWS に書いた許可は、全部本番に実在する（消える許可が無い）", () => {
    const existing = new Set(NON_MENU_KEYS);
    const missing = ROLE_ROWS.flatMap((r) => r.keys).filter((k) => !existing.has(k));
    expect(missing).toEqual([]);
  });

  it("どの行にも入らない許可は、区分ごとの「メニュー以外の許可」の行になる", () => {
    const others = rows.filter((r) => r.section === "other");
    expect(others.every((r) => r.category && r.menus === null)).toBe(true);
    const keys = others.flatMap((r) => r.keys);
    expect(keys.length).toBe(41);
    expect(keys).toContain("purchase_orders.view");
    expect(keys).toContain("central.tcg.edit");
    expect(keys).not.toContain("leads.view");
    // 区分名は DB の値のまま
    for (const r of others) {
      for (const k of r.keys) {
        expect(PROD.find(([key]) => key === k)?.[1]).toBe(r.category);
      }
    }
  });

  it("新しい許可が増えても「メニュー以外の許可」に自動で出る", () => {
    const withNew = buildRows([...PERMS, { key: "newthing.view", category: "新規" }], ROLE_ROWS);
    expect(withNew.some((r) => r.section === "other" && r.keys.includes("newthing.view"))).toBe(true);
  });

  it("区分の並びは categoryOrder の順（無い区分は後ろ）", () => {
    const ordered = buildRows(PERMS, ROLE_ROWS, { 分析: 2, アーカイブ: 1 });
    const cats = ordered.filter((r) => r.section === "other").map((r) => r.category);
    expect(cats.slice(0, 2)).toEqual(["アーカイブ", "分析"]);
  });

  it("区切りの順は 左の列 → チーム → データ → 事業 → その他", () => {
    const order = ["sidebar", "team", "data", "business", "other"];
    const idx = rows.map((r) => order.indexOf(r.section));
    expect([...idx].sort((a, b) => a - b)).toEqual(idx);
  });

  it("許可が実在しない行は出ない（固定の行は残る）", () => {
    const only = buildRows([{ key: "dashboard.view", category: "x" }], ROLE_ROWS);
    expect(only.map((r) => r.id)).toEqual(["dashboard", "schedule", "loginRequests"]);
  });
});

describe("isViewKey", () => {
  it("view・view_*・*_view を「見る」許可とする", () => {
    for (const k of [
      "orders.view", "buddy.view_own", "staff_reports.view_team", "system.audit_view",
      "analytics.customer_priority.view", "tenant.profile.view",
    ]) {
      expect(isViewKey(k), k).toBe(true);
    }
  });

  it("それ以外は「見る」許可ではない", () => {
    for (const k of [
      "orders.create", "inventory.visibility.full", "central.tcg.edit",
      "leads.discord_resync", "views.manage", "tenant.inventory_visibility.edit",
    ]) {
      expect(isViewKey(k), k).toBe(false);
    }
  });

  it("本番で名前が .view で終わらない「見る」許可は 4 件", () => {
    const odd = NON_MENU_KEYS.filter((k) => isViewKey(k) && !k.endsWith(".view"));
    expect(odd.sort()).toEqual([
      "buddy.view_own", "staff_reports.view_own", "staff_reports.view_team", "system.audit_view",
    ]);
  });
});

describe("rowState（3択の決め方）", () => {
  const orders = ["orders.view", "orders.create", "orders.update", "orders.delete"];

  it("0 件 → 非表示", () => {
    expect(rowState(orders, new Set())).toBe("off");
  });

  it("見る許可だけ全部（他は 0）→ 表示のみ", () => {
    expect(rowState(orders, new Set(["orders.view"]))).toBe("view");
  });

  it("全部 → 編集可", () => {
    expect(rowState(orders, new Set(orders))).toBe("edit");
  });

  it("それ以外 → 個別", () => {
    expect(rowState(orders, new Set(["orders.create"]))).toBe("mixed");
    expect(rowState(orders, new Set(["orders.view", "orders.create"]))).toBe("mixed");
  });

  it("営業ロールのリード・顧客の行は「個別」", () => {
    const crm = rowOf("crm").keys;
    const sales = new Set([
      "leads.convert", "leads.create", "leads.update", "leads.view", "leads.discord_invite",
      "leads.discord_resync", "customers.create", "customers.update", "customers.view",
    ]);
    expect(rowState(crm, sales)).toBe("mixed");
  });

  it("見る許可しか無い行は、全部持つと表示のみ", () => {
    const dash = rowOf("dashboard").keys;
    expect(rowState(dash, new Set(["dashboard.view"]))).toBe("view");
    expect(rowState(dash, new Set())).toBe("off");
    expect(canSetEdit(dash)).toBe(false);
    expect(canSetView(dash)).toBe(true);
  });

  it("見る許可が無い行は、／ を押せない", () => {
    const central = rows.find((r) => r.category === "中央マスタ");
    expect(central).toBeTruthy();
    expect(canSetView(central!.keys)).toBe(false);
    expect(canSetEdit(central!.keys)).toBe(true);
  });

  it("許可の無い行（固定の行）は非表示のまま", () => {
    expect(rowState([], new Set(["x"]))).toBe("off");
  });
});

describe("applyState（押したあとの一覧）", () => {
  const orders = ["orders.view", "orders.create", "orders.update", "orders.delete"];
  const outside = ["leads.view", "menu.dashboard", "menu.faq", "dashboard.view"];

  it("✕: 行の許可を全部外す（行の外は変えない）", () => {
    const held = new Set([...orders, ...outside]);
    const next = applyState(held, orders, "off");
    expect(orders.filter((k) => next.has(k))).toEqual([]);
    expect(outside.every((k) => next.has(k))).toBe(true);
  });

  it("／: 見る許可だけを付け、他を外す", () => {
    const held = new Set(["orders.create", "orders.delete", ...outside]);
    const next = applyState(held, orders, "view");
    expect(orders.filter((k) => next.has(k))).toEqual(["orders.view"]);
    expect(outside.every((k) => next.has(k))).toBe(true);
  });

  it("✓: 行の許可を全部付ける（行の外は変えない）", () => {
    const held = new Set(outside);
    const next = applyState(held, orders, "edit");
    expect(orders.every((k) => next.has(k))).toBe(true);
    expect(next.size).toBe(orders.length + outside.length);
  });

  it("「個別」の行でも、押すとその状態にそろう", () => {
    const held = new Set(["orders.create"]);
    expect(rowState(orders, applyState(held, orders, "off"))).toBe("off");
    expect(rowState(orders, applyState(held, orders, "view"))).toBe("view");
    expect(rowState(orders, applyState(held, orders, "edit"))).toBe("edit");
  });

  it("新しい Set を返し、元の Set を書き換えない", () => {
    const held = new Set(["orders.view"]);
    const next = applyState(held, orders, "edit");
    expect(next).not.toBe(held);
    expect([...held]).toEqual(["orders.view"]);
  });

  it("見る許可が無い行に ／ を押しても何も変わらない", () => {
    const keys = ["central.tcg.edit", "central.dex.edit"];
    const held = new Set(["central.tcg.edit", "leads.view"]);
    expect([...applyState(held, keys, "view")].sort()).toEqual([...held].sort());
  });

  it("画面を開いて何も触らなければ一覧は変わらない（menu.* 19 件も残る）", () => {
    // 営業ロールのような一部だけ持つ一覧 + menu.* 全部
    const held = new Set([...MENU_KEYS, "leads.view", "leads.create", "orders.view", "dashboard.view"]);
    for (const r of rows) {
      const s = rowState(r.keys, held);
      // 押す = 今と同じ状態を選び直す（個別は押せない）
      if (s === "mixed") continue;
      const next = applyState(held, r.keys, s);
      expect([...next].sort()).toEqual([...held].sort());
    }
    expect(MENU_KEYS.every((k) => held.has(k))).toBe(true);
  });

  it("1 行変えて戻すと、元の一覧に戻る", () => {
    const held = new Set([...MENU_KEYS, "orders.view", "orders.create"]);
    const changed = applyState(held, orders, "off");
    const back = new Set(changed);
    for (const k of ["orders.view", "orders.create"]) back.add(k);
    expect([...back].sort()).toEqual([...held].sort());
    // どの操作でも menu.* は 1 つも変わらない
    for (const st of ["off", "view", "edit"] as const) {
      const n = applyState(held, orders, st);
      expect(MENU_KEYS.every((k) => n.has(k))).toBe(true);
    }
  });

  it("全部の行・全部の操作で、行の外の鍵は 1 つも変わらない", () => {
    const held = new Set(NON_MENU_KEYS.filter((_, i) => i % 3 === 0).concat(MENU_KEYS));
    for (const r of rows) {
      const inRow = new Set(r.keys);
      for (const st of ["off", "view", "edit"] as const) {
        const next = applyState(held, r.keys, st);
        const outsideBefore = [...held].filter((k) => !inRow.has(k)).sort();
        const outsideAfter = [...next].filter((k) => !inRow.has(k)).sort();
        expect(outsideAfter, `${r.id}/${st}`).toEqual(outsideBefore);
      }
    }
  });
});
