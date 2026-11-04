/**
 * Playwright config (Phase 1-E F2-S3).
 *
 * 撮影台本 docs/META_APP_REVIEW_SCREENCAST_SCRIPT.md の 7 シーン + Data Deletion を
 * frontend E2E でカバーする。実機 Meta OAuth は通さず、API レイヤを mock する。
 *
 * - baseURL: Vite dev server (localhost:5173)
 * - browser: chromium 単体（CI 時間短縮 / multi-browser は後追い）
 * - webServer: 自動で `npm run dev` を起動する
 * - retain-on-failure: trace / video / screenshot を artifact 化
 *
 * 使い方:
 *   npm run test:e2e:install   # browser を一度だけ install
 *   npm run test:e2e
 *   npm run test:e2e:ui        # interactive UI mode
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";

/**
 * 幅を自分で決める visual-language spec（最初の goto の前に viewport を上書きする 16 本）。
 *
 * vl-tablet-768 と vl-desktop-1280 はどちらも Desktop Chrome（isMobile・hasTouch なし）で、
 * 幅は spec が上書きするため同じ確かめになる。そこで vl-tablet-768 では流さない。
 * vl-mobile-390 は isMobile・hasTouch が効く（hover:none・meta viewport）ので別の確かめとして残す。
 * 根拠: docs/handoff/visual-check-dedup/design.md（2節・3節）、recon.md 7節。
 */
const SELF_WIDTH_SPECS = [
  "drawer-inert-closed.spec.ts",
  "inventory-mobile-baseline.spec.ts",
  "inventory-raw-text-mobile.spec.ts",
  "inventory-series-sort-panel.spec.ts",
  "inventory-toolbar-mercari.spec.ts",
  "popover-mold.spec.ts",
  "viewer-choice-sheet.spec.ts",
  "viewer-control-tap-size.spec.ts",
  "viewer-filter-panel-mercari.spec.ts",
  "viewer-filter-row-mercari.spec.ts",
  "viewer-focus-trap.spec.ts",
  "viewer-header-remove.spec.ts",
  "viewer-inventory-mobile-filter.spec.ts",
  "viewer-search-mercari.spec.ts",
  "viewer-search-suggestions.spec.ts",
  "viewer-top-compact.spec.ts",
];

// 見張り（design.md 3節・K5）: 一覧の spec が project の幅・触る扱いを読み始めたら、
// タブレット幅の確かめが黙って抜けるので config 読み込み時に止める。
// 単語 isMobile（コメント内のアプリ側の説明）と page.viewportSize() は止めない。
const PROJECT_DEPENDENT = [
  /\.project\b/,
  /projectWidth/,
  /hasTouch/,
  /touchscreen/,
  /\.tap\(/,
  /async \(\{[^)]*\bisMobile\b/,
];
for (const name of SELF_WIDTH_SPECS) {
  const file = fileURLToPath(new URL(`./tests-e2e/visual-language/${name}`, import.meta.url));
  let text: string;
  try {
    text = readFileSync(file, "utf8");
  } catch {
    throw new Error(`SELF_WIDTH_SPECS の spec が見つからない: ${name}（${file}）`);
  }
  const hit = PROJECT_DEPENDENT.find((re) => re.test(text));
  if (hit) {
    throw new Error(
      `SELF_WIDTH_SPECS の ${name} が project の幅・触る扱いを読んでいる（${hit}）。` +
        "一覧から外すこと（docs/handoff/visual-check-dedup/design.md）",
    );
  }
}
const SELF_WIDTH_IGNORE = SELF_WIDTH_SPECS.map((n) => new RegExp(`visual-language/${n.replace(/\./g, "\\.")}$`));

const PORT = Number(process.env.PORT || 5173);
const BASE_URL = process.env.E2E_BASE_URL || `http://localhost:${PORT}`;

export default defineConfig({
  testDir: "./tests-e2e",
  // spec ファイル間は並列実行。各 spec 内のテストは順序依存があるため直列のまま。
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  // CI: 4 workers で並列実行（GitHub Actions ubuntu-latest は 4 vCPU）
  // local: CPU コア数に応じて自動調整（undefined = Playwright デフォルト）
  workers: process.env.CI ? 4 : undefined,
  reporter: process.env.CI
    ? [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]]
    : [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],

  use: {
    baseURL: BASE_URL,
    // CI のフレーク削減: trace を毎回 retain（失敗時 artifact 化）
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },

  expect: {
    toHaveScreenshot: {
      // アンチエイリアス差（~0.3%）を吸収しつつ、5px+ の配置ズレを検出するしきい値
      maxDiffPixelRatio: 0.005,
      // ピクセルごとの色距離（0〜1）: 0.15 = サブピクセル差を許容
      threshold: 0.15,
    },
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
      // 3幅検査（visual-language）は専用 project でのみ実行する
      testIgnore: /visual-language\/.*\.spec\.ts/,
    },
    {
      name: "vl-mobile-390",
      testMatch: /visual-language\/.*\.spec\.ts/,
      use: { ...devices["Desktop Chrome"], viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true },
    },
    {
      name: "vl-tablet-768",
      testMatch: /visual-language\/.*\.spec\.ts/,
      // 幅を自分で決める spec は vl-desktop-1280 と同じ確かめなのでここでは流さない（上部 SELF_WIDTH_SPECS）
      testIgnore: SELF_WIDTH_IGNORE,
      use: { ...devices["Desktop Chrome"], viewport: { width: 768, height: 1024 } },
    },
    {
      name: "vl-desktop-1280",
      testMatch: /visual-language\/.*\.spec\.ts/,
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } },
    },
  ],

  // Vite dev server を自動起動する。開発サーバーでは開発用の偽ログインが登録され、
  // tests-e2e/utils/auth.ts の addInitScript と組み合わせて認証を bypass する。
  webServer: process.env.E2E_NO_WEBSERVER
    ? undefined
    : {
        command: "npm run dev -- --port " + PORT,
        url: BASE_URL,
        reuseExistingServer: !process.env.CI,
        timeout: 60_000,
        env: {
          // ファネルダッシュボード: E2E はモックデータで実行
          VITE_FUNNEL_DASHBOARD: "mock",
        },
      },
});
