/**
 * visual-language/inbox-single-column.spec.ts — 受信箱「1画面1ページ」の画面検査（合否を出す）
 *
 * inbox-baseline.spec.ts は測って記録するだけ。こちらは壊れていたら赤くする検査。
 *
 * なぜ要るか: PR #4165 で「スマホの一覧へ戻るが効かない」状態を本番に出し、#4168 で撤回した。
 * この端末（arm64 / Termux）では Playwright の chromium が動かず、開く→戻るを手元で確認できない。
 * 実機 ADB では見た目は撮れるが、マージ前の自動確認にはならない。
 * そのため「開く→戻る」の構造だけは CI（x86）で恒久的に検査する。
 *
 * 検査する幅（playwright.config.ts の project）:
 *   vl-mobile-390   … 一覧と会話を同時に出さない。選ぶ→会話が全画面、戻る→一覧が全画面
 *   vl-tablet-768   … スマホ用レイアウトの境界の外側（tokens.css --breakpoint-tablet-min）
 *   vl-desktop-1280 … 一覧と会話が同時に見え、戻るボタンは出ない（PC は従来どおり）
 *
 *   cd frontend && npm run test:e2e:vl
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";
import type { Locator, Page, TestInfo } from "@playwright/test";
import { installAuthBypass } from "../utils/auth";
import { mockApi } from "../utils/api-mock";
import {
  MIN_TOUCH_TARGET_PX,
  MOBILE_MAX_PX,
  SAMPLE_CONVERSATION_NAME,
  baseMocks,
  openConversation,
  openInboxList,
  openInboxListWithConversations,
  openInboxListWithDiscordUnlinkedConversation,
  openInboxListWithLeadStatus,
  openInboxListWithLeadStatusAndStaff,
} from "./inbox-helpers";

/**
 * 長押しの再現方法（受信箱 第4便）:
 * `useLongPress`（src/hooks/useLongPress.ts）は pointerType で絞り込まない作りに
 * したため、実際の（トラステッドな）マウス入力でも成立する。
 * Playwright の `page.mouse.down()` / `.up()` は CDP 経由の本物の入力で、
 * Chromium はこれに対し pointerdown → mousedown の順で本物のイベントを発火し、
 * 押しっぱなしのまま LONG_PRESS_MS（500ms）待つとハンドラ内の setTimeout が発火する。
 * `locator.dispatchEvent("pointerdown", ...)` も試したが、合成イベントだけでは
 * ブラウザが後続の click を合成してくれないため「長押し成立後の click 無効化」を
 * 検査できない。本物の入力（page.mouse）のほうが「押しただけで開かない」
 * 「普通のタップでは開く」の両方を同じ経路で検査できるため、これを採用した。
 */
const LONG_PRESS_WAIT_MS = 650; // LONG_PRESS_MS(500) + 余裕

async function longPressRow(page: Page, row: Locator): Promise<{ x: number; y: number }> {
  const box = await row.boundingBox();
  if (!box) throw new Error("行の矩形が取れない");
  const x = box.x + box.width / 2;
  const y = box.y + box.height / 2;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.waitForTimeout(LONG_PRESS_WAIT_MS);
  return { x, y };
}

interface Rect { x: number; y: number; width: number; height: number }

/** メニューの矩形が行の矩形と重なる、または上下に隣接しているか */
function overlapsOrAdjacent(menu: Rect, row: Rect): boolean {
  const overlapsX = menu.x < row.x + row.width && row.x < menu.x + menu.width;
  const overlapsY = menu.y < row.y + row.height && row.y < menu.y + menu.height;
  if (overlapsX && overlapsY) return true;
  const adjacentGap = 16; // px — 隣接とみなす最大の隙間
  const verticallyAdjacent =
    Math.abs(menu.y - (row.y + row.height)) <= adjacentGap ||
    Math.abs(row.y - (menu.y + menu.height)) <= adjacentGap;
  return overlapsX && verticallyAdjacent;
}

/** project の viewport 幅。実行前に分かる値なので test.skip の条件に使える */
function projectWidth(testInfo: TestInfo): number {
  const viewport = testInfo.project.use.viewport;
  if (!viewport) throw new Error(`viewport が未設定の project: ${testInfo.project.name}`);
  return viewport.width;
}

const list = (page: Page): Locator => page.locator(".inbox-left-panel");
const thread = (page: Page): Locator => page.locator(".inbox-center");
const backButton = (page: Page): Locator => page.locator(".inbox-back-to-list");

/** URL に lead_id が残っていないこと。#4165 はここが残ったまま戻した結果、会話に戻ってしまった */
function expectNoLeadIdInUrl(page: Page): void {
  expect(new URL(page.url()).searchParams.get("lead_id")).toBeNull();
}

