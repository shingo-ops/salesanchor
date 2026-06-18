/**
 * mobile-bp-token-g5.spec.ts — ADR-140 PR-A: G5 + 構造2 検証
 *
 * ADR-140: Drawer/Modal の @media ブレークポイントを 640px → 767px に統一。
 *
 * G5: 641〜767px 帯（代表: 700px）で Drawer パネルと Modal ダイアログが
 *     viewport 全幅になること（中途半端な幅にならないこと）。
 *
 * 検証方法:
 *   - viewport 700px × 900px で CSS を評価
 *   - .comp-drawer-panel に `max-width: 100%` が適用されているか
 *     → getBoundingClientRect().width ≈ viewport.width（≥ 690px）
 *   - .comp-modal-dialog--md に `max-width: 100% !important` が適用されているか
 *     → getBoundingClientRect().width ≈ viewport.width（≥ 690px）
 *
 * 参照:
 *   設計doc §受け入れ基準 G5 / docs/handoff/mobile-responsive/design.md
 */

import { expect, test } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi } from "./utils/api-mock";
import { commonMocks } from "./utils/common-mocks";

const TABLET_BOUNDARY_VIEWPORT = { width: 700, height: 900 };

function dashboardMocks() {
  return {
    "GET /analytics/followups": { overdue: [], due_today: [], upcoming: [], stalled: [] },
    "GET /analytics/forecast": {
      forecast_amount: 0,
      won_amount: 0,
      open_deal_count: 0,
      period_start: "2026-06-01",
      period_end: "2026-06-30",
    },
    "GET /analytics/stalled-deals": { stalled_count: 0, stalled_deals: [] },
    "GET /analytics/monthly-revenue": { granularity: "monthly", entries: [] },
    "GET /goals/summary": { monthly: [], weekly: [] },
    "GET /conversations": { conversations: [], total: 0 },
  };
}

test.describe("G5: 641-767px 帯での Drawer/Modal 全幅表示（ADR-140 PR-A）", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(TABLET_BOUNDARY_VIEWPORT);
    await installAuthBypass(page);
    await mockApi(page, { ...commonMocks(), ...dashboardMocks() });
    await page.goto("/");
    await page.waitForLoadState("networkidle");
  });

  test("700px 幅で @media (max-width: 767px) が発火する（前提確認）", async ({ page }) => {
    const mq = await page.evaluate(() =>
      window.matchMedia("(max-width: 767px)").matches,
    );
    expect(mq).toBe(true);
  });

  test("G5-drawer: 700px で comp-drawer-panel が viewport 全幅になる", async ({ page }) => {
    // .comp-drawer-panel を DOM に注入して幅を計測
    // ※ アプリバンドルに Drawer.css が含まれているため、注入要素にも CSS が適用される
    const panelWidth = await page.evaluate(() => {
      const panel = document.createElement("div");
      panel.className = "comp-drawer-panel comp-drawer-panel--open";
      // 固定配置で右端から表示（Drawer の通常挙動と同じ）
      Object.assign(panel.style, {
        position: "fixed",
        top: "0",
        right: "0",
        height: "200px",
        zIndex: "-999",
        visibility: "hidden",
      });
      document.body.appendChild(panel);
      const rect = panel.getBoundingClientRect();
      const w = rect.width;
      document.body.removeChild(panel);
      return w;
    });

    // 700px（<= 767px = --breakpoint-mobile-max）では width: 100% が適用される
    // → panel 幅 ≈ viewport 幅（700px）。旧 640px では ~480px（--drawer-panel-width）のまま
    expect(panelWidth).toBeGreaterThanOrEqual(690);
    expect(panelWidth).toBeLessThanOrEqual(710);
  });

  test("G5-modal: 700px で comp-modal-dialog が viewport 全幅になる", async ({ page }) => {
    // .comp-modal-overlay（flex コンテナ）に .comp-modal-dialog--md を注入して幅を計測
    const dialogWidth = await page.evaluate(() => {
      const overlay = document.createElement("div");
      Object.assign(overlay.style, {
        position: "fixed",
        inset: "0",
        display: "flex",
        alignItems: "flex-end",
        padding: "0",
        zIndex: "-999",
        visibility: "hidden",
      });

      const dialog = document.createElement("div");
      dialog.className = "comp-modal-dialog comp-modal-dialog--md";

      overlay.appendChild(dialog);
      document.body.appendChild(overlay);
      const rect = dialog.getBoundingClientRect();
      const w = rect.width;
      document.body.removeChild(overlay);
      return w;
    });

    // 700px（<= 767px）では max-width: 100% !important が適用される
    // → dialog 幅 ≈ viewport 幅（700px）。旧 640px では max-width: var(--modal-max-w-md) = 600px
    expect(dialogWidth).toBeGreaterThanOrEqual(690);
    expect(dialogWidth).toBeLessThanOrEqual(710);
  });
});
