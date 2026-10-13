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
  openInboxListWithConversations,
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

    // 会話を開くと操作行が出ること（返信中に使うため）
    await openConversation(page);
    await expect(page.locator(".page-header-actions")).toHaveCount(1);
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
    const karteToggle = await measure(".karte-toggle-btn");
    // 本便で変更していないものも値を記録に残す（design §7）。
    //   .send-attach-btn … 送信ピルの内側（44px にするとピルが膨らむ）
    //   .inbox-header-menu-btn … 実機実測で 15x38dp。幅が足りないのは画面右端で
    //     切れているため（ヘッダの中身が 360dp に収まっていない）。寸法ではなく
    //     ヘッダの中身を減らす判断が必要なので本便では触らない。
    const attach = await measure(".send-attach-btn");
    const headerMenu = await measure(".inbox-header-menu-btn");

    await testInfo.attach("touch-targets", {
      body: JSON.stringify(
        {
          絞り込み: filter,
          送信: sendBtn,
          顧客情報: karteToggle,
          "添付（この便では未対応）": attach,
          "三点メニュー（この便では未対応・右端で切れている）": headerMenu,
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

    // 2026-10-14（第3便・CI の検査が検出・PO 訂正）: 当初「スクロール箱は
    // .inbox-left-panel」という推測で sticky を足したが誤りだった。実際に
    // スクロールする箱は .inbox-conversation-list（frontend/src/pages/inbox/InboxPage.css
    // の .inbox-conversation-list: flex:1; min-height:0; overflow-y:auto）で、
    // ヘッダー（.inbox-mobile-header）と検索欄（.inbox-mobile-search-row）は
    // InboxConversationListMobile.tsx 内でその外側（flex の兄弟要素として前）に
    // 置かれている。.inbox-left-panel 自身は中身があふれないため
    // scrollHeight === clientHeight のまま＝sticky を置いても何もしない。
    // 調べた結果「ヘッダーは元から動かない」ことが構造上の事実と分かったため、
    // sticky の指定は撤回し（InboxPage.css 参照）、この検査は「本当のスクロール箱」
    // である .inbox-conversation-list を600pxスクロールさせて確認する形に直した。
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
