/**
 * mobile-shell.spec.ts — KGI-2: MobileShell 成立検証（PR-R2-C）
 *
 * ADR-137: 767px 以下で MobileShell が表示される。
 *   useIsMobile() が true → MobileShell DOM（.mobile-topbar / .mobile-drawer）が存在する。
 *
 * 検証内容:
 *   - 375×812 で .mobile-topbar が表示される
 *   - sidebar-panel が DOM に存在しない
 *   - hamburger クリック → MobileDrawer が開く
 *   - backdrop クリック → MobileDrawer が閉じる
 *   - Escape キー → MobileDrawer が閉じる
 *   - nav item クリック → MobileDrawer が閉じる
 *   - avatar クリック → user-drawer--open が付与される
 */

import { expect, test } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi } from "./utils/api-mock";
import { commonMocks } from "./utils/common-mocks";

const MOBILE_VIEWPORT = { width: 375, height: 812 };

function dashboardMock() {
  return {
    "GET /analytics/followups": { overdue: [], due_today: [], upcoming: [], stalled: [] },
    "GET /analytics/forecast": { forecast_amount: 0, won_amount: 0, open_deal_count: 0, period_start: "2026-06-01", period_end: "2026-06-30" },
    "GET /analytics/stalled-deals": { stalled_count: 0, stalled_deals: [] },
    "GET /analytics/monthly-revenue": { granularity: "monthly", entries: [] },
    "GET /goals/summary": { monthly: [], weekly: [] },
    "GET /conversations": { conversations: [], total: 0 },
  };
}

test.describe("MobileShell KGI-2 検証（375×812）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await installAuthBypass(page);
    await mockApi(page, { ...commonMocks(), ...dashboardMock() });
    await page.goto("/");
    await page.waitForLoadState("networkidle");
  });

  test(".mobile-topbar が DOM に存在し可視である", async ({ page }) => {
    const topbar = page.locator(".mobile-topbar");
    await expect(topbar).toBeVisible({ timeout: 10_000 });
  });

  test("DesktopShell 固有要素（#sidebar-panel）が DOM に存在しない", async ({ page }) => {
    const sidebar = page.locator("#sidebar-panel");
    await expect(sidebar).not.toBeAttached();
  });

  test("hamburger / title / avatar が重ならない（BoundingRect が独立している）", async ({ page }) => {
    const hamburger = page.locator(".mobile-topbar-hamburger");
    const title = page.locator(".mobile-topbar-title");
    const avatar = page.locator(".mobile-topbar-avatar");

    await expect(hamburger).toBeVisible({ timeout: 10_000 });
    await expect(title).toBeVisible();
    await expect(avatar).toBeVisible();

    const hBox = await hamburger.boundingBox();
    const tBox = await title.boundingBox();
    const aBox = await avatar.boundingBox();

    expect(hBox).not.toBeNull();
    expect(tBox).not.toBeNull();
    expect(aBox).not.toBeNull();

    // hamburger と title が重ならない（right of hamburger < left of title）
    expect(hBox!.x + hBox!.width).toBeLessThanOrEqual(tBox!.x + 8);
    // title と avatar が重ならない（right of title ≤ left of avatar）
    expect(tBox!.x + tBox!.width).toBeLessThanOrEqual(aBox!.x + 8);
  });

  test("hamburger クリックで MobileDrawer が開く", async ({ page }) => {
    const hamburger = page.locator(".mobile-topbar-hamburger");
    await hamburger.click();

    const drawer = page.locator(".mobile-drawer--open");
    await expect(drawer).toBeVisible({ timeout: 5_000 });
  });

  test("MobileDrawer 開いた後に backdrop クリックで閉じる", async ({ page }) => {
    const hamburger = page.locator(".mobile-topbar-hamburger");
    await hamburger.click();

    const drawer = page.locator(".mobile-drawer--open");
    await expect(drawer).toBeVisible({ timeout: 5_000 });

    const backdrop = page.locator(".mobile-drawer-backdrop");
    // mobile-drawer (z-index:210) が backdrop (z-index:200) の前面にあるため、
    // drawer 幅（240px）の外側（375px viewport の右端付近）をクリックする。
    await backdrop.click({ position: { x: 320, y: 400 } });
    await expect(drawer).not.toBeVisible({ timeout: 3_000 });
  });

  test("MobileDrawer 開いた後に Escape キーで閉じる", async ({ page }) => {
    const hamburger = page.locator(".mobile-topbar-hamburger");
    await hamburger.click();

    const drawer = page.locator(".mobile-drawer--open");
    await expect(drawer).toBeVisible({ timeout: 5_000 });

    await page.keyboard.press("Escape");
    await expect(drawer).not.toBeVisible({ timeout: 3_000 });
  });

  test("MobileDrawer 内の閉じボタンでドロワーが閉じる", async ({ page }) => {
    const hamburger = page.locator(".mobile-topbar-hamburger");
    await hamburger.click();

    const drawer = page.locator(".mobile-drawer--open");
    await expect(drawer).toBeVisible({ timeout: 5_000 });

    const closeBtn = page.locator(".mobile-drawer-close");
    await closeBtn.click();
    await expect(drawer).not.toBeVisible({ timeout: 3_000 });
  });

  test("avatar クリックで user-drawer--open が付与される", async ({ page }) => {
    const avatar = page.locator(".mobile-topbar-avatar");
    await expect(avatar).toBeVisible({ timeout: 10_000 });
    await avatar.click();

    const userDrawer = page.locator(".user-drawer--open");
    await expect(userDrawer).toBeVisible({ timeout: 5_000 });
  });

  test("avatar クリックで表示された user-drawer が close ボタン直接クリックで閉じる", async ({ page }) => {
    const avatar = page.locator(".mobile-topbar-avatar");
    await avatar.click();

    const userDrawer = page.locator(".user-drawer--open");
    await expect(userDrawer).toBeVisible({ timeout: 5_000 });

    // mobile-topbar-avatar は in-flow（position: fixed 不使用）なので
    // user-drawer-close ボタンを直接クリックできる。
    const closeBtn = page.locator(".user-drawer-close");
    await closeBtn.click();
    await expect(userDrawer).not.toBeVisible({ timeout: 3_000 });
  });
});

