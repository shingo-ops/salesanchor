/**
 * notice-bell.spec.ts — 全画面の右上の鈴（未読数 + 知らせ一覧）。
 * 設計: docs/handoff/in-app-notice-bell/design.md §2 K1〜K3・§7-5。
 * API はモック（GET /notices・POST /notices/{id}/read）。3 幅（390 / 768 / 1280）の project で流れる。
 * 幅によって MobileShell（767px 以下）と DesktopShell（768px 以上）が切り替わるが、鈴はどちらにもある。
 */
import { expect, test } from "@playwright/test";
import type { Page, Route } from "@playwright/test";
import { installAuthBypass } from "../utils/auth";
import { mockApi } from "../utils/api-mock";
import { commonMocks } from "../utils/common-mocks";

interface FakeNotice {
  id: number;
  kind: string;
  actor_name: string;
  channel_name: string;
  link_url: string;
  created_at: string;
  read_at: string | null;
}

function makeNotices(n: number): FakeNotice[] {
  // 新しい順（API の並びと同じ）。id が大きいほど新しい
  return Array.from({ length: n }, (_, i) => {
    const id = n - i;
    return {
      id,
      kind: "discord_outside_ticket_post",
      actor_name: `user-${id}`,
      channel_name: "general",
      link_url: `https://discord.com/channels/1/2/${id}`,
      created_at: new Date(Date.now() - i * 60_000).toISOString(),
      read_at: null,
    };
  });
}

async function setup(page: Page, count: number): Promise<FakeNotice[]> {
  const notices = makeNotices(count);
  const unread = () => notices.filter((n) => !n.read_at).length;

  // window.open の呼び出しを記録する（新しいタブは開かない）
  await page.addInitScript(() => {
    (window as unknown as { __opened: string[] }).__opened = [];
    window.open = ((url?: string | URL) => {
      (window as unknown as { __opened: string[] }).__opened.push(String(url));
      return null;
    }) as typeof window.open;
  });

  await installAuthBypass(page);
  await mockApi(page, {
    ...commonMocks(),
    "GET /conversations": { conversations: [], total: 0 },
    "GET /notices": (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: notices.slice(0, 50), unread_count: unread() }),
      }),
    // API モックは完全一致のみなので、id ごとに既読の口を用意する
    ...Object.fromEntries(
      notices.map((n) => [
        `POST /notices/${n.id}/read`,
        (route: Route) => {
          if (!n.read_at) n.read_at = new Date().toISOString();
          return route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ unread_count: unread() }),
          });
        },
      ]),
    ),
  });
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  return notices;
}

const bell = (page: Page) => page.getByTestId("notice-bell");
const badge = (page: Page) => bell(page).locator(".comp-badge, .mobile-tab-badge");

