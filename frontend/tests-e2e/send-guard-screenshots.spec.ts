/**
 * 送信ガード Phase A — 目視確認用スクリーンショット撮影スクリプト
 * npx playwright test tests-e2e/send-guard-screenshots.spec.ts --reporter=list
 */

import { expect, test } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi } from "./utils/api-mock";
import { commonMocks } from "./utils/common-mocks";
import { loadFixture } from "./utils/fixtures";
import * as path from "node:path";

const conversationsFixture = loadFixture("mock-conversations.json");
const messagesFullFixture = loadFixture<Record<string, unknown>>("mock-messages.json");
const messagesFixture = messagesFullFixture["messenger_within_24h"] as Record<string, unknown>;

const OUT = path.resolve(import.meta.dirname, "../../qa-screenshots");

function baseMocks() {
  return {
    ...commonMocks(),
    "GET /conversations": conversationsFixture,
    "GET /leads/5001/messages": messagesFixture,
    "POST /leads/5001/messages/mark-read": { marked_count: 1 },
    "GET /leads/5001": {
      id: 5001,
      customer_name: "Taro Sender",
      platform: "messenger",
      discord_dm_channel_id: null,
      discord_user_id: null,
    },
  };
}

async function openInbox(page: import("@playwright/test").Page, dark = false) {
  await installAuthBypass(page);
  await mockApi(page, {
    ...baseMocks(),
    "GET /staff/me": {
      id: 1,
      primary_email: "review@salesanchor.jp",
      ui_preferences: {
        dark_mode: dark,
        show_chat_menu: true,
        show_sales_menu: true,
        show_settings_menu: true,
        show_admin_menu: true,
        show_sidebar: true,
      },
    },
  });
  await page.goto("/lead-chat");
  await expect(page.getByRole("heading", { name: "受信箱" })).toBeVisible({ timeout: 20_000 });
  await page.locator("button.conversation-item", { hasText: "Taro Sender" }).click();
  await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
}

test.describe("screenshots", () => {
  test("01_light_toggle_and_layout — ライトモード: トグル + 全体レイアウト", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await openInbox(page, false);
    // トグルが見えている状態でフルページ
    await expect(page.locator(".send-guard-lang-toggle")).toBeVisible();
    await page.screenshot({ path: `${OUT}/01_light_toggle_layout.png`, fullPage: false });
  });

  test("02_light_dialog — ライトモード: ダイアログ", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await openInbox(page, false);
    const textarea = page.locator(".inbox-textarea");
    await textarea.fill("こんにちは");
    await page.locator(".inbox-send-btn").click();
    await expect(page.locator(".send-guard-dialog")).toBeVisible();
    await page.screenshot({ path: `${OUT}/02_light_dialog.png`, fullPage: false });
  });

  test("03_dark_toggle_and_layout — ダークモード: トグル + 全体レイアウト", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await openInbox(page, true);
    await expect(page.locator(".send-guard-lang-toggle")).toBeVisible();
    await page.screenshot({ path: `${OUT}/03_dark_toggle_layout.png`, fullPage: false });
  });

  test("04_dark_dialog — ダークモード: ダイアログ", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await openInbox(page, true);
    const textarea = page.locator(".inbox-textarea");
    await textarea.fill("こんにちは");
    await page.locator(".inbox-send-btn").click();
    await expect(page.locator(".send-guard-dialog")).toBeVisible();
    await page.screenshot({ path: `${OUT}/04_dark_dialog.png`, fullPage: false });
  });

  test("05_light_toggle_en_active — ライトモード: 英語トグル active 状態", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await openInbox(page, false);
    await page.locator(".send-guard-lang-btn", { hasText: "英語" }).click();
    await expect(page.locator(".send-guard-lang-btn.active")).toContainText("英語");
    // トグル部分をクローズアップ
    const toggle = page.locator(".send-guard-lang-toggle");
    await toggle.screenshot({ path: `${OUT}/05_light_toggle_en_active.png` });
  });

  test("06_dialog_closeup — ダイアログ拡大（ライト）", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await openInbox(page, false);
    await page.locator(".inbox-textarea").fill("テスト送信です");
    await page.locator(".inbox-send-btn").click();
    await expect(page.locator(".send-guard-dialog")).toBeVisible();
    const dialog = page.locator(".send-guard-dialog");
    await dialog.screenshot({ path: `${OUT}/06_dialog_closeup.png` });
  });
});
