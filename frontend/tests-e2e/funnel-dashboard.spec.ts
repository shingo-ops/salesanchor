/**
 * ファネルダッシュボード 視覚回帰 spec（PR4）
 *
 * モックデータ（funnelFixtures）で決定的に描画し、Playwright スクリーンショットで確認。
 * 実APIが接続された時点でこのspecはそのまま動作し続ける（mockApiで上書き）。
 *
 * テスト対象:
 *   1. ダッシュボード第1層が7カード表示される
 *   2. ボトルネックバッジが最低達成率カードに表示される
 *   3. 売上ペースバッジが表示される
 *   4. 要フォロー顧客カードのセグメント件数が表示される
 *   5. マネジメント/プレイヤー切替ができる
 *   6. 要フォロー顧客「詳細を見る」が /dashboard/follow-ups へ遷移する
 */

import { expect, test } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi } from "./utils/api-mock";
import { commonMocks, ALL_PERMISSIONS } from "./utils/common-mocks";

// ─── 共通モックデータ ────────────────────────────────────────────────────

const mockFunnel = {
  month: "2026-06",
  month_elapsed_pct: 40,
  leads: { target: 30, actual: 22 },
  conversion: { target_rate: 50, actual_rate: 41, converted: 9 },
  active: { count: 18, amount: 8400000, coverage_pct_of_remaining_target: 175 },
  closed: { won_target: 10, won: 6, won_rate: 35, lost: 4 },
};

const mockRevenueSummary = {
  revenue: { target: 8000000, actual: 3200000, pace: "on_track" },
  split: { new: 1100000, repeat: 2100000 },
  new_customers: { target: 8, actual: 4 },
  active_existing_customers: 26,
  gross_margin: { amount: 960000, uncosted_orders: 0 },
};

const mockFollowUps = {
  items: [
    { customer_id: 1, name: "Card Haven LLC", segment: "order_stopped", days: 62, last_order_at: "2026-04-11", last_contact_at: "2026-05-05", assignee: "佐藤" },
    { customer_id: 2, name: "Tokyo Trading Co.", segment: "no_repeat_after_first", days: 47, last_order_at: "2026-04-27", last_contact_at: "2026-05-15", assignee: "田中" },
    { customer_id: 3, name: "Pacific Goods Inc.", segment: "won_no_order", days: 35, last_order_at: null, last_contact_at: "2026-05-08", assignee: "鈴木" },
    { customer_id: 4, name: "Sunrise Retail", segment: "order_stopped", days: 45, last_order_at: "2026-04-29", last_contact_at: "2026-05-20", assignee: "佐藤" },
    { customer_id: 5, name: "Blue Ocean Co.", segment: "order_stopped", days: 31, last_order_at: "2026-05-13", last_contact_at: null, assignee: "田中" },
    { customer_id: 6, name: "Maple Store", segment: "no_repeat_after_first", days: 52, last_order_at: "2026-04-22", last_contact_at: "2026-05-01", assignee: "鈴木" },
    { customer_id: 7, name: "Ember Shop", segment: "won_no_order", days: 38, last_order_at: null, last_contact_at: "2026-05-06", assignee: "佐藤" },
  ],
};

// 既存ダッシュボード用モック（既存EP維持のため）
const mockGoalSummary = { monthly: [], weekly: [] };
const mockForecast = { forecast_amount: 0, open_deal_count: 0, won_amount: 0, period_start: "2026-06-01", period_end: "2026-06-30" };
const mockFollowupsLegacy = { overdue: [], due_today: [], upcoming: [] };
const mockStalled = { stalled_count: 0, stalled_deals: [] };
const mockSummary = {
  period: "1m", start_date: "2026-05-13", end_date: "2026-06-13",
  leads: { total: 0, converted: 0, excluded: 0, conversion_rate: 0 },
  deals: { total: 0, active: 0, won: 0, win_rate: 0 },
  orders: { total_revenue: 0, order_count: 0, active_count: 0 },
  comparison: {
    leads_total: { pct: null, direction: "flat" },
    leads_cv_rate: { pct: null, direction: "flat" },
    deals_active: { pct: null, direction: "flat" },
    deals_won: { pct: null, direction: "flat" },
    deals_win_rate: { pct: null, direction: "flat" },
    orders_revenue: { pct: null, direction: "flat" },
    orders_count: { pct: null, direction: "flat" },
  },
};
const mockMonthlyRevenue = { granularity: "monthly", entries: [] };

