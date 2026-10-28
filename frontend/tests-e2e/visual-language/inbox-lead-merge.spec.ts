/**
 * visual-language/inbox-lead-merge.spec.ts — 受信箱のカルテから「ほかのリードとまとめる」（ADR-1049）
 *
 * 設計: docs/specs/transaction-flow/lead-merge/design.md §5-5(2)
 *   - 権限ありで項目が出る／leads.delete が無いと出ない（K6）
 *   - 幅 390 でメニュー項目・窓のボタンの高さが MIN_TOUCH_TARGET_PX 以上、横のはみ出し 0（K7）
 *   - 手順1〜3の写真を testInfo.attach（step1-menu / step2-select / step3-confirm）
 *
 * 下見・統合の入口と権限は route で作り物を返す（サーバーには繋がない）。
 */

import { expect, test } from "@playwright/test";
import type { Page, TestInfo } from "@playwright/test";
import { installAuthBypass } from "../utils/auth";
import { mockApi } from "../utils/api-mock";
import {
  MIN_TOUCH_TARGET_PX,
  MOBILE_MAX_PX,
  baseMocks,
  openConversation,
} from "./inbox-helpers";

function projectWidth(testInfo: TestInfo): number {
  const viewport = testInfo.project.use.viewport;
  if (!viewport) throw new Error(`viewport が未設定の project: ${testInfo.project.name}`);
  return viewport.width;
}

const MASTER_CANDIDATE = { id: 5002, lead_code: "LEAD-2026-5002", customer_name: "Master Candidate", status: "lead" };

const PREVIEW = {
  tables: [
    { table: "meta_messages", moved: 3, deleted: 0 },
    { table: "conversation_logs", moved: 2, deleted: 0 },
    { table: "lead_channels", moved: 0, deleted: 1 },
  ],
  fills: [{ field: "email", current: null, new: "taro@example.com" }],
};

/** 商談段階 lead の相手で受信箱を開く。permissions は呼び出し側が決める */
async function openWithPermissions(page: Page, permissions: string[]): Promise<void> {
  const base = baseMocks();
  const leadDetail = base["GET /leads/5001"] as Record<string, unknown>;
  await installAuthBypass(page);
  await mockApi(page, {
    ...base,
    "GET /me/permissions": { permissions },
    "GET /leads/5001": { ...leadDetail, status: "lead", lead_code: "LEAD-2026-5001" },
    "GET /leads": [MASTER_CANDIDATE],
    "POST /leads/5002/merge/preview": PREVIEW,
    "POST /leads/5002/merge": { id: 5002, customer_name: MASTER_CANDIDATE.customer_name, status: "lead" },
  });
  await page.goto("/lead-chat");
  await expect(page.getByRole("heading", { name: "受信箱" })).toBeVisible({ timeout: 20_000 });
  await expect(page.locator("button.conversation-item").first()).toBeVisible({ timeout: 10_000 });
  await openConversation(page);

  // スマホは「顧客情報」ボタン、タブレットは開閉ボタンで開く（デスクトップは常時表示）
  const mobileBtn = page.locator(".inbox-thread-header-mobile-btn[aria-label='顧客情報']");
  if (await mobileBtn.isVisible().catch(() => false)) {
    await mobileBtn.click();
  } else {
    const toggle = page.locator("button.karte-toggle-btn");
    if (await toggle.isVisible().catch(() => false)) await toggle.click();
  }
  await expect(page.locator('[data-testid="karte-action-bar"]')).toBeVisible({ timeout: 10_000 });
  await page.locator('[data-testid="karte-action-overflow"]').click();
}

test.describe("visual-language: 受信箱 カルテからリードをまとめる（ADR-1049）", () => {
  test("権限あり: 「ほかのリードとまとめる」がメニューに出る", async ({ page }) => {
    await openWithPermissions(page, ["leads.delete", "leads.view"]);
    await expect(page.locator('[data-testid="karte-menu-merge"]')).toBeVisible();
  });

  test("権限なし（leads.delete が無い）: 項目が出ない", async ({ page }) => {
    await openWithPermissions(page, ["leads.view"]);
    await expect(page.locator(".karte-overflow-menu")).toBeVisible();
    await expect(page.locator('[data-testid="karte-menu-merge"]')).toHaveCount(0);
  });

  test("3手順の写真と、スマホ幅の高さ・はみ出しの測定", async ({ page }, testInfo) => {
    const isMobile = projectWidth(testInfo) <= MOBILE_MAX_PX;
    await openWithPermissions(page, ["leads.delete", "leads.view"]);

    const item = page.locator('[data-testid="karte-menu-merge"]');
    await expect(item).toBeVisible();
    if (isMobile) {
      const box = await item.boundingBox();
      expect(box, "メニュー項目の矩形が取れない").not.toBeNull();
      expect(box!.height, "メニュー項目の高さが基準未満").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    }
    await testInfo.attach("step1-menu", { body: await page.screenshot(), contentType: "image/png" });

    await item.click();
    // 画面には dialog が複数ある（メニュー・絞り込み等）ので、題名でまとめる窓だけに絞る
    // （題名は src/locales/ja.json の mergeLead.title と同じ文字）
    const dialog = page.getByRole("dialog", { name: "リードをまとめる" });
    await expect(dialog).toBeVisible();
    await dialog.getByText(MASTER_CANDIDATE.customer_name).click();
    await testInfo.attach("step2-select", { body: await page.screenshot(), contentType: "image/png" });

    await dialog.locator(".form-actions button").last().click();
    await expect(dialog.getByText("残す方へ移るもの")).toBeVisible({ timeout: 10_000 });
    await expect(dialog.getByText("taro@example.com")).toBeVisible();
    await testInfo.attach("step3-confirm", { body: await page.screenshot(), contentType: "image/png" });

    if (isMobile) {
      const buttons = dialog.locator(".form-actions button");
      const count = await buttons.count();
      expect(count, "窓のボタンが無い").toBeGreaterThan(0);
      for (let i = 0; i < count; i++) {
        const b = await buttons.nth(i).boundingBox();
        expect(b, "窓のボタンの矩形が取れない").not.toBeNull();
        expect(b!.height, `窓のボタン ${i} の高さが基準未満`).toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
      }
      const overflow = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
      }));
      await testInfo.attach("scroll-width", { body: JSON.stringify(overflow), contentType: "application/json" });
      expect(overflow.scrollWidth, "横にはみ出している").toBeLessThanOrEqual(overflow.clientWidth);
    }
  });
});
