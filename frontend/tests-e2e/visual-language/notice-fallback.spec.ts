/**
 * notice-fallback.spec.ts — 通知の設定ページの区画「担当者がいないときに受け取る人」。
 * 設計: docs/handoff/in-app-notice-bell/design.md §4-改訂2（K9）。API はモック。
 * 区画は notifications.manage を持つ人だけに出る。選んで保存すると PUT で user_ids が送られる。
 */
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { installAuthBypass } from "../utils/auth";
import { mockApi } from "../utils/api-mock";
import { commonMocks } from "../utils/common-mocks";

const CANDIDATES = [
  { user_id: 10, name: "山田 太郎" },
  { user_id: 11, name: "佐藤 花子" },
];

async function setup(page: Page, permissions: string[]): Promise<{ puts: unknown[] }> {
  const state = { selected: [] as number[] };
  const puts: unknown[] = [];
  await installAuthBypass(page);
  await mockApi(page, {
    ...commonMocks(),
    "GET /me/permissions": { permissions },
    "GET /notices": { items: [], unread_count: 0 },
    "GET /notification-channels": [],
    "GET /notification-event-types": [],
    "GET /notice-fallback-recipients": (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          selected: state.selected,
          defaulted_to_owner: state.selected.length === 0,
          candidates: CANDIDATES,
        }),
      }),
    "PUT /notice-fallback-recipients": (route) => {
      const body = route.request().postDataJSON() as { user_ids: number[] };
      puts.push(body);
      state.selected = body.user_ids;
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          selected: state.selected,
          defaulted_to_owner: state.selected.length === 0,
          candidates: CANDIDATES,
        }),
      });
    },
  });
  await page.goto("/management-center/notifications");
  await page.waitForLoadState("networkidle");
  return { puts };
}

test.describe("担当者がいないときに受け取る人（通知の設定）", () => {
  test("notifications.manage があると区画が出て、選んで保存できる", async ({ page }) => {
    const { puts } = await setup(page, ["notifications.view", "notifications.manage"]);
    const section = page.getByTestId("notice-fallback-section");
    await expect(section).toBeVisible({ timeout: 10_000 });

    await page.getByTestId("notice-fallback-select-button").click();
    await page.getByTestId("notice-fallback-select-option-11").check();
    // 選択の一覧（Popover）は選んだあとも開いたままで、外を押すと閉じるので、見出しを押して閉じてから保存を押す
    await section.getByRole("heading").click();
    await expect(page.getByTestId("notice-fallback-select-clear")).toHaveCount(0);
    await page.getByTestId("notice-fallback-save").click();

    await expect(section.getByRole("status")).toBeVisible();
    expect(puts).toEqual([{ user_ids: [11] }]);
  });

  test("notifications.manage が無いと区画は出ない", async ({ page }) => {
    await setup(page, ["notifications.view"]);
    await expect(page.getByTestId("notice-fallback-section")).toHaveCount(0);
  });
});
