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

import { expect, test } from "@playwright/test";
import type { Locator, Page, TestInfo } from "@playwright/test";
import {
  MIN_TOUCH_TARGET_PX,
  MOBILE_MAX_PX,
  SAMPLE_CONVERSATION_NAME,
  openConversation,
  openInboxList,
} from "./inbox-helpers";

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

  test("スマホ: 一覧ではヘッダーの操作行を出さず、絞り込みは検索欄の横に出る", async ({ page }, testInfo) => {
    test.skip(projectWidth(testInfo) > MOBILE_MAX_PX, "スマホ用レイアウトの幅のみ対象");

    await openInboxList(page);

    // 2026-10-13（PO 指定）: 一覧では操作行（テンプレート / FAQ / 受信箱の設定）を出さない。
    // 一覧では使い道がなく、その高さを一覧に回す。
    await expect(page.locator(".page-header-actions")).toHaveCount(0);

    // 絞り込みは一覧専用なので検索欄の横へ移した。一覧では必ず使えること。
    const filterInSearchRow = page.locator(".inbox-search-row .inbox-mobile-filter-toggle");
    await expect(filterInSearchRow).toBeVisible();
    // 押すと絞り込み（ステータスタブ）が開くこと
    await expect(page.locator(".inbox-full-tab-bar")).toBeHidden();
    await filterInSearchRow.click();
    await expect(page.locator(".inbox-full-tab-bar")).toBeVisible();
    await filterInSearchRow.click();
    await expect(page.locator(".inbox-full-tab-bar")).toBeHidden();

    // 会話を開くと操作行が出ること（返信中に使うため）
    await openConversation(page);
    await expect(page.locator(".page-header-actions")).toHaveCount(1);
    // 一覧専用の絞り込みは会話側では見えない（一覧が隠れているため）
    await expect(filterInSearchRow).toBeHidden();
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
    // ヘッダーの操作行は PC・タブレットでは一覧を見ているときも出す（従来どおり）
    await expect(page.locator(".page-header-actions")).toHaveCount(1);
    // 絞り込みボタンは DOM にはあるが PC・タブレットでは表示しない
    await expect(page.locator(".inbox-search-row .inbox-mobile-filter-toggle")).toBeHidden();
  });
});
