/**
 * 本番の画面点検: ログイン済みの page を worker ごとに 1 回のログインで配る
 *
 * nginx は /api/v1/auth/ を送信元 IP ごと 10r/m（burst=5）で絞る。test ごとにログインすると
 * 429 になるため、worker の間ログインは 1 回だけにして、その context を使い回す。
 * storageState を別 context に渡す方式は使わない（refresh token は使うたびに入れ替わり、
 * 古いものを再提示すると一族ごと無効になる: backend/app/auth/self_tokens.py）。
 */

import { test as base, type BrowserContext, type Page } from "@playwright/test";
import { creds, login } from "./login";

const BASE_URL = process.env.PROD_CHECK_BASE_URL || "https://app.salesanchor.jp";
export const SKIP_REASON = "点検用の人の秘密情報が未登録";

type WorkerFixtures = { loggedInContext: BrowserContext | null };
type TestFixtures = { authedPage: Page };

export const test = base.extend<TestFixtures, WorkerFixtures>({
  // 秘密情報が無いときは null（authedPage 側で skip にする）。ログインは worker の最初の 1 回だけ。
  loggedInContext: [
    async ({ browser }, use) => {
      const c = creds();
      if (!c) {
        await use(null);
        return;
      }
      const context = await browser.newContext({ baseURL: BASE_URL });
      context.setDefaultTimeout(15_000);
      context.setDefaultNavigationTimeout(30_000);
      const page = await context.newPage();
      await login(page, c.email, c.password);
      await page.close();
      await use(context);
      await context.close();
    },
    { scope: "worker" },
  ],

  authedPage: async ({ loggedInContext }, use) => {
    test.skip(!loggedInContext, SKIP_REASON);
    const page = await loggedInContext!.newPage();
    await use(page);
    await page.close();
  },
});

export { expect } from "@playwright/test";
