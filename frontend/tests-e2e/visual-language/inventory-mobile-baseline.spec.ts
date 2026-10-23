/**
 * visual-language/inventory-mobile-baseline.spec.ts — 在庫表スマホのベースライン計測（便0・測るだけ）
 *
 * design.md（docs/handoff/inventory-mobile-responsive/design.md）設計 ④・⑤ の
 * A1〜A5 を満たすための計測本体。**合否は出さない**（この便は見た目を1pxも変えない。
 * 測定が成立したことだけを assert し、残りは console.log に JSON 1行で吐いて CI ログに残す）。
 *
 * なぜ visual-language/ に置くか（2026-10-21 に一次情報で確認）:
 *   .github/workflows/e2e.yml:247 の `playwright` ジョブ（Playwright E2E (chromium)）は
 *   `if: false # 一時停止 2026-06-01` で止まっている。CI で実際に走る Playwright は
 *   「画面検査（内部）」の vl-mobile-390 / vl-tablet-768 / vl-desktop-1280 だけで、
 *   playwright.config.ts の testMatch が `visual-language/*.spec.ts` に限定されている。
 *   つまり tests-e2e/ 直下に置くと CI では1度も走らない（既存 inventory-raw-text-mobile.spec.ts
 *   と同じ理由。PR #4602 で実測済み）。
 *
 * 幅を spec 側で 360 と 390 の両方に設定する理由:
 *   過去の実機記録は 360 CSS px で、project 既定（vl-mobile-390 の viewport 390px）より
 *   30px 狭い。390 で収まっても 360 で溢れる可能性があるため両方測る（design.md 4-2）。
 *   3つの project すべてでこの spec が収集される関係で、同じ計測が3回走る
 *   （既存 inventory-raw-text-mobile.spec.ts と同じ割り切り。短いので許容する）。
 *
 * ログの接頭辞 `INVENTORY_BASELINE` / `INVENTORY_DRAWER_BASELINE` /
 * `INVENTORY_DRAWER_TABS_BASELINE` は design.md 設計 ⑤ A3/A4/A5 の判定にそのまま
 * 文字列検索で使うため、変えないこと。
 *
 * 「解析｜原文」の切り替えタブ（InventoryRowDrawer.tsx:207-217・super admin のときだけ出る）は
 * 今回は対象外（未測定）。認証モックの作り替え（is_super_admin）が本便の範囲を越えるため、
 * 別便に持ち越す。
 */
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { gotoInventory } from "./inventory-helpers";

/**
 * 開いている詳細パネル（supplier-drawer の --open）を測る共通処理。
 * Playwright の Locator.evaluate はこの関数をブラウザ側へそのまま送って実行するため、
 * 外側スコープの変数（round / rectOf 等）は参照できない。全部この関数の中に閉じる。
 */
function measureDrawerPanel(panelEl: Element) {
  const round = (n: number) => Math.round(n);
  const rectOf = (el: Element) => {
    const r = el.getBoundingClientRect();
    return { x: round(r.x), y: round(r.y), w: round(r.width), h: round(r.height) };
  };
  const classOf = (el: Element) => (typeof el.className === "string" ? el.className.slice(0, 120) : "");

  const panelRect = panelEl.getBoundingClientRect();
  const panelData = {
    rect: rectOf(panelEl),
    scrollW: panelEl.scrollWidth,
    clientW: panelEl.clientWidth,
    overflow: panelEl.scrollWidth - panelEl.clientWidth,
  };
  const base = panelRect.right;
  const descendants = Array.from(panelEl.querySelectorAll("*"));

  const overflowAll: Array<{
    tag: string;
    cls: string;
    testid: string | null;
    rect: { x: number; y: number; w: number; h: number };
    over: number;
  }> = [];
  for (const el of descendants) {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) continue;
    if (r.right <= base + 1) continue;
    overflowAll.push({
      tag: el.tagName.toLowerCase(),
      cls: classOf(el),
      testid: el.getAttribute("data-testid"),
      rect: rectOf(el),
      over: round(r.right - base),
    });
  }
  overflowAll.sort((a, b) => b.over - a.over);
  const panelOverflowingTotal = overflowAll.length;
  const panelOverflowing = overflowAll.slice(0, 20);

  const widestInPanel = descendants
    .map((el) => ({ el, r: el.getBoundingClientRect() }))
    .filter(({ r }) => r.width > 0 && r.height > 0)
    .sort((a, b) => b.r.width - a.r.width)
    .slice(0, 5)
    .map(({ el, r }) => ({
      tag: el.tagName.toLowerCase(),
      cls: classOf(el),
      testid: el.getAttribute("data-testid"),
      rect: { x: round(r.x), y: round(r.y), w: round(r.width), h: round(r.height) },
    }));

  // タブ列: components/Tabs.tsx が role="tablist"（コンテナ・Tabs.tsx:70）/
  // role="tab"（各タブ・Tabs.tsx:83）を付ける。在庫の行ドロワー（InventoryRowDrawer.tsx）は
  // super admin のときだけ「解析｜原文」の modeTabs（:207-217）を描き、原文が2件以上の
  // ときだけ itemTabs（:161-169）を描く。mock が原文1件のときはどちらの条件も満たさず
  // found:false、原文2件以上（rawTexts オプション）のときは itemTabs が出て found:true になる。
  const tablistEl = panelEl.querySelector('[role="tablist"]');
  const tabs = tablistEl
    ? {
        found: true,
        rect: rectOf(tablistEl),
        tabs: Array.from(tablistEl.querySelectorAll('[role="tab"]')).map((t) => ({
          testid: t.getAttribute("data-testid"),
          rect: rectOf(t),
        })),
      }
    : { found: false };

  // 原文を表示している要素: ShadowSourcePane.tsx が1行ずつ
  // <span class="shadow-source-line-text"> に原文を入れ、折り返し規則
  // （white-space: pre-wrap; overflow-wrap: anywhere;）はこの要素自身に
  // 乗っている（shadow-source-pane.css:58-60）。外側の .shadow-source-pane /
  // .shadow-source-lines にはこれらの指定が無いため、ここを計測対象にする。
  const rawTextEl = panelEl.querySelector(".shadow-source-line-text");
  const rawText = rawTextEl
    ? (() => {
        const style = getComputedStyle(rawTextEl);
        return {
          found: true,
          rect: rectOf(rawTextEl),
          scrollW: rawTextEl.scrollWidth,
          clientW: rawTextEl.clientWidth,
          whiteSpace: style.whiteSpace,
          overflowWrap: style.overflowWrap,
          wordBreak: style.wordBreak,
        };
      })()
    : { found: false };

  return {
    panel: panelData,
    panelOverflowing,
    // 20件に切った場合だけ全件数を入れる（design.md 2-2）。
    ...(panelOverflowingTotal > 20 ? { panelOverflowingTotal } : {}),
    widestInPanel,
    tabs,
    rawText,
  };
}

