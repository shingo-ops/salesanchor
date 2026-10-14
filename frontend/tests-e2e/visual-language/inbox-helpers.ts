/**
 * visual-language/inbox-helpers.ts — 受信箱の画面検査で共通に使う mock と開き方
 *
 * inbox-baseline.spec.ts（測るだけ）と inbox-single-column.spec.ts（合否を出す）の
 * 両方から使う。mock の中身を2か所に分けて書くと片方だけ古くなるため、ここを唯一の置き場にする。
 * このファイルは `.spec.ts` ではないので Playwright のテスト収集対象にはならない。
 */

import { expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import { installAuthBypass } from "../utils/auth";
import { mockApi } from "../utils/api-mock";
import { commonMocks } from "../utils/common-mocks";
import { loadFixture } from "../utils/fixtures";

const conversationsFixture = loadFixture("mock-conversations.json");
const messagesFullFixture = loadFixture<Record<string, unknown>>("mock-messages.json");
const messagesFixture = messagesFullFixture["messenger_within_24h"] as Record<string, unknown>;

/** 検査で開く会話の相手名（mock-conversations.json の lead 5001） */
export const SAMPLE_CONVERSATION_NAME = "Taro Sender";

/** スマホ用レイアウトの境界。tokens.css の --breakpoint-mobile-max と同じ値 */
export const MOBILE_MAX_PX = 767;

/** 押す場所の最小寸法（design.md §10 / WhatsApp 実測の 48dp に対する下限） */
export const MIN_TOUCH_TARGET_PX = 44;

export function baseMocks() {
  return {
    ...commonMocks(),
    "GET /conversations": conversationsFixture,
    "GET /leads/5001/messages": messagesFixture,
    "POST /leads/5001/messages/mark-read": { marked_count: 1 },
    "POST /leads/5001/messages/mark-unread": { unmarked_count: 1 },
    "GET /leads/5001": {
      id: 5001,
      customer_name: SAMPLE_CONVERSATION_NAME,
      platform: "messenger",
      discord_dm_channel_id: null,
      discord_user_id: null,
    },
    "GET /staff/me": {
      id: 1,
      primary_email: "review@salesanchor.jp",
      ui_preferences: {
        dark_mode: false,
        show_chat_menu: true,
        show_sales_menu: true,
        show_settings_menu: true,
        show_admin_menu: true,
        show_sidebar: true,
      },
    },
  };
}

/** 受信箱を開き、会話一覧の項目が出るまで待つ */
export async function openInboxList(page: Page): Promise<void> {
  await installAuthBypass(page);
  await mockApi(page, baseMocks());
  await page.goto("/lead-chat");
  await expect(page.getByRole("heading", { name: "受信箱" })).toBeVisible({ timeout: 20_000 });
  await expect(page.locator("button.conversation-item").first()).toBeVisible({ timeout: 10_000 });
}

/** 会話を1件開き、入力欄が出るまで待つ */
export async function openConversation(page: Page): Promise<void> {
  await page.locator("button.conversation-item", { hasText: SAMPLE_CONVERSATION_NAME }).click();
  await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
}

/** いまの画面幅がスマホ用レイアウト（1画面1ページ）かどうか */
export async function isSingleColumn(page: Page): Promise<boolean> {
  return page.evaluate((max) => window.innerWidth <= max, MOBILE_MAX_PX);
}
