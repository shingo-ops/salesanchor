/**
 * Karte Visual Gate — ADR-108/110 acceptance criteria automated verification.
 *
 * This spec mechanizes the acceptance criteria of ADR-108 (Inbox Karte Redesign)
 * and ADR-110 (Karte Reference Alignment) so that any PR touching the karte
 * structure is automatically validated before merge.
 *
 * Reference: docs/adr/karte_reference.html
 */

import { expect, test, type Page } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi, type MockMap } from "./utils/api-mock";
import { commonMocks } from "./utils/common-mocks";
import { loadFixture } from "./utils/fixtures";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const leadShinki = loadFixture("karte-lead-shinki-with-deal.json") as Record<string, unknown>;
const leadShinkiNoDeal = loadFixture("karte-lead-shinki-no-deal.json") as Record<string, unknown>;
const leadShoudanchuu = loadFixture("karte-lead-shoudanchuu-with-deal.json") as Record<string, unknown>;
const leadShoudanchuuNoDeal = loadFixture("karte-lead-shoudanchuu-no-deal.json") as Record<string, unknown>;
const leadKisonkosaku = loadFixture("karte-lead-kisonkosaku-with-deal.json") as Record<string, unknown>;
const leadKisonkosakuNoDeal = loadFixture("karte-lead-kisonkosaku-no-deal.json") as Record<string, unknown>;
const leadOikomi = loadFixture("karte-lead-oikomi-with-deal.json") as Record<string, unknown>;
const leadOikomiNoDeal = loadFixture("karte-lead-oikomi-no-deal.json") as Record<string, unknown>;

const invoicesPaid = loadFixture("karte-invoices-paid.json");
const invoicesEmpty = loadFixture("karte-invoices-empty.json");

const discordConfig = loadFixture("karte-discord-config.json");
const karteMessages = loadFixture("karte-messages.json");

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a conversations response with a single entry matching the given lead fixture. */
function makeConversations(lead: Record<string, unknown>) {
  return {
    conversations: [
      {
        lead_id: lead.id,
        lead_code: lead.lead_code,
        customer_name: lead.customer_name,
        lead_status: lead.status,
        platform: "messenger",
        page_id: null,
        last_message_text: "Hello",
        last_message_at: "2026-06-01T10:00:00+00:00",
        last_message_direction: "inbound",
        unread_count: 0,
        messaging_window_expires_at: "2026-06-02T10:00:00+00:00",
        profile_picture_url: null,
      },
    ],
    next_cursor: null,
  };
}