test.describe("visual-language: 受信箱 1画面1ページ", () => {
  test("スマホ: 一覧 → 会話 → 一覧 を切り替える", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    // 1. 開いた直後は一覧だけ
    await openInboxList(page);
    await expect(list(page)).toBeVisible();
    await expect(thread(page)).toBeHidden();
    await expect(backButton(page)).toHaveCount(0);
    expectNoLeadIdInUrl(page);

    // 2. 会話を選ぶと会話だけ
    await openConversation(page);
    await expect(thread(page)).toBeVisible();
    await expect(list(page)).toBeHidden();
    const back = backButton(page);
    await expect(back).toBeVisible();

    // 戻るボタンは指で押せる大きさであること
    const box = await back.boundingBox();
    expect(box, "戻るボタンの寸法が取得できない").not.toBeNull();
    expect(box!.width).toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    expect(box!.height).toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);

    // 3. 戻ると一覧だけに戻る（#4165 の退行をここで止める）
    await back.click();
    await expect(list(page)).toBeVisible({ timeout: 10_000 });
    await expect(thread(page)).toBeHidden();
    await expect(backButton(page)).toHaveCount(0);
    expectNoLeadIdInUrl(page);

    // 4. 戻った後にもう一度開ける（一度きりしか動かない状態を弾く）
    await openConversation(page);
    await expect(thread(page)).toBeVisible();
    await expect(list(page)).toBeHidden();
  });

  test("スマホ: 上部のページ名バーが無く、下部タブバーで移動できる", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);

    // 2026-10-13（PO 指定）: 上部のページ名バー（高さ56px）を MobileShell から削除した。
    // 中身はページ名のテキストだけで操作を持たず、空いた高さは一覧に回る。
    await expect(page.locator(".mobile-topbar")).toHaveCount(0);

    // ただし移動手段は失ってはいけない。メニュー（「もっと」シート）を開けるのは
    // 下部タブバーだけなので、タブバーの存在と押せる大きさをここで守る。
    const tabbar = page.locator(".mobile-tabbar");
    await expect(tabbar).toBeVisible();
    const tabs = tabbar.locator("a, button");
    expect(await tabs.count()).toBeGreaterThanOrEqual(2);
    const menuBox = await tabs.last().boundingBox();
    expect(menuBox, "下部タブの寸法が取得できない").not.toBeNull();
    expect(menuBox!.height).toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);

    // ページ名は読み上げ用に残っていること（見出しとして取得できる＝現在地が分かる）
    await expect(page.getByRole("heading", { name: "受信箱" })).toHaveCount(1);
  });

  test("スマホ: 会話を開いている間は下部タブバーが隠れ、戻ると見える", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    // card-a2 §13（PO 2026-11-02）: 会話を開いている間だけ下のメニューを隠す
    await openInboxList(page);
    await expect(page.locator(".mobile-tabbar")).toBeVisible();

    await openConversation(page);
    await expect(page.locator(".mobile-tabbar")).toBeHidden();
    const viewport = page.viewportSize();
    expect(viewport, "viewport が取れない").not.toBeNull();
    const sendBox = await page.locator(".inbox-send-area").boundingBox();
    expect(sendBox, "入力欄の帯の寸法が取得できない").not.toBeNull();
    expect(Math.abs(sendBox!.y + sendBox!.height - viewport!.height), "入力欄の帯の下端が画面の下端と一致しない")
      .toBeLessThanOrEqual(1);

    await backButton(page).click();
    await expect(page.locator(".mobile-tabbar")).toBeVisible();
  });

  test("スマホ: 一覧ではヘッダーの操作行を出さず、絞り込みはヘッダーの右端に出る", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);

    // 2026-10-13（PO 指定）: 一覧では操作行（テンプレート / FAQ / 受信箱の設定）を出さない。
    // 一覧では使い道がなく、その高さを一覧に回す。
    await expect(page.locator(".page-header-actions")).toHaveCount(0);

    // 絞り込みは一覧専用。第2便でヘッダーの右端（お手本の位置）へ移した。一覧では必ず使えること。
    const filterInHeader = page.locator(".inbox-mobile-header .inbox-mobile-filter-toggle");
    await expect(filterInHeader).toBeVisible();

    // 2026-10-13（PO 指定）: 押すと帯が開くのではなく、下から出るシート
    // （Sheet 金型）が出て、選んだら閉じる。
    const sheet = page.locator('[data-testid="sheet-panel"]');
    const sheetOpen = page.locator('[data-testid="sheet-panel"].comp-sheet-panel--open');
    // 帯はスマホでは常に出さない
    await expect(page.locator(".inbox-full-tab-bar")).toBeHidden();
    await expect(sheetOpen).toHaveCount(0);

    // 押すとシートが開く
    await filterInHeader.click();
    await expect(sheetOpen).toHaveCount(1);
    await expect(sheet.getByRole("heading")).toBeVisible();

    // 選ぶと閉じて、絞り込みが効く（印が付く）
    const option = page.locator(".inbox-filter-sheet-option").first();
    await expect(option).toBeVisible();
    const optionBox = await option.boundingBox();
    expect(optionBox, "選択肢の寸法が取れない").not.toBeNull();
    expect(optionBox!.height, "選択肢の高さ").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    await page.locator(".inbox-filter-sheet-option", { hasText: "未読" }).first().click();
    await expect(sheetOpen).toHaveCount(0);
    await expect(filterInHeader).toHaveClass(/has-active/);

    // もう一度開いて背景タップで閉じる
    await filterInHeader.click();
    await expect(sheetOpen).toHaveCount(1);
    await page.locator(".comp-sheet-overlay").click();
    await expect(sheetOpen).toHaveCount(0);

    // 2026-10-14（第6便・PO 決定）: 会話を開いても操作行は出さない（帯を2本から1本に統合）。
    // テンプレート・顧客情報は会話ヘッダーの右に、FAQ・受信箱の設定は「…」に移した
    // （InboxThreadHeaderMobile.tsx・本ファイル下部の「受信箱 第6便」describe を参照）。
    // この assertion は第2便時点の仕様（会話を開くと操作行が出る）を検証していたが、
    // 第6便の PO 決定で逆（出さない）になったためここを更新した。
    await openConversation(page);
    await expect(page.locator(".page-header-actions")).toHaveCount(0);
    // 一覧専用の絞り込みは会話側では見えない（一覧が隠れているため）
    await expect(filterInHeader).toBeHidden();
  });

  test("スマホ: 地が1色・左右対称・12px文字のコントラストが基準以上", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);

    // 2026-10-13: 実機の画素を数えて分かった3点を、ここで数値として固定する。
    //   ① 行の左右の余白が対称（以前は左12px・右0px の非対称だった）
    //   ② 12px の副文字が 4.5:1 以上（以前は --text-muted で 3.74:1）
    //   ③ 一覧の面が画面の下まで伸びる（以前は下の空き領域にページの地が出て
    //      地が2色に割れていた。実測 45.9% + 44.0%）
    const row = page.locator("button.conversation-item").first();
    const panel = page.locator(".inbox-left-panel");

    // ① 行の左端と右端の余白が同じ（左右対称）
    const geo = await page.evaluate(() => {
      const el = document.querySelector("button.conversation-item") as HTMLElement | null;
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { left: Math.round(r.left), right: Math.round(window.innerWidth - r.right) };
    });
    expect(geo, "会話の行が見つからない").not.toBeNull();
    expect(geo!.left, "行の左の余白").toBe(geo!.right);

    // ② 12px の文字（時刻・プレビュー）の明暗差が 4.5:1 以上
    const contrast = await page.evaluate(() => {
      const lum = (c: string) => {
        const m = c.match(/\d+/g);
        if (!m) return null;
        const [r, g, b] = m.slice(0, 3).map((v) => {
          const x = Number(v) / 255;
          return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
        });
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
      };
      const el = document.querySelector(".conv-preview-text") as HTMLElement | null;
      if (!el) return null;
      const fg = lum(getComputedStyle(el).color);
      // 背景は祖先をたどって透明でない最初の色を使う
      let node: HTMLElement | null = el;
      let bg: number | null = null;
      while (node) {
        const c = getComputedStyle(node).backgroundColor;
        if (c && c !== "rgba(0, 0, 0, 0)" && c !== "transparent") { bg = lum(c); break; }
        node = node.parentElement;
      }
      if (fg === null || bg === null) return null;
      const hi = Math.max(fg, bg), lo = Math.min(fg, bg);
      return Math.round(((hi + 0.05) / (lo + 0.05)) * 100) / 100;
    });
    expect(contrast, "プレビュー文の明暗差が測れない").not.toBeNull();
    expect(contrast!, "12px の副文字の明暗差").toBeGreaterThanOrEqual(4.5);

    // ③ 地が1色であること。
    //    一覧の面は画面の高さまで伸びていない（この検査環境では画面の約34%で止まる）。
    //    根因は wrapper の height:100% が親まで届かないことだが、直すと
    //    PageLayout / MobileShell という全ページ共通の部品に波及するため、
    //    本便では「覆われていない領域の色を一覧の面と同じにする」方針を採った
    //    （design: docs/handoff/inbox-mobile-polish/design.md §2-1・§7-1）。
    //    したがってここで検査するのは高さではなく**色が同じであること**。
    const ground = await page.evaluate(() => {
      const wrap = document.querySelector(".inbox-wrapper") as HTMLElement | null;
      const panel = document.querySelector(".inbox-left-panel") as HTMLElement | null;
      if (!wrap || !panel) return null;
      return {
        wrapper: getComputedStyle(wrap).backgroundColor,
        panel: getComputedStyle(panel).backgroundColor,
      };
    });
    expect(ground, "受信箱の下地が測れない").not.toBeNull();
    expect(ground!.wrapper, "下地が透明のままだと一覧の下にページの地が出る").not.toBe("rgba(0, 0, 0, 0)");
    expect(ground!.wrapper, "下地と一覧の面の色が違うと地が2色に割れる").toBe(ground!.panel);

    // ④ 面の色が画面の下端近くまで届いていること（2026-10-13・PO 指定）。
    //    お手本（WhatsApp のチャット一覧・ライト）は一覧の面が画面の上端から
    //    下端まで1色（実測 白 79.76%・全幅を占める範囲 y=111〜2129）。
    //    当方は投入前 白 45.7% ／ ページの地 44.1% で、地が出ていたのは
    //    一覧の最後の行より下（231dp）だった。
    //    どの段で高さが切れているか後から分かるよう、鎖の各段を記録に残す。
    const chain = await page.evaluate(() => {
      const pick = (sel: string) => {
        const el = document.querySelector(sel) as HTMLElement | null;
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return {
          top: Math.round(r.top),
          bottom: Math.round(r.bottom),
          height: Math.round(r.height),
          background: getComputedStyle(el).backgroundColor,
        };
      };
      return {
        viewport: window.innerHeight,
        mobileContent: pick(".mobile-content"),
        pageLayout: pick(".page-layout"),
        pageContent: pick(".page-layout-content"),
        wrapper: pick(".inbox-wrapper"),
        leftPanel: pick(".inbox-left-panel"),
      };
    });
    await testInfo.attach("height-chain", {
      body: JSON.stringify(chain, null, 2),
      contentType: "application/json",
    });
    // 面の色を敷いている要素のうち、最も下まで届いているものを見る
    const painted = [chain.pageContent, chain.wrapper, chain.leftPanel]
      .filter((e): e is NonNullable<typeof e> => e !== null && e.background !== "rgba(0, 0, 0, 0)")
      .map((e) => e.bottom);
    expect(painted.length, "面の色を敷いた要素が1つも見つからない").toBeGreaterThan(0);
    expect(Math.max(...painted), "面の色が画面の7割より下まで届いていない").toBeGreaterThan(
      chain.viewport * 0.7,
    );

    await expect(row).toBeVisible();
    await expect(panel).toBeVisible();
  });

  test("スマホ: 名前と本文に大きさと太さの段差がある", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);

    // 2026-10-13: お手本（WhatsApp のチャット一覧）を同じ文字種どうしで実測すると
    //   日付のインク高さ 28px ／ 名前 37px ＝ 名前は日付の 1.32 倍
    //   線の太さ: 名前 6.0px ／ 本文 4.0px ＝ 1.5 倍
    // 当方は投入前 名前 14.4px/400・本文 12px/400 ＝ 大きさ 1.2 倍・太さの差なし。
    // 名前を 16px/600 にして段差を付けた（16÷12 = 1.33 でお手本に一致）。
    // 未読の行は名前も本文も 700（既存仕様 InboxPage.css の .conv-name.unread /
    // .conv-preview-text.unread）。太さの段差は**既読の行**で見る。
    // 検査データ（mock-conversations.json）には既読の会話が1件ある（lead 5003・未読0）。
    const type = await page.evaluate(() => {
      const read = (sel: string) => {
        const el = document.querySelector(sel) as HTMLElement | null;
        if (!el) return null;
        const st = getComputedStyle(el);
        return { fontSize: parseFloat(st.fontSize), fontWeight: Number(st.fontWeight) };
      };
      return {
        既読の名前: read(".conv-name:not(.unread)"),
        既読の本文: read(".conv-preview-text:not(.unread)"),
        未読の名前: read(".conv-name.unread"),
        未読の本文: read(".conv-preview-text.unread"),
        時刻: read(".conv-time"),
      };
    });
    await testInfo.attach("type-scale", { body: JSON.stringify(type, null, 2), contentType: "application/json" });
    const nameRead = type["既読の名前"];
    const prevRead = type["既読の本文"];
    expect(nameRead, "既読の行の名前が見つからない").not.toBeNull();
    expect(prevRead, "既読の行の本文が見つからない").not.toBeNull();
    // 大きさの段差（お手本 1.32 倍）。未読・既読で大きさは変わらない
    expect(nameRead!.fontSize / prevRead!.fontSize).toBeGreaterThanOrEqual(1.3);
    // 太さの段差（お手本は線幅 1.5 倍）。既読の行で名前が本文より重いこと
    expect(nameRead!.fontWeight).toBeGreaterThan(prevRead!.fontWeight);

    // ダークモードでも役割の割り当てが崩れないことを確認する。
    // このアプリは OS 設定を無視しアプリ設定（users.theme）で切り替えるため
    // （src/index.css:212 / src/contexts/ThemeContext.tsx:15）、実機では
    // 利用者の保存設定を書き換えないと測れない。検査では force-dark クラスを
    // 直接付けて測り、DB には一切触らない。
    const dark = await page.evaluate(() => {
      document.documentElement.classList.add("force-dark");
      const lum = (c: string) => {
        const m = c.match(/\d+/g);
        if (!m) return null;
        const [r, g, b] = m.slice(0, 3).map((v) => {
          const x = Number(v) / 255;
          return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
        });
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
      };
      const ratio = (fg: string, bg: string) => {
        const a = lum(fg), b = lum(bg);
        if (a === null || b === null) return null;
        const hi = Math.max(a, b), lo = Math.min(a, b);
        return Math.round(((hi + 0.05) / (lo + 0.05)) * 100) / 100;
      };
      const panel = document.querySelector(".inbox-left-panel") as HTMLElement | null;
      const prev = document.querySelector(".conv-preview-text") as HTMLElement | null;
      const nameEl = document.querySelector(".conv-name") as HTMLElement | null;
      const bg = panel ? getComputedStyle(panel).backgroundColor : "";
      const out = {
        panelBackground: bg,
        previewContrast: prev ? ratio(getComputedStyle(prev).color, bg) : null,
        nameContrast: nameEl ? ratio(getComputedStyle(nameEl).color, bg) : null,
      };
      document.documentElement.classList.remove("force-dark");
      return out;
    });
    await testInfo.attach("dark-mode-contrast", { body: JSON.stringify(dark, null, 2), contentType: "application/json" });
    // ダークでも 12px の副文字が本文の基準を満たすこと
    expect(dark.previewContrast, "ダークの副文字の明暗差が測れない").not.toBeNull();
    expect(dark.previewContrast!, "ダークの副文字の明暗差").toBeGreaterThanOrEqual(4.5);
    expect(dark.nameContrast!, "ダークの名前の明暗差").toBeGreaterThanOrEqual(4.5);
  });

  test("スマホ: 主要な操作ボタンが44px以上", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);

    // 2026-10-13（WCAG 2.5.5）: 押す場所を 44px 以上にする。
    // ピルの外側にある3つを 44px（--size-icon-btn-lg）にした。
    // 一覧では絞り込み、会話ではスレッドの操作と送信を測る。
    const measure = async (sel: string) => {
      const box = await page.locator(sel).first().boundingBox();
      return box ? { w: Math.round(box.width), h: Math.round(box.height) } : null;
    };

    const filter = await measure(".inbox-mobile-header .inbox-mobile-filter-toggle");
    expect(filter, "絞り込みボタンが見つからない").not.toBeNull();

    await openConversation(page);
    const sendBtn = await measure(".inbox-send-btn");
    // 第6便（2026-10-14）: スマホの会話ヘッダーを作り直したため、旧ヘッダーの
    // ボタン（.karte-toggle-btn / .inbox-header-menu-btn）はスマホには存在しない。
    // 新しいヘッダー（.inbox-thread-header-mobile）のボタンを測る。
    //   旧 .inbox-header-menu-btn（三点）は実機実測で 27x38dp・画面右端で切れていたが、
    //   第6便で**スマホでは廃止**した（中身は第4便で一覧の長押しメニューへ移設済み）。
    const karteToggle = await measure(".inbox-thread-header-mobile-btn[aria-label='顧客情報']");
    const headerMore = await measure(".inbox-thread-header-mobile-btn[aria-label='その他の操作']");
    // 本便で変更していないものも値を記録に残す（design §7）。
    //   .send-attach-btn … 送信ピルの内側（44px にするとピルが膨らむ）
    const attach = await measure(".send-attach-btn");
    // スマホでは旧三点が存在しないことを機械で確かめる（作り直しの証拠）
    const oldMenuCount = await page.locator(".inbox-header-menu-btn").count();
    expect(oldMenuCount, "スマホに旧三点メニューが残っている").toBe(0);

    await testInfo.attach("touch-targets", {
      body: JSON.stringify(
        {
          絞り込み: filter,
          送信: sendBtn,
          顧客情報: karteToggle,
          "その他の操作": headerMore,
          "添付（この便では未対応）": attach,
          "旧三点メニュー（第6便でスマホでは廃止）": oldMenuCount,
        },
        null,
        2,
      ),
      contentType: "application/json",
    });

    expect(filter!.w, "絞り込みの幅").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    expect(filter!.h, "絞り込みの高さ").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    expect(sendBtn, "送信ボタンが見つからない").not.toBeNull();
    expect(sendBtn!.w, "送信の幅").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    expect(sendBtn!.h, "送信の高さ").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    expect(karteToggle, "顧客情報ボタンが見つからない").not.toBeNull();
    // 幅はアイコンと文言に任せるため高さだけを基準にする
    expect(karteToggle!.h, "顧客情報ボタンの高さ").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    // 第6便: 旧三点の置き換えである「その他の操作」も 44px 以上であること
    expect(headerMore, "その他の操作ボタンが見つからない").not.toBeNull();
    expect(headerMore!.w, "その他の操作の幅").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    expect(headerMore!.h, "その他の操作の高さ").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
  });

  test("スマホ: 検索欄の2つのボタンが別のアイコンで、管理は文言を出さない", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);

    // 2026-10-13（PO 指摘）: 検索欄の右に同じ filter アイコンが2つ並んで区別できなかった。
    // 管理ボタンを「選択モード」の通例である丸いチェック（outline）に差し替え、
    // スマホでは文言を隠してアイコンだけにした。
    const info = await page.evaluate(() => {
      const pick = (sel: string) => {
        const el = document.querySelector(sel) as HTMLElement | null;
        if (!el) return null;
        const svg = el.querySelector("svg");
        return {
          // svg の中身（path の d 属性）が同じなら同じアイコン
          icon: svg ? Array.from(svg.querySelectorAll("path")).map((p) => p.getAttribute("d")).join("|") : null,
          accessibleName: el.getAttribute("aria-label"),
          visibleText: (el.innerText || "").trim(),
        };
      };
      return {
        filter: pick(".inbox-mobile-header .inbox-mobile-filter-toggle"),
        manage: pick(".inbox-manage-btn"),
      };
    });
    await testInfo.attach("search-row-buttons", {
      body: JSON.stringify(
        {
          filter: { ...info.filter, icon: info.filter?.icon?.slice(0, 40) },
          manage: { ...info.manage, icon: info.manage?.icon?.slice(0, 40) },
        },
        null,
        2,
      ),
      contentType: "application/json",
    });

    expect(info.filter, "絞り込みボタンが見つからない").not.toBeNull();
    expect(info.manage, "管理ボタンが見つからない").not.toBeNull();
    // 1. 2つのアイコンが別物であること（同じ図形を2つ並べない）
    expect(info.manage!.icon, "管理のアイコンが取れない").not.toBeNull();
    expect(info.manage!.icon).not.toBe(info.filter!.icon);
    // 2. 管理はスマホで文言を出さない
    expect(info.manage!.visibleText, "管理の文言がスマホで出ている").toBe("");
    // 3. 文言が無くても読み上げで分かること
    expect(info.manage!.accessibleName, "管理の読み上げ名が無い").toBeTruthy();

    // 4. 押す場所が 44px 以上（WCAG 2.5.5）。PR 4204 では対象から漏れていた
    //    （padding で寸法が決まるため width/height の grep で拾えなかった）。
    //    文言を隠すと幅も狭くなるので、ここで必ず確認する。
    const manageBox = await page.locator(".inbox-manage-btn").first().boundingBox();
    expect(manageBox, "管理ボタンの寸法が取れない").not.toBeNull();
    expect(Math.round(manageBox!.width), "管理ボタンの幅").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    expect(Math.round(manageBox!.height), "管理ボタンの高さ").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
  });

  test("スマホ: 一覧の上にヘッダーが出て、検索欄が横幅いっぱいのピルになる", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);

    // 2026-10-13（第2便）: お手本（WhatsApp チャット一覧・ライト・360dp幅）を実測して
    // 合わせた値（design: docs/handoff/app-visual-language/card-stage4b-inbox-mobile.md §16）。
    // この project（vl-mobile-390）は幅390pxでお手本の360dpとは異なるため、
    // 幅に依存する値は viewportSize() から取った幅を基準に相対で判定する。
    const viewport = page.viewportSize();
    expect(viewport, "viewport のサイズが取れない").not.toBeNull();
    const viewportWidth = viewport!.width;

    const header = page.locator(".inbox-mobile-header");
    const title = page.locator(".inbox-mobile-header-title");
    const filter = page.locator(".inbox-mobile-header .inbox-mobile-filter-toggle");
    const manage = page.locator(".inbox-mobile-header .inbox-manage-btn");
    const searchInput = page.locator(".inbox-mobile-search-row .inbox-search-input");

    // 隠れている可能性のある要素は isVisible() を見てから測る
    // （boundingBox() は要素が見えるまで待って actionTimeout で落ちる）。
    for (const [name, loc] of [
      ["header", header],
      ["title", title],
      ["filter", filter],
      ["manage", manage],
      ["searchInput", searchInput],
    ] as const) {
      expect(await loc.isVisible(), `${name} が見えない`).toBe(true);
    }

    const headerBox = await header.boundingBox();
    const titleBox = await title.boundingBox();
    const filterBox = await filter.boundingBox();
    const manageBox = await manage.boundingBox();
    const searchInputBox = await searchInput.boundingBox();
    expect(headerBox, "ヘッダーの寸法が取れない").not.toBeNull();
    expect(titleBox, "タイトルの寸法が取れない").not.toBeNull();
    expect(filterBox, "絞り込みボタンの寸法が取れない").not.toBeNull();
    expect(manageBox, "管理ボタンの寸法が取れない").not.toBeNull();
    expect(searchInputBox, "検索欄の寸法が取れない").not.toBeNull();

    const titleFontSize = await title.evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
    const searchInputRadius = await searchInput.evaluate((el) => parseFloat(getComputedStyle(el).borderRadius));
    const headingCount = await page.getByRole("heading", { name: "受信箱" }).count();

    await testInfo.attach("mobile-header-measurements", {
      body: JSON.stringify(
        {
          viewportWidth,
          header: headerBox,
          title: { ...titleBox, fontSize: titleFontSize },
          filter: filterBox,
          manage: manageBox,
          searchInput: { ...searchInputBox, borderRadius: searchInputRadius },
          headingCount,
        },
        null,
        2,
      ),
      contentType: "application/json",
    });

    // ヘッダー全体の高さ 56px（--topbar-height）
    expect(Math.abs(headerBox!.height - 56), "ヘッダーの高さ").toBeLessThanOrEqual(1);

    // タイトルの左端 x = 16px（--space-4）
    expect(Math.abs(titleBox!.x - 16), "タイトルの左端 x").toBeLessThanOrEqual(1);

    // タイトルの文字サイズ 21px（--font-title-mobile）。
    // お手本の漢字インク 19.0dp に合わせた値（第3便で 20→21。字種をそろえて測り直した結果、
    // --font-xl の20pxでは漢字インクが18.0dpで1dp足りなかった）。
    expect(titleFontSize, "タイトルの文字サイズ").toBe(21);

    // ヘッダー内の押せる部品2つ（絞り込み・管理）は 44px 以上×44px 以上（WCAG 2.5.5）
    expect(filterBox!.width, "絞り込みの幅").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    expect(filterBox!.height, "絞り込みの高さ").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    expect(manageBox!.width, "管理の幅").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    expect(manageBox!.height, "管理の高さ").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);

    // ヘッダーの最後の部品（管理ボタン）の右端 = ビューポート右端（お手本の右端寄せ）
    const headerLastRight = manageBox!.x + manageBox!.width;
    expect(Math.abs(headerLastRight - viewportWidth), "ヘッダー最後の部品の右端").toBeLessThanOrEqual(1);

    // 検索欄の高さ 48px（--comp-btn-height-lg）
    expect(Math.abs(searchInputBox!.height - 48), "検索欄の高さ").toBeLessThanOrEqual(1);

    // 検索欄の左端 12px（--space-3）・右端はビューポート幅-12px（横幅いっぱい）
    expect(Math.abs(searchInputBox!.x - 12), "検索欄の左端").toBeLessThanOrEqual(1);
    const searchInputRight = searchInputBox!.x + searchInputBox!.width;
    expect(Math.abs(searchInputRight - (viewportWidth - 12)), "検索欄の右端").toBeLessThanOrEqual(1);

    // 検索欄の丸み: 高さの半分以上（48px 高に対し 24px 以上）＝完全なピル。
    // --radius-full（9999px）は computed でそのまま返るため数値として比較する。
    expect(searchInputRadius, "検索欄の丸み").toBeGreaterThanOrEqual(searchInputBox!.height / 2);

    // ヘッダーの下端と検索欄（入力欄）の上端の間が 4px（--space-1。今便で padding-top に追加）
    const gap = searchInputBox!.y - (headerBox!.y + headerBox!.height);
    expect(Math.abs(gap - 4), "ヘッダーと検索欄の間").toBeLessThanOrEqual(1);

    // 見出しの二重がないこと（新ヘッダーのタイトルは aria-hidden の span なので増えない）
    expect(headingCount, "「受信箱」の見出しが複数ある").toBe(1);
  });

  test("スマホ: 一覧をスクロールしてもヘッダーが動かない", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    // 2026-10-14（第3便）: 当初「スクロール箱は .inbox-left-panel」という推測で
    // sticky を足したが誤りだった（CI がこの検査の関所の行で検出）。直した先として
    // 一旦は「スクロール箱は .inbox-conversation-list」と決め打ちしたが、要素名を
    // 決め打ちすると将来別の箇所がスクロールを持つようになったときに追従できない。
    // そのため下の 1. では要素名を書かず「実際に scrollHeight > clientHeight かつ
    // overflow-y が auto/scroll の最初の祖先」をブラウザ内で探して使う形にしている。
    // ヘッダー（.inbox-mobile-header）と検索欄（.inbox-mobile-search-row）は
    // InboxConversationListMobile.tsx 内で一覧の行より外側（flex の兄弟要素として前）に
    // 置かれているため、どの要素が実際にスクロールしても「ヘッダーと検索欄は動かない」
    // ことが構造上の事実（frontend/src/pages/inbox/InboxPage.css:82-91・252-256）。
    // お手本（WhatsApp）は検索欄が一覧と一緒に流れるが、当方は検索欄もヘッダーと
    // 同じ外側にあるため両方固定側になる。これは意図した差ではなく構造上そうなる
    // というだけだが、現状の事実としてここで記録する。
    const SCROLL_PX = 600;
    // 画面が埋まる行数より十分多い件数（inbox-helpers.ts の manyConversations
    // コメントに根拠を記載）。20件あれば確実にスクロールが出る。
    await openInboxListWithConversations(page, 20);

    const header = page.locator(".inbox-mobile-header");
    const manage = page.locator(".inbox-mobile-header .inbox-manage-btn");
    const searchRow = page.locator(".inbox-mobile-search-row");
    const firstRow = page.locator("button.conversation-item").first();

    const viewport = page.viewportSize();
    expect(viewport, "viewport のサイズが取れない").not.toBeNull();
    const viewportWidth = viewport!.width;

    // 1. 「実際にスクロールしている箱」をブラウザの中で特定する。
    //    どの要素がスクロールするかは CSS の積み重ねで決まり、読んだだけでは
    //    確実に言えない（第3便で .inbox-left-panel → .inbox-conversation-list と
    //    二度推測を外した）。行から親をたどって、本当に中身があふれている最初の
    //    箱を選ぶ。見つからなければページ全体（scrollingElement）を使う。
    //    どれがスクロールしても「ヘッダーは動かない」ことがこの検査の要件なので、
    //    箱を決め打ちしないこの形が要件に一致する。
    const scrollInfo = await page.evaluate(() => {
      const row = document.querySelector("button.conversation-item");
      const chain: Array<{ sel: string; scrollH: number; clientH: number; overflowY: string }> = [];
      let el: HTMLElement | null = row?.parentElement ?? null;
      let found: HTMLElement | null = null;
      while (el) {
        const cs = getComputedStyle(el);
        const sel =
          el.className && typeof el.className === "string"
            ? `${el.tagName.toLowerCase()}.${el.className.trim().split(/\s+/).join(".")}`
            : el.tagName.toLowerCase();
        chain.push({ sel, scrollH: el.scrollHeight, clientH: el.clientHeight, overflowY: cs.overflowY });
        if (!found && el.scrollHeight > el.clientHeight + 1 && /(auto|scroll)/.test(cs.overflowY)) {
          found = el;
          el.setAttribute("data-vl-scrollbox", "1");
        }
        el = el.parentElement;
      }
      const doc = document.scrollingElement as HTMLElement | null;
      const pageScrollable = doc ? doc.scrollHeight > doc.clientHeight + 1 : false;
      if (!found && doc && pageScrollable) doc.setAttribute("data-vl-scrollbox", "1");
      return {
        chain,
        usedSelector: found ? chain.find((c) => c.scrollH > c.clientH + 1)?.sel ?? null : "scrollingElement",
        pageScrollHeight: doc?.scrollHeight ?? null,
        pageClientHeight: doc?.clientHeight ?? null,
        rowCount: document.querySelectorAll("button.conversation-item").length,
      };
    });
    await testInfo.attach("scroll-box-detection", {
      body: JSON.stringify(scrollInfo, null, 2),
      contentType: "application/json",
    });

    const scrollBox = page.locator("[data-vl-scrollbox]").first();
    const scrollable = (await scrollBox.count()) > 0;
    expect(
      scrollable,
      `スクロールできる箱が1つも無い（検査データが足りない）。行数=${scrollInfo.rowCount} / 親の連なり=${JSON.stringify(scrollInfo.chain)}`,
    ).toBe(true);

    // 2. スクロール前の寸法を記録
    const headerBoxBefore = await header.boundingBox();
    const manageBoxBefore = await manage.boundingBox();
    const searchRowBoxBefore = await searchRow.boundingBox();
    const firstRowBoxBefore = await firstRow.boundingBox();
    expect(headerBoxBefore, "スクロール前のヘッダーの寸法が取れない").not.toBeNull();
    expect(manageBoxBefore, "スクロール前の管理ボタンの寸法が取れない").not.toBeNull();
    expect(searchRowBoxBefore, "スクロール前の検索欄の寸法が取れない").not.toBeNull();
    expect(firstRowBoxBefore, "スクロール前の1行目の寸法が取れない").not.toBeNull();

    // 3. 特定したスクロール箱を600pxスクロールする
    await scrollBox.evaluate((el, y) => { el.scrollTop = y; }, SCROLL_PX);
    await expect
      .poll(() => scrollBox.evaluate((el) => el.scrollTop), "scrollTop が反映されるまで待つ")
      .toBeGreaterThan(0);

    // 4. スクロール後の寸法を記録
    const headerBoxAfter = await header.boundingBox();
    const manageBoxAfter = await manage.boundingBox();
    const searchRowBoxAfter = await searchRow.boundingBox();
    const firstRowBoxAfter = await firstRow.boundingBox();
    const scrollTopAfter = await scrollBox.evaluate((el) => el.scrollTop);

    await testInfo.attach("sticky-header-scroll", {
      body: JSON.stringify(
        {
          scrollTopAfter,
          viewportWidth,
          headerBoxBefore,
          headerBoxAfter,
          manageBoxBefore,
          manageBoxAfter,
          searchRowBoxBefore,
          searchRowBoxAfter,
          firstRowBoxBefore,
          firstRowBoxAfter,
        },
        null,
        2,
      ),
      contentType: "application/json",
    });

    expect(headerBoxAfter, "スクロール後のヘッダーの寸法が取れない").not.toBeNull();
    expect(manageBoxAfter, "スクロール後の管理ボタンの寸法が取れない").not.toBeNull();
    expect(searchRowBoxAfter, "スクロール後の検索欄の寸法が取れない").not.toBeNull();
    expect(firstRowBoxAfter, "スクロール後の1行目の寸法が取れない").not.toBeNull();

    // 5. ヘッダーのy・高さが変わっていない（±1px）
    expect(Math.abs(headerBoxAfter!.y - headerBoxBefore!.y), "ヘッダーのyが動いた").toBeLessThanOrEqual(1);
    expect(
      Math.abs(headerBoxAfter!.height - headerBoxBefore!.height),
      "ヘッダーの高さが変わった",
    ).toBeLessThanOrEqual(1);

    // 6. 検索欄のyも変わっていない（±1px）。当方はヘッダーと同じくスクロール箱の
    //    外側にあるため動かない（お手本は検索欄が一覧と一緒に流れる＝当方との差。
    //    設計の意図ではなく構造上そうなっているだけなので、揃えるなら別便で判断する）
    expect(Math.abs(searchRowBoxAfter!.y - searchRowBoxBefore!.y), "検索欄のyが動いた").toBeLessThanOrEqual(1);

    // 7. ヘッダー右端のボタン（管理）の右端がビューポート右端のまま（±1px）
    const manageRightAfter = manageBoxAfter!.x + manageBoxAfter!.width;
    expect(Math.abs(manageRightAfter - viewportWidth), "管理ボタンの右端がビューポート右端からずれた").toBeLessThanOrEqual(1);

    // 8. 一覧が実際に動いた証拠: 1行目のyがスクロール前より小さくなっている（上へ流れた）
    expect(firstRowBoxAfter!.y, "1行目が上へ流れていない").toBeLessThan(firstRowBoxBefore!.y);

    // 9. スクロールが本当に効いた証拠: scrollTop が0より大きい。
    //    どの箱がスクロールするかで到達できる量が変わる（中身の高さで頭打ちになる）ため、
    //    600ちょうどは要求しない。実際の値は上の添付に残している。
    expect(scrollTopAfter, "scrollTop が0のまま＝スクロールが効いていない").toBeGreaterThan(0);
  });

  test("PC・タブレット: 一覧と会話が同時に見え、戻るボタンは出ない", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) <= MOBILE_MAX_PX, "スマホ用レイアウトの幅は対象外");

    await openInboxList(page);
    await expect(list(page)).toBeVisible();
    await expect(thread(page)).toBeVisible();

    await openConversation(page);
    // 選んでも一覧は消えない（PC の操作感を変えていないことの確認）
    await expect(list(page)).toBeVisible();
    await expect(thread(page)).toBeVisible();
    await expect(page.locator("button.conversation-item", { hasText: SAMPLE_CONVERSATION_NAME })).toBeVisible();
    // 戻るボタンは DOM にはあるが表示しない
    await expect(backButton(page)).toBeHidden();
    // モバイル専用の殻（MobileShell）は 768px 以上では描かれない＝PC 側は無関係
    await expect(page.locator(".mobile-tabbar")).toHaveCount(0);
    await expect(page.locator(".mobile-topbar")).toHaveCount(0);
    // スマホ専用に新設した会話一覧ヘッダー（第2便）も PC・タブレットには出ない
    await expect(page.locator(".inbox-mobile-header")).toHaveCount(0);
    // ヘッダーの操作行は PC・タブレットでは一覧を見ているときも出す（従来どおり）
    await expect(page.locator(".page-header-actions")).toHaveCount(1);
    // 管理ボタンの文言は PC・タブレットでは出す（スマホだけ隠す）
    await expect(page.locator(".inbox-manage-btn .inbox-manage-label")).toBeVisible();
    // 絞り込みボタンは DOM にはあるが PC・タブレットでは表示しない
    await expect(page.locator(".inbox-search-row .inbox-mobile-filter-toggle")).toBeHidden();
    // PC・タブレットでは帯が常時出て、シートは開かない
    await expect(page.locator(".inbox-full-tab-bar")).toBeVisible();
    await expect(page.locator('[data-testid="sheet-panel"].comp-sheet-panel--open')).toHaveCount(0);
  });
});

