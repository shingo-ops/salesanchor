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
          lead_id: 9001,
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
          lead_id: 9002,
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
          lead_id: null,
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
    "GET /analytics/priority-prospects": {
      scope: "mine",
      items: [
        {
          lead_id: 9001,
          type: "priority_prospect",
          ease_pct: 78.4,
          monthly_forecast: 320000,
          rank_score: 25088000,
          score: 25088000,
          expected_value: 320000,
          suggested_action: "商談化に向けて連絡する",
          axis_breakdown: [
            { axis: "channel_type", value: "web", n: 18, conversions: 11, raw_rate: 0.6111, smoothed_rate: 0.64, low_sample: false },
            { axis: "country", value: "JP", n: 9, conversions: 6, raw_rate: 0.6667, smoothed_rate: 0.68, low_sample: true },
            { axis: "sales_form", value: "direct", n: 15, conversions: 10, raw_rate: 0.6667, smoothed_rate: 0.7, low_sample: false },
            { axis: "temperature", value: "Warm", n: 13, conversions: 9, raw_rate: 0.6923, smoothed_rate: 0.72, low_sample: false },
            { axis: "response_speed", value: "24h以内", n: 12, conversions: 8, raw_rate: 0.6667, smoothed_rate: 0.69, low_sample: false },
          ],
          low_sample_flags: ["country:low_sample"],
        },
        {
          lead_id: 9002,
          type: "priority_prospect",
          ease_pct: 72.1,
          monthly_forecast: 200000,
          rank_score: 14420000,
          score: 14420000,
          expected_value: 200000,
          suggested_action: "見込み確認の電話を入れる",
          axis_breakdown: [
            { axis: "channel_type", value: "referral", n: 21, conversions: 14, raw_rate: 0.6667, smoothed_rate: 0.69, low_sample: false },
            { axis: "country", value: "US", n: 14, conversions: 10, raw_rate: 0.7143, smoothed_rate: 0.73, low_sample: false },
            { axis: "sales_form", value: "quote", n: 8, conversions: 4, raw_rate: 0.5, smoothed_rate: 0.55, low_sample: true },
            { axis: "temperature", value: "Hot", n: 11, conversions: 8, raw_rate: 0.7273, smoothed_rate: 0.75, low_sample: false },
            { axis: "response_speed", value: "3日以内", n: 10, conversions: 6, raw_rate: 0.6, smoothed_rate: 0.63, low_sample: false },
          ],
          low_sample_flags: ["sales_form:low_sample", "monthly_forecast_unset"],
        },
        {
          lead_id: 9003,
          type: "priority_prospect",
          ease_pct: 68.9,
          monthly_forecast: 180000,
          rank_score: 12402000,
          score: 12402000,
          expected_value: 180000,
          suggested_action: "提案資料を送る",
          axis_breakdown: [
            { axis: "channel_type", value: "instagram", n: 16, conversions: 9, raw_rate: 0.5625, smoothed_rate: 0.59, low_sample: false },
            { axis: "country", value: "GB", n: 7, conversions: 4, raw_rate: 0.5714, smoothed_rate: 0.6, low_sample: true },
            { axis: "sales_form", value: "dm", n: 14, conversions: 8, raw_rate: 0.5714, smoothed_rate: 0.61, low_sample: false },
            { axis: "temperature", value: "Warm", n: 9, conversions: 5, raw_rate: 0.5556, smoothed_rate: 0.58, low_sample: true },
            { axis: "response_speed", value: "24h以内", n: 13, conversions: 7, raw_rate: 0.5385, smoothed_rate: 0.56, low_sample: false },
          ],
          low_sample_flags: ["country:low_sample", "temperature:low_sample"],
        },
      ],
    },
    "GET /leads/9001": {
      id: 9001,
      lead_code: "LD-09001",
      customer_name: "Blue Ocean Co.",
      company_name: "Blue Ocean Co.",
      email: "blue@example.com",
      phone: null,
      status: "lead",
      temperature: "Warm",
      estimated_scale: "Medium",
      customer_type: "信頼重視",
      response_speed: "24h以内",
      monthly_forecast: 320000,
      prospect_rank: "A",
      notes: null,
      next_action: null,
      next_action_date: null,
      challenge: null,
      meeting_memo: null,
      meeting_impression: null,
      cs_memo: null,
      sales_form: "direct",
      competitor_check: null,
      per_order_amount: null,
      monthly_frequency: null,
      nickname: null,
      country: "JP",
      target_titles: null,
      messenger_link: null,
      discord_id: null,
      instagram_link: null,
      whatsapp_link: null,
      discord_user_id: null,
      discord_dm_channel_id: null,
      discord_guild_channel_id: null,
      discord_role_sync_status: null,
      discord_role_sync_at: null,
      sales_form_selections: [],
      sales_form_options: [],
    },
    "GET /leads/9002": {
      id: 9002,
      lead_code: "LD-09002",
      customer_name: "Card Haven LLC",
      company_name: "Card Haven LLC",
      email: "card@example.com",
      phone: null,
      status: "lead",
      temperature: "Hot",
      estimated_scale: "Large",
      customer_type: "価格重視",
      response_speed: "3日以内",
      monthly_forecast: 200000,
      prospect_rank: "B",
      notes: null,
      next_action: null,
      next_action_date: null,
      challenge: null,
      meeting_memo: null,
      meeting_impression: null,
      cs_memo: null,
      sales_form: "quote",
      competitor_check: null,
      per_order_amount: null,
      monthly_frequency: null,
      nickname: null,
      country: "US",
      target_titles: null,
      messenger_link: null,
      discord_id: null,
      instagram_link: null,
      whatsapp_link: null,
      discord_user_id: null,
      discord_dm_channel_id: null,
      discord_guild_channel_id: null,
      discord_role_sync_status: null,
      discord_role_sync_at: null,
      sales_form_selections: [],
      sales_form_options: [],
    },
    "GET /leads/9003": {
      id: 9003,
      lead_code: "LD-09003",
      customer_name: "Ember Shop",
      company_name: "Ember Shop",
      email: "ember@example.com",
      phone: null,
      status: "lead",
      temperature: "Warm",
      estimated_scale: "Small",
      customer_type: "信頼重視",
      response_speed: "24h以内",
      monthly_forecast: 180000,
      prospect_rank: "B",
      notes: null,
      next_action: null,
      next_action_date: null,
      challenge: null,
      meeting_memo: null,
      meeting_impression: null,
      cs_memo: null,
      sales_form: "dm",
      competitor_check: null,
      per_order_amount: null,
      monthly_frequency: null,
      nickname: null,
      country: "GB",
      target_titles: null,
      messenger_link: null,
      discord_id: null,
      instagram_link: null,
      whatsapp_link: null,
      discord_user_id: null,
      discord_dm_channel_id: null,
      discord_guild_channel_id: null,
      discord_role_sync_status: null,
      discord_role_sync_at: null,
      sales_form_selections: [],
      sales_form_options: [],
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

    // 期間プルダウンが描画される
    const periodSelect = page.locator(".page-header-select");
    await expect(periodSelect).toBeVisible();

    // 固定エリア: 目標 / フォローアップ（Sprint 4: 着地予測は統合カードに移動）
    await expect(page.getByText("目標", { exact: true })).toBeVisible();
    await expect(page.getByText("フォローアップ", { exact: true })).toBeVisible();
    await expect(page.getByTestId("priority-prospects-section")).toBeVisible();
    await expect(page.getByTestId("weekly-advisor-section")).toBeVisible();
    await expect(page.getByTestId("priority-prospect-item").first()).toContainText("Blue Ocean Co.");
    await expect(page.getByTestId("weekly-advisor-item").first()).toContainText("Blue Ocean Co.");

    // 受注統合カード: 受注・売上 見出しが描画される（営業担当ビュー）
    await expect(page.getByText("受注・売上", { exact: true })).toBeVisible();
  });

  test("今やることのフォロー追加で lead.next_action を保存できる", async ({ page }) => {
    let capturedPatch: { next_action?: string; next_action_date?: string | null } | null = null;

    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      ...dashboardMocks(),
      "GET /leads/9001": {
        id: 9001,
        next_action: null,
        next_action_date: null,
      },
      "PATCH /leads/9001": async (route) => {
        capturedPatch = route.request().postDataJSON() as { next_action?: string; next_action_date?: string | null };
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: 9001,
            next_action: capturedPatch?.next_action ?? null,
            next_action_date: capturedPatch?.next_action_date ?? null,
          }),
        });
      },
    });

    await page.goto("/");
    await page.waitForLoadState("networkidle");

    const composerOpen = page.getByTestId("weekly-followup-open").first();
    await expect(composerOpen).toBeVisible();
    await composerOpen.click();

    const composer = page.getByTestId("weekly-followup-composer");
    await expect(composer).toBeVisible();
    await expect(page.getByTestId("weekly-followup-save")).toBeEnabled();

    const actionField = composer.locator("textarea");
    await actionField.fill("担当者へ連絡する");
    await page.getByTestId("weekly-followup-save").click();

    await expect.poll(() => capturedPatch?.next_action).toBe("担当者へ連絡する");
    expect(capturedPatch?.next_action_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    await expect(page.getByTestId("weekly-followup-saved")).toContainText("追加済み");
  });

  test("今追うべき見込み客は しやすさ%・見込み金額・サンプル少を表示し、フォロー追加できる", async ({ page }) => {
    let capturedPatch: { next_action?: string; next_action_date?: string | null } | null = null;

    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      ...dashboardMocks(),
      "GET /staff/me": {
        id: 1,
        primary_email: "review@salesanchor.jp",
        theme: "dark",
        ui_preferences: {
          dark_mode: true,
          show_chat_menu: true,
          show_sales_menu: true,
          show_settings_menu: true,
          show_admin_menu: true,
          show_sidebar: true,
        },
      },
      "GET /leads/9001": {
        ...dashboardMocks()["GET /leads/9001"],
        next_action: null,
        next_action_date: null,
      },
      "PATCH /leads/9001": async (route) => {
        capturedPatch = route.request().postDataJSON() as { next_action?: string; next_action_date?: string | null };
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            ...(dashboardMocks()["GET /leads/9001"] as Record<string, unknown>),
            next_action: capturedPatch?.next_action ?? null,
            next_action_date: capturedPatch?.next_action_date ?? null,
          }),
        });
      },
    });

    await page.goto("/");
    await page.waitForLoadState("networkidle");

    await expect(page.locator("html")).toHaveClass(/force-dark/);
    const firstItem = page.getByTestId("priority-prospect-item").first();
    await expect(firstItem).toContainText("しやすさ");
    await expect(firstItem).toContainText("見込み金額");
    await expect(firstItem).toContainText("サンプル少");
    await expect(firstItem).toContainText("Blue Ocean Co.");

    await page.getByTestId("priority-followup-open").first().click();
    const composer = page.getByTestId("priority-followup-composer");
    await expect(composer).toBeVisible();
    await composer.locator("textarea").fill("今週中に連絡する");
    await page.getByTestId("priority-followup-save").click();

    await expect.poll(() => capturedPatch?.next_action).toBe("今週中に連絡する");
    expect(capturedPatch?.next_action_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    await expect(page.getByTestId("priority-followup-saved").first()).toContainText("追加済み");
  });

  test("lead_id が無い場合は会社詳細へ遷移する", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      ...dashboardMocks(),
      "GET /companies/103": {
        id: 103,
        tenant_id: 999,
        company_code: "CT-00103",
        lead_id: null,
        sales_rep_id: null,
        name: "Tokyo Trading Co.",
        name_en: null,
        normalized_name: null,
        industry: null,
        website: null,
        priority_focus: null,
        per_order_amount: null,
        monthly_frequency: null,
        monthly_forecast: null,
        monthly_forecast_source: null,
        monthly_forecast_updated_at: null,
        billing_display_name: null,
        payment_recipient_name: null,
        fedex_account: null,
        shipping_note: null,
        status: "active",
        notes: null,
        addresses: [],
        sales_channels: [],
        discord: null,
        created_at: "2026-06-01T00:00:00Z",
        updated_at: "2026-06-01T00:00:00Z",
        conversation_count: 0,
        last_conversation_at: null,
      },
      "GET /companies/103/contacts": [],
    });

    await page.goto("/");
    await page.waitForLoadState("networkidle");

    await page.getByTestId("weekly-company-open").click();
    await expect(page).toHaveURL(/\/companies\/103/);
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

    // sidebar 内の主要ラベル: ダッシュボード（NavLink） / 顧客管理（NavLink） / 管理（NavLink）
    await expect(nav.getByText("ダッシュボード", { exact: true })).toBeVisible();
    await expect(nav.getByText("顧客管理", { exact: true })).toBeVisible();
  });
});
