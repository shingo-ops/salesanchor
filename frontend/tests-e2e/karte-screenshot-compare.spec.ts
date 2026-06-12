/**
 * Phase 5a 目視確認用 比較スクリーンショット生成
 *
 * toHaveScreenshot() は使わない（ベースライン比較なし）。
 * アプリ描画と karte_reference.html を PNG 化して CI アーティファクトに保存し、
 * Shingo の「見本どおり」承認の判断材料にする。
 * 承認後に Phase 5b で toHaveScreenshot() ベースラインを確定する。
 *
 * 出力: frontend/screenshots/compare/*.png
 * CI artifact: karte-compare-screenshots（retention 14日）
 */

import { test, type Page } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi, type MockMap } from "./utils/api-mock";
import { commonMocks } from "./utils/common-mocks";
import { loadFixture } from "./utils/fixtures";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

// ESM __dirname equivalent
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ── fixtures ─────────────────────────────────────────────────────────────────
// leadShinki (新規) → deal tab default
// leadKisonkosaku (既存顧客) → company tab default
const leadShinki      = loadFixture("karte-lead-shinki-with-deal.json") as Record<string, unknown>;
const leadKisonkosaku = loadFixture("karte-lead-kisonkosaku-with-deal.json") as Record<string, unknown>;
const invoicesPaid    = loadFixture("karte-invoices-paid.json");
const discordConfig   = loadFixture("karte-discord-config.json");
const karteMessages   = loadFixture("karte-messages.json");

// ── helper ────────────────────────────────────────────────────────────────────
function makeConversations(lead: Record<string, unknown>) {
  return {
    conversations: [{
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
    }],
    next_cursor: null,
  };
}

async function openKartePanel(page: Page, lead: Record<string, unknown>): Promise<void> {
  const leadId = lead.id as number;
  await installAuthBypass(page);
  const mocks: MockMap = {
    ...commonMocks(),
    "GET /conversations": makeConversations(lead),
    [`GET /leads/${leadId}`]: async (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(lead) }),
    [`GET /leads/${leadId}/messages`]: karteMessages,
    "GET /admin/discord-config": discordConfig,
    "GET /invoices": invoicesPaid,
    [`POST /leads/${leadId}/messages/mark-read`]: { marked_count: 0 },
  };
  await mockApi(page, mocks);
  await page.goto("/lead-chat");
  await page.locator("button.conversation-item").first().waitFor({ state: "visible", timeout: 20_000 });
  await page.locator("button.conversation-item").first().click();
  const toggle = page.locator("button.karte-toggle-btn");
  if (await toggle.isVisible()) await toggle.click();
  await page.locator('[data-testid="karte-tab-bar"]').waitFor({ timeout: 10_000 });
}

// ── paths ──────────────────────────────────────────────────────────────────────
const OUT_DIR  = path.join(process.cwd(), "screenshots", "compare");
// __dirname = frontend/tests-e2e/ → ../../ = repo root
const REF_HTML = path.resolve(__dirname, "../../docs/adr/karte_reference.html");

test.beforeAll(() => fs.mkdirSync(OUT_DIR, { recursive: true }));
// 1000px height: ヘッダー〜アクションバーが全て収まる高さ（パネル高 ≈ 940px）
test.use({ viewport: { width: 1280, height: 1000 } });

// ── capture tests ─────────────────────────────────────────────────────────────
test.describe("Visual comparison — Phase 5a review", () => {

  test("app: リード ＋ 商談タブ", async ({ page }) => {
    await openKartePanel(page, leadShinki);
    // deal tab is default for shinki; click explicitly to be certain
    await page.locator('[data-testid="karte-tab-deal"]').click();
    // アクションバー表示を確認してからスクロールをリセット
    await page.locator('[data-testid="karte-action-bar"]').waitFor({ state: "visible", timeout: 5_000 });
    await page.locator(".inbox-right-panel").evaluate((el) => { el.scrollTop = 0; });
    await page.waitForTimeout(300);
    await page.locator(".inbox-right-panel").screenshot({
      path: path.join(OUT_DIR, "app-lead-deal.png"),
    });
  });

  test("app: 既存顧客 ＋ 顧客タブ", async ({ page }) => {
    await openKartePanel(page, leadKisonkosaku);
    // company tab is default for kisonkosaku; click explicitly to be certain
    await page.locator('[data-testid="karte-tab-company"]').click();
    // アクションバー表示を確認してからスクロールをリセット
    await page.locator('[data-testid="karte-action-bar"]').waitFor({ state: "visible", timeout: 5_000 });
    await page.locator(".inbox-right-panel").evaluate((el) => { el.scrollTop = 0; });
    await page.waitForTimeout(300);
    await page.locator(".inbox-right-panel").screenshot({
      path: path.join(OUT_DIR, "app-customer-company.png"),
    });
  });

  test("reference HTML: リード ＋ 商談タブ", async ({ page }) => {
    await page.goto(`file://${REF_HTML}`);
    await page.locator("#panel .hd").waitFor({ timeout: 5_000 });
    await page.locator('#seg button[data-stage="lead"]').click();
    await page.waitForTimeout(300);
    await page.locator("#panel").screenshot({
      path: path.join(OUT_DIR, "ref-lead-deal.png"),
    });
  });

  test("reference HTML: 既存顧客 ＋ 顧客タブ", async ({ page }) => {
    await page.goto(`file://${REF_HTML}`);
    await page.locator("#panel .hd").waitFor({ timeout: 5_000 });
    // default: stage=cust, tab=customer — just screenshot
    await page.waitForTimeout(300);
    await page.locator("#panel").screenshot({
      path: path.join(OUT_DIR, "ref-customer-company.png"),
    });
  });

});
