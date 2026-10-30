/**
 * 本番の画面点検（prod-ui-check）— Playwright 設定
 *
 * 本番 (https://app.salesanchor.jp) を画面から見るだけの点検。書き込みはしない。
 * 旧 tests/qa-smoke とは別資産（X-QA-Smoke ヘッダは付けない）。
 * リポジトリが公開なので、入力値が残る trace・html・スクリーンショットは作らない（ADR-1051）。
 *
 * 環境変数:
 *   PROD_CHECK_BASE_URL  点検先 (default: https://app.salesanchor.jp)
 *   PROD_CHECK_FORCE_FAIL=1  通知の試験用に必ず落ちる点検を 1 本足す
 *   SMOKE_E2E_EMAIL / SMOKE_E2E_PASSWORD  点検用の人の認証情報（CI の secrets）
 */

import { defineConfig, devices } from "@playwright/test";
import { BASE_URL } from "./login";

export default defineConfig({
  testDir: ".",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 1,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 10_000 },

  reporter: [["list"], ["json", { outputFile: "results.json" }]],

  use: {
    baseURL: BASE_URL,
    trace: "off",
    screenshot: "off",
    video: "off",
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },

  projects: [
    {
      name: "chromium-prod-check",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