test.describe("visual-language: 受信箱 第4便（一覧の行を長押しするとメニューを出す）", () => {
  const row = (page: Page): Locator =>
    page.locator("button.conversation-item", { hasText: SAMPLE_CONVERSATION_NAME });
  const menu = (page: Page): Locator => page.locator(".comp-context-menu");
  const menuItems = (page: Page): Locator => menu(page).locator('[role="menuitem"]');

  test("スマホ: 行を長押しするとメニューが出て、項目は3つ・文言と押す場所が仕様どおり", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);
    const theRow = row(page);
    const rowBoxBefore = await theRow.boundingBox();
    expect(rowBoxBefore, "行の矩形が取れない").not.toBeNull();

    await longPressRow(page, theRow);
    await expect(menu(page)).toBeVisible();

    // 2. 項目が3つで、文言が「未読にする」「対象外にする」「削除」であること
    const items = menuItems(page);
    await expect(items).toHaveCount(3);
    const labels = await items.allTextContents();
    expect(labels).toEqual(["未読にする", "対象外にする", "削除"]);

    // 3. 各項目の押す場所が44px以上
    const itemBoxes = await Promise.all(
      (await items.all()).map((it) => it.boundingBox()),
    );
    for (const box of itemBoxes) {
      expect(box, "メニュー項目の矩形が取れない").not.toBeNull();
      expect(box!.height, "メニュー項目の高さ").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    }

    // 4. メニューが押した行の近くに出て、画面からはみ出していない
    const menuBox = await menu(page).boundingBox();
    expect(menuBox, "メニューの矩形が取れない").not.toBeNull();
    const viewport = page.viewportSize();
    expect(viewport, "viewport のサイズが取れない").not.toBeNull();
    expect(overlapsOrAdjacent(menuBox!, rowBoxBefore!), "メニューが行の近くに出ていない").toBe(true);
    expect(menuBox!.x, "メニューの左端").toBeGreaterThanOrEqual(0);
    expect(menuBox!.x + menuBox!.width, "メニューの右端").toBeLessThanOrEqual(viewport!.width);
    expect(menuBox!.y + menuBox!.height, "メニューの下端").toBeLessThanOrEqual(viewport!.height);

    await testInfo.attach("row-context-menu", {
      body: JSON.stringify({ row: rowBoxBefore, menu: menuBox, items: itemBoxes, labels }, null, 2),
      contentType: "application/json",
    });

    // 長押し中に mouse.down() のままだったので、ここで離す（後続テストへの影響防止）
    await page.mouse.up();
  });

  test("スマホ: 長押ししただけでは会話が開かない（一覧のまま）", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);
    await longPressRow(page, row(page));
    await expect(menu(page)).toBeVisible();
    await page.mouse.up();

    // 長押し成立後に続く click は無効化される（useLongPress.ts）→ 会話は開かない
    await expect(page.locator(".inbox-textarea")).toHaveCount(0);
    await expect(page.locator(".inbox-left-panel")).toBeVisible();
  });

  test("スマホ: 普通のタップでは今までどおり会話が開く（退行していない）", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);
    await openConversation(page); // 内部で row.click() → .inbox-textarea が出るまで待つ
    await expect(page.locator(".inbox-textarea")).toBeVisible();
  });

  test("スマホ: 外側を押すとメニューが閉じる", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);
    await longPressRow(page, row(page));
    await expect(menu(page)).toBeVisible();
    await page.mouse.up();

    // ヘッダーのタイトル（メニュー・行のどちらでもない場所）を押す
    await page.locator(".inbox-mobile-header-title").click({ force: true });
    await expect(menu(page)).toHaveCount(0);
  });

  test("スマホ: 選択モードでは長押しでメニューが出ない", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);
    await page.locator(".inbox-manage-btn").click();
    await expect(page.locator(".inbox-bulk-bar")).toBeVisible();

    await longPressRow(page, row(page));
    await page.mouse.up();
    await expect(menu(page)).toHaveCount(0);
  });

  test("スマホ: 「未読にする」を押すと mark-unread が呼ばれ、対象 lead id が渡る", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    const calls: number[] = [];
    await installAuthBypass(page);
    await mockApi(page, {
      ...baseMocks(),
      "POST /leads/5001/messages/mark-unread": async (route) => {
        calls.push(5001);
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ unmarked_count: 1 }),
        });
      },
    });
    await page.goto("/lead-chat");
    await expect(page.getByRole("heading", { name: "受信箱" })).toBeVisible({ timeout: 20_000 });
    await expect(row(page)).toBeVisible({ timeout: 10_000 });

    await longPressRow(page, row(page));
    await expect(menu(page)).toBeVisible();
    await page.mouse.up();

    await menuItems(page).filter({ hasText: "未読にする" }).click();
    await expect(menu(page)).toHaveCount(0);
    await expect.poll(() => calls.length, { message: "mark-unread が呼ばれていない" }).toBe(1);

    await testInfo.attach("mark-unread-calls", {
      body: JSON.stringify(calls, null, 2),
      contentType: "application/json",
    });
    expect(calls).toEqual([5001]);
  });
});

