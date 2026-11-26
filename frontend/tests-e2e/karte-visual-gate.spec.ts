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

const leadStatsPaid = loadFixture("karte-lead-stats-paid.json");
const leadStatsEmpty = loadFixture("karte-lead-stats-empty.json");

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
  statsFixture: unknown,
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
    [`GET /leads/${leadId}/stats`]: statsFixture,
    "GET /admin/discord-config": discordConfig,
    [`POST /leads/${leadId}/messages/mark-read`]: { marked_count: 0 },
    "GET /leads/sales-form-options": [
      { id: 1, label: "実店舗", value: "physical_store", sort_order: 1, is_active: true },
      { id: 2, label: "ECサイト", value: "ec_site", sort_order: 2, is_active: true },
      { id: 3, label: "ライブ配信", value: "live_streaming", sort_order: 3, is_active: true },
      { id: 4, label: "卸・代理店", value: "wholesale", sort_order: 4, is_active: true },
      { id: 5, label: "その他", value: "other", sort_order: 5, is_active: true },
    ],
  };

  await mockApi(page, mocks);
  await page.goto("/lead-chat");

  // Wait for conversation list to render and click the first conversation
  const convItem = page.locator("button.conversation-item").first();
  await expect(convItem).toBeVisible({ timeout: 20_000 });
  await convItem.click();

  // On desktop (≥1280px), karte panel is always shown via CSS.
  // On tablet/mobile (≤1279px), a toggle button appears – click it to open the panel.
  const karteToggle = page.locator('button.karte-toggle-btn');
  if (await karteToggle.isVisible()) {
    await karteToggle.click();
  }

  // Wait for karte panel tab bar to appear
  await page.locator('[data-testid="karte-tab-bar"]').waitFor({ timeout: 10_000 });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe("Karte Visual Gate -- ADR-108/110", () => {

  test.describe("Tab structure (all stages)", () => {

    test("[ADR-1089-1] Lead shows tabs deal / contact", async ({ page }) => {
      await renderKarte(page, leadShinki, leadStatsPaid);
      const tabs = page.locator('[data-testid="karte-tab-bar"] button');
      await expect(tabs).toHaveCount(2);
      await expect(tabs.nth(0)).toHaveAttribute("data-testid", "karte-tab-deal");
      await expect(tabs.nth(1)).toHaveAttribute("data-testid", "karte-tab-contact");
    });

    test("[ADR-1089-1] Negotiating shows tabs deal / contact", async ({ page }) => {
      await renderKarte(page, leadShoudanchuu, leadStatsPaid);
      const tabs = page.locator('[data-testid="karte-tab-bar"] button');
      await expect(tabs).toHaveCount(2);
      await expect(tabs.nth(0)).toHaveAttribute("data-testid", "karte-tab-deal");
      await expect(tabs.nth(1)).toHaveAttribute("data-testid", "karte-tab-contact");
    });

    test("[ADR-1089-1] Customer shows tabs company / contact / deal", async ({ page }) => {
      await renderKarte(page, leadKisonkosaku, leadStatsPaid);
      const tabs = page.locator('[data-testid="karte-tab-bar"] button');
      await expect(tabs).toHaveCount(3);
      await expect(tabs.nth(0)).toHaveAttribute("data-testid", "karte-tab-company");
      await expect(tabs.nth(1)).toHaveAttribute("data-testid", "karte-tab-contact");
      await expect(tabs.nth(2)).toHaveAttribute("data-testid", "karte-tab-deal");
    });

    test("[ADR-110-2] Stage badge is displayed in the header", async ({ page }) => {
      await renderKarte(page, leadShinki, leadStatsPaid);

      const badge = page.locator('[data-testid="karte-stage-badge"]');
      await expect(badge).toBeVisible();
      // For shinki (new) status, the badge should display the lead stage text
      await expect(badge).not.toHaveText("");
    });

    test("[ADR-110-2] Last contact elapsed is displayed in the header", async ({ page }) => {
      await renderKarte(page, leadShinki, leadStatsPaid);

      const lastContact = page.locator('[data-testid="karte-last-contact"]');
      await expect(lastContact).toBeVisible();
    });

    test("[ADR-110-3] Fixed action bar has overflow button", async ({ page }) => {
      // Shinki (new) has a primary action (convert), so the action bar renders
      await renderKarte(page, leadShinki, leadStatsPaid);

      const actionBar = page.locator('[data-testid="karte-action-bar"]');
      await expect(actionBar).toBeVisible();

      const overflow = page.locator('[data-testid="karte-action-overflow"]');
      await expect(overflow).toBeVisible();
    });

    test("[ADR-110-6] Performance summary heading has lock icon (read-only distinction)", async ({ page }) => {
      await renderKarte(page, leadKisonkosaku, leadStatsPaid);

      const lockIcon = page.locator('[data-testid="karte-lock-icon"]');
      await expect(lockIcon).toBeVisible({ timeout: 5_000 });
    });
  });

  test.describe("Fields per stage and tab (ADR-1089)", () => {

    // 正本 karteLayout.ts と同じ並び。試験は画面の data-testid で照らす。
    const ALL_FIELDS = [
      "nickname", "country", "customer_type", "target_titles", "sales_form",
      "next_action", "next_action_date", "response_speed", "temperature", "challenge",
      "competitor_check", "estimated_scale", "monthly_forecast", "per_order_amount",
      "monthly_frequency", "meeting_memo", "cs_memo",
    ];

    async function expectFields(page: Page, visible: string[], perfVisible: boolean) {
      const content = page.locator(".right-panel-tab-content");
      for (const f of ALL_FIELDS) {
        const loc = content.locator(`[data-testid="karte-field-${f}"]`);
        if (visible.includes(f)) {
          await expect(loc, `${f} should be visible`).toBeVisible({ timeout: 5_000 });
        } else {
          await expect(loc, `${f} should not exist`).toHaveCount(0);
        }
      }
      const perf = content.locator('[data-testid="karte-performance-section"]');
      if (perfVisible) {
        await expect(perf).toBeVisible({ timeout: 10_000 });
      } else {
        await expect(perf).toHaveCount(0);
      }
    }

    test("[ADR-1089-2] Lead deal tab shows only lead fields", async ({ page }) => {
      await renderKarte(page, leadShinki, leadStatsPaid);
      await expectFields(page, [
        "nickname", "country", "target_titles", "sales_form",
        "next_action", "next_action_date", "response_speed", "temperature", "estimated_scale",
      ], false);
    });

    test("[ADR-1089-2] Negotiating deal tab shows deal fields, no performance / cs_memo", async ({ page }) => {
      await renderKarte(page, leadShoudanchuu, leadStatsPaid);
      await expectFields(page, [
        "nickname", "country", "customer_type", "target_titles", "sales_form",
        "next_action", "next_action_date", "response_speed", "temperature", "challenge",
        "competitor_check", "estimated_scale", "monthly_forecast", "per_order_amount",
        "monthly_frequency", "meeting_memo",
      ], false);
    });

    test("[ADR-1089-2] Customer company tab shows customer fields", async ({ page }) => {
      await renderKarte(page, leadKisonkosaku, leadStatsPaid);
      await expectFields(page, [
        "nickname", "country", "customer_type", "target_titles", "sales_form",
        "next_action", "next_action_date", "cs_memo",
      ], true);
    });

    test("[ADR-1089-2] Customer deal tab shows deal record fields", async ({ page }) => {
      await renderKarte(page, leadKisonkosaku, leadStatsPaid);
      await page.locator('[data-testid="karte-tab-deal"]').click();
      await expectFields(page, [
        "response_speed", "temperature", "challenge", "competitor_check",
        "estimated_scale", "monthly_forecast", "per_order_amount", "monthly_frequency",
        "meeting_memo",
      ], false);
    });

    test("[ADR-1091] Follow-up (oikomi) uses the negotiating layout", async ({ page }) => {
      await renderKarte(page, leadOikomi, leadStatsPaid);
      await expectFields(page, [
        "nickname", "country", "customer_type", "target_titles", "sales_form",
        "next_action", "next_action_date", "response_speed", "temperature", "challenge",
        "competitor_check", "estimated_scale", "monthly_forecast", "per_order_amount",
        "monthly_frequency", "meeting_memo",
      ], false);
    });

    test("[ADR-110-4] Customer company tab has its section headings", async ({ page }) => {
      await renderKarte(page, leadKisonkosaku, leadStatsPaid);
      for (const id of [
        "karte-section-basic-heading", "karte-section-deal-profile-heading",
        "karte-section-next-action-heading", "karte-section-ro-heading",
        "karte-section-handover-heading",
      ]) {
        await expect(page.locator(`[data-testid="${id}"]`)).toBeVisible({ timeout: 5_000 });
      }
    });

    test("[ADR-1089-7] Customer deal tab has no next-action heading", async ({ page }) => {
      await renderKarte(page, leadKisonkosaku, leadStatsPaid);
      await page.locator('[data-testid="karte-tab-deal"]').click();
      await expect(page.locator('[data-testid="karte-section-analysis-heading"]')).toBeVisible({ timeout: 5_000 });
      await expect(page.locator('[data-testid="karte-section-next-action-heading"]')).toHaveCount(0);
    });
  });

  test.describe("Performance summary -- no deals (ADR-110-5 / ADR-108-6)", () => {

    test('[ADR-110-5] With 0 invoices, "No transaction history" is displayed', async ({ page }) => {
      await renderKarte(page, leadKisonkosakuNoDeal, leadStatsEmpty);

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
      await renderKarte(page, leadShinki, leadStatsPaid);

      const dealTab = page.locator('[data-testid="karte-tab-deal"]');
      await expect(dealTab).toHaveClass(/active/);
    });

    test("[ADR-108-4] Shoudanchuu defaults to deal tab", async ({ page }) => {
      await renderKarte(page, leadShoudanchuu, leadStatsPaid);

      const dealTab = page.locator('[data-testid="karte-tab-deal"]');
      await expect(dealTab).toHaveClass(/active/);
    });

    test("[ADR-108-4] Existing customer defaults to company tab", async ({ page }) => {
      await renderKarte(page, leadKisonkosaku, leadStatsPaid);

      const companyTab = page.locator('[data-testid="karte-tab-company"]');
      await expect(companyTab).toHaveClass(/active/);
    });

    test("[ADR-1091] Oikomi (follow-up) defaults to deal tab", async ({ page }) => {
      await renderKarte(page, leadOikomi, leadStatsPaid);

      const dealTab = page.locator('[data-testid="karte-tab-deal"]');
      await expect(dealTab).toHaveClass(/active/);
    });
  });

  test.describe("Contact tab -- no manual URL input (ADR-108-8)", () => {

    test("[ADR-108-8] Contact tab has no URL input field", async ({ page }) => {
      await renderKarte(page, leadShinki, leadStatsPaid);
      await page.locator('[data-testid="karte-tab-contact"]').click();

      // Wait for contact tab to render
      await expect(page.locator(".right-panel-section")).toBeVisible({ timeout: 5_000 });

      // No input[type="url"] should exist in the tab content
      const urlInputs = page.locator('.right-panel-tab-content input[type="url"]');
      await expect(urlInputs).toHaveCount(0);
    });

    test("[ADR-108-8] When discord_guild_channel_id is null, no discord link is shown", async ({ page }) => {
      // leadShinki has discord_guild_channel_id: null
      await renderKarte(page, leadShinki, leadStatsPaid);
      await page.locator('[data-testid="karte-tab-contact"]').click();

      // Wait for contact tab to render
      await expect(page.locator(".right-panel-section")).toBeVisible({ timeout: 5_000 });

      // The "Not linked" badge for Meta channels should be visible
      // eslint-disable-next-line local/no-japanese-literal -- asserting i18n output
      await expect(page.getByText("未連携")).toBeVisible();
    });
  });

  test.describe("Forbidden items (ADR-110-8/9)", () => {

    async function expectAbsentOnAllTabs(page: Page, text: string) {
      const tabs = page.locator('[data-testid="karte-tab-bar"] button');
      const count = await tabs.count();
      for (let i = 0; i < count; i++) {
        await tabs.nth(i).click();
        await expect(page.getByText(text)).not.toBeVisible();
      }
    }

    for (const [label, fixture] of [["lead", leadShinki], ["customer", leadKisonkosaku]] as const) {
      // eslint-disable-next-line local/no-japanese-literal -- test name names the forbidden text
      test(`[ADR-110-8] Text "追加予定" does not appear on screen (${label})`, async ({ page }) => {
        await renderKarte(page, fixture, leadStatsPaid);
        // eslint-disable-next-line local/no-japanese-literal -- asserting absence of forbidden text
        await expectAbsentOnAllTabs(page, "追加予定");
      });

      // eslint-disable-next-line local/no-japanese-literal -- test name names the forbidden text
      test(`[ADR-110-8] Text "担当者" does not appear on screen (${label})`, async ({ page }) => {
        await renderKarte(page, fixture, leadStatsPaid);
        // eslint-disable-next-line local/no-japanese-literal -- asserting absence of forbidden text
        await expectAbsentOnAllTabs(page, "担当者");
      });
    }
  });
});

