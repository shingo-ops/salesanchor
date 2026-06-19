/**
 * mobile-shell.spec.ts — ADR-140 PR-B: MobileShell 下部タブバー検証
 *
 * ADR-140: MobileShell をハンバーガー+Drawer → 下部タブバー（受信箱・在庫表・受注管理・メニュー）に刷新。
 *
 * KGI 検証:
 *   G1: 375px で横スクロールなし（document.scrollWidth <= window.innerWidth）
 *   G2: 375px で本文が画面全幅（サイドバー分の余白なし）
 *   G3: 下部タブで遷移・「…」でメニュー開閉
 *   G4: タブ各項目・「メニュー」のタップ領域が高さ ≥ 44px
 *   構造1: PC（1280px）でサイドバー等の既存ナビが変化していない
 *   構造3: モバイルで #sidebar-panel が DOM に存在しない
 *
 * 検証幅:
 *   - モバイル: 375×812
 *   - PC: 1280×900
 */

import { expect, test } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi } from "./utils/api-mock";
import { commonMocks } from "./utils/common-mocks";

const MOBILE_VIEWPORT = { width: 375, height: 812 };
const PC_VIEWPORT = { width: 1280, height: 900 };

function mobileShellMocks() {
  const mocks = commonMocks();
  return {
    ...mocks,
    "GET /me/permissions": {
      permissions: [...mocks["GET /me/permissions"].permissions, "orders.view"],
    },
  };
}

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

// ────────────────────────────────────────────────────────────────────────────
// 基本構造（.mobile-topbar / sidebar-panel）
// ────────────────────────────────────────────────────────────────────────────

test.describe("MobileShell 基本構造（375×812）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await installAuthBypass(page);
    await mockApi(page, { ...mobileShellMocks(), ...dashboardMock() });
    await page.goto("/");
    await page.waitForLoadState("networkidle");
  });

  test(".mobile-topbar が DOM に存在し可視である", async ({ page }) => {
    const topbar = page.locator(".mobile-topbar");
    await expect(topbar).toBeVisible({ timeout: 10_000 });
  });

  test("構造3: DesktopShell 固有要素（#sidebar-panel）が DOM に存在しない", async ({ page }) => {
    const sidebar = page.locator("#sidebar-panel");
    await expect(sidebar).not.toBeAttached();
  });

  test(".mobile-tabbar が DOM に存在し可視である", async ({ page }) => {
    const tabbar = page.locator(".mobile-tabbar");
    await expect(tabbar).toBeVisible({ timeout: 10_000 });
  });

  test("下部タブは 4 つでダッシュボードは含まれない", async ({ page }) => {
    const tabs = page.locator(".mobile-tabbar .mobile-tab");
    await expect(tabs).toHaveCount(4);
    await expect(page.locator(".mobile-tabbar a[href='/']")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "メニュー" })).toBeVisible();
  });

  test("390×844 でも MobileShell が表示される", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    const topbar = page.locator(".mobile-topbar");
    await expect(topbar).toBeVisible({ timeout: 10_000 });
    const sidebar = page.locator("#sidebar-panel");
    await expect(sidebar).not.toBeAttached();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// G1: 横スクロールなし（375px）
// ────────────────────────────────────────────────────────────────────────────

test.describe("G1: 375px で横スクロールなし（ADR-140）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await installAuthBypass(page);
    await mockApi(page, { ...mobileShellMocks(), ...dashboardMock() });
  });

  for (const path of ["/", "/lead-chat", "/orders", "/inventory"]) {
    test(`G1: ${path} で横スクロールなし`, async ({ page }) => {
      await mockApi(page, { ...mobileShellMocks(), ...dashboardMock() });
      await page.goto(path);
      await page.waitForLoadState("networkidle");

      const hasOverflow = await page.evaluate(
        () => document.documentElement.scrollWidth > window.innerWidth,
      );
      expect(hasOverflow).toBe(false);
    });
  }
});

// ────────────────────────────────────────────────────────────────────────────
// G2: 本文全幅（サイドバー余白なし）
// ────────────────────────────────────────────────────────────────────────────

test.describe("G2: 375px で本文が画面全幅（ADR-140）", () => {
  test("G2: .mobile-content が viewport 幅とほぼ一致する", async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await installAuthBypass(page);
    await mockApi(page, { ...mobileShellMocks(), ...dashboardMock() });
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    const contentWidth = await page
      .locator(".mobile-content")
      .evaluate((el) => el.getBoundingClientRect().width);

    // viewport幅（375px）に対してサイドバー分の大きな余白がないこと
    // サイドバー幅(54px)以上の乖離がなければOK
    expect(contentWidth).toBeGreaterThanOrEqual(375 - 54);
  });
});

// ────────────────────────────────────────────────────────────────────────────
// G3: タブナビゲーション・メニューシート開閉
// ────────────────────────────────────────────────────────────────────────────