/** Set up all API mocks and navigate to the karte panel for the given lead. */
async function renderKarte(
  page: Page,
  leadFixture: Record<string, unknown>,
  invoicesFixture: unknown,
) {
  const leadId = leadFixture.id as number;

  await installAuthBypass(page);

  // Lead fixtures contain a "status" field (e.g. "新規") which causes
  // isResponseDetail() in api-mock.ts to misidentify them as MockResponseDetail
  // objects. Wrapping with an explicit route handler avoids this issue.
  const mocks: MockMap = {
    ...commonMocks(),
    "GET /conversations": makeConversations(leadFixture),
    [`GET /leads/${leadId}`]: async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(leadFixture),
      });
    },
    [`GET /leads/${leadId}/messages`]: karteMessages,
    "GET /admin/discord-config": discordConfig,
    "GET /invoices": invoicesFixture,
    [`POST /leads/${leadId}/messages/mark-read`]: { marked_count: 0 },
  };

  await mockApi(page, mocks);
  await page.goto("/lead-chat");

  // Wait for conversation list to render and click the first conversation
  const convItem = page.locator("button.conversation-item").first();
  await expect(convItem).toBeVisible({ timeout: 20_000 });
  await convItem.click();

  // The karte panel is not auto-opened; click the toggle button to open it
  const karteToggle = page.locator('button.karte-toggle-btn');
  await expect(karteToggle).toBeVisible({ timeout: 10_000 });
  await karteToggle.click();

  // Wait for karte panel tab bar to appear
  await page.locator('[data-testid="karte-tab-bar"]').waitFor({ timeout: 10_000 });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe("Karte Visual Gate -- ADR-108/110", () => {

  test.describe("Tab structure (all stages)", () => {

    test("[ADR-110-1] Tab order is deal / company / contact", async ({ page }) => {
      await renderKarte(page, leadShinki, invoicesPaid);

      const tabBar = page.locator('[data-testid="karte-tab-bar"]');
      const tabs = tabBar.locator("button");

      await expect(tabs).toHaveCount(3);

      // Verify order via data-testid
      await expect(tabs.nth(0)).toHaveAttribute("data-testid", "karte-tab-deal");
      await expect(tabs.nth(1)).toHaveAttribute("data-testid", "karte-tab-company");
      await expect(tabs.nth(2)).toHaveAttribute("data-testid", "karte-tab-contact");
    });

    test("[ADR-110-2] Stage badge is displayed in the header", async ({ page }) => {
      await renderKarte(page, leadShinki, invoicesPaid);

      const badge = page.locator('[data-testid="karte-stage-badge"]');
      await expect(badge).toBeVisible();
      // For shinki (new) status, the badge should display the lead stage text
      await expect(badge).not.toHaveText("");
    });

    test("[ADR-110-2] Last contact elapsed is displayed in the header", async ({ page }) => {
      await renderKarte(page, leadShinki, invoicesPaid);

      const lastContact = page.locator('[data-testid="karte-last-contact"]');
      await expect(lastContact).toBeVisible();
    });

    test("[ADR-110-3] Fixed action bar has overflow button", async ({ page }) => {
      // Shinki (new) has a primary action (convert), so the action bar renders
      await renderKarte(page, leadShinki, invoicesPaid);

      const actionBar = page.locator('[data-testid="karte-action-bar"]');
      await expect(actionBar).toBeVisible();

      const overflow = page.locator('[data-testid="karte-action-overflow"]');
      await expect(overflow).toBeVisible();
    });

    test("[ADR-110-6] Performance summary heading has lock icon (read-only distinction)", async ({ page }) => {
      await renderKarte(page, leadShinki, invoicesPaid);

      // Switch to company tab to see the performance summary section
      await page.locator('[data-testid="karte-tab-company"]').click();

      const lockIcon = page.locator('[data-testid="karte-lock-icon"]');
      await expect(lockIcon).toBeVisible({ timeout: 5_000 });
    });
  });

  test.describe("Deal tab -- customer fields must not appear (ADR-108-1)", () => {

    // The app renders in Japanese (i18n fallback: ja). The label texts below
    // are the ja.json values for the customer-section fields that belong to
    // the company tab and must NOT appear on the deal tab.

    test("[ADR-108-1] Deal tab does not show nickname field", async ({ page }) => {
      await renderKarte(page, leadShinki, invoicesPaid);

      // Deal tab is already active (default for shinki)
      const tabContent = page.locator(".right-panel-tab-content");
      // ja.json: leads.nickname = "呼び名"
      // eslint-disable-next-line local/no-japanese-literal -- asserting i18n output
      await expect(tabContent.locator('.right-panel-label:has-text("呼び名")')).not.toBeVisible();
    });

    test("[ADR-108-1] Deal tab does not show country field", async ({ page }) => {
      await renderKarte(page, leadShinki, invoicesPaid);

      const tabContent = page.locator(".right-panel-tab-content");
      // ja.json: leads.country = "国"
      // eslint-disable-next-line local/no-japanese-literal -- asserting i18n output
      await expect(tabContent.locator('.right-panel-label:has-text("国")')).not.toBeVisible();
    });

    test("[ADR-108-1] Deal tab does not show customer_type field", async ({ page }) => {
      await renderKarte(page, leadShinki, invoicesPaid);

      const tabContent = page.locator(".right-panel-tab-content");
      // ja.json: leads.customerType = "顧客タイプ"
      // eslint-disable-next-line local/no-japanese-literal -- asserting i18n output
      await expect(tabContent.locator('.right-panel-label:has-text("顧客タイプ")')).not.toBeVisible();
    });

    test("[ADR-108-1] Deal tab does not show target_titles field", async ({ page }) => {
      await renderKarte(page, leadShinki, invoicesPaid);

      const tabContent = page.locator(".right-panel-tab-content");
      // ja.json: leads.targetTitles = "取り扱いタイトル"
      // eslint-disable-next-line local/no-japanese-literal -- asserting i18n output
      await expect(tabContent.locator('.right-panel-label:has-text("取り扱いタイトル")')).not.toBeVisible();
    });

    test("[ADR-108-1] Deal tab does not show sales_form field", async ({ page }) => {
      await renderKarte(page, leadShinki, invoicesPaid);

      const tabContent = page.locator(".right-panel-tab-content");
      // ja.json: leads.salesForm = "販売形態"
      // eslint-disable-next-line local/no-japanese-literal -- asserting i18n output
      await expect(tabContent.locator('.right-panel-label:has-text("販売形態")')).not.toBeVisible();
    });
  });

  test.describe("Company tab -- 4 sections (ADR-110-4)", () => {

    test("[ADR-110-4] Company tab has Basic section heading", async ({ page }) => {
      await renderKarte(page, leadShinki, invoicesPaid);
      await page.locator('[data-testid="karte-tab-company"]').click();

      await expect(
        page.locator('[data-testid="karte-section-basic-heading"]'),
      ).toBeVisible({ timeout: 5_000 });
    });

    test("[ADR-110-4] Company tab has Trade Profile section heading", async ({ page }) => {
      await renderKarte(page, leadShinki, invoicesPaid);
      await page.locator('[data-testid="karte-tab-company"]').click();

      await expect(
        page.locator('[data-testid="karte-section-deal-profile-heading"]'),
      ).toBeVisible({ timeout: 5_000 });
    });

    test("[ADR-110-4] Company tab has Performance Summary section heading (read-only)", async ({ page }) => {
      await renderKarte(page, leadShinki, invoicesPaid);
      await page.locator('[data-testid="karte-tab-company"]').click();

      await expect(
        page.locator('[data-testid="karte-section-ro-heading"]'),
      ).toBeVisible({ timeout: 5_000 });
    });

    test("[ADR-110-4] Company tab has Handover section heading", async ({ page }) => {
      await renderKarte(page, leadShinki, invoicesPaid);
      await page.locator('[data-testid="karte-tab-company"]').click();

      await expect(
        page.locator('[data-testid="karte-section-handover-heading"]'),
      ).toBeVisible({ timeout: 5_000 });
    });
  });

  test.describe("Performance summary -- no deals (ADR-110-5 / ADR-108-6)", () => {

    test('[ADR-110-5] With 0 invoices, "No transaction history" is displayed', async ({ page }) => {
      await renderKarte(page, leadShinkiNoDeal, invoicesEmpty);
      await page.locator('[data-testid="karte-tab-company"]').click();

      const perfSection = page.locator('[data-testid="karte-performance-section"]');
      await expect(perfSection).toBeVisible({ timeout: 10_000 });

      // Wait for loading to complete (the "..." disappears)
      await expect(perfSection.getByText("...")).not.toBeVisible({ timeout: 10_000 });

      // Check for the "no history" text. The i18n value in ja.json is "取引実績なし"
      // and en.json is "No transaction history". Since the app defaults to Japanese locale,
      // we check for the Japanese text.
      // eslint-disable-next-line local/no-japanese-literal -- asserting i18n output
      await expect(perfSection.getByText("取引実績なし")).toBeVisible();
    });
  });

  test.describe("Default tab switching (ADR-108-4)", () => {

    test("[ADR-108-4] Lead (shinki) defaults to deal tab", async ({ page }) => {
      await renderKarte(page, leadShinki, invoicesPaid);

      const dealTab = page.locator('[data-testid="karte-tab-deal"]');
      await expect(dealTab).toHaveClass(/active/);
    });

    test("[ADR-108-4] Shoudanchuu defaults to deal tab", async ({ page }) => {
      await renderKarte(page, leadShoudanchuu, invoicesPaid);

      const dealTab = page.locator('[data-testid="karte-tab-deal"]');
      await expect(dealTab).toHaveClass(/active/);
    });

    test("[ADR-108-4] Existing customer defaults to company tab", async ({ page }) => {
      await renderKarte(page, leadKisonkosaku, invoicesPaid);

      const companyTab = page.locator('[data-testid="karte-tab-company"]');
      await expect(companyTab).toHaveClass(/active/);
    });

    test("[ADR-108-4] Oikomi (follow-up) defaults to company tab", async ({ page }) => {
      await renderKarte(page, leadOikomi, invoicesPaid);

      const companyTab = page.locator('[data-testid="karte-tab-company"]');
      await expect(companyTab).toHaveClass(/active/);
    });
  });

  test.describe("Contact tab -- no manual URL input (ADR-108-8)", () => {

    test("[ADR-108-8] Contact tab has no URL input field", async ({ page }) => {
      await renderKarte(page, leadShinki, invoicesPaid);
      await page.locator('[data-testid="karte-tab-contact"]').click();

      // Wait for contact tab to render
      await expect(page.locator(".right-panel-section")).toBeVisible({ timeout: 5_000 });

      // No input[type="url"] should exist in the tab content
      const urlInputs = page.locator('.right-panel-tab-content input[type="url"]');
      await expect(urlInputs).toHaveCount(0);
    });

    test("[ADR-108-8] When discord_guild_channel_id is null, no discord link is shown", async ({ page }) => {
      // leadShinki has discord_guild_channel_id: null
      await renderKarte(page, leadShinki, invoicesPaid);
      await page.locator('[data-testid="karte-tab-contact"]').click();

      // Wait for contact tab to render
      await expect(page.locator(".right-panel-section")).toBeVisible({ timeout: 5_000 });

      // The "Not linked" badge for Meta channels should be visible
      // eslint-disable-next-line local/no-japanese-literal -- asserting i18n output
      await expect(page.getByText("未連携")).toBeVisible();
    });
  });

  test.describe("Forbidden items (ADR-110-8/9)", () => {

    test('[ADR-110-8] Text "追加予定" does not appear on screen', async ({ page }) => {
      await renderKarte(page, leadShinki, invoicesPaid);

      // Check all three tabs
      // eslint-disable-next-line local/no-japanese-literal -- asserting absence of forbidden text
      await expect(page.getByText("追加予定")).not.toBeVisible();

      await page.locator('[data-testid="karte-tab-company"]').click();
      // eslint-disable-next-line local/no-japanese-literal -- asserting absence of forbidden text
      await expect(page.getByText("追加予定")).not.toBeVisible();

      await page.locator('[data-testid="karte-tab-contact"]').click();
      // eslint-disable-next-line local/no-japanese-literal -- asserting absence of forbidden text
      await expect(page.getByText("追加予定")).not.toBeVisible();
    });

    test('[ADR-110-8] Text "担当者" does not appear on screen', async ({ page }) => {
      await renderKarte(page, leadShinki, invoicesPaid);

      // Check all three tabs
      // eslint-disable-next-line local/no-japanese-literal -- asserting absence of forbidden text
      await expect(page.getByText("担当者")).not.toBeVisible();

      await page.locator('[data-testid="karte-tab-company"]').click();
      // eslint-disable-next-line local/no-japanese-literal -- asserting absence of forbidden text
      await expect(page.getByText("担当者")).not.toBeVisible();

      await page.locator('[data-testid="karte-tab-contact"]').click();
      // eslint-disable-next-line local/no-japanese-literal -- asserting absence of forbidden text
      await expect(page.getByText("担当者")).not.toBeVisible();
    });
  });
});
