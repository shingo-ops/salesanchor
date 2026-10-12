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
