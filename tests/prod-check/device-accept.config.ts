/**
 * 本番の受入（ADR-1055 段C）— Playwright 設定
 *
 * device-accept.spec.ts（C1）と device-k7.spec.ts（C5）を流す。書き込みを伴うので、
 * 毎朝の点検（playwright.config.ts）とは別の入口（手動の workflow）からだけ流す。
 * 流すときにファイル名を渡して1本だけ動かす。やり直しは依頼の枠（1人1時間5件）を超えるので retries 0。
 * リポジトリが公開なので trace・スクリーンショット・動画は作らない。
 */

import { defineConfig, devices } from "@playwright/test";
import { BASE_URL } from "./login";

export default defineConfig({
  testDir: ".",
  testMatch: ["device-accept.spec.ts", "device-k7.spec.ts"],
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  timeout: 10 * 60_000,
  expect: { timeout: 10_000 },

  reporter: [["list"]],

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
      name: "chromium-prod-device-accept",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