test.describe("visual-language: 受信箱 第5便（メニューを左側に出し、長押しの文字選択を止める）", () => {
  const row = (page: Page): Locator =>
    page.locator("button.conversation-item", { hasText: SAMPLE_CONVERSATION_NAME });
  const menu = (page: Page): Locator => page.locator(".comp-context-menu");

  test("スマホ: メニューの左端が画面左から --space-3 の余白に出る（PO 指摘・右側だと押しづらい）", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);
    const theRow = row(page);
    const rowBoxBefore = await theRow.boundingBox();
    expect(rowBoxBefore, "行の矩形が取れない").not.toBeNull();

    await longPressRow(page, theRow);
    await expect(menu(page)).toBeVisible();
    await page.mouse.up();

    // ContextMenu.tsx の align="left" は --space-3 トークンの値を左端の余白に使う。
    // ここでは実際にそのトークンの値を読んで比べる（固定の 12 を書かない）。
    const spaceToken = await page.evaluate(() =>
      Number.parseFloat(
        getComputedStyle(document.documentElement).getPropertyValue("--space-3").trim(),
      ),
    );
    expect(Number.isFinite(spaceToken), "--space-3 トークンが読めない").toBe(true);

    const menuBox = await menu(page).boundingBox();
    expect(menuBox, "メニューの矩形が取れない").not.toBeNull();

    // 1. 左端が --space-3 の余白（±1px）であること＝左側に出ていること
    expect(menuBox!.x, "メニューの左端").toBeGreaterThanOrEqual(spaceToken - 1);
    expect(menuBox!.x, "メニューの左端").toBeLessThanOrEqual(spaceToken + 1);

    // 2. 画面内に収まっていること（従来どおり）
    const viewport = page.viewportSize();
    expect(viewport, "viewport のサイズが取れない").not.toBeNull();
    expect(menuBox!.x, "メニューの左端").toBeGreaterThanOrEqual(0);
    expect(menuBox!.x + menuBox!.width, "メニューの右端").toBeLessThanOrEqual(viewport!.width);
    expect(menuBox!.y + menuBox!.height, "メニューの下端").toBeLessThanOrEqual(viewport!.height);

    // 3. 縦位置は従来どおり：押した行の近くに出ること（横位置が変わっても縦は変えない）
    expect(
      overlapsOrAdjacent(menuBox!, rowBoxBefore!),
      "メニューが行の近くに出ていない（縦方向）",
    ).toBe(true);
  });

  // 2026-10-14（PO 指摘・実機実測）: 指で長押しすると OS の文字選択（青いハイライトと
  // 選択ハンドル）が働く不具合があった。この端末では Playwright が動かず実機でも
  // 確認できないため、CI（本テスト・マウス操作）でできるのは
  // 「user-select: none の指定が効いているか」の確認だけである。
  // 実機の選択が実際に止まることの証明にはならない（CI はマウス操作のため、
  // 指特有のこの不具合は元々 CI では再現しない＝検出できていなかった）。
  test("スマホ: 行とメニューに user-select: none が指定されている（文字選択の抑止・実機確認は別途必要）", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);
    const rowUserSelect = await row(page).evaluate((el) => getComputedStyle(el).userSelect);
    expect(rowUserSelect, "行の user-select").toBe("none");

    await longPressRow(page, row(page));
    await expect(menu(page)).toBeVisible();
    await page.mouse.up();

    const menuUserSelect = await menu(page).evaluate((el) => getComputedStyle(el).userSelect);
    expect(menuUserSelect, "メニューの user-select").toBe("none");
  });
});

