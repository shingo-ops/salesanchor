/**
 * 本番の全画面の速さの記録（ADR-1053）— Playwright 設定
 *
 * 今の点検（playwright.config.ts）とは分ける。判定も再試行もしない。
 * リポジトリが公開なので、trace・html・スクリーンショット・動画は作らない（ADR-1051）。
 * 表は tests/prod-check/page-speed.md に書き、ワークフローが実行記録の要約に足す。
 */

import { defineConfig, devices } from "@playwright/test";
import { BASE_URL } from "./login";

export default defineConfig({
  testDir: ".",
  testMatch: "page-speed.spec.ts",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  timeout: 45 * 60 * 1000,

  reporter: [["list"]],

  use: {
    baseURL: BASE_URL,
    trace: "off",
    screenshot: "off",
    video: "off",
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    // 関所（context.route）をすり抜けないように止める
    serviceWorkers: "block",
  },

  projects: [
    {
      name: "chromium-page-speed",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
