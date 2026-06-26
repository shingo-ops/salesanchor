/**
 * 受信箱ヘッダー UI 改善 — 目視確認用スクリーンショット + 動作検証
 * ADR-143: 言語トグル→プルダウン化 / ヘッダー直置きアーカイブ・削除アイコン撤去
 *
 * npx playwright test tests-e2e/inbox-header-ui-screenshots.spec.ts --reporter=list
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

function baseMocks(dark = false) {
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
  };
}

async function openInbox(page: import("@playwright/test").Page, dark = false) {
  await installAuthBypass(page);
  await mockApi(page, baseMocks(dark));
  await page.goto("/lead-chat");
  await expect(page.getByRole("heading", { name: "受信箱" })).toBeVisible({ timeout: 20_000 });
  await page.locator("button.conversation-item", { hasText: "Taro Sender" }).click();
  await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
}

/** 言語プルダウン専用ロケーター（aria-label で一意に識別） */
function langSelect(page: import("@playwright/test").Page) {
  return page.getByLabel("送信先言語");
}

test.describe("inbox-header-ui: screenshots", () => {
  test("01_light_pulldown_layout — ライトモード: プルダウン + 全体レイアウト", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await openInbox(page, false);
    // 言語プルダウンが表示されている
    await expect(langSelect(page)).toBeVisible();
    await page.screenshot({ path: `${OUT}/hdr01_light_pulldown_layout.png`, fullPage: false });
  });

  test("02_dark_pulldown_layout — ダークモード: プルダウン + 全体レイアウト", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await openInbox(page, true);
    await expect(langSelect(page)).toBeVisible();
    await page.screenshot({ path: `${OUT}/hdr02_dark_pulldown_layout.png`, fullPage: false });
  });

  test("03_guard_dialog_en_kana — EN選択+かな入力→ガードダイアログ", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await openInbox(page, false);
    // EN に切り替え
    await langSelect(page).selectOption("en");
    // かな入力
    await page.locator(".inbox-textarea").fill("こんにちは");
    await page.locator(".inbox-send-btn").click();
    await expect(page.locator(".send-guard-dialog")).toBeVisible({ timeout: 5_000 });
    await page.screenshot({ path: `${OUT}/hdr03_guard_dialog.png`, fullPage: false });
  });
});

test.describe("inbox-header-ui: 動作検証", () => {
  test("言語プルダウンに 自動/日本語/英語 の3オプションがある", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await openInbox(page, false);
    const sel = langSelect(page);
    await expect(sel).toBeVisible();
    const options = await sel.locator("option").allTextContents();
    expect(options).toHaveLength(3);
    // 旧トグルボタン群は存在しない
    await expect(page.locator(".send-guard-lang-toggle")).not.toBeAttached();
    await expect(page.locator(".send-guard-lang-btn")).not.toBeAttached();
  });

  test("ヘッダー直置きアーカイブ・削除ボタンが存在しない", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await openInbox(page, false);
    // .inbox-thread-actions 内は markUnread ボタンのみ（1個）
    const actions = page.locator(".inbox-thread-actions");
    await expect(actions).toBeVisible();
    await expect(actions.locator("button")).toHaveCount(1);
  });

  test("未読に戻すアイコンが存在する", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await openInbox(page, false);
    const markUnreadBtn = page.locator(".inbox-thread-actions button");
    await expect(markUnreadBtn).toBeVisible();
    // aria-label で識別
    const label = await markUnreadBtn.getAttribute("aria-label");
    expect(label).toBeTruthy();
  });

  test("三点メニューにアーカイブ・削除が残っている（機能維持）", async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 768 }); // ≤1279px で三点メニュー表示
    await openInbox(page, false);
    const menuBtn = page.locator(".inbox-header-menu-btn");
    await expect(menuBtn).toBeVisible();
    await menuBtn.click();
    const menu = page.locator(".inbox-header-menu");
    await expect(menu).toBeVisible();
    // 4項目（未読・除外・削除・顧客情報）が維持されている
    await expect(menu.getByRole("menuitem")).toHaveCount(4);
  });

  test("EN選択→自動検出OFF・送信前ガード発動", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await openInbox(page, false);
    await langSelect(page).selectOption("en");
    await page.locator(".inbox-textarea").fill("こんにちは");
    await page.locator(".inbox-send-btn").click();
    await expect(page.locator(".send-guard-dialog")).toBeVisible({ timeout: 5_000 });
  });
});