/** 詳細パネルを開き、トランジション（--transition-slow 280ms）が収まるまで待つ */
async function openAndSettleDrawerPanel(page: Page) {
  await page.locator('[data-testid^="inventory-raw-text-"]').first().click();
  // supplier-drawer は「表の設定」ドロワーと行ドロワーの2つが同一画面の DOM に居るため、
  // 開いている方（--open）だけに絞る（inventory-raw-text-mobile.spec.ts と同じ絞り込み。
  // PR #4602 で実測した strict mode violation の罠）。
  const panel = page.locator('[data-testid="supplier-drawer"].comp-drawer-panel--open');
  await expect(panel).toHaveCount(1);
  await expect(panel).toBeVisible();

  // 途中で測ると rect が実際の位置と一致しないため、幅が viewport と一致するまで待つ
  // （inventory-raw-text-mobile.spec.ts A3/A4 と同じ待ち方）。
  const viewport = page.viewportSize();
  if (!viewport) throw new Error("viewport size is null");
  await expect
    .poll(async () => {
      const box = await panel.boundingBox();
      return box ? Math.round(box.width) : null;
    })
    .toBe(viewport.width);

  return panel;
}

const LIST_WIDTHS = [360, 390] as const;

test.describe("visual-language: 在庫表ベースライン計測 — 一覧（便0・測るだけ）", () => {
  for (const width of LIST_WIDTHS) {
    test(`${width}px: 一覧の計測`, async ({ page }) => {
      // gotoInventory が inventory-row-row-1 の可視を確認済み（測定成立の一部・design.md 4-4）。
      await gotoInventory(page, { width, height: 800 });

      const data = await page.evaluate(() => {
        const round = (n: number) => Math.round(n);
        const rectOf = (el: Element) => {
          const r = el.getBoundingClientRect();
          return { x: round(r.x), y: round(r.y), w: round(r.width), h: round(r.height) };
        };
        const classOf = (el: Element) =>
          typeof el.className === "string" ? el.className.slice(0, 120) : "";

        const mobileContentEl = document.querySelector(".mobile-content");
        const mobileContent = mobileContentEl
          ? {
              found: true,
              scrollW: mobileContentEl.scrollWidth,
              clientW: mobileContentEl.clientWidth,
              overflow: mobileContentEl.scrollWidth - mobileContentEl.clientWidth,
              rect: rectOf(mobileContentEl),
            }
          : { found: false };

        // 基準の右端: .mobile-content があればその右端、無ければ viewport の右端。
        const base = mobileContentEl ? mobileContentEl.getBoundingClientRect().right : window.innerWidth;

        const overflowAll: Array<{
          tag: string;
          cls: string;
          testid: string | null;
          rect: { x: number; y: number; w: number; h: number };
          over: number;
        }> = [];
        document.querySelectorAll("*").forEach((el) => {
          const r = el.getBoundingClientRect();
          if (r.width <= 0 || r.height <= 0) return;
          if (r.right <= base + 1) return; // 1px は端数の許容
          overflowAll.push({
            tag: el.tagName.toLowerCase(),
            cls: classOf(el),
            testid: el.getAttribute("data-testid"),
            rect: rectOf(el),
            over: round(r.right - base),
          });
        });
        overflowAll.sort((a, b) => b.over - a.over);
        const overflowingTotal = overflowAll.length;
        const overflowing = overflowAll.slice(0, 40);

        const toolbarLeftEl = document.querySelector(".content-toolbar__left");
        const toolbarParentEl = document.querySelector(".content-toolbar");
        const toolbar = toolbarLeftEl
          ? (() => {
              const children = Array.from(toolbarLeftEl.children);
              const firstY = children.length > 0 ? children[0].getBoundingClientRect().y : null;
              return {
                found: true,
                rect: rectOf(toolbarLeftEl),
                childCount: children.length,
                children: children.map((child) => {
                  const r = child.getBoundingClientRect();
                  return {
                    tag: child.tagName.toLowerCase(),
                    testid: child.getAttribute("data-testid"),
                    rect: rectOf(child),
                    sameRowAsFirst: firstY != null && Math.abs(r.y - firstY) < 2,
                  };
                }),
                toolbarParent: toolbarParentEl ? rectOf(toolbarParentEl) : null,
              };
            })()
          : { found: false, toolbarParent: toolbarParentEl ? rectOf(toolbarParentEl) : null };

        const cardEls = Array.from(
          document.querySelectorAll('[data-testid^="inventory-row-"][role="listitem"]'),
        );
        const firstCardRect = cardEls.length > 0 ? rectOf(cardEls[0]) : null;
        const cards = {
          count: cardEls.length,
          firstRect: firstCardRect,
          perScreen:
            firstCardRect && firstCardRect.h > 0 ? Math.floor(window.innerHeight / firstCardRect.h) : null,
        };

        const firstCard = cardEls[0] ?? null;
        const labelEl = firstCard?.querySelector(".comp-table__card-label") ?? null;
        const valueEl = firstCard?.querySelector(".comp-table__card-value") ?? null;
        const fontSizes = {
          label: labelEl ? getComputedStyle(labelEl).fontSize : null,
          value: valueEl ? getComputedStyle(valueEl).fontSize : null,
        };

        return {
          viewport: { w: window.innerWidth, h: window.innerHeight },
          doc: {
            scrollW: document.documentElement.scrollWidth,
            clientW: document.documentElement.clientWidth,
            overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
          },
          mobileContent,
          overflowing,
          // 40件に切った場合だけ全件数を入れる（design.md 2-1）。
          ...(overflowingTotal > 40 ? { overflowingTotal } : {}),
          toolbar,
          cards,
          fontSizes,
        };
      });

      console.log("INVENTORY_BASELINE w=" + width + " " + JSON.stringify(data));

      // 測定が成立したことだけを確かめる（design.md 4-4）。合否は出さない。
      expect(data.cards.count).toBeGreaterThanOrEqual(1);
    });
  }
});

