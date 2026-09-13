/**
 * Foundation F3 — lead channel control E2E
 *
 * 目的:
 *   - channel combobox が /api/v1/channel-masters を消費すること
 *   - dark mode のままでもフォームが動くこと
 *   - 保存時に canonical channel_type が送られること
 */

import { expect, test } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi, type MockMap } from "./utils/api-mock";
import { commonMocks, ALL_PERMISSIONS } from "./utils/common-mocks";

const leadFixture = {
  id: 1,
  lead_code: "LD-00001",
  customer_name: "Channel Control Lead",
  company_name: "Channel Control Co.",
  email: "lead@example.com",
  phone: "0312345678",
  channel_type: "whatsapp_personal",
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
  notes: "channel fixture",
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
      "GET /countries": {
        body: [
          { code: "JP", name: "Japan", dial_code: "+81", is_active: true },
          { code: "US", name: "United States", dial_code: "+1", is_active: true },
        ],
      },
      "GET /leads/1": leadFixture,
    };
  }

test.describe("Foundation F3 — lead channel control", () => {
  test("channel combobox は /channel-masters を読み、canonical channel_type を保存し、dark mode でも動く", async ({ page }) => {
    let channelMasterCalls = 0;
    let capturedPatch: { channel_type?: string | null } | null = null;

    await installAuthBypass(page);
    await mockApi(page, {
      ...baseMocks(),
      "GET /channel-masters": (route) => {
        channelMasterCalls += 1;
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            { id: 1, platform: "discord", display_name: "Discord", connection_type: "auto", is_active: true },
            { id: 2, platform: "in_person", display_name: "対面", connection_type: "manual", is_active: true },
            { id: 3, platform: "instagram", display_name: "Instagram", connection_type: "auto", is_active: true },
            { id: 4, platform: "messenger", display_name: "Messenger", connection_type: "auto", is_active: true },
            { id: 5, platform: "phone", display_name: "電話", connection_type: "manual", is_active: true },
            { id: 6, platform: "whatsapp", display_name: "WhatsApp", connection_type: "manual", is_active: true },
          ]),
        });
      },
      "PATCH /leads/1": async (route) => {
        capturedPatch = route.request().postDataJSON() as { channel_type?: string | null };
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            ...leadFixture,
            channel_type: capturedPatch?.channel_type ?? null,
          }),
        });
      },
    });

    await page.goto("/crm/leads/1/edit");
    await page.waitForLoadState("networkidle");

    await expect(page.locator("html")).toHaveClass(/force-dark/);
    await expect.poll(() => channelMasterCalls).toBeGreaterThan(0);

    const channelInput = page.locator("#lead-channel-type");
    await expect(channelInput).toBeVisible();
    await expect(channelInput).toHaveValue("whatsapp_personal");
    await channelInput.click();
    await page.getByRole("option", { name: /WhatsApp/i }).click();
    await expect(channelInput).toHaveValue(/WhatsApp.*whatsapp/i);

    await page.getByRole("button", { name: /更新|Update/ }).click();
    await expect.poll(() => capturedPatch?.channel_type).toBe("whatsapp");
  });
});
