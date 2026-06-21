/**
 * Scene 1: Intro — SalesAnchor Dashboard Overview
 *
 * 撮影台本対応: docs/META_APP_REVIEW_SCREENCAST_SCRIPT.md §2 (0:00–0:30)
 *
 * 目的:
 *   - LoginPage の DOM 要素（Email / Password / ログインボタン）が描画される
 *   - 認証 bypass 後、Dashboard ('/') が新構造（タブ・期間・固定/期間連動エリア）で表示される
 *   - 上段ブランドバー + 主要メニュー（リード / 在庫 / 管理 / その他）が描画される
 *
 * 変更履歴:
 *   2026-05-25: ダッシュボード強化（タブ・期間フィルター・目標・着地予測）に合わせて更新
 */

import { expect, test } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi } from "./utils/api-mock";
import { commonMocks } from "./utils/common-mocks";

/** 新ダッシュボード用 API モック群 */
function dashboardMocks() {
  return {
    // 目標サマリー（個人・チーム）— GoalSummary 型に合わせた形式
    "GET /goals/summary": { monthly: [], weekly: [] },
    // フォローアップリマインド
    "GET /analytics/followups": {
      overdue: [],
      due_today: [],
      upcoming: [],
      stalled: [],
    },
    "GET /analytics/weekly-advisor-defensive": {
      period: "3m",
      scope: "mine",
      stale_days: 14,
      actions: [
        {
          rank: 1,
          type: "churn_risk",
          company_id: 101,
          company_name: "Blue Ocean Co.",
          score: 12800,
          expected_value: 320000,
          suggested_action: "状況確認の連絡",
          reason: {
            last_order_at: "2026-05-18",
            last_contact_at: "2026-05-22",
            avg_interval_days: 20,
            days_since_last_order: 34,
            days_since_contact: 30,
            pace_score: 18,
            contact_score: 12,
            decline_score: 40,
            total_score: 70,
            current_order_count: 1,
            previous_order_count: 4,
            current_revenue: 320000,
            previous_revenue: 1280000,
          },
        },
        {
          rank: 2,
          type: "reorder",
          company_id: 102,
          company_name: "Card Haven LLC",
          score: 7600,
          expected_value: 380000,
          suggested_action: "再受注の案内",
          reason: {
            last_order_at: "2026-05-28",
            last_contact_at: "2026-06-01",
            avg_interval_days: 18,
            days_since_last_order: 24,
            days_since_contact: 20,
            current_order_count: 3,
            previous_order_count: 0,
            current_revenue: 1140000,
            previous_revenue: 0,
          },
        },
        {
          rank: 3,
          type: "comm_low",
          company_id: 103,
          company_name: "Tokyo Trading Co.",
          score: 3200,
          expected_value: 280000,
          suggested_action: "近況確認の連絡",
          reason: {
            last_order_at: "2026-06-02",
            last_contact_at: "2026-05-18",
            days_since_contact: 34,
            current_order_count: 2,
            previous_order_count: 1,
            current_revenue: 560000,
            previous_revenue: 300000,
          },
        },
      ],
    },
    // 着地予測
    "GET /analytics/forecast": {
      forecast_amount: 3200000,
      won_amount: 1800000,
      open_deal_count: 4,
      period_start: "2026-05-01",
      period_end: "2026-05-31",
    },
    // 滞留商談アラート
    "GET /analytics/stalled-deals": {
      stalled_count: 0,
      stalled_deals: [],
    },
    // 受注グラフ（Sprint 4: 期間連動・粒度切り替え対応）
    "GET /analytics/monthly-revenue": {
      granularity: "monthly",
      entries: [
        { label: "2026-01", actual: 3200000, forecast: null, remaining: 0, is_current: false },
        { label: "2026-02", actual: 2800000, forecast: null, remaining: 0, is_current: false },
        { label: "2026-03", actual: 4100000, forecast: null, remaining: 0, is_current: false },
        { label: "2026-04", actual: 3600000, forecast: null, remaining: 0, is_current: false },
        { label: "2026-05", actual: 1800000, forecast: 3200000, remaining: 1400000, is_current: true },
      ],
    },
    // 期間連動 KPI サマリー
    "GET /analytics/summary": {
      leads: {
        total: 18,
        converted: 7,
        excluded: 2,
        conversion_rate: 38.9,
      },
      deals: {
        total: 12,
        active: 5,
        won: 4,
        win_rate: 44.4,
      },
      orders: {
        total_revenue: 5400000,
        order_count: 9,
        active_count: 2,
      },
      comparison: {
        leads_total: { pct: 12.5, direction: "up" },
        leads_cv_rate: { pct: -3.2, direction: "down" },
        deals_active: { pct: 0, direction: "flat" },
        deals_won: { pct: 25.0, direction: "up" },
        deals_win_rate: { pct: 8.1, direction: "up" },
        orders_revenue: { pct: 15.3, direction: "up" },
        orders_count: { pct: null, direction: "flat" },
      },
    },
  };
}