test.describe("visual-language: 受信箱 第6便（会話画面のヘッダーを一覧と同じ形にする）", () => {
  /**
   * 第6便の背景（PO 決定 2026-10-14）: 旧スマホの会話画面は帯が2本
   * （上の操作行＋会話ヘッダー）あり、会話ヘッダー側の旧三点メニューは
   * 実機実測で 27x38dp しかなく画面右端で切れていた。
   * 1本（56dp）に統合し、右にテンプレート・顧客情報・「…」を置く
   * （テンプレートと顧客情報は独立ボタンで即開ける＝PO 指示）。
   * 「…」の中身は 送信先の言語／FAQ／受信箱の設定（この3つはスマホでは
   * 上の操作行が唯一の入口だったため、入口を失わないようここへ移した）。
   * 旧三点の中身（未読にする/対象外にする/削除/顧客情報）は第4便で
   * 一覧の長押しメニューに移設済み（本番稼働中）のためここには含まれない。
   *
   * 第7便（PO 指摘・2026-10-14）で以下を更新: テンプレートの独立ボタンは
   * 過密（お手本の WhatsApp も右は2つ）のため「…」の中へ移し、右は
   * 顧客情報・「…」の2つにした。このブロックの assertion は第7便時点の
   * 形に合わせて更新している（新しい挙動の検査は後続の「受信箱 第7便」
   * describe を参照）。
   */
  const header = (page: Page): Locator => page.locator(".inbox-thread-header-mobile");
  const name = (page: Page): Locator => page.locator(".inbox-thread-header-mobile-name");
  const actionButtons = (page: Page): Locator => page.locator(".inbox-thread-header-mobile-btn");
  const moreMenu = (page: Page): Locator => page.locator(".comp-context-menu");
  const moreMenuItems = (page: Page): Locator => moreMenu(page).locator('[role="menuitem"]');
  // Sheet.tsx は開閉に関わらず DOM を常にマウントする（アニメーションのため）。
  // このページには絞り込み用（InboxPage.tsx）と言語選択用（本便）の2つの Sheet が
  // 同時にマウントされるため、"今開いている" パネルだけに絞って中の要素を探す。
  const openSheetPanel = (page: Page): Locator =>
    page.locator('[data-testid="sheet-panel"].comp-sheet-panel--open');

  test("スマホ: 会話を開くと帯が1本だけになり、各部品の寸法・配置が仕様どおり", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    const viewport = page.viewportSize();
    expect(viewport, "viewport のサイズが取れない").not.toBeNull();
    const viewportWidth = viewport!.width;

    await openInboxList(page);
    await openConversation(page);

    // 1. 帯が1本だけ（上の操作行は出さない＝PO 決定）
    await expect(page.locator(".page-header-actions")).toHaveCount(0);
    await expect(header(page)).toBeVisible();

    const headerBox = await header(page).boundingBox();
    const backBox = await backButton(page).boundingBox();
    const nameBox = await name(page).boundingBox();
    const buttons = actionButtons(page);
    const buttonCount = await buttons.count();
    const buttonBoxes = await Promise.all((await buttons.all()).map((b) => b.boundingBox()));

    expect(headerBox, "ヘッダーの寸法が取れない").not.toBeNull();
    expect(backBox, "戻るボタンの寸法が取れない").not.toBeNull();
    expect(nameBox, "名前の寸法が取れない").not.toBeNull();
    for (const b of buttonBoxes) expect(b, "右の操作ボタンの寸法が取れない").not.toBeNull();

    await testInfo.attach("thread-header-measurements", {
      body: JSON.stringify(
        { viewportWidth, header: headerBox, back: backBox, name: nameBox, buttonCount, buttons: buttonBoxes },
        null,
        2,
      ),
      contentType: "application/json",
    });

    // 2. ヘッダー全体の高さ 56px（--topbar-height）
    expect(Math.abs(headerBox!.height - 56), "ヘッダーの高さ").toBeLessThanOrEqual(1);

    // 3. 戻るボタンが左端（ヘッダーの左 padding の位置）にあり、48px 以上
    const spaceToken4 = await page.evaluate(() =>
      Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--space-4").trim()),
    );
    expect(Number.isFinite(spaceToken4), "--space-4 トークンが読めない").toBe(true);
    expect(Math.abs(backBox!.x - (headerBox!.x + spaceToken4)), "戻るボタンの左端").toBeLessThanOrEqual(1);
    expect(backBox!.width, "戻るボタンの幅").toBeGreaterThanOrEqual(48);
    expect(backBox!.height, "戻るボタンの高さ").toBeGreaterThanOrEqual(48);

    // 4. 右の2つ（顧客情報・「…」）が各44px以上で、
    //    最後のボタンの右端がビューポート右端に接する（一覧のヘッダーと同じ作法）。
    //    第7便（PO 指摘）: テンプレートは独立ボタンだと右が3つになり過密
    //    （お手本の WhatsApp も右は2つ）のため「…」の中へ移した。
    expect(buttonCount, "右の操作ボタンが2つであること（顧客情報・もっと）").toBe(2);
    for (const b of buttonBoxes) {
      expect(b!.width, "操作ボタンの幅").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
      expect(b!.height, "操作ボタンの高さ").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    }
    const lastButtonBox = buttonBoxes[buttonBoxes.length - 1]!;
    expect(
      Math.abs(lastButtonBox.x + lastButtonBox.width - viewportWidth),
      "最後のボタンの右端",
    ).toBeLessThanOrEqual(1);

    // テンプレートの独立ボタンが無いこと（第7便）。残る2つは顧客情報とその他の操作だけ。
    const buttonAriaLabels = await Promise.all(
      (await buttons.all()).map((b) => b.getAttribute("aria-label")),
    );
    expect(buttonAriaLabels, "右の操作ボタンの読み上げ名").toEqual(["顧客情報", "その他の操作"]);

    // 5. 相手の名前が表示され、右のボタン群と重なっていない
    await expect(name(page)).toContainText(SAMPLE_CONVERSATION_NAME);
    const firstButtonBox = buttonBoxes[0]!;
    expect(
      nameBox!.x + nameBox!.width,
      "名前の右端が右のボタン群の左端を超えている（重なっている）",
    ).toBeLessThanOrEqual(firstButtonBox.x + 1);
  });

  test("スマホ: 「もっと」を押すと4項目（送信先の言語／テンプレート／FAQ／受信箱の設定）が出る", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);
    await openConversation(page);

    const buttons = actionButtons(page);
    // 第7便（PO 指摘）: 右は顧客情報・「もっと」の2つ
    await expect(buttons).toHaveCount(2);
    await buttons.last().click();

    await expect(moreMenu(page)).toBeVisible();
    const items = moreMenuItems(page);
    // 第7便: テンプレートを独立ボタンから「…」の中へ移した
    await expect(items).toHaveCount(4);
    const labels = await items.allTextContents();
    // 実際の i18n 文言（src/locales/ja.json）: translation.sendGuard.langToggleLabel /
    // nav.templates / faq.title / inbox.settings.title
    expect(labels).toEqual(["送信先言語", "テンプレート", "FAQ", "受信箱の設定"]);

    // 外側を押すと閉じる（第4便と同じ金型・同じ作法）
    await name(page).click({ force: true });
    await expect(moreMenu(page)).toHaveCount(0);
  });

  test("スマホ: 「送信先の言語」を押すとシートが開き、選択肢が3つ・各44px以上・選ぶと閉じる", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);
    await openConversation(page);

    await actionButtons(page).last().click();
    await expect(moreMenu(page)).toBeVisible();
    await moreMenuItems(page).filter({ hasText: "送信先言語" }).click();

    // 「…」メニューは選ぶと閉じ、シートが開く
    await expect(moreMenu(page)).toHaveCount(0);
    const sheetOpen = openSheetPanel(page);
    await expect(sheetOpen).toHaveCount(1);
    await expect(sheetOpen.getByRole("heading")).toHaveText("送信先言語");

    // 選択肢は3つ（自動／日本語／英語）・各44px以上
    const options = sheetOpen.locator(".inbox-filter-sheet-option");
    await expect(options).toHaveCount(3);
    const labels = await options.allTextContents();
    expect(labels).toEqual(["自動", "日本語", "英語"]);
    const optionBoxes = await Promise.all((await options.all()).map((o) => o.boundingBox()));
    for (const b of optionBoxes) {
      expect(b, "選択肢の寸法が取れない").not.toBeNull();
      expect(b!.height, "選択肢の高さ").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    }

    // 既定値（auto）に active が付いている＝いま選ばれている値が分かる
    await expect(options.nth(0)).toHaveClass(/active/);

    // 選ぶと閉じる
    await options.nth(1).click(); // 日本語
    await expect(openSheetPanel(page)).toHaveCount(0);
  });

  test("PC・タブレット: スマホ用の会話ヘッダーは出ず、従来どおり操作行と言語の SelectControl が見える", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) <= MOBILE_MAX_PX, "スマホ用レイアウトの幅は対象外");

    await openInboxList(page);
    await openConversation(page);

    // 新設したスマホ専用クラスは出ない
    await expect(page.locator(".inbox-thread-header-mobile")).toHaveCount(0);

    // 操作行（テンプレート / FAQ / 受信箱の設定）は PC・タブレットでは従来どおり1件
    await expect(page.locator(".page-header-actions")).toHaveCount(1);

    // 言語の SelectControl は会話ヘッダーの中に従来どおり見える
    // （.inbox-platform-select は一覧側のプラットフォーム絞り込みにも同じクラス名が
    //  使われているため、会話ヘッダー .inbox-center-header の中に限定して探す）
    const langSelect = page.locator(".inbox-center-header .inbox-platform-select");
    await expect(langSelect).toBeVisible();
  });

  /**
   * 2026-10-14（Opus 判断・追加分）: Discord 未連携の表示を落とすとスマホの
   * 利用者だけ気づけなくなるため、名前の下の2段目として残した
   * （お手本=WhatsApp の会話ヘッダーも左側2段。実機の構造ダンプで
   * conversation_contact_name=高さ22.7dp・conversation_contact_status=
   * 高さ16.3dp を確認済み）。条件・i18n キーは PC と同一
   * （`messagesData.lead.platform === "discord" && !leadDetail.discord_user_id`・
   * `inbox.discordNotLinked`）で、新しい状態は作っていない。
   */
  test("スマホ: Discord 未連携のときは名前の下に表示が出て、高さ56pxのまま・ボタン群と重ならない", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxListWithDiscordUnlinkedConversation(page);
    await openConversation(page);

    const headerBox = await header(page).boundingBox();
    expect(headerBox, "ヘッダーの寸法が取れない").not.toBeNull();

    // Discord 未連携の表示が見えている（PC と同じ i18n キー inbox.discordNotLinked）
    const status = page.locator(".inbox-thread-header-mobile-status");
    await expect(status).toBeVisible();
    await expect(status).toHaveText("Discord未連携");

    // 2段になってもヘッダーの高さは 56px（--topbar-height）のまま
    expect(Math.abs(headerBox!.height - 56), "ヘッダーの高さ（2段表示時）").toBeLessThanOrEqual(1);

    // 名前・状態の縦積みが右の操作ボタン群と重なっていない（既存の検査5と同じ判定）
    const identity = page.locator(".inbox-thread-header-mobile-identity");
    const identityBox = await identity.boundingBox();
    const firstButtonBox = await actionButtons(page).first().boundingBox();
    expect(identityBox, "名前・状態の縦積みの寸法が取れない").not.toBeNull();
    expect(firstButtonBox, "右の操作ボタンの寸法が取れない").not.toBeNull();
    expect(
      identityBox!.x + identityBox!.width,
      "名前・状態の縦積みの右端が右のボタン群の左端を超えている（重なっている）",
    ).toBeLessThanOrEqual(firstButtonBox!.x + 1);

    await testInfo.attach("discord-unlinked-two-row-header", {
      body: JSON.stringify({ headerBox, identityBox, firstButtonBox }, null, 2),
      contentType: "application/json",
    });
  });

  test("スマホ: Discord 連携済み（または他プラットフォーム）のときは名前だけで高さ56pxのまま", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    // 既存の openInboxList（baseMocks）は platform: "messenger" のため
    // 2段目は出ない。高さが変わらないことの対照として確認する。
    await openInboxList(page);
    await openConversation(page);

    await expect(page.locator(".inbox-thread-header-mobile-status")).toHaveCount(0);
    const headerBox = await header(page).boundingBox();
    expect(headerBox, "ヘッダーの寸法が取れない").not.toBeNull();
    expect(Math.abs(headerBox!.height - 56), "ヘッダーの高さ（1段表示時）").toBeLessThanOrEqual(1);
  });
});

