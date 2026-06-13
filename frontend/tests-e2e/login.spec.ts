/**
 * LoginPage: KGI 1-3 検証
 *
 * KGI-1: ユーザーがパスワードを忘れても、自分で再設定メールを送信できる。
 * KGI-2: 未ログインで保護ページへアクセスした場合、ログイン後に元ページへ戻れる。
 * KGI-3: 既にログイン済みのユーザーが /login を開いた場合、アプリ本体へ自動遷移する。
 */

import { expect, test } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi } from "./utils/api-mock";
import { commonMocks } from "./utils/common-mocks";

test.describe("LoginPage KGI検証", () => {
  // ─── KGI-3: ログイン済みで /login を開くと Dashboard に自動遷移 ─────────────
  test("KGI-3: ログイン済みユーザーが /login にアクセスすると / に自動遷移する", async ({
    page,
  }) => {
    await installAuthBypass(page);
    await mockApi(page, commonMocks());
    await page.goto("/login");
    await expect(page).toHaveURL("/", { timeout: 10_000 });
  });

  // ─── KGI-1: パスワード再設定 UI フロー ────────────────────────────────────────
  test("KGI-1: 「パスワードをお忘れの方」クリックで再設定モードに切り替わる", async ({
    page,
  }) => {
    await page.goto("/login");

    // 初期状態: ログインフォーム
    await expect(page.getByLabel("メールアドレス")).toBeVisible();
    await expect(page.getByLabel("パスワード")).toBeVisible();
    await expect(page.getByRole("button", { name: "ログイン" })).toBeVisible();

    // 「パスワードをお忘れの方」クリック
    await page.getByRole("button", { name: "パスワードをお忘れの方" }).click();

    // 再設定フォームに切り替わる
    await expect(page.getByText("パスワード再設定")).toBeVisible();
    await expect(page.getByRole("button", { name: "再設定メールを送信" })).toBeVisible();
    await expect(page.getByRole("button", { name: "ログイン画面に戻る" })).toBeVisible();
    // パスワード入力欄は非表示
    await expect(page.getByLabel("パスワード")).not.toBeVisible();
  });

  test("KGI-1: 再設定メール送信成功で成功メッセージが表示され、フォームが非表示になる", async ({
    page,
  }) => {
    // Firebase sendOobCode エンドポイントをモック
    await page.route("**/identitytoolkit.googleapis.com/**sendOobCode**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ email: "test@example.com" }),
      });
    });

    await page.goto("/login");
    await page.getByRole("button", { name: "パスワードをお忘れの方" }).click();

    // メールアドレスを入力して送信
    await page.getByLabel("メールアドレス").fill("test@example.com");
    await page.getByRole("button", { name: "再設定メールを送信" }).click();

    // 成功メッセージを確認
    await expect(
      page.getByText("再設定メールを送信しました。メールをご確認ください。"),
    ).toBeVisible({ timeout: 5_000 });

    // 送信後はフォームが非表示、戻るリンクは残る
    await expect(page.getByRole("button", { name: "再設定メールを送信" })).not.toBeVisible();
    await expect(page.getByRole("button", { name: "ログイン画面に戻る" })).toBeVisible();
  });

  test("KGI-1: 「ログイン画面に戻る」でサインインモードに戻る", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: "パスワードをお忘れの方" }).click();
    await page.getByRole("button", { name: "ログイン画面に戻る" }).click();

    // ログインフォームに戻る
    await expect(page.getByLabel("メールアドレス")).toBeVisible();
    await expect(page.getByLabel("パスワード")).toBeVisible();
    await expect(page.getByRole("button", { name: "ログイン" })).toBeVisible();
    await expect(
      page.getByRole("button", { name: "パスワードをお忘れの方" }),
    ).toBeVisible();
  });

  // ─── KGI-2: 未ログインで保護ページ → /login にリダイレクト ─────────────────
  test("KGI-2: 未ログインで保護ページにアクセスすると /login にリダイレクトされる", async ({
    page,
  }) => {
    // auth bypass なしで保護ページへ
    await page.goto("/crm/leads");

    // /login に遷移することを確認
    await expect(page).toHaveURL("/login", { timeout: 10_000 });
    // ログインフォームが表示されている
    await expect(page.getByRole("button", { name: "ログイン" })).toBeVisible();
  });
});