test.describe("G3: タブナビ遷移・メニューシート（ADR-140）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await installAuthBypass(page);
    await mockApi(page, { ...mobileShellMocks(), ...dashboardMock() });
    await page.goto("/");
    await page.waitForLoadState("networkidle");
  });

  test("G3: ダッシュボードは下部タブに無く、メニュー内から / に遷移する", async ({ page }) => {
    await expect(page.locator(".mobile-tabbar a[href='/']")).toHaveCount(0);

    const menuBtn = page.getByRole("button", { name: "メニュー" });
    await menuBtn.click();

    const dashboardLink = page.getByRole("link", { name: "ダッシュボード" });
    await expect(dashboardLink).toBeVisible({ timeout: 10_000 });
    await dashboardLink.click();

    await expect(page).toHaveURL("/", { timeout: 5_000 });
  });

  test("G3: 「メニュー」ボタンクリックで .mobile-more-sheet--open が付与される", async ({ page }) => {
    const menuBtn = page.getByRole("button", { name: "メニュー" });
    await expect(menuBtn).toBeVisible({ timeout: 10_000 });
    await menuBtn.click();

    const sheet = page.locator(".mobile-more-sheet--open");
    await expect(sheet).toBeVisible({ timeout: 5_000 });
  });

  test("G3: メニューシートが開いた後、backdrop クリックで閉じる", async ({ page }) => {
    const menuBtn = page.getByRole("button", { name: "メニュー" });
    await menuBtn.click();

    const sheet = page.locator(".mobile-more-sheet--open");
    await expect(sheet).toBeVisible({ timeout: 5_000 });

    const backdrop = page.locator(".mobile-more-backdrop");
    await backdrop.click({ position: { x: 187, y: 200 } });
    await expect(sheet).not.toBeVisible({ timeout: 3_000 });
  });

  test("G3: メニューシートには 5 項目のリンクがある", async ({ page }) => {
    const menuBtn = page.getByRole("button", { name: "メニュー" });
    await menuBtn.click();

    const sheet = page.locator(".mobile-more-sheet--open");
    await expect(sheet).toBeVisible({ timeout: 5_000 });
    await expect(sheet.locator(".nav-item-list__item")).toHaveCount(5);
  });
});

// ────────────────────────────────────────────────────────────────────────────
// G4: タップ領域 ≥ 44px（WCAG 2.5.5）
// ────────────────────────────────────────────────────────────────────────────

test.describe("G4: タップターゲット ≥ 44px（ADR-140）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await installAuthBypass(page);
    await mockApi(page, { ...mobileShellMocks(), ...dashboardMock() });
    await page.goto("/");
    await page.waitForLoadState("networkidle");
  });

  test("G4: .mobile-tabbar 内の全タブ要素が高さ ≥ 44px", async ({ page }) => {
    const tabs = page.locator(".mobile-tabbar .mobile-tab");
    const count = await tabs.count();
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < count; i++) {
      const box = await tabs.nth(i).boundingBox();
      expect(box).not.toBeNull();
      expect(box!.height).toBeGreaterThanOrEqual(44);
    }
  });

  test("G4: .mobile-tabbar のトップバー全体高さが ≥ 44px", async ({ page }) => {
    const tabbar = page.locator(".mobile-tabbar");
    const box = await tabbar.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.height).toBeGreaterThanOrEqual(44);
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 構造1: PC（1280px）でサイドバー等の既存ナビが変化していない
// ────────────────────────────────────────────────────────────────────────────

test.describe("構造1: PC（1280px）でサイドバーが存在する（ADR-140）", () => {
  test("構造1: 1280px で #sidebar-panel が DOM に存在し可視", async ({ page }) => {
    await page.setViewportSize(PC_VIEWPORT);
    await installAuthBypass(page);
    await mockApi(page, { ...mobileShellMocks(), ...dashboardMock() });
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    const sidebar = page.locator("#sidebar-panel");
    await expect(sidebar).toBeAttached({ timeout: 10_000 });
  });

  test("構造1: 1280px で .mobile-tabbar が DOM に存在しない", async ({ page }) => {
    await page.setViewportSize(PC_VIEWPORT);
    await installAuthBypass(page);
    await mockApi(page, { ...mobileShellMocks(), ...dashboardMock() });
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    const tabbar = page.locator(".mobile-tabbar");
    await expect(tabbar).not.toBeAttached();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// CSS 検証: nav-item-list__item スタイル（メニューシート内）
// ────────────────────────────────────────────────────────────────────────────

test.describe("MobileShell more-sheet nav-item-list CSS 検証（375×812）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await installAuthBypass(page);
    await mockApi(page, { ...mobileShellMocks(), ...dashboardMock() });
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    // メニューシートを開く
    await page.getByRole("button", { name: "メニュー" }).click();
    await page.waitForSelector(".mobile-more-sheet--open", { timeout: 5_000 });
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
});
