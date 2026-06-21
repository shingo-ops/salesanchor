/**
 * Foundation F2 — lead country control E2E
 *
 * 目的:
 *   - country combobox が /api/v1/countries を消費すること
 *   - dark mode のままでもフォームが動くこと
 *   - 保存時に alpha-2 が送られること
 */

import { expect, test } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi, type MockMap } from "./utils/api-mock";
import { commonMocks, ALL_PERMISSIONS } from "./utils/common-mocks";

const leadFixture = {
  id: 1,
  lead_code: "LD-00001",
  customer_name: "Country Control Lead",
  company_name: "Country Control Co.",
  email: "lead@example.com",
  phone: "0312345678",
  channel_type: "web",
  initiative: "inbound",
  type: "Inbound",
  status: "lead",
  temperature: "Warm",
  estimated_scale: "Medium",
  customer_type: "信頼重視",
  response_speed: "24h以内",
  monthly_forecast: 120000,
  prospect_rank: "B",
  assigned_to: null,
  converted_deal_id: null,
  notes: "country fixture",
  country: null,
  created_at: "2026-06-21T00:00:00Z",
  updated_at: "2026-06-21T00:00:00Z",
  discord_user_id: null,
  discord_role_sync_status: null,
};

function baseMocks(): MockMap {
  return {
    ...commonMocks(),
    "GET /me/permissions": {
      permissions: [...ALL_PERMISSIONS, "leads.update", "leads.create"],
    },
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
    "GET /leads/1": leadFixture,
  };
}

test.describe("Foundation F2 — lead country control", () => {
  test("country combobox は /countries を読み、alpha-2 を保存し、dark mode でも動く", async ({ page }) => {
    let countriesCalls = 0;
    let capturedPatch: { country?: string | null } | null = null;

    await installAuthBypass(page);
    await mockApi(page, {
      ...baseMocks(),
      "GET /countries": (route) => {
        countriesCalls += 1;
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            { code: "JP", name: "Japan", dial_code: "+81", is_active: true },
            { code: "US", name: "United States", dial_code: "+1", is_active: true },
            { code: "GB", name: "United Kingdom", dial_code: "+44", is_active: true },
          ]),
        });
      },
      "PATCH /leads/1": async (route) => {
        capturedPatch = route.request().postDataJSON() as { country?: string | null };
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            ...leadFixture,
            country: capturedPatch?.country ?? null,
          }),
        });
      },
    });

    await page.goto("/crm/leads/1/edit");
    await page.waitForLoadState("networkidle");

    await expect(page.locator("html")).toHaveClass(/force-dark/);
    await expect.poll(() => countriesCalls).toBeGreaterThan(0);

    const countryInput = page.locator("#lead-country");
    await expect(countryInput).toBeVisible();
    await countryInput.click();
    await countryInput.fill("Japan");
    await expect(page.getByRole("option", { name: /Japan/i })).toBeVisible();
    await page.getByRole("option", { name: /Japan/i }).click();
    await expect(countryInput).toHaveValue(/Japan.*JP/);

    await page.getByRole("button", { name: /更新|Update/ }).click();
    await expect.poll(() => capturedPatch?.country).toBe("JP");
  });
});
