/**
 * horizontal-overflow.spec.ts — KGI-5: 主要ページ横スクロールなし検証（PR-R2-C）
 *
 * ADR-137: 375px（モバイル幅）で主要 6 route に横スクロールが発生しないことを確認する。
 *
 * 検証方法: `document.documentElement.scrollWidth > window.innerWidth` → false
 *
 * 対象 route:
 *   /           ダッシュボード
 *   /lead-chat  受信箱（inbox）
 *   /crm        顧客管理ハブ
 *   /inventory  在庫表
 *   /quotes     見積一覧
 *   /orders     受注一覧
 */

import { expect, test } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi } from "./utils/api-mock";
import { commonMocks } from "./utils/common-mocks";

const MOBILE_VIEWPORT = { width: 375, height: 812 };

/** scrollWidth > innerWidth が false かどうかを評価する */
async function hasNoHorizontalOverflow(page: import("@playwright/test").Page): Promise<boolean> {
  return page.evaluate(
    () => document.documentElement.scrollWidth <= window.innerWidth,
  );
}

function routeMocks() {
  return {
    "GET /analytics/followups": { overdue: [], due_today: [], upcoming: [], stalled: [] },
    "GET /analytics/forecast": { forecast_amount: 0, won_amount: 0, open_deal_count: 0, period_start: "2026-06-01", period_end: "2026-06-30" },
    "GET /analytics/stalled-deals": { stalled_count: 0, stalled_deals: [] },
    "GET /analytics/monthly-revenue": { granularity: "monthly", entries: [] },
    "GET /goals/summary": { monthly: [], weekly: [] },
    "GET /conversations": { conversations: [], total: 0 },
    "GET /leads": { leads: [], total: 0 },
    "GET /crm/companies": { companies: [], total: 0 },
    "GET /products": { products: [], total: 0 },
    "GET /quotes": { quotes: [], total: 0 },
    "GET /orders": { orders: [], total: 0 },
  };
}

test.describe("KGI-5: 375px 横スクロールなし検証", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await installAuthBypass(page);
    await mockApi(page, { ...commonMocks(), ...routeMocks() });
  });

  test("/ (ダッシュボード) — 横スクロールなし", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    const noOverflow = await hasNoHorizontalOverflow(page);
    expect(noOverflow).toBe(true);
  });

  test("/lead-chat (受信箱) — 横スクロールなし", async ({ page }) => {
    await page.goto("/lead-chat");
    await page.waitForLoadState("networkidle");
    const noOverflow = await hasNoHorizontalOverflow(page);
    expect(noOverflow).toBe(true);
  });

  test("/crm (顧客管理ハブ) — 横スクロールなし", async ({ page }) => {
    await page.goto("/crm");
    await page.waitForLoadState("networkidle");
    const noOverflow = await hasNoHorizontalOverflow(page);
    expect(noOverflow).toBe(true);
  });

  test("/inventory (在庫表) — 横スクロールなし", async ({ page }) => {
    await page.goto("/inventory");
    await page.waitForLoadState("networkidle");
    const noOverflow = await hasNoHorizontalOverflow(page);
    expect(noOverflow).toBe(true);
  });

  test("/quotes (見積一覧) — 横スクロールなし", async ({ page }) => {
    await page.goto("/quotes");
    await page.waitForLoadState("networkidle");
    const noOverflow = await hasNoHorizontalOverflow(page);
    expect(noOverflow).toBe(true);
  });

  test("/orders (受注一覧) — 横スクロールなし", async ({ page }) => {
    await page.goto("/orders");
    await page.waitForLoadState("networkidle");
    const noOverflow = await hasNoHorizontalOverflow(page);
    expect(noOverflow).toBe(true);
  });
});
