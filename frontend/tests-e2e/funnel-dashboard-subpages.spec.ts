/**
 * ファネルダッシュボード 下層ページ spec（PR5）
 *
 * モックデータで4つの下層ルートを確認:
 *   /dashboard/follow-ups  — 要フォロー顧客一覧
 *   /dashboard/leads       — リード流入分析
 *   /dashboard/revenue     — 売上・粗利内訳
 *   /dashboard/reasons     — 成約・失注理由
 */

import { expect, test, type Route } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi } from "./utils/api-mock";
import { commonMocks } from "./utils/common-mocks";

// ─── 共通モックデータ ────────────────────────────────────────────────────

const mockFollowUps = {
  items: [
    { customer_id: 1, name: "Card Haven LLC", segment: "order_stopped", days: 62, last_order_at: "2026-04-11", last_contact_at: "2026-05-05", assignee: "佐藤" },
    { customer_id: 2, name: "Tokyo Trading Co.", segment: "no_repeat_after_first", days: 47, last_order_at: "2026-04-27", last_contact_at: "2026-05-15", assignee: "田中" },
    { customer_id: 3, name: "Pacific Goods Inc.", segment: "won_no_order", days: 35, last_order_at: null, last_contact_at: "2026-05-08", assignee: "鈴木" },
    { customer_id: 4, name: "Sunrise Retail", segment: "order_stopped", days: 45, last_order_at: "2026-04-29", last_contact_at: "2026-05-20", assignee: "佐藤" },
  ],
};

const mockChannels = {
  rows: [
    { initiative: "inbound", channel: "instagram", leads: 8, conversion_rate: 50, win_rate: 40, avg_order_value: 240000, gross_margin: 64000 },
    { initiative: "outbound", channel: "referral", leads: 6, conversion_rate: 67, win_rate: 75, avg_order_value: 320000, gross_margin: 96000 },
  ],
};

const mockRevenueSummary = {
  revenue: { target: 8000000, actual: 3200000, pace: "on_track" },
  split: { new: 1100000, repeat: 2100000 },
  new_customers: { target: 8, actual: 4 },
  active_existing_customers: 26,
  gross_margin: { amount: 960000, uncosted_orders: 0 },
};

const mockReasonsWon = {
  reasons: [
    { label: "在庫・品揃え", primary_count: 3, secondary_count: 2 },
    { label: "価格", primary_count: 1, secondary_count: 1 },
  ],
  memos: [
    { deal_id: 12, primary_label: "在庫・品揃え", memo: "探していたBOXが揃っていた", closed_at: "2026-06-05" },
  ],
};

const mockReasonsLost = {
  reasons: [
    { label: "価格が合わなかった", primary_count: 2, secondary_count: 1 },
  ],
  memos: [
    { deal_id: 8, primary_label: "価格が合わなかった", memo: "他社が5%安かった", closed_at: "2026-06-03" },
  ],
};

// ─── /dashboard/follow-ups ─────────────────────────────────────────────────

test.describe("/dashboard/follow-ups — 要フォロー顧客", () => {
  test("テーブルと顧客名が表示される", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      "GET /analytics/follow-ups": mockFollowUps,
    });
    await page.goto("/dashboard/follow-ups");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Card Haven LLC")).toBeVisible();
    await expect(page.getByText("Tokyo Trading Co.")).toBeVisible();
  });

  test("セグメントフィルタで絞り込みができる", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      "GET /analytics/follow-ups": mockFollowUps,
    });
    await page.goto("/dashboard/follow-ups");
    await page.waitForLoadState("networkidle");

    // 発注停止フィルタをクリック
    await page.click("button:has-text('発注停止')");
    await expect(page.getByText("Card Haven LLC")).toBeVisible();
    // 初回後未フォローは非表示
    await expect(page.getByText("Tokyo Trading Co.")).not.toBeVisible();
  });

  test("行クリックでドロワーが開く", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      "GET /analytics/follow-ups": mockFollowUps,
    });
    await page.goto("/dashboard/follow-ups");
    await page.waitForLoadState("networkidle");

    // 最初の行をクリック
    await page.click("tr:has-text('Card Haven LLC')");
    // ドロワータイトルに顧客名が表示される
    await expect(page.getByText("Card Haven LLC")).toHaveCount(2); // テーブル + ドロワー
  });

  test("戻るボタンでダッシュボードに戻る", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      "GET /analytics/follow-ups": mockFollowUps,
    });
    await page.goto("/dashboard/follow-ups");
    await page.waitForLoadState("networkidle");

    await page.click("button:has-text('ダッシュボード')");
    await expect(page).toHaveURL("/");
  });

  test("スクリーンショット", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      "GET /analytics/follow-ups": mockFollowUps,
    });
    await page.goto("/dashboard/follow-ups");
    await page.waitForLoadState("networkidle");
    await page.screenshot({ path: "test-results/follow-ups-page.png" });
  });
});