test.describe("Scene 1: Dashboard Overview", () => {
  test("LoginPage は Email / Password / ログインボタンが見える", async ({ page }) => {
    // 0:02–0:10 のフレーム: 認証前のログイン画面（Firebase auth bypass 不要）
    await page.goto("/login");

    await expect(page.getByLabel("メールアドレス")).toBeVisible();
    await expect(page.getByLabel("パスワード")).toBeVisible();
    await expect(page.getByRole("button", { name: "ログイン" })).toBeVisible();
  });

  test("認証済 user は Dashboard を見られ、新構造（タブ・期間・KPIセクション）が描画される", async ({
    page,
  }) => {
    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      ...dashboardMocks(),
    });

    // 0:12 の Dashboard 描画
    await page.goto("/");

    // h2 "ダッシュボード"
    await expect(page.getByRole("heading", { name: "ダッシュボード" })).toBeVisible({
      timeout: 20_000,
    });

    // 営業担当 / リード担当 / チーム タブが描画される（Sprint 1 でタブ構造変更）
    await expect(page.getByRole("button", { name: "営業担当" })).toBeVisible();
    await expect(page.getByRole("button", { name: "リード担当" })).toBeVisible();
    await expect(page.getByRole("button", { name: "チーム" })).toBeVisible();

    // 期間プルダウンが描画される
    const periodSelect = page.locator(".page-header-select");
    await expect(periodSelect).toBeVisible();

    // 固定エリア: 目標 / フォローアップ（Sprint 4: 着地予測は統合カードに移動）
    await expect(page.getByText("目標", { exact: true })).toBeVisible();
    await expect(page.getByText("フォローアップ", { exact: true })).toBeVisible();
    await expect(page.getByText("今やること", { exact: true })).toBeVisible();
    await expect(page.getByTestId("weekly-advisor-section")).toBeVisible();
    await expect(page.getByTestId("weekly-advisor-item").first()).toContainText("Blue Ocean Co.");

    // 受注統合カード: 受注・売上 見出しが描画される（営業担当ビュー）
    await expect(page.getByText("受注・売上", { exact: true })).toBeVisible();

    // チームタブに切り替えると商談・リードセクションが表示される
    // db-period-area にスコープして sidebar-label の "リード" (opacity:0) と衝突しないようにする
    await page.getByRole("button", { name: "チーム" }).click();
    await expect(page.locator(".db-period-area").getByText("リード", { exact: true })).toBeVisible();
    await expect(page.locator(".db-period-area").getByText("商談", { exact: true })).toBeVisible();
  });

  test("0:18–0:25: メインナビにダッシュボード / リード / 管理メニューが出ている", async ({
    page,
  }) => {
    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      ...dashboardMocks(),
    });

    await page.goto("/");
    await expect(page.getByRole("heading", { name: "ダッシュボード" })).toBeVisible({
      timeout: 20_000,
    });

    // ADR-044: Meta Business Suite 風 UI 刷新 (ADR-022) で nav 構造が
    // `<nav class="mainnav">` から sidebar (`<nav class="sidebar-nav-items">`) に変更。
    // .sidebar-label は折り畳み時 opacity:0 のため、ホバーで展開してから検証する。
    const sidebar = page.locator("aside.sidebar-panel");
    await sidebar.hover();

    const nav = page.locator("nav.sidebar-nav-items");
    await expect(nav).toBeVisible();

    // sidebar 内の主要ラベル: ダッシュボード（NavLink） / リード（NavLink） / 管理センター（NavLink, 管理アコーディオン廃止）
    // nav.leads は commit 9980895 で "顧客管理" → "リード" に変更済み
    await expect(nav.getByText("ダッシュボード", { exact: true })).toBeVisible();
    await expect(nav.getByText("リード", { exact: true })).toBeVisible();
    await expect(nav.getByText("管理センター", { exact: true })).toBeVisible();
  });
});