test.describe("visual-language: 在庫表ベースライン計測 — 詳細パネル（便0・測るだけ）", () => {
  // 360px のみ測る。パネルは767px以下で width:100%（Drawer.css:105-113）になるため
  // 360/390 どちらで測っても構造は同じ。計測コストを抑えるため実機記録に近い狭い方だけ測る。
  test("360px: 詳細パネルの計測（原文1件・タブ無し）", async ({ page }) => {
    const width = 360;
    await gotoInventory(page, { width, height: 800 });

    const panel = await openAndSettleDrawerPanel(page);
    const data = await panel.evaluate(measureDrawerPanel);

    console.log("INVENTORY_DRAWER_BASELINE w=" + width + " " + JSON.stringify(data));
  });

  // タブ列（itemTabs）は原文が2件以上のときだけ描かれる（InventoryRowDrawer.tsx:161-169）。
  // 上の「原文1件」計測だけでは「タブが出ない状態」しか把握できず、現状把握として不十分
  // （実運用では1行に複数の原文がまとまりタブが出ることがある）。
  // installInventoryMocks の rawTexts オプションで原文3件を返し、タブが出る条件を
  // 実際に満たした上で同じ項目を測る。
  test("360px: 詳細パネルの計測（原文3件・タブ有り）", async ({ page }) => {
    const width = 360;
    await gotoInventory(page, { width, height: 800, rawTexts: 3 });

    const panel = await openAndSettleDrawerPanel(page);
    const data = await panel.evaluate(measureDrawerPanel);

    console.log("INVENTORY_DRAWER_TABS_BASELINE w=" + width + " " + JSON.stringify(data));

    // タブが出る条件（原文2件以上・InventoryRowDrawer.tsx:161-169）を実際に満たした
    // ことの確認。これが false のままなら「タブ無しの状態しか測れていない」ことに
    // なるため、測定成立の assert として入れる（design.md 4-4 の範囲。合否判定ではない）。
    expect(data.tabs.found).toBe(true);
  });
});
