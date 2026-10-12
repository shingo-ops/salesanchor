/**
 * visual-language/inbox-baseline.spec.ts — 受信箱の3幅ベースライン計測（段階1・測るだけ）
 *
 * 実行は vl-mobile-390 / vl-tablet-768 / vl-desktop-1280 の project のみ（playwright.config.ts）。
 * 合否を出す検査は inbox-single-column.spec.ts（開く→戻るの構造）にある。
 * 記録のみで、はみ出し・44px未満の部品があっても失敗にしない。
 * 失敗にするのは「画面が開かない（待っている要素が出ない）」ときだけ。
 *
 *   cd frontend && npm run test:e2e:vl
 */

import { expect, test } from "@playwright/test";
import type { Page, TestInfo } from "@playwright/test";
import {
  MIN_TOUCH_TARGET_PX,
  isSingleColumn,
  openConversation,
  openInboxList,
} from "./inbox-helpers";

const INTERACTIVE_SELECTOR = 'button, a[href], [role="button"], input, select, textarea';

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
      // boundingBox() は要素が見えるまで待つ（見えないと actionTimeout で失敗する）。
      // スマホの状態Aでは会話側の区画が存在しないため、見えているときだけ測る。
      const box = isVisible ? await locator.boundingBox() : null;
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
  // 再読み込み中（一覧が「読み込み中」に戻る瞬間）を撮らないよう、見えるべきものが出てから測る。
  // 状態A（会話未選択）は入力欄が存在しない（InboxMessageThread は empty-state を返す）。
  // 状態B のスマホは1画面1ページなので一覧が消えている。待つ対象を状態と幅で切り替える。
  const singleColumn = await isSingleColumn(page);
  if (state === "A" || !singleColumn) {
    await expect(page.locator("button.conversation-item").first()).toBeVisible({ timeout: 10_000 });
  }
  if (state === "B") {
    await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
  }
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
