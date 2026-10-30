/**
 * 本番の画面点検 S1〜S8（見るだけ。書き込み操作はしない）
 *
 * 各 test 名は通知文にそのまま出る。何が壊れたか分かる名前にする。
 */

import { test, expect } from "@playwright/test";
import { creds, login, signOut } from "./login";
import { expectSettled, trackApi } from "./settle";

const NO_ERROR_BANNER = ".error-banner";
const SKIP_REASON = "点検用の人の秘密情報が未登録";

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

  test("S3 ダッシュボードにエラーが出ない", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    const api = trackApi(page);
    const c = creds();
    test.skip(!c, SKIP_REASON);
    const { email, password } = c!;
    await login(page, email, password);
    await page.goto("/");
    await expectSettled(page, api);
    expect(errors, `console.error が ${errors.length} 件`).toHaveLength(0);
  });

  test("S4 会社一覧とリード一覧が開く", async ({ page }) => {
    const api = trackApi(page);
    const c = creds();
    test.skip(!c, SKIP_REASON);
    const { email, password } = c!;
    await login(page, email, password);

    await page.goto("/crm/companies");
    await expect(page.getByPlaceholder("顧客名・コードで検索...")).toBeVisible();
    await expect(page.locator(NO_ERROR_BANNER)).toHaveCount(0);
    await expect(page.locator(".error-message")).toHaveCount(0);

    await page.goto("/crm/leads");
    await page.waitForURL((url) => url.pathname === "/crm/leads");
    await expectSettled(page, api);
    await expect(page.locator("main")).toBeVisible();
    await expect(page.locator(NO_ERROR_BANNER)).toHaveCount(0);
    await expect(page.locator(".error-message")).toHaveCount(0);
  });

  test("S5 会社一覧の検索", async ({ page }) => {
    const api = trackApi(page);
    const c = creds();
    test.skip(!c, SKIP_REASON);
    const { email, password } = c!;
    await login(page, email, password);
    await page.goto("/crm/companies");
    const box = page.getByPlaceholder("顧客名・コードで検索...");
    await expect(box).toBeVisible();
    await box.fill("テスト");
    await expectSettled(page, api);
    await expect(box).toHaveValue("テスト");
    await expect(page.locator(NO_ERROR_BANNER)).toHaveCount(0);
  });

  test("S6 会社の詳細が開く", async ({ page }) => {
    const api = trackApi(page);
    const c = creds();
    test.skip(!c, SKIP_REASON);
    const { email, password } = c!;
    await login(page, email, password);
    await page.goto("/crm/companies");
    await expect(page.getByPlaceholder("顧客名・コードで検索...")).toBeVisible();
    await expectSettled(page, api);
    const link = page.locator('main a[href^="/companies/"]').first();
    test.skip((await link.count()) === 0, "会社 0 件");
    await link.click();
    await page.waitForURL(/\/crm\/companies\/[^/]+$/);
    await expectSettled(page, api);
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
