/**
 * 本番の画面点検: ログイン手順（この 1 ファイルに閉じ込める）
 *
 * ログイン切替（ADR-1013）のときはこのファイルだけ差し替える。
 * 認証情報は環境変数から読み、値はログに出さない。
 */

import { expect, type Page } from "@playwright/test";

/** 点検先。今の点検の config と速さの記録がここを読む（fixtures.ts は同じ式を自前で持つ） */
export const BASE_URL = process.env.PROD_CHECK_BASE_URL || "https://app.salesanchor.jp";

// 入口（nginx）は /api/v1/auth/ を 1 つの IP から 1 分 10 件（6 秒に 1 件）・まとめて 5 件までに制限する（nginx/nginx.conf:6・:145）。
// 速さの記録（page-speed.spec.ts）が login の前に呼び、前回から 8 秒あける（6 秒に 1 件より遅くする）。今の点検は fixtures.ts の間隔を使う。
// login は 1 回で最大 3 件（refresh 401・login・refresh）を使う。超過は 5 件のまとめ枠が吸収する。
// 最初の 1 回も、このファイルを読み込んだ時刻から数える（再試行は新しい作業者で最初からやり直すため）。
const AUTH_PACE_MS = 8_000;
let lastAuthAt = Date.now();

export async function authPace(): Promise<void> {
  const wait = lastAuthAt + AUTH_PACE_MS - Date.now();
  if (wait > 0) await new Promise((resolve) => setTimeout(resolve, wait));
  lastAuthAt = Date.now();
}

// 秘密情報が未登録のときは null を返す（呼び出し側が test.skip にする）。値は出力しない。
// 今の点検は fixtures.ts の authedPage が、速さの記録は test.skip が飛ばす。
export function creds(): { email: string; password: string } | null {
  const email = process.env.SMOKE_E2E_EMAIL;
  const password = process.env.SMOKE_E2E_PASSWORD;
  if (!email || !password) return null;
  return { email, password };
}

export async function login(page: Page, email: string, password: string): Promise<void> {
  // 点検のブラウザでは顔・指紋（パスキー）を使えない扱いにし、ログイン直後の登録案内を出さない（本番に記録を残さない・ADR-1013）
  await page.addInitScript(() => {
    Object.defineProperty(globalThis, "PublicKeyCredential", { value: undefined, configurable: true });
  });
  // 点検のブラウザでは「予備の合言葉を作りませんか」の小窓を出さない（残りがある扱いにする・本番に記録を残さない・ADR-1055）
  await page.context().route("**/api/v1/auth/recovery-codes/status", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ remaining: 10 }) }),
  );
  await page.goto("/login");
  await page.getByLabel("メールアドレス").fill(email);
  await page.getByLabel("パスワード", { exact: true }).fill(password);
  await page.getByRole("button", { name: "ログイン", exact: true }).click();
  await page.waitForURL(
    (url) => url.pathname === "/" || url.pathname === "/dashboard",
    { timeout: 30_000 },
  );
}

// 右上のアバター（ユーザーメニューを開く）→「サインアウト」→ 確認ダイアログの「サインアウト」
export async function signOut(page: Page): Promise<void> {
  await page.getByRole("button", { name: "ユーザーメニューを開く" }).click();
  await page.getByRole("button", { name: "サインアウト" }).first().click();
  await expect(page.getByText("サインアウトしますか？")).toBeVisible();
  // 確認ダイアログは DOM の後ろ側にあるので最後のボタンを押す
  await page.getByRole("button", { name: "サインアウト" }).last().click();
  await page.waitForURL((url) => url.pathname === "/login", { timeout: 30_000 });
}