test.describe("MobileShell KGI-2 検証（390×844）", () => {
  test("390×844 でも MobileShell が表示される", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await installAuthBypass(page);
    await mockApi(page, { ...commonMocks(), ...dashboardMock() });
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    const topbar = page.locator(".mobile-topbar");
    await expect(topbar).toBeVisible({ timeout: 10_000 });
    const sidebar = page.locator("#sidebar-panel");
    await expect(sidebar).not.toBeAttached();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// CSS 検証: nav-item-list__item が青いデフォルトリンクでないこと
// fix/morimoto/mobile-nav-css で追加（.nav-item-list__* CSS 欠落修正）
// ────────────────────────────────────────────────────────────────────────────

test.describe("MobileShell nav-item-list CSS 検証（375×812）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await installAuthBypass(page);
    await mockApi(page, { ...commonMocks(), ...dashboardMock() });
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    // ドロワーを開く
    await page.locator(".mobile-topbar-hamburger").click();
    await page.waitForSelector(".mobile-drawer--open", { timeout: 5_000 });
    await page.waitForSelector(".nav-item-list__item", { timeout: 5_000 });
  });

  test("最初の nav-item-list__item が青いデフォルトリンク（text-decoration）でないこと", async ({
    page,
  }) => {
    const firstItem = page.locator(".nav-item-list__item").first();
    await expect(firstItem).toBeVisible();

    const textDecorationLine = await firstItem.evaluate(
      (el) => getComputedStyle(el).textDecorationLine,
    );
    expect(textDecorationLine).toBe("none");
  });

  test("最初の nav-item-list__item が display:flex（横並びレイアウト）であること", async ({
    page,
  }) => {
    const firstItem = page.locator(".nav-item-list__item").first();
    const display = await firstItem.evaluate(
      (el) => getComputedStyle(el).display,
    );
    expect(display).toBe("flex");
  });

  test("最初の nav-item-list__item のタップターゲット高さが 44px 以上であること（WCAG 2.5.5）", async ({
    page,
  }) => {
    const firstItem = page.locator(".nav-item-list__item").first();
    const box = await firstItem.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.height).toBeGreaterThanOrEqual(44);
  });

  test("ドロワー内のすべての nav 項目がドロワー幅内に収まること（横スクロールなし）", async ({
    page,
  }) => {
    const drawerWidth = await page
      .locator(".mobile-drawer")
      .evaluate((el) => el.getBoundingClientRect().width);

    const items = page.locator(".nav-item-list__item");
    const count = await items.count();
    for (let i = 0; i < count; i++) {
      const box = await items.nth(i).boundingBox();
      if (!box) continue;
      // 各アイテムの右端がドロワー幅内に収まること（1px 誤差許容）
      expect(box.x + box.width).toBeLessThanOrEqual(drawerWidth + 1);
    }
  });
});
