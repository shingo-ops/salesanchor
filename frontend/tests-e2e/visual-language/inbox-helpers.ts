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

type ConversationsFixture = {
  conversations: Array<Record<string, unknown>>;
  next_cursor: unknown;
};

/**
 * 件数を増やした会話一覧を作る（第3便・ヘッダー固定検査でスクロールを確実に出すため）。
 * fixture JSON ファイル（mock-conversations.json）は変更せず、その1件目の形をそのまま
 * 複製し、lead_id / lead_code / customer_name だけ一意にずらす。実データの入れ物の
 * キー名（lead_id / lead_code / customer_name / platform / last_message_text /
 * last_message_at / last_message_direction / unread_count /
 * messaging_window_expires_at）は変えない。
 *
 * 件数の根拠（vl-mobile-390 の viewport 390x844・tokens.css の
 * --min-height-conv-item-mobile: 76px）:
 *   画面高 844px のうちヘッダー56px（--topbar-height）＋検索欄56px
 *   （--comp-btn-height-lg 48px＋上下 padding 8px）＝112px を一覧の上で占有する。
 *   残り (844-112)/76 ≈ 9.6 件で画面が埋まる。600px スクロールさせても
 *   下に十分な余りが残るよう、埋まる件数の2倍以上を確保する目的で20件にする。
 */
export function manyConversations(count: number): { conversations: Array<Record<string, unknown>>; next_cursor: null } {
  const base = (conversationsFixture as ConversationsFixture).conversations[0];
  const conversations = Array.from({ length: count }, (_, i) => ({
    ...base,
    lead_id: 9000 + i,
    lead_code: `LEAD-2026-STICKY-${String(i).padStart(4, "0")}`,
    customer_name: `Sticky Header Test ${i}`,
  }));
  return { conversations, next_cursor: null };
}

/** 受信箱を開き、会話一覧の項目が出るまで待つ */
export async function openInboxList(page: Page): Promise<void> {
  await installAuthBypass(page);
  await mockApi(page, baseMocks());
  await page.goto("/lead-chat");
  await expect(page.getByRole("heading", { name: "受信箱" })).toBeVisible({ timeout: 20_000 });
  await expect(page.locator("button.conversation-item").first()).toBeVisible({ timeout: 10_000 });
}

/**
 * 件数を増やした一覧で受信箱を開く（第3便: ヘッダー固定検査専用）。
 * baseMocks() の "GET /conversations" だけ manyConversations(count) に差し替える。
 * 既存の openInboxList は3件のまま変更しない。
 */
export async function openInboxListWithConversations(page: Page, count: number): Promise<void> {
  await installAuthBypass(page);
  await mockApi(page, { ...baseMocks(), "GET /conversations": manyConversations(count) });
  await page.goto("/lead-chat");
  await expect(page.getByRole("heading", { name: "受信箱" })).toBeVisible({ timeout: 20_000 });
  await expect(page.locator("button.conversation-item").first()).toBeVisible({ timeout: 10_000 });
}

/**
 * Discord 未連携の会話（第6便・会話ヘッダー2段表示の検査専用）。
 * baseMocks() の lead 5001 はもともと discord_user_id が null なので、
 * platform だけ "discord" に差し替えれば「messagesData.lead.platform === "discord"
 * && !leadDetail.discord_user_id」（PC の Discord 未連携バッジと同じ式・
 * frontend/src/pages/inbox/InboxMessageThread.tsx）が成立する。
 * 既存の openInboxList() / baseMocks() はそのまま変更しない。
 */
/**
 * 商談段階が "lead" の相手で一覧を開く（第8便・カルテの固定操作バーの検査用）。
 *
 * カルテの固定操作バー（karte-action-bar）は
 * `frontend/src/pages/inbox/InboxKartePanel.tsx` の `if (!primaryLabel) return null;` のとおり、
 * **商談段階が "lead"（または "existing_customer"）のときだけ**描かれる。
 * 既定の仮データ（baseMocks の "GET /leads/5001"）には status が無いため出ない。
 * 既定を変えると他の検査の見え方が変わるので、この検査専用にここで status を足す。
 */
export async function openInboxListWithLeadStatus(page: Page): Promise<void> {
  const base = baseMocks();
  const leadDetail = base["GET /leads/5001"] as Record<string, unknown>;

  await installAuthBypass(page);
  await mockApi(page, {
    ...base,
    "GET /leads/5001": { ...leadDetail, status: "lead" },
  });
  await page.goto("/lead-chat");
  await expect(page.getByRole("heading", { name: "受信箱" })).toBeVisible({ timeout: 20_000 });
  await expect(page.locator("button.conversation-item").first()).toBeVisible({ timeout: 10_000 });
}

export async function openInboxListWithDiscordUnlinkedConversation(page: Page): Promise<void> {
  const base = baseMocks();
  const conversations = (conversationsFixture as ConversationsFixture).conversations.map((c) =>
    c.lead_id === 5001 ? { ...c, platform: "discord" } : c,
  );
  const messages = messagesFixture as { lead: Record<string, unknown> } & Record<string, unknown>;
  const leadDetail = base["GET /leads/5001"] as Record<string, unknown>;

  await installAuthBypass(page);
  await mockApi(page, {
    ...base,
    "GET /conversations": { conversations, next_cursor: null },
    "GET /leads/5001/messages": { ...messages, lead: { ...messages.lead, platform: "discord" } },
    "GET /leads/5001": { ...leadDetail, platform: "discord" },
  });
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
