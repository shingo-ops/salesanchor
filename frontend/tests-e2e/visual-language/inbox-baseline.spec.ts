/**
 * visual-language/inbox-baseline.spec.ts — 受信箱の3幅ベースライン計測（段階1・測るだけ）
 *
 * 実行は vl-mobile-390 / vl-tablet-768 / vl-desktop-1280 の project のみ（playwright.config.ts）。
 * 記録のみで、はみ出し・44px未満の部品があっても失敗にしない。
 * 失敗にするのは「画面が開かない（待っている要素が出ない）」ときだけ。
 *
 *   cd frontend && npx playwright test --project=vl-mobile-390 --project=vl-tablet-768 --project=vl-desktop-1280
 */

import { expect, test } from "@playwright/test";
import type { Page, TestInfo } from "@playwright/test";
import { installAuthBypass } from "../utils/auth";
import { mockApi } from "../utils/api-mock";
import { commonMocks } from "../utils/common-mocks";
import { loadFixture } from "../utils/fixtures";

const conversationsFixture = loadFixture("mock-conversations.json");
const messagesFullFixture = loadFixture<Record<string, unknown>>("mock-messages.json");
const messagesFixture = messagesFullFixture["messenger_within_24h"] as Record<string, unknown>;

const MIN_TOUCH_TARGET_PX = 44;
const INTERACTIVE_SELECTOR = 'button, a[href], [role="button"], input, select, textarea';

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

async function openInboxList(page: Page): Promise<void> {
  await installAuthBypass(page);
  await mockApi(page, baseMocks());
  await page.goto("/lead-chat");
  await expect(page.getByRole("heading", { name: "受信箱" })).toBeVisible({ timeout: 20_000 });
  await expect(page.locator("button.conversation-item").first()).toBeVisible({ timeout: 10_000 });
}

async function openConversation(page: Page): Promise<void> {
  await page.locator("button.conversation-item", { hasText: "Taro Sender" }).click();
  await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
}

async function measureOverflow(page: Page) {
  return page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
}

async function measureSmallTargets(page: Page, minPx: number, selector: string) {
  return page.evaluate(
    ({ minPx: min, selector: sel }) => {
      const result: Array<{
        element: string;
        className: string;
        label: string;
        width: number;
        height: number;
      }> = [];
      let visibleCount = 0;
      document.querySelectorAll(sel).forEach((el) => {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        const isVisible =
          rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
        if (!isVisible) return;
        visibleCount += 1;
        if (rect.width >= min && rect.height >= min) return;
        const aria = el.getAttribute("aria-label");
        const text = (el.textContent ?? "").trim().slice(0, 30);
        result.push({
          element: el.tagName.toLowerCase(),
          className: typeof el.className === "string" ? el.className : "",
          label: aria && aria.length > 0 ? aria : text,
          width: Math.round(rect.width * 10) / 10,
          height: Math.round(rect.height * 10) / 10,
        });
      });
      return { visibleCount, smallTargets: result };
    },
    { minPx, selector },
  );
}

/** 3つの区画（会話一覧 / メッセージ表示 / 右のカルテ）が見えているかを selector で測る */
const PANE_SELECTORS = {
  conversationList: ".inbox-conversation-list",
  messageThread: ".inbox-center-header",
  karteRightPanel: ".inbox-right-panel",
} as const;

async function measurePanes(page: Page) {
  const entries = await Promise.all(
    Object.entries(PANE_SELECTORS).map(async ([name, selector]) => {
      const locator = page.locator(selector).first();
      const isVisible = await locator.isVisible();
      const box = await locator.boundingBox();
      return [
        name,
        {
          selector,
          isVisible,
          boundingBox: box
            ? { x: Math.round(box.x), y: Math.round(box.y), width: Math.round(box.width), height: Math.round(box.height) }
            : null,
        },
      ] as const;
    }),
  );
  return Object.fromEntries(entries);
}

async function record(page: Page, testInfo: TestInfo, state: "A" | "B"): Promise<void> {
  // 再読み込み中（一覧が「読み込み中」に戻る瞬間）を撮らないよう、一覧の項目が見えてから測る
  await expect(page.locator("button.conversation-item").first()).toBeVisible({ timeout: 10_000 });
  await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
  const overflow = await measureOverflow(page);
  const targets = await measureSmallTargets(page, MIN_TOUCH_TARGET_PX, INTERACTIVE_SELECTOR);
  const metrics = {
    project: testInfo.project.name,
    state,
    overflow: { ...overflow, diff: overflow.scrollWidth - overflow.innerWidth },
    visibleInteractiveCount: targets.visibleCount,
    smallTargetCount: targets.smallTargets.length,
    smallTargets: targets.smallTargets,
    panes: await measurePanes(page),
  };
  await testInfo.attach("metrics", {
    body: JSON.stringify(metrics, null, 2),
    contentType: "application/json",
  });
  await testInfo.attach("screenshot", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });
}

test.describe("visual-language: inbox baseline", () => {
  test("A: 会話一覧", async ({ page }, testInfo) => {
    await openInboxList(page);
    await record(page, testInfo, "A");
  });

  test("B: 会話を開いた状態", async ({ page }, testInfo) => {
    await openInboxList(page);
    await openConversation(page);
    await record(page, testInfo, "B");
  });
});