// ---------------------------------------------------------------------------
// Phase 5b — 視覚回帰ゲート（toHaveScreenshot）
// ---------------------------------------------------------------------------
// ベースラインは ubuntu-latest で workflow_dispatch --update-snapshots を使って生成する。
// Mac 差によるフォント描画ズレで誤検知しないよう、ローカル生成は禁止。
// ---------------------------------------------------------------------------

test.describe("Visual regression — Phase 5b", () => {

  // 1280×900: デスクトップ幅（カルテ常時表示）＋パネル全体が見えるだけの高さ
  test.use({ viewport: { width: 1280, height: 900 } });

  test("[visual] karte-lead-deal: Phase 5a 承認済み描画と一致", async ({ page }) => {
    await renderKarte(page, leadShinki, leadStatsPaid);
    await page.locator('[data-testid="karte-tab-deal"]').click();
    await page.waitForTimeout(300);
    await expect(page.locator(".inbox-right-panel")).toHaveScreenshot("karte-lead-deal.png");
  });

  test("[visual] karte-customer-company: Phase 5a 承認済み描画と一致", async ({ page }) => {
    await renderKarte(page, leadKisonkosaku, leadStatsPaid);
    await page.locator('[data-testid="karte-tab-company"]').click();
    await page.waitForTimeout(300);
    await expect(page.locator(".inbox-right-panel")).toHaveScreenshot("karte-customer-company.png");
  });

});