test.describe("visual-language: 受信箱 第7便（テンプレートを「…」へ移し、カルテボタンを人型にし、準備中ページの行き止まりを解消する）", () => {
  /**
   * 第7便の背景（PO 指摘・実機を見て・2026-10-14）:
   * 1. テンプレートが独立ボタンだと右が3つになり過密（お手本の WhatsApp も
   *    会話ヘッダーの右は2つ）。「…」の中へ移し、右は顧客情報・「…」の2つにした。
   * 2. カルテ（顧客情報）ボタンの絵柄がクリップボードのままだったため人型に変えた
   *    （PC 側の PAGE_ICONS.kartePanel は変えていない。別キー kartePanelMobile を
   *    新設した）。
   * 3. 「…」→テンプレートで開く /templates は中身のない「準備中」の仮ページ
   *    （ComingSoonPage・frontend/src/App.tsx:281 / pages/coming-soon/ComingSoonPage.tsx）で、
   *    戻る手段が無い行き止まりだった（下部タブで受信箱の一覧には行けるが、
   *    開いていた会話には戻れない）。ComingSoonPage に戻るボタン（navigate(-1)）を
   *    追加した。
   */
  const actionButtons = (page: Page): Locator => page.locator(".inbox-thread-header-mobile-btn");
  const moreMenu = (page: Page): Locator => page.locator(".comp-context-menu");
  const moreMenuItems = (page: Page): Locator => moreMenu(page).locator('[role="menuitem"]');

  test("スマホ: 「もっと」→「テンプレート」で /templates に移動し、「戻る」で元の会話に戻れる（行き止まりの解消）", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);
    await openConversation(page);
    const beforeUrl = page.url();
    expect(beforeUrl, "会話を開いた URL に lead_id が無い").toContain("lead_id=5001");

    await actionButtons(page).last().click();
    await expect(moreMenu(page)).toBeVisible();
    await moreMenuItems(page).filter({ hasText: "テンプレート" }).click();

    // 1. /templates に移動すること
    await expect(page).toHaveURL(/\/templates(\?|$)/);

    // 2. 戻るボタンがあり、44px以上（既存の金型 Button・既存キー common.back を使用）
    const back = page.getByRole("button", { name: "戻る" });
    await expect(back).toBeVisible();
    const backBox = await back.boundingBox();
    expect(backBox, "戻るボタンの寸法が取れない").not.toBeNull();
    expect(backBox!.width, "戻るボタンの幅").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    expect(backBox!.height, "戻るボタンの高さ").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);

    // 3. 押すと元の会話に戻れる（URL と、会話の入力欄が見えることの両方で確認）
    await back.click();
    await expect(page).toHaveURL(beforeUrl);
    await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });

    await testInfo.attach("templates-back-navigation", {
      body: JSON.stringify({ beforeUrl }, null, 2),
      contentType: "application/json",
    });
  });

  test("スマホ: 準備中ページは戻る矢印のぶんだけカードを上に詰める（PO 決定・B案）", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await installAuthBypass(page);
    await page.goto("/templates");
    await expect(page.locator(".coming-soon")).toBeVisible({ timeout: 10_000 });

    // PO 決定（2026-10-14・B案）: 矢印を足したぶんカードを上に詰め、
    // 矢印が無かったときと同じ位置に見えるようにする。
    //   期待値 = --coming-soon-margin-top(80px) - --space-2(8px) - --size-icon-btn-lg(44px) = 28px
    // 値はトークンから読んで計算し、テスト側に生の数値を書かない。
    const measured = await page.evaluate(() => {
      const root = getComputedStyle(document.documentElement);
      const num = (name: string) => parseFloat(root.getPropertyValue(name));
      const card = document.querySelector(".coming-soon") as HTMLElement | null;
      return {
        marginTop: card ? parseFloat(getComputedStyle(card).marginTop) : null,
        expected: num("--coming-soon-margin-top") - num("--space-2") - num("--size-icon-btn-lg"),
        backRowVisible: !!document.querySelector(".coming-soon-back-row"),
      };
    });
    await testInfo.attach("coming-soon-spacing", {
      body: JSON.stringify(measured, null, 2),
      contentType: "application/json",
    });

    expect(measured.backRowVisible, "戻る矢印の行が無い").toBe(true);
    expect(measured.marginTop, "カードの上余白が取れない").not.toBeNull();
    expect(
      Math.abs(measured.marginTop! - measured.expected),
      "カードの上余白が矢印のぶんだけ詰まっていない",
    ).toBeLessThanOrEqual(1);
  });

  test("PC・タブレット: 準備中ページの戻る矢印は出さない（左のメニューで移動できるため）", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) <= MOBILE_MAX_PX, "スマホ用レイアウトの幅は対象外");

    await installAuthBypass(page);
    await page.goto("/templates");
    // PO 決定（2026-10-14）: 矢印はスマホのときだけ。PC は左のメニューから移動できる。
    await expect(page.locator(".coming-soon-back-row")).toBeHidden();
  });

  test("スマホ: FAQ（もう一方の準備中ページ）でも「戻る」が効く", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    // ComingSoonPage は /templates と /faq の2ルートから使われている（App.tsx）。
    // 両方で意味が通ることを確認する（/faq 側は一覧に戻る動線しか無いため、
    // ここでは一覧の URL に戻ることだけを見る）。
    await openInboxList(page);
    const beforeUrl = page.url();

    // 一覧ではヘッダーの会話用「…」は出ないため、下部タブの「もっと」経由ではなく
    // 直接 /faq を開いて戻る動線だけを確認する（この検査の対象は ComingSoonPage 側）。
    await page.goto("/faq");
    await expect(page).toHaveURL(/\/faq(\?|$)/);

    const back = page.getByRole("button", { name: "戻る" });
    await expect(back).toBeVisible();
    await back.click();
    await expect(page).toHaveURL(beforeUrl);
  });

  test("スマホ: カルテ（顧客情報）ボタンの絵柄がクリップボードから別物に変わっている", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);
    await openConversation(page);

    const readIcon = (sel: string) =>
      page.evaluate((s) => {
        const el = document.querySelector(s);
        const svg = el?.querySelector("svg");
        if (!svg) return null;
        // svg の中身（path の d 属性）が同じなら同じアイコン（第4便と同じ作法）
        return Array.from(svg.querySelectorAll("path")).map((p) => p.getAttribute("d")).join("|");
      }, sel);

    const newIcon = await readIcon(".inbox-thread-header-mobile-btn[aria-label='顧客情報']");
    expect(newIcon, "新しいカルテボタンのアイコンが取れない").toBeTruthy();

    // 変更前（クリップボード = PAGE_ICONS.kartePanel）と比べる。ハードコードした
    // path 文字列は貼らず、PC 側の同じ役割のボタン（.karte-toggle-btn。今も
    // PAGE_ICONS.kartePanel を使用中・frontend/src/pages/inbox/InboxMessageThread.tsx）
    // から実際に読んで比較する。useIsMobile（window.matchMedia）は resize に
    // 追従するため、同じページ内で viewport をデスクトップ幅に変えるだけで
    // PC 側のヘッダーが描かれる（reload 不要）。
    await page.setViewportSize({ width: 1280, height: 900 });
    const oldIcon = await readIcon(".karte-toggle-btn");
    expect(oldIcon, "PC側のクリップボードアイコン（PAGE_ICONS.kartePanel）が取れない").toBeTruthy();

    await testInfo.attach("karte-icon-diff", {
      body: JSON.stringify({ newIconLength: newIcon?.length, oldIconLength: oldIcon?.length }, null, 2),
      contentType: "application/json",
    });

    // クリップボード（PAGE_ICONS.kartePanel）と別物であること
    expect(newIcon, "顧客情報ボタンのアイコンが PAGE_ICONS.kartePanel（クリップボード）のまま変わっていない").not.toBe(oldIcon);
  });
});

