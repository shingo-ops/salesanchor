/**
 * 開発用の偽ログインに利用者を先に入れる Playwright E2E の補助。
 *
 * 開発サーバーでは main.tsx が開発用の偽ログイン（src/lib/auth/devSession.ts）を登録する。
 * その偽ログインは window.__salesanchorE2eAuthUser と localStorage のキーを読むため、ページ読み込み前に
 * dummy user を埋めておけば LoginPage を経由せずに保護ページを描画できる。
 */

import type { Page } from "@playwright/test";

export const E2E_USER = {
  uid: "e2e-test-user-uid",
  email: "review@salesanchor.jp",
  displayName: "E2E Test User",
};

/**
 * Playwright の page に、開発用の偽ログインの利用者を注入する。
 */
export async function installAuthBypass(page: Page): Promise<void> {
  await page.addInitScript(
    ({ user }) => {
      (window as unknown as { __salesanchorE2eAuthUser?: unknown }).__salesanchorE2eAuthUser = {
        uid: user.uid,
        email: user.email,
        displayName: user.displayName,
        emailVerified: true,
      };
      try {
        localStorage.setItem(
          "salesanchor:e2e-auth-user",
          JSON.stringify({
            uid: user.uid,
            email: user.email,
            displayName: user.displayName,
            emailVerified: true,
          }),
        );
      } catch {
        // noop
      }
    },
    {
      user: E2E_USER,
    },
  );
}

/**
 * Vite dev server が落ちている / E2E スキップ環境用の guard。
 * テスト先頭で呼ぶことで、サーバ未起動を早期検知する。
 */
export async function ensureWebServerUp(page: Page, baseURL?: string): Promise<void> {
  const url = baseURL || page.context()["_options"]?.baseURL || "http://localhost:5173";
  try {
    const res = await page.request.get(url, { timeout: 5000 });
    if (!res.ok() && res.status() !== 304) {
      throw new Error(`web server returned ${res.status()}`);
    }
  } catch (e) {
    throw new Error(
      `Vite dev server is not reachable at ${url}: ${
        e instanceof Error ? e.message : String(e)
      }`,
    );
  }
}
