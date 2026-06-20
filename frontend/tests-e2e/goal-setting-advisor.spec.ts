import { expect, test } from "@playwright/test";
import { mockApi } from "./utils/api-mock";
import { installAuthBypass } from "./utils/auth";

function currentPeriod() {
  const now = new Date();
  return {
    year: now.getFullYear(),
    month: now.getMonth() + 1,
  };
}

function currentWeek() {
  const now = new Date();
  const startOfYear = new Date(now.getFullYear(), 0, 1);
  const week = Math.ceil(
    ((now.getTime() - startOfYear.getTime()) / 86_400_000 + startOfYear.getDay() + 1) / 7,
  );
  return {
    year: now.getFullYear(),
    week,
  };
}

test.describe("Goal setting advisor", () => {
  test("shows recommendation, keeps inputs editable, and exposes reasoning", async ({ page }) => {
    await installAuthBypass(page);
    const { year, month } = currentPeriod();
    const { week } = currentWeek();

    let adviceUrl = "";
    await mockApi(page, {
      "GET /auth/me": { id: 6, role: "admin" },
      "GET /teams": [{ id: 1, name: "営業本部", leader_id: 6 }],
      "GET /goals": (route) => {
        const url = new URL(route.request().url());
        if (url.searchParams.get("team_id")) {
          return route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify([
              { id: 31, user_id: null, team_id: 1, period_type: "monthly", period_year: year, period_num: month, kpi_type: "revenue", target_value: 5000000 },
              { id: 32, user_id: null, team_id: 1, period_type: "weekly", period_year: year, period_num: week, kpi_type: "revenue", target_value: 1200000 },
            ]),
          });
        }
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            { id: 11, user_id: 6, team_id: null, period_type: "monthly", period_year: year, period_num: month, kpi_type: "revenue", target_value: 3000000 },
            { id: 12, user_id: 6, team_id: null, period_type: "weekly", period_year: year, period_num: week, kpi_type: "revenue", target_value: 750000 },
          ]),
        });
      },
      "GET /analytics/new-goal-advice": async (route) => {
        adviceUrl = route.request().url();
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            inputs: {
              monthly_kgi: 3000000,
              kgi_type: "revenue",
              period: "3m",
              scope: "mine",
            },
            rates_used: {
              unit_price: 100000,
              win_rate: 50,
              deal_rate: 40,
            },
            monthly_required: {
              wins: 30,
              deals: 60,
              leads: 150,
            },
            weekly_required: {
              wins: 8,
              deals: 16,
              leads: 40,
            },
            working_days: {
              remaining_month: 18,
              remaining_week: 5,
              shift_status: "submitted",
            },
            data_sufficient: true,
          }),
        });
      },
    });

    await page.goto("/goals/settings");
    await expect(page.getByTestId("goal-advisor-card")).toBeVisible();

    await page.getByTestId("goal-advisor-monthly-kgi").fill("3000000");
    await page.getByTestId("goal-advisor-type-revenue").click();
    await page.getByTestId("goal-advisor-generate").click();

    await expect(page.getByText("おすすめの週次プラン")).toBeVisible();
    await expect(page.getByText("シフト提出済み")).toBeVisible();
    await expect(page.getByTestId("goal-advisor-weekly-leads").locator("input")).toHaveValue("40");
    await expect(page.getByTestId("goal-advisor-weekly-deals").locator("input")).toHaveValue("16");
    await expect(page.getByTestId("goal-advisor-weekly-wins").locator("input")).toHaveValue("8");
    await expect(page.getByText("逆算の内訳を見る")).toBeVisible();

    await page.getByTestId("goal-advisor-weekly-leads").locator("input").fill("44");
    await expect(page.getByTestId("goal-advisor-weekly-leads").locator("input")).toHaveValue("44");
    await expect(page.getByText("AIは提案だけです。入力と最終決定は担当者本人が行ってください。")).toBeVisible();

    expect(adviceUrl).toContain("scope=mine");
    expect(adviceUrl).toContain("kgi_type=revenue");
    expect(adviceUrl).toContain("period=3m");
  });

  test("shows insufficient-data and shift-not-submitted messages", async ({ page }) => {
    await installAuthBypass(page);
    const { year, month } = currentPeriod();
    const { week } = currentWeek();

    await mockApi(page, {
      "GET /auth/me": { id: 6, role: "admin" },
      "GET /teams": [{ id: 1, name: "営業本部", leader_id: 6 }],
      "GET /goals": (route) => {
        const url = new URL(route.request().url());
        if (url.searchParams.get("team_id")) {
          return route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify([]),
          });
        }
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            { id: 11, user_id: 6, team_id: null, period_type: "monthly", period_year: year, period_num: month, kpi_type: "revenue", target_value: 3000000 },
            { id: 12, user_id: 6, team_id: null, period_type: "weekly", period_year: year, period_num: week, kpi_type: "revenue", target_value: 750000 },
          ]),
        });
      },
      "GET /analytics/new-goal-advice": {
        inputs: {
          monthly_kgi: 8,
          kgi_type: "wins",
          period: "3m",
          scope: "mine",
        },
        rates_used: {
          unit_price: null,
          win_rate: 0,
          deal_rate: 0,
        },
        monthly_required: {
          wins: null,
          deals: null,
          leads: null,
        },
        weekly_required: {
          wins: null,
          deals: null,
          leads: null,
        },
        working_days: {
          remaining_month: 20,
          remaining_week: 5,
          shift_status: "not_submitted",
        },
        data_sufficient: false,
      },
    });

    await page.goto("/goals/settings");
    await page.getByTestId("goal-advisor-monthly-kgi").fill("8");
    await page.getByTestId("goal-advisor-type-wins").click();
    await page.getByTestId("goal-advisor-generate").click();

    await expect(page.getByText("実績が足りないため自動計算できません。手動で設定してください。")).toBeVisible();
    await expect(page.getByText("シフト未提出のため週5日（平日）で計上しています。")).toBeVisible();
    await expect(page.getByText("シフト未提出")).toBeVisible();
    await expect(page.getByTestId("goal-advisor-weekly-leads").locator("input")).toHaveValue("");
    await expect(page.getByTestId("goal-advisor-weekly-deals").locator("input")).toHaveValue("");
    await expect(page.getByTestId("goal-advisor-weekly-wins").locator("input")).toHaveValue("");
  });
});