test.describe("visual-language: 受信箱 第8便（顧客ページ（カルテ）をスマホで全画面にする）", () => {
  /**
   * 第8便の背景（PO 決定・2026-10-14）:
   * スマホのカルテは従来「下から 80vh のボトムシート」だった
   * （InboxPage.css の旧コメント「カルテをボトムシートに変換」）。
   * お手本（WhatsApp）の連絡先画面は画面全体（実測 y=0〜2340・下部タブも見えない）
   * のため、PO が次の3点を決定: ①画面全体に広げる・下部タブも覆う
   * ②閉じ方を「← 顧客情報」の帯に統一する（会話画面と同じ戻り方）
   * ③動きを下から上ではなく右から左にする。
   * 重なり順は新しいトークンを足さず、既存の --z-drawer（301）を使う。
   */
  const karteOpenBtn = (page: Page): Locator =>
    page.locator(".inbox-thread-header-mobile-btn[aria-label='顧客情報']");
  const panel = (page: Page): Locator => page.locator(".inbox-right-panel");
  const backBtn = (page: Page): Locator => page.locator(".karte-close-back-btn");

  test("スマホ: カルテが画面全体になる（下部タブバーは会話を開いた時点で隠れている）", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);
    await openConversation(page);
    await karteOpenBtn(page).click();
    await expect(panel(page)).toHaveClass(/karte-open/);

    const viewport = page.viewportSize();
    expect(viewport, "viewport が取れない").not.toBeNull();

    const measured = await page.evaluate(() => {
      const panelEl = document.querySelector(".inbox-right-panel") as HTMLElement | null;
      const tabbarEl = document.querySelector(".mobile-tabbar") as HTMLElement | null;
      const panelRect = panelEl?.getBoundingClientRect() ?? null;
      const tabbarRect = tabbarEl?.getBoundingClientRect() ?? null;
      return {
        panelRect: panelRect
          ? { x: panelRect.x, y: panelRect.y, width: panelRect.width, height: panelRect.height }
          : null,
        tabbarRect: tabbarRect
          ? { x: tabbarRect.x, y: tabbarRect.y, width: tabbarRect.width, height: tabbarRect.height }
          : null,
        panelZIndex: panelEl ? parseInt(getComputedStyle(panelEl).zIndex, 10) : null,
        tabbarZIndex: tabbarEl ? parseInt(getComputedStyle(tabbarEl).zIndex, 10) : null,
      };
    });
    await testInfo.attach("karte-fullscreen", {
      body: JSON.stringify({ viewport, measured }, null, 2),
      contentType: "application/json",
    });

    expect(measured.panelRect, "カルテの矩形が取れない").not.toBeNull();
    await expect(page.locator(".mobile-tabbar")).toBeHidden();
    const panelRect = measured.panelRect!;
    const tabbarRect = measured.tabbarRect!;
    const v = viewport!;

    // 1. カルテが画面全体であること（上端0・左右もビューポート幅と一致・高さも一致、±1px）
    expect(Math.abs(panelRect.x), "カルテの左端が0でない").toBeLessThanOrEqual(1);
    expect(Math.abs(panelRect.y), "カルテの上端が0でない").toBeLessThanOrEqual(1);
    expect(Math.abs(panelRect.width - v.width), "カルテの幅がビューポート幅と一致しない").toBeLessThanOrEqual(1);
    expect(Math.abs(panelRect.height - v.height), "カルテの高さがビューポート高さと一致しない").toBeLessThanOrEqual(1);
  });

  test("スマホ: 左上の戻る矢印が44px以上で、押すとカルテが閉じて会話に戻る", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);
    await openConversation(page);
    await karteOpenBtn(page).click();
    await expect(panel(page)).toHaveClass(/karte-open/);

    const back = backBtn(page);
    await expect(back).toBeVisible();
    // 会話画面と同じ戻るラベル（既存キー common.back）を使っていること
    await expect(back).toHaveAccessibleName("戻る");

    const box = await back.boundingBox();
    expect(box, "戻る矢印の寸法が取れない").not.toBeNull();
    expect(box!.width, "戻る矢印の幅").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    expect(box!.height, "戻る矢印の高さ").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    await testInfo.attach("karte-back-btn-box", { body: JSON.stringify(box), contentType: "application/json" });

    await back.click();
    await expect(panel(page)).not.toHaveClass(/karte-open/);
    // 会話に戻っていること（入力欄が見える）
    await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
  });

  test("スマホ: 固定の操作バー（karte-action-bar）が画面内に見えている", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    // 固定操作バーは商談段階が "lead" のときだけ描かれる
    // （frontend/src/pages/inbox/InboxKartePanel.tsx の `if (!primaryLabel) return null;`）。
    // 既定の仮データには status が無く出ないため、この検査だけ status を足して開く。
    await openInboxListWithLeadStatus(page);
    await openConversation(page);
    await karteOpenBtn(page).click();
    await expect(panel(page)).toHaveClass(/karte-open/);

    const actionBar = page.locator('[data-testid="karte-action-bar"]');
    await expect(actionBar).toBeVisible();
    const box = await actionBar.boundingBox();
    const viewport = page.viewportSize();
    expect(box, "操作バーの矩形が取れない").not.toBeNull();
    expect(viewport, "viewport が取れない").not.toBeNull();
    await testInfo.attach("karte-action-bar-box", {
      body: JSON.stringify({ box, viewport }),
      contentType: "application/json",
    });

    expect(box!.y, "操作バーの上端が画面より上にある").toBeGreaterThanOrEqual(0);
    expect(box!.y + box!.height, "操作バーの下端がビューポートを超えている")
      .toBeLessThanOrEqual(viewport!.height + 1);
  });

  test("PC・タブレット: カルテは全画面にならない（従来どおり）", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) <= MOBILE_MAX_PX, "スマホ用レイアウトの幅は対象外");

    await openInboxList(page);
    await openConversation(page);

    const viewport = page.viewportSize();
    expect(viewport, "viewport が取れない").not.toBeNull();

    // タブレット幅（768〜1279px）はドロワー方式のため .karte-toggle-btn を押して開く。
    // デスクトップ幅（1280px以上）は常時表示なのでクリック不要（存在すれば押す）。
    const toggle = page.locator("button.karte-toggle-btn");
    if (await toggle.isVisible().catch(() => false)) {
      await toggle.click();
    }
    await expect(panel(page)).toBeVisible();

    const box = await panel(page).boundingBox();
    expect(box, "カルテの矩形が取れない").not.toBeNull();
    await testInfo.attach("karte-pc-tablet-box", {
      body: JSON.stringify({ box, viewport, width: projectWidth(testInfo) }),
      contentType: "application/json",
    });

    // 全画面になっていない＝幅がビューポート未満であること
    expect(box!.width, "カルテの幅がビューポートと同じ（全画面化している）").toBeLessThan(viewport!.width);
  });
});

