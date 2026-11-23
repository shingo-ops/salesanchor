/**
 * visual-language/inbox-page-no-vertical-overflow.spec.ts — 受信箱のページが縦にはみ出さない
 *
 * ヘッダー右端のボタンの吹き出しが位置の基準を持たないと、窓の下に置かれページが縦に伸びる。
 * 根拠: docs/handoff/inbox-header-tooltip-overflow/design.md
 *
 *   cd frontend && npm run test:e2e:vl
 */
import { expect, test } from "@playwright/test";
import { MOBILE_MAX_PX, openInboxList } from "./inbox-helpers";

test.describe("受信箱のページが縦にはみ出さない", () => {
  test("ヘッダーの吹き出し付きボタンに位置の基準があり、ページの高さが窓と同じ", async ({ page }) => {
    const width = page.viewportSize()?.width ?? 0;
    test.skip(width <= MOBILE_MAX_PX, "スマホ幅ではヘッダーのボタンを出さない（InboxPage.tsx の showHeaderActions）");

    await openInboxList(page);

    const tooltipHosts = page.locator(".page-header-actions [data-tooltip]");
    await expect(tooltipHosts.first()).toBeVisible();
    const positions = await tooltipHosts.evaluateAll((els) =>
      els.map((el) => window.getComputedStyle(el).position),
    );
    expect(positions.length).toBeGreaterThan(0);
    expect(positions.filter((p) => p === "static")).toEqual([]);

    const size = await page.evaluate(() => ({
      scrollHeight: document.documentElement.scrollHeight,
      innerHeight: window.innerHeight,
    }));
    expect(size.scrollHeight).toBeLessThanOrEqual(size.innerHeight);
  });
});