// ─── /dashboard/leads ──────────────────────────────────────────────────────

test.describe("/dashboard/leads — リード流入分析", () => {
  test("チャネルテーブルが表示される", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      "GET /analytics/channels": mockChannels,
    });
    await page.goto("/dashboard/leads");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("instagram")).toBeVisible();
    await expect(page.getByText("referral")).toBeVisible();
  });

  test("initiative チップが表示される", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      "GET /analytics/channels": mockChannels,
    });
    await page.goto("/dashboard/leads");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("顧客起点")).toBeVisible();
    await expect(page.getByText("自社起点")).toBeVisible();
  });

  test("スクリーンショット", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      "GET /analytics/channels": mockChannels,
    });
    await page.goto("/dashboard/leads");
    await page.waitForLoadState("networkidle");
    await page.screenshot({ path: "test-results/leads-page.png" });
  });
});

// ─── /dashboard/revenue ────────────────────────────────────────────────────

test.describe("/dashboard/revenue — 売上・粗利内訳", () => {
  test("売上金額と目標が表示される", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      "GET /analytics/revenue-summary": mockRevenueSummary,
    });
    await page.goto("/dashboard/revenue");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("¥3,200,000")).toBeVisible();
    await expect(page.getByText(/¥8,000,000/)).toBeVisible();
  });

  test("ペースバッジが表示される", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      "GET /analytics/revenue-summary": mockRevenueSummary,
    });
    await page.goto("/dashboard/revenue");
    await page.waitForLoadState("networkidle");

    await expect(page.locator(".frp-pace-badge")).toContainText("ペース正常");
  });

  test("新規/リピート分割が表示される", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      "GET /analytics/revenue-summary": mockRevenueSummary,
    });
    await page.goto("/dashboard/revenue");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("新規 / リピート内訳")).toBeVisible();
    await expect(page.getByText("¥1,100,000")).toBeVisible();
    await expect(page.getByText("¥2,100,000")).toBeVisible();
  });

  test("スクリーンショット", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      "GET /analytics/revenue-summary": mockRevenueSummary,
    });
    await page.goto("/dashboard/revenue");
    await page.waitForLoadState("networkidle");
    await page.screenshot({ path: "test-results/revenue-page.png" });
  });
});

// ─── /dashboard/reasons ────────────────────────────────────────────────────

test.describe("/dashboard/reasons — 成約・失注理由", () => {
  const reasonsMockFn = async (route: Route) => {
    const url = new URL(route.request().url());
    const type = url.searchParams.get("type");
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(type === "lost" ? mockReasonsLost : mockReasonsWon),
    });
  };

  test("成約タブで成約理由ランキングが表示される", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      "GET /analytics/reasons": reasonsMockFn,
    });
    await page.goto("/dashboard/reasons");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("在庫・品揃え")).toBeVisible();
    await expect(page.getByText("価格")).toBeVisible();
  });

  test("失注タブに切り替えると失注理由が表示される", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      "GET /analytics/reasons": reasonsMockFn,
    });
    await page.goto("/dashboard/reasons");
    await page.waitForLoadState("networkidle");

    // 初期表示: 成約ランキング
    await expect(page.getByText("在庫・品揃え")).toBeVisible();

    // 失注タブをクリック
    await page.click("button:has-text('失注')");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("価格が合わなかった")).toBeVisible();
  });

  test("メモ一覧に顧客の言葉が表示される", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      "GET /analytics/reasons": reasonsMockFn,
    });
    await page.goto("/dashboard/reasons");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("探していたBOXが揃っていた")).toBeVisible();
  });

  test("スクリーンショット", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      "GET /analytics/reasons": reasonsMockFn,
    });
    await page.goto("/dashboard/reasons");
    await page.waitForLoadState("networkidle");
    await page.screenshot({ path: "test-results/reasons-page.png" });
  });
});