test.describe("visual-language: 受信箱 第9便（カルテのヘッダー統一＋商談化の確認ポップアップ）", () => {
  /**
   * 第9便の背景（PO 決定・2026-10-14）:
   * ①カルテ上部の帯を会話画面ヘッダーと同じ並び（戻る矢印→顔写真→顧客名）にする
   *   （スマホ幅のみ。タブレットは従来の「顧客情報 ×」のまま）。
   * ②「顧客ページを開く」リンクを削除する（PO 決定・不要）。
   * ③「商談化」を押すと中央にポップアップが出て、担当の営業をプルダウンから選び、
   *   確定すると PATCH /leads/{id} で status="negotiating" + assigned_to を保存する。
   *   旧実装は /crm/leads?convert= へ移動するだけで、それを読む画面は存在せず
   *   処理が無かった（全文検索0件で確認済み）。新しい API・保存先は作らない。
   */
  const karteOpenBtn = (page: Page): Locator =>
    page.locator(".inbox-thread-header-mobile-btn[aria-label='顧客情報']");
  const panel = (page: Page): Locator => page.locator(".inbox-right-panel");
  const backBtn = (page: Page): Locator => page.locator(".karte-close-back-btn");
  const mobileIdentity = (page: Page): Locator => page.locator(".karte-close-mobile-identity");
  const convertBtn = (page: Page): Locator => page.locator('[data-testid="karte-action-primary"]');
  const convertDialog = (page: Page): Locator => page.locator(".comp-modal-dialog[role='dialog']");
  // ConfirmModal の .form-actions は [閉じる(secondary), 確定(primary)] の順（ConfirmModal.tsx 参照）
  const dialogButtons = (page: Page): Locator => convertDialog(page).locator(".form-actions button");
  const stageBadge = (page: Page): Locator => page.locator('[data-testid="karte-stage-badge"]');

  // 役割を混ぜた GET /staff の仮データ。検査 4（営業・リーダーだけが並ぶ）に使う:
  //   山田太郎=営業/在籍中/user_id あり → 出る
  //   佐藤花子=リーダー/在籍中/user_id あり → 出る
  //   鈴木一郎=CS/在籍中/user_id あり → 出ない（role_name 対象外）
  //   高橋次郎=営業/在籍中/user_id なし → 出ない（assigned_to に入れられない）
  //   田中三郎=営業/休止中/user_id あり → 出ない（在籍中のみ。status=active の
  //     query はこの mock では無視されるため、クライアント側の絞り込みの検査も兼ねる）
  const STAFF_SALES_LEADER_MIX = [
    { id: 1, user_id: 11, role_name: "営業", status: "active", surname_jp: "山田", given_name_jp: "太郎" },
    { id: 2, user_id: 12, role_name: "リーダー", status: "active", surname_jp: "佐藤", given_name_jp: "花子" },
    { id: 3, user_id: 13, role_name: "CS", status: "active", surname_jp: "鈴木", given_name_jp: "一郎" },
    { id: 4, user_id: null, role_name: "営業", status: "active", surname_jp: "高橋", given_name_jp: "次郎" },
    { id: 5, user_id: 15, role_name: "営業", status: "inactive", surname_jp: "田中", given_name_jp: "三郎" },
    // 第11便（PO 決定 2026-10-15）: 本番の役割名は「リーダー」ではなく「マネージャー」だった。
    // マネージャーも候補に含める（実機で確認した事実にもとづく）。
    { id: 6, user_id: 16, role_name: "マネージャー", status: "active", surname_jp: "渡辺", given_name_jp: "四郎" },
    // 第12便（PO 決定 2026-10-15）: PO の言う admin ＝ オーナー。候補に含める。
    { id: 7, user_id: 17, role_name: "オーナー", status: "active", surname_jp: "伊藤", given_name_jp: "五郎" },
  ];

  test("スマホ: カルテの帯に戻る矢印・顔写真・顧客名が並び、高さ56px・矢印44px以上", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);
    await openConversation(page);
    await karteOpenBtn(page).click();
    await expect(panel(page)).toHaveClass(/karte-open/);

    const row = page.locator(".karte-close-row");
    await expect(row).toBeVisible();
    const rowBox = await row.boundingBox();
    expect(rowBox, "帯の矩形が取れない").not.toBeNull();
    expect(Math.abs(rowBox!.height - 56), "帯の高さが56pxでない").toBeLessThanOrEqual(1);

    const back = backBtn(page);
    await expect(back).toBeVisible();
    const backBox = await back.boundingBox();
    expect(backBox, "戻る矢印の寸法が取れない").not.toBeNull();
    expect(backBox!.width, "戻る矢印の幅").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    expect(backBox!.height, "戻る矢印の高さ").toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);

    const identity = mobileIdentity(page);
    await expect(identity).toBeVisible();
    const avatar = identity.locator(".right-panel-avatar");
    const name = identity.locator(".right-panel-display-name");
    await expect(avatar).toBeVisible();
    await expect(name).toBeVisible();
    await expect(name).toHaveText(SAMPLE_CONVERSATION_NAME);

    // 並び順: 戻る矢印 → 顔写真・顧客名（会話画面ヘッダーと同じ並び）
    const order = await row.evaluate((el) =>
      Array.from(el.children).map((c) => (c as HTMLElement).className)
    );
    const backIdx = order.findIndex((c) => c.includes("karte-close-back-btn"));
    const identityIdx = order.findIndex((c) => c.includes("karte-close-mobile-identity"));
    expect(backIdx, "戻る矢印が帯に見つからない").toBeGreaterThanOrEqual(0);
    expect(identityIdx, "顔写真・顧客名の並びが帯に見つからない").toBeGreaterThan(backIdx);
  });

  test("スマホ: 「顧客ページを開く」がどこにも無い", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);
    await openConversation(page);
    await karteOpenBtn(page).click();
    await expect(panel(page)).toHaveClass(/karte-open/);

    // eslint-disable-next-line local/no-japanese-literal -- 削除済みテキストが無いことの確認
    await expect(page.getByText("顧客ページを開く")).toHaveCount(0);
    await expect(page.locator(".karte-open-link")).toHaveCount(0);
  });

  test("スマホ: 「商談化」を押すと中央にポップアップが出て、プルダウンには営業・リーダーだけが並ぶ", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxListWithLeadStatusAndStaff(page, STAFF_SALES_LEADER_MIX);
    await openConversation(page);
    await karteOpenBtn(page).click();
    await expect(panel(page)).toHaveClass(/karte-open/);

    await convertBtn(page).click();
    const dialog = convertDialog(page);
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveAttribute("role", "dialog");

    const select = dialog.locator("select");
    await expect(select).toBeVisible();

    const optionLabels = await select.locator("option").allTextContents();
    // eslint-disable-next-line local/no-japanese-literal -- 既存キー common.pleaseSelect の出力確認
    const nonPlaceholder = optionLabels.filter((label) => label !== "選択してください");
    // eslint-disable-next-line local/no-japanese-literal -- 期待値は仮データの氏名
    expect(nonPlaceholder.sort()).toEqual(["伊藤 五郎", "佐藤 花子", "山田 太郎", "渡辺 四郎"].sort());
  });

  test("スマホ: 確定・閉じるが横並びで、確定がネイビー（--accent）・閉じるがグレーであること", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxListWithLeadStatusAndStaff(page, STAFF_SALES_LEADER_MIX);
    await openConversation(page);
    await karteOpenBtn(page).click();
    await convertBtn(page).click();
    await expect(convertDialog(page)).toBeVisible();

    const buttons = dialogButtons(page);
    await expect(buttons).toHaveCount(2);

    const box0 = await buttons.nth(0).boundingBox();
    const box1 = await buttons.nth(1).boundingBox();
    expect(box0, "閉じるの矩形が取れない").not.toBeNull();
    expect(box1, "確定の矩形が取れない").not.toBeNull();
    // 横並び＝ y 座標がほぼ同じ
    expect(Math.abs(box0!.y - box1!.y), "確定・閉じるが横並びでない").toBeLessThanOrEqual(2);

    const colors = await page.evaluate(() => {
      const probe = document.createElement("div");
      probe.style.backgroundColor = "var(--accent)";
      document.body.appendChild(probe);
      const accentRgb = getComputedStyle(probe).backgroundColor;
      probe.remove();
      const btns = document.querySelectorAll(".comp-modal-dialog .form-actions button");
      return {
        accentRgb,
        cancelBg: getComputedStyle(btns[0]).backgroundColor,
        confirmBg: getComputedStyle(btns[1]).backgroundColor,
      };
    });

    expect(colors.confirmBg, "確定の背景色が --accent（ネイビー）と一致しない").toBe(colors.accentRgb);
    expect(colors.cancelBg, "閉じるの背景色が確定と同じ（--accent）になっている").not.toBe(colors.accentRgb);
  });

  test("スマホ: 確定を押すと PATCH /leads/5001 が status=negotiating・assigned_to付きで呼ばれ、ポップアップが閉じて段階バッジが更新される", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    const calls: Array<Record<string, unknown>> = [];
    const base = baseMocks();
    const leadDetail = base["GET /leads/5001"] as Record<string, unknown>;
    // サーバ側の保存結果を模すため、status を可変にする（PATCH 成功後の
    // loadLeadDetail 再取得で「商談中」バッジに変わることまで検査するため）。
    let leadStatus = "lead";

    await installAuthBypass(page);
    await mockApi(page, {
      ...base,
      "GET /leads/5001": async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ ...leadDetail, status: leadStatus }),
        });
      },
      "GET /staff": STAFF_SALES_LEADER_MIX,
      "PATCH /leads/5001": async (route) => {
        const body = route.request().postDataJSON() as Record<string, unknown>;
        calls.push(body);
        leadStatus = body.status as string;
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ ...leadDetail, status: leadStatus }),
        });
      },
    });
    await page.goto("/lead-chat");
    await expect(page.getByRole("heading", { name: "受信箱" })).toBeVisible({ timeout: 20_000 });
    await expect(page.locator("button.conversation-item").first()).toBeVisible({ timeout: 10_000 });

    await openConversation(page);
    await karteOpenBtn(page).click();
    await convertBtn(page).click();
    const dialog = convertDialog(page);
    await expect(dialog).toBeVisible();

    await dialog.locator("select").selectOption("11");
    // ConfirmModal の .form-actions は [閉じる, 確定] の順
    // 第9便（CI が検出した退行の歯止め）: 全画面のカルテ（重なり順）の上に
    // ポップアップが出るため、確定ボタンの真上に他の要素が被っていないことを
    // 先に確かめる。被っていると click は「見えて押せる」のに時間切れになる。
    const confirmBtn = dialogButtons(page).nth(1);
    const topMost = await confirmBtn.evaluate((el) => {
      const r = el.getBoundingClientRect();
      const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return hit === el || el.contains(hit as Node);
    });
    expect(topMost, "確定ボタンの上に別の要素が重なっている").toBe(true);
    await confirmBtn.click();

    await expect.poll(() => calls.length, { message: "PATCH /leads/5001 が呼ばれていない" }).toBe(1);
    expect(calls[0]).toEqual({ status: "negotiating", assigned_to: 11 });

    // 確定後: ポップアップが閉じ、顧客情報に戻る
    await expect(dialog).toHaveCount(0);
    await expect(panel(page)).toBeVisible();

    // 段階バッジが更新される（既存の読み直し処理 loadLeadDetail を使用。
    // ja.json: leads.statusCode.negotiating = "商談中"）
    // eslint-disable-next-line local/no-japanese-literal -- 既存キーの出力確認
    await expect(stageBadge(page)).toHaveText("商談中");
  });

  test("スマホ: ポップアップが画面の中央に出て、左右に余白がある（PO 決定・2026-10-15）", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxListWithLeadStatusAndStaff(page, STAFF_SALES_LEADER_MIX);
    await openConversation(page);
    await karteOpenBtn(page).click();
    await expect(panel(page)).toHaveClass(/karte-open/);
    await convertBtn(page).click();

    const dialog = convertDialog(page);
    await expect(dialog).toBeVisible();
    const box = await dialog.boundingBox();
    const viewport = page.viewportSize();
    expect(box, "ポップアップの矩形が取れない").not.toBeNull();
    expect(viewport, "viewport が取れない").not.toBeNull();

    // 画面の中央: ポップアップの中心と画面の中心の差が小さいこと
    const dialogCenterY = box!.y + box!.height / 2;
    const viewportCenterY = viewport!.height / 2;
    // 左右に余白があること（下から出る帯のときは全幅＝余白0だった）
    const leftGap = box!.x;
    const rightGap = viewport!.width - (box!.x + box!.width);

    await testInfo.attach("modal-center", {
      body: JSON.stringify({ box, viewport, dialogCenterY, viewportCenterY, leftGap, rightGap }, null, 2),
      contentType: "application/json",
    });

    expect(Math.abs(dialogCenterY - viewportCenterY), "ポップアップが縦の中央にない").toBeLessThanOrEqual(2);
    expect(leftGap, "左に余白がない").toBeGreaterThan(0);
    expect(rightGap, "右に余白がない").toBeGreaterThan(0);
    expect(Math.abs(leftGap - rightGap), "左右の余白が揃っていない").toBeLessThanOrEqual(1);
  });

  test("スマホ: カルテの帯が画面の幅いっぱいにある（会話画面と同じ見え方）", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);
    await openConversation(page);
    await karteOpenBtn(page).click();
    await expect(panel(page)).toHaveClass(/karte-open/);

    const row = page.locator(".karte-close-row");
    const box = await row.boundingBox();
    const viewport = page.viewportSize();
    expect(box, "帯の矩形が取れない").not.toBeNull();
    expect(viewport, "viewport が取れない").not.toBeNull();
    // 親が中央寄せのため帯が中央に寄っていた（2026-10-15 実機で発見）。
    expect(Math.abs(box!.x - 0), "帯が左端から始まっていない").toBeLessThanOrEqual(1);
    expect(Math.abs(box!.width - viewport!.width), "帯が画面の幅いっぱいでない").toBeLessThanOrEqual(1);
  });

  test("PC・タブレット: カルテの帯は従来どおりで、顔写真・顧客名の重複表示が出ない", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) <= MOBILE_MAX_PX, "スマホ用レイアウトの幅は対象外");

    await openInboxList(page);
    await openConversation(page);
    const toggle = page.locator("button.karte-toggle-btn");
    if (await toggle.isVisible().catch(() => false)) {
      await toggle.click();
    }
    await expect(panel(page)).toBeVisible();

    // スマホ専用の帯（戻る矢印→顔写真→顧客名）はここでは出ない
    await expect(mobileIdentity(page)).toBeHidden();

    // タブレット幅（768〜1279px）だけ、従来の「顧客情報 ×」の帯が残っていることを確認
    // （デスクトップ幅では .karte-close-row 自体が出ない。第8便までと同じ仕様で、
    // 第9便では変えていない）
    if (projectWidth(testInfo) < 1280) {
      const title = page.locator(".karte-close-title");
      await expect(title).toBeVisible();
      // eslint-disable-next-line local/no-japanese-literal -- asserting i18n output
      await expect(title).toHaveText("顧客情報");
      await expect(page.locator(".karte-close-btn")).toBeVisible();
    }

    // 顔写真・顧客名は .right-panel-header 側にそのまま残っている（第9便で消していない）
    await expect(page.locator(".right-panel-header .right-panel-avatar")).toBeVisible();
    await expect(page.locator(".right-panel-header .right-panel-display-name")).toBeVisible();
  });
});

test.describe("visual-language: 受信箱 入力欄（card-a2 §14）", () => {
  test("スマホ: 入力欄に案内文が出ず、Enter で改行され送信されない", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    let sendCount = 0;
    await installAuthBypass(page);
    await mockApi(page, {
      ...baseMocks(),
      "POST /leads/5001/messages": async (route) => {
        sendCount += 1;
        await route.fulfill({ body: JSON.stringify({ id: 1, text: "a\nb" }) });
      },
    });
    await page.goto("/lead-chat");
    await expect(page.getByRole("heading", { name: "受信箱" })).toBeVisible({ timeout: 20_000 });
    await expect(page.locator("button.conversation-item").first()).toBeVisible({ timeout: 10_000 });
    await openConversation(page);

    const textarea = page.locator(".inbox-textarea");
    // 案内文（placeholder）が無い、または空
    const placeholder = await textarea.getAttribute("placeholder");
    expect(placeholder ?? "", "スマホでは案内文を出さない").toBe("");

    // Enter は改行。送信は呼ばれない
    await textarea.fill("a");
    await textarea.press("Enter");
    await textarea.pressSequentially("b");
    await expect(textarea).toHaveValue("a\nb");
    await page.waitForTimeout(300);
    expect(sendCount, "Enter で送信 API が呼ばれた").toBe(0);
  });

  test("PC・タブレット: 案内文は今のまま出る", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) <= MOBILE_MAX_PX, "スマホ用レイアウトの幅は対象外");

    const ja = JSON.parse(readFileSync(resolve(process.cwd(), "src/locales/ja.json"), "utf-8")) as {
      inbox: { messagePlaceholder: string };
    };

    await openInboxList(page);
    await openConversation(page);
    await expect(page.locator(".inbox-textarea")).toHaveAttribute("placeholder", ja.inbox.messagePlaceholder);
  });
});
