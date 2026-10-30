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
type TestFixtures = { authedPage: Page; authPacing: void };

// /api/v1/auth/ は 10r/m・burst=5・nodelay なので、1 件ぶんの枠が戻るのに 6 秒かかる。
// 画面は goto のたびに refresh を 1 件呼び、1 つの test が使う auth 系は最大 3 件
// （refresh 401・login・refresh）。6 秒 × 3 = 18 秒 + 余裕で、test の始まり同士を 20 秒空ける。
const AUTH_SPACING_MS = 20_000;
// 前の test の始まりの時刻（同じ worker の中で共有。再試行も 1 本の test として数える）
let lastTestStartedAt: number | null = null;

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

  // 全 test で自動で動く。2 本目以降は前の test の始まりから 20 秒たつまで待つ。
  // 待ちは test の timeout に含めない（待った分だけ timeout を足す）。
  // 共有ログイン（loggedInContext）はこの後に動く: authedPage が authPacing を先に並べているので、
  // ログインの前にも同じ待ちがかかる。
  authPacing: [
    async ({}, use, testInfo) => {
      if (lastTestStartedAt !== null) {
        const waitMs = Math.max(0, lastTestStartedAt + AUTH_SPACING_MS - Date.now());
        if (waitMs > 0) {
          testInfo.setTimeout(testInfo.timeout + waitMs);
          await new Promise((resolve) => setTimeout(resolve, waitMs));
        }
      }
      lastTestStartedAt = Date.now();
      await use();
    },
    { auto: true },
  ],

  authedPage: async ({ authPacing, loggedInContext }, use) => {
    void authPacing;
    test.skip(!loggedInContext, SKIP_REASON);
    const page = await loggedInContext!.newPage();
    await use(page);
    await page.close();
  },
});

export { expect } from "@playwright/test";