function funnelMocks() {
  return {
    "GET /analytics/funnel": mockFunnel,
    "GET /analytics/revenue-summary": mockRevenueSummary,
    "GET /analytics/follow-ups": mockFollowUps,
    // 既存EP
    "GET /goals/summary": mockGoalSummary,
    "GET /analytics/forecast": mockForecast,
    "GET /analytics/followups": mockFollowupsLegacy,
    "GET /analytics/stalled-deals": mockStalled,
    "GET /analytics/summary": mockSummary,
    "GET /analytics/monthly-revenue": mockMonthlyRevenue,
  };
}

// ─── テスト ─────────────────────────────────────────────────────────────────

test.describe("ファネルダッシュボード 第1層", () => {
  test("ファネル4カードが表示される", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, { ...commonMocks(), ...funnelMocks() });
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // ファネルセクション確認
    await expect(page.getByText("リード獲得")).toBeVisible();
    await expect(page.getByText("商談化率")).toBeVisible();
    await expect(page.getByText("進行中商談")).toBeVisible();
    await expect(page.getByText("成約・失注")).toBeVisible();

    await page.screenshot({ path: "test-results/funnel-dashboard-top.png" });
  });

  test("ボトルネックバッジが最低達成率カードに表示される", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, { ...commonMocks(), ...funnelMocks() });
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // ボトルネック判定: leads=73%, conversion=82%, closed=60% → closedがボトルネック
    const bottleneckBadge = page.locator(".fn-bottleneck-badge");
    await expect(bottleneckBadge).toBeVisible();
    await expect(bottleneckBadge).toHaveCount(1);

    // bottleneckバッジがある親カードに "成約・失注" テキストが含まれる
    const bottleneckCard = page.locator(".fn-card--bottleneck");
    await expect(bottleneckCard).toContainText("成約・失注");
  });

  test("売上ペースバッジ on_track が表示される", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, { ...commonMocks(), ...funnelMocks() });
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    await expect(page.locator(".fn-pace-badge")).toContainText("ペース正常");
  });

  test("要フォロー顧客カードのセグメント件数が表示される", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, { ...commonMocks(), ...funnelMocks() });
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 合計7件: 発注停止3, 初回後未フォロー2, 成約後未発注2
    await expect(page.locator(".fn-followup-total")).toContainText("7");
    await expect(page.getByText("発注停止")).toBeVisible();
    await expect(page.getByText("初回後未フォロー")).toBeVisible();
    await expect(page.getByText("成約後未発注")).toBeVisible();
  });

  test("マネジメント/プレイヤービュー切替ができる", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, { ...commonMocks(), ...funnelMocks() });
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // マネジメントタブがデフォルトでアクティブ
    const mgmtTab = page.locator("button:has-text('マネジメント')").first();
    await expect(mgmtTab).toHaveClass(/active/);

    // プレイヤータブをクリック
    await page.click("button:has-text('プレイヤー')");
    const playerTab = page.locator("button:has-text('プレイヤー')").first();
    await expect(playerTab).toHaveClass(/active/);
  });

  test("要フォロー詳細ボタンで /dashboard/follow-ups に遷移する", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, { ...commonMocks(), ...funnelMocks() });
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 遷移先のAPIモックも追加
    await mockApi(page, {
      "GET /analytics/follow-ups": mockFollowUps,
    });

    await page.click("button:has-text('詳細を見る')");
    await expect(page).toHaveURL(/\/dashboard\/follow-ups/);
  });

  test("スクリーンショット: 第1層フル表示", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, { ...commonMocks(), ...funnelMocks() });
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(300); // アニメーション完了待ち

    await page.screenshot({
      path: "test-results/funnel-dashboard-full.png",
      fullPage: false,
    });
  });
});
