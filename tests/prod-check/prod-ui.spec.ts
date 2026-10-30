/**
 * 本番の画面点検 S1〜S8（見るだけ。書き込み操作はしない）
 *
 * 各 test 名は通知文にそのまま出る。何が壊れたか分かる名前にする。
 */

import type { Page } from "@playwright/test";
import { test, expect, SKIP_REASON } from "./fixtures";
import { creds, login, signOut } from "./login";

const NO_ERROR_BANNER = ".error-banner";

// API の返事そのものを待つ。goto/click/fill の「前」に呼んで、あとで await する（返事の取りこぼし防止）
function apiOk(page: Page, pathRe: RegExp) {
  return page.waitForResponse(
    (r) => r.request().method() === "GET" && pathRe.test(new URL(r.url()).pathname),
    { timeout: 20_000 },
  );
}
const COMPANIES_API = /^\/api\/v1\/companies$/;
const LEADS_API = /^\/api\/v1\/leads$/;
const COMPANY_DETAIL_API = /^\/api\/v1\/companies\/[^/]+$/;

test.describe("本番の画面点検", () => {
  test("S1 画面が開く（ログイン画面）", async ({ page }) => {
    const res = await page.goto("/login");
    expect(res?.status(), "ログイン画面の応答").toBe(200);
    await expect(page.getByLabel("メールアドレス")).toBeVisible();
    await expect(page.getByLabel("パスワード", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "ログイン" })).toBeVisible();
  });

  test("S2 ログイン", async ({ page }) => {
    const c = creds();
    test.skip(!c, SKIP_REASON);
    const { email, password } = c!;
    await login(page, email, password);
    await expect(page).toHaveURL(/\/(dashboard)?$/);
  });

  test("S3 ダッシュボードにエラーが出ない", async ({ authedPage: page }) => {
    // ログイン済みの page を作ったあとから数える（/login を開いたときの refresh 401 は正常な動き）
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    await page.goto("/");
    // 画面は常時接続（新着の知らせ）を持つため networkidle にならない。読み込み完了＋5秒の間に出たエラーを数える
    await page.waitForLoadState("load");
    await expect(page.locator("main")).toBeVisible();
    await page.waitForTimeout(5_000);
    expect(errors, `console.error が ${errors.length} 件`).toHaveLength(0);
  });

  test("S4 会社一覧とリード一覧が開く", async ({ authedPage: page }) => {

    const companies = apiOk(page, COMPANIES_API);
    await page.goto("/crm/companies");
    expect((await companies).status(), "会社一覧の API の応答").toBeLessThan(400);
    await expect(page.getByPlaceholder("顧客名・コードで検索...")).toBeVisible();
    await expect(page.locator(NO_ERROR_BANNER)).toHaveCount(0);
    await expect(page.locator(".error-message")).toHaveCount(0);

    const leads = apiOk(page, LEADS_API);
    await page.goto("/crm/leads");
    expect((await leads).status(), "リード一覧の API の応答").toBeLessThan(400);
    await page.waitForURL((url) => url.pathname === "/crm/leads");
    await expect(page.locator("main")).toBeVisible();
    await expect(page.locator(NO_ERROR_BANNER)).toHaveCount(0);
    await expect(page.locator(".error-message")).toHaveCount(0);
  });

  test("S5 会社一覧の検索", async ({ authedPage: page }) => {
    const first = apiOk(page, COMPANIES_API);
    await page.goto("/crm/companies");
    expect((await first).status(), "会社一覧の API の応答").toBeLessThan(400);
    const box = page.getByPlaceholder("顧客名・コードで検索...");
    await expect(box).toBeVisible();
    const searched = page.waitForResponse(
      (r) => {
        const u = new URL(r.url());
        return r.request().method() === "GET" && COMPANIES_API.test(u.pathname) && u.searchParams.get("search") === "テスト";
      },
      { timeout: 20_000 },
    );
    await box.fill("テスト");
    expect((await searched).status(), "会社検索の API の応答").toBeLessThan(400);
    await expect(box).toHaveValue("テスト");
    await expect(page.locator(NO_ERROR_BANNER)).toHaveCount(0);
  });

  test("S6 会社の詳細が開く", async ({ authedPage: page }) => {
    const list = apiOk(page, COMPANIES_API);
    await page.goto("/crm/companies");
    expect((await list).status(), "会社一覧の API の応答").toBeLessThan(400);
    await expect(page.getByPlaceholder("顧客名・コードで検索...")).toBeVisible();
    await expect(page.locator("main .sa-loading-block")).toHaveCount(0);
    const link = page.locator('main a[href^="/companies/"]').first();
    test.skip((await link.count()) === 0, "会社 0 件");
    const detail = apiOk(page, COMPANY_DETAIL_API);
    await link.click();
    expect((await detail).status(), "会社詳細の API の応答").toBeLessThan(400);
    await page.waitForURL(/\/crm\/companies\/[^/]+$/);
    await expect(page.locator("main .sa-loading-block")).toHaveCount(0);
    await expect(page.locator(NO_ERROR_BANNER)).toHaveCount(0);
    await expect(page.locator("main")).toBeVisible();
  });

  // 点検用の人のメールでは行わない（失敗を重ねると締め出されるため）
  test("S7 間違ったパスワードでは入れない", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("メールアドレス").fill("prod-ui-check-nobody@example.invalid");
    await page.getByLabel("パスワード", { exact: true }).fill("prod-ui-check-wrong-password-0");
    await page.getByRole("button", { name: "ログイン" }).click();
    await expect(page.locator(".error-message")).toBeVisible();
    expect(new URL(page.url()).pathname).toBe("/login");
  });

  test("S8 ログアウト", async ({ page }) => {
    const c = creds();
    test.skip(!c, SKIP_REASON);
    const { email, password } = c!;
    await login(page, email, password);
    await signOut(page);
    await expect(page).toHaveURL(/\/login$/);
  });

  // 通知の試験用。PROD_CHECK_FORCE_FAIL=1 のときだけ足す（必ず落ちる）
  if (process.env.PROD_CHECK_FORCE_FAIL === "1") {
    test("S9 通知の試験（わざと落とす）", async ({ page }) => {
      await page.goto("/login");
      await expect(page.getByText("prod-ui-check-force-fail-zzz")).toBeVisible({ timeout: 3_000 });
    });
  }
});