test.describe("鈴（NoticeBell）", () => {
  test("K1: 未読 3 件 → 鈴に数字 3。開くと 3 行が新しい順に出る", async ({ page }) => {
    await setup(page, 3);
    await expect(bell(page)).toBeVisible({ timeout: 10_000 });
    await expect(badge(page)).toHaveText("3");
    await bell(page).click();
    const rows = page.locator(".notice-row");
    await expect(rows).toHaveCount(3);
    await expect(rows.first()).toContainText("user-3");
    await expect(rows.last()).toContainText("user-1");
  });

  test("K3: 1 行を押すと Discord のリンクを開き、数字が 1 減る。既読の行は押しても変わらない", async ({ page }) => {
    await setup(page, 3);
    await bell(page).click();
    await page.locator(".notice-row").first().click();
    await expect(badge(page)).toHaveText("2");
    const opened = await page.evaluate(() => (window as unknown as { __opened: string[] }).__opened);
    expect(opened).toEqual(["https://discord.com/channels/1/2/3"]);
    // 既読になった行をもう一度押しても数字は 2 のまま
    await page.locator(".notice-row").first().click();
    await expect(badge(page)).toHaveText("2");
  });

  test("0 件: 数字が出ない。開くと「知らせはありません」", async ({ page }) => {
    await setup(page, 0);
    await expect(bell(page)).toBeVisible({ timeout: 10_000 });
    await expect(badge(page)).toHaveCount(0);
    await bell(page).click();
    await expect(page.locator(".notice-panel-empty")).toBeVisible();
    await expect(page.locator(".notice-row")).toHaveCount(0);
  });

  test("K1: 100 件以上は「99+」", async ({ page }) => {
    await setup(page, 100);
    await expect(badge(page)).toHaveText("99+");
  });

  test("スマホ: 鈴は下のタブの中にあり、右上には無い。開くと一覧が鈴の上に出る", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "vl-mobile-390", "390 のみ");
    await setup(page, 3);
    await expect(bell(page)).toBeVisible({ timeout: 10_000 });
    await expect(page.locator(".mobile-tabbar").getByTestId("notice-bell")).toHaveCount(1);
    await expect(page.locator(".top-right-cluster--mobile")).toHaveCount(0);
    await bell(page).click();
    const panel = page.locator(".notice-panel");
    await expect(panel).toBeVisible();
    const bellBox = await bell(page).boundingBox();
    const panelBox = await panel.boundingBox();
    expect(bellBox).not.toBeNull();
    expect(panelBox).not.toBeNull();
    expect(panelBox!.y + panelBox!.height).toBeLessThanOrEqual(bellBox!.y);
  });

  test("PC: 鈴に丸い囲み・枠・影が無く、赤い数字は鈴の絵の右下に重なる（インスタの実測位置）。乗せると色だけ変わる", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "vl-desktop-1280", "1280 のみ");
    await setup(page, 3);
    const btn = page.locator(".notice-bell-btn");
    await expect(btn).toBeVisible({ timeout: 10_000 });
    const style = () =>
      btn.evaluate((el) => {
        const s = getComputedStyle(el);
        return { border: s.borderTopWidth, shadow: s.boxShadow, bg: s.backgroundColor, color: s.color };
      });
    const before = await style();
    expect(before.border).toBe("0px");
    expect(before.shadow).toBe("none");
    expect(before.bg).toBe("rgba(0, 0, 0, 0)");
    await expect(badge(page)).toHaveText("3");
    const b = await btn.boundingBox();
    const g = await badge(page).boundingBox();
    expect(b).not.toBeNull();
    expect(g).not.toBeNull();
    const i = await btn.locator("svg").first().boundingBox();
    expect(i).not.toBeNull();
    expect(i!.width).toBeCloseTo(24, 0);
    expect(i!.height).toBeCloseTo(24, 0);
    expect(g!.x - i!.x).toBeCloseTo(11, 0);
    expect(g!.y - i!.y).toBeCloseTo(9, 0);
    expect(g!.width).toBeCloseTo(22, 0);
    expect(g!.height).toBeCloseTo(22, 0);
    const a = await page.locator(".top-right-cluster .avatar-btn").boundingBox();
    expect(a).not.toBeNull();
    expect(g!.x + g!.width).toBeLessThanOrEqual(a!.x);
    await btn.hover();
    await expect.poll(async () => (await style()).color).not.toBe(before.color);
    expect((await style()).bg).toBe("rgba(0, 0, 0, 0)");
  });

  test("PC: 押さずに乗せるだけで一覧が開き、一覧へ動かしても開いたまま、外へ出すと閉じる", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "vl-desktop-1280", "1280 のみ");
    await setup(page, 3);
    const btn = page.locator(".notice-bell-btn");
    await expect(btn).toBeVisible({ timeout: 10_000 });
    const panel = page.locator(".notice-panel");
    await expect(panel).toHaveCount(0);
    await btn.hover();
    await expect(panel).toBeVisible();
    await page.locator(".notice-row").first().hover();
    await page.waitForTimeout(500);
    await expect(panel).toBeVisible();
    await page.mouse.move(10, 700);
    await expect(panel).toHaveCount(0);
  });
});
