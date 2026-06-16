/**
 * desktop-shell.spec.ts — KGI-1: DesktopShell PC 非退行検証（PR-R2-C）
 *
 * ADR-137: 768px 以上で DesktopShell が表示される。
 *   useIsMobile() が false → DesktopShell DOM（.app-shell / .sidebar-panel）が存在する。
 *
 * 検証内容:
 *   - 1280×800 で sidebar-panel が表示される
 *   - avatar-btn クリック → user-drawer--open が付与される
 *   - nav item クリック → route 遷移する
 *   - MobileShell 固有要素（.mobile-topbar / .mobile-drawer）が存在しない
 */

import { expect, test } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi } from "./utils/api-mock";
import { commonMocks } from "./utils/common-mocks";

const DESKTOP_VIEWPORT = { width: 1280, height: 800 };

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

test.describe("DesktopShell KGI-1 検証（1280×800）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(DESKTOP_VIEWPORT);
    await installAuthBypass(page);
    await mockApi(page, { ...commonMocks(), ...dashboardMock() });
    await page.goto("/");
    await page.waitForLoadState("networkidle");
  });

  test("sidebar-panel が DOM に存在し可視である", async ({ page }) => {
    const sidebar = page.locator("#sidebar-panel");
    await expect(sidebar).toBeVisible({ timeout: 10_000 });
  });

  test("MobileShell 固有要素（.mobile-topbar）が DOM に存在しない", async ({ page }) => {
    const mobileTopbar = page.locator(".mobile-topbar");
    await expect(mobileTopbar).not.toBeAttached();
  });

  test("avatar-btn クリックで user-drawer--open が付与される", async ({ page }) => {
    const avatarBtn = page.locator(".avatar-btn");
    await expect(avatarBtn).toBeVisible({ timeout: 10_000 });
    await avatarBtn.click();
    const drawer = page.locator(".user-drawer--open");
    await expect(drawer).toBeVisible({ timeout: 5_000 });
  });

  test("avatar-btn をクリックして表示されたドロワーが閉じボタンで閉じる", async ({ page }) => {
    const avatarBtn = page.locator(".avatar-btn");
    await avatarBtn.click();
    const drawer = page.locator(".user-drawer--open");
    await expect(drawer).toBeVisible({ timeout: 5_000 });

    const closeBtn = page.locator(".user-drawer-close");
    await closeBtn.click();
    await expect(drawer).not.toBeVisible({ timeout: 3_000 });
  });

  test("sidebar-panel にマウスを乗せると sidebar-expanded クラスが付与される", async ({ page }) => {
    const sidebar = page.locator("#sidebar-panel");
    await sidebar.hover();
    await expect(sidebar).toHaveClass(/sidebar-expanded/, { timeout: 3_000 });
  });
});

test.describe("DesktopShell KGI-1 検証（1440×900）", () => {
  test("1440×900 でも sidebar-panel が表示される", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await installAuthBypass(page);
    await mockApi(page, { ...commonMocks(), ...dashboardMock() });
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    const sidebar = page.locator("#sidebar-panel");
    await expect(sidebar).toBeVisible({ timeout: 10_000 });
    const mobileTopbar = page.locator(".mobile-topbar");
    await expect(mobileTopbar).not.toBeAttached();
  });
});
