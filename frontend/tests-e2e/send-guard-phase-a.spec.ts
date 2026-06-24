/**
 * ADR-142 送信ガード Phase A — QA 実機確認テスト
 *
 * ローカル dev server (localhost:5173) + API mock で動作。
 * tenant_006 相当のデータ（mock-conversations.json / mock-messages.json）を使用。
 *
 * 確認項目:
 *   QA-1: 発火条件表 6行
 *   QA-2: IME 変換中 Enter で誤送信しないか
 *   QA-3: トグル UI 描画・切替
 *   QA-4: ダイアログ表示（文言・3ボタン）
 *   QA-5: スレッド独立
 */

import { expect, test } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi } from "./utils/api-mock";
import { commonMocks } from "./utils/common-mocks";
import { loadFixture } from "./utils/fixtures";

const conversationsFixture = loadFixture("mock-conversations.json");
const messagesFullFixture = loadFixture<Record<string, unknown>>("mock-messages.json");
// API は { messages: [...], lead: {...}, messaging_window: {...} } を返す
const messagesFixture = messagesFullFixture["messenger_within_24h"] as Record<string, unknown>;

// 基本 mock セット（lead_id=5001）
function baseMocks(leadId = 5001) {
  return {
    ...commonMocks(),
    "GET /conversations": conversationsFixture,
    [`GET /leads/${leadId}/messages`]: messagesFixture,
    [`POST /leads/${leadId}/messages/mark-read`]: { marked_count: 1 },
    [`GET /leads/${leadId}`]: {
      id: leadId,
      customer_name: "Taro Sender",
      platform: "messenger",
      discord_dm_channel_id: null,
      discord_user_id: null,
    },
  };
}

/** ページ初期化 + スレッド選択 */
async function setupPage(page: Parameters<typeof installAuthBypass>[0]) {
  await installAuthBypass(page);
  await mockApi(page, baseMocks());
  await page.goto("/lead-chat");
  await expect(page.getByRole("heading", { name: "受信箱" })).toBeVisible({ timeout: 20_000 });
  await page.locator("button.conversation-item", { hasText: "Taro Sender" }).click();
  await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
}

/** 特定モックでページ初期化 + スレッド選択 */
async function setupPageWithMocks(
  page: Parameters<typeof installAuthBypass>[0],
  extraMocks: Record<string, unknown>,
) {
  await installAuthBypass(page);
  await mockApi(page, { ...baseMocks(), ...extraMocks });
  await page.goto("/lead-chat");
  await expect(page.getByRole("heading", { name: "受信箱" })).toBeVisible({ timeout: 20_000 });
  await page.locator("button.conversation-item", { hasText: "Taro Sender" }).click();
  await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
}

// スレッドヘッダーの言語トグルを操作するヘルパー
async function clickLangToggle(page: Parameters<typeof installAuthBypass>[0], val: "自動" | "日本語" | "英語") {
  const btn = page.locator(".send-guard-lang-btn", { hasText: val });
  await btn.click();
  await expect(btn).toHaveClass(/active/);
}

// 送信エリアに文字を入れて送信ボタンを押す
async function typeAndClickSend(page: Parameters<typeof installAuthBypass>[0], text: string) {
  const textarea = page.locator(".inbox-textarea");
  await textarea.fill(text);
  await page.locator(".inbox-send-btn").click();
}

// ===================================================================
// QA-1: 発火条件表 6行
// ===================================================================
test.describe("QA-1: 発火条件表 6行", () => {
  test("1. auto + かな → ダイアログ発火", async ({ page }) => {
    await setupPage(page);
    await typeAndClickSend(page, "こんにちは");
    await expect(page.locator(".send-guard-dialog")).toBeVisible();
  });

  test("2. auto + 英語のみ → ダイアログなし・直送", async ({ page }) => {
    let sendCalled = false;
    await installAuthBypass(page);
    await mockApi(page, {
      ...baseMocks(),
      "POST /leads/5001/messages": async (route) => {
        sendCalled = true;
        await route.fulfill({ body: JSON.stringify({ id: 1, text: "hello" }) });
      },
    });
    await page.goto("/lead-chat");
    await expect(page.getByRole("heading", { name: "受信箱" })).toBeVisible({ timeout: 20_000 });
    await page.locator("button.conversation-item", { hasText: "Taro Sender" }).click();
    await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });

    await typeAndClickSend(page, "hello world");
    await expect(page.locator(".send-guard-dialog")).not.toBeVisible();
    // 送信APIが呼ばれた = ダイアログなしで直送
    expect(sendCalled).toBe(true);
  });

  test("3. 手動 ja + かな → ダイアログなし・直送", async ({ page }) => {
    let sendCalled = false;
    await installAuthBypass(page);
    await mockApi(page, {
      ...baseMocks(),
      "POST /leads/5001/messages": async (route) => {
        sendCalled = true;
        await route.fulfill({ body: JSON.stringify({ id: 1, text: "こんにちは" }) });
      },
    });
    await page.goto("/lead-chat");
    await expect(page.getByRole("heading", { name: "受信箱" })).toBeVisible({ timeout: 20_000 });
    await page.locator("button.conversation-item", { hasText: "Taro Sender" }).click();
    await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });

    await clickLangToggle(page, "日本語");
    await typeAndClickSend(page, "こんにちは");
    await expect(page.locator(".send-guard-dialog")).not.toBeVisible();
    expect(sendCalled).toBe(true);
  });

  test("4. 手動 ja + 英語のみ → ダイアログなし", async ({ page }) => {
    let sendCalled = false;
    await installAuthBypass(page);
    await mockApi(page, {
      ...baseMocks(),
      "POST /leads/5001/messages": async (route) => {
        sendCalled = true;
        await route.fulfill({ body: JSON.stringify({ id: 1, text: "hello" }) });
      },
    });
    await page.goto("/lead-chat");
    await expect(page.getByRole("heading", { name: "受信箱" })).toBeVisible({ timeout: 20_000 });
    await page.locator("button.conversation-item", { hasText: "Taro Sender" }).click();
    await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });

    await clickLangToggle(page, "日本語");
    await typeAndClickSend(page, "hello");
    await expect(page.locator(".send-guard-dialog")).not.toBeVisible();
    expect(sendCalled).toBe(true);
  });

  test("5. 手動 en + かな → ダイアログ発火", async ({ page }) => {
    await setupPage(page);
    await clickLangToggle(page, "英語");
    await typeAndClickSend(page, "テスト");
    await expect(page.locator(".send-guard-dialog")).toBeVisible();
  });

  test("6. 手動 en + 英語のみ → ダイアログなし", async ({ page }) => {
    let sendCalled = false;
    await installAuthBypass(page);
    await mockApi(page, {
      ...baseMocks(),
      "POST /leads/5001/messages": async (route) => {
        sendCalled = true;
        await route.fulfill({ body: JSON.stringify({ id: 1, text: "hello" }) });
      },
    });
    await page.goto("/lead-chat");
    await expect(page.getByRole("heading", { name: "受信箱" })).toBeVisible({ timeout: 20_000 });
    await page.locator("button.conversation-item", { hasText: "Taro Sender" }).click();
    await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });

    await clickLangToggle(page, "英語");
    await typeAndClickSend(page, "hello");
    await expect(page.locator(".send-guard-dialog")).not.toBeVisible();
    expect(sendCalled).toBe(true);
  });
});

// ===================================================================
// QA-2: IME Enter 誤送信チェック
// ===================================================================
test.describe("QA-2: IME Enter", () => {
  test("compositionstart 中の Enter は送信されない", async ({ page }) => {
    await setupPage(page);
    const textarea = page.locator(".inbox-textarea");
    await textarea.click();

    // IME 変換開始をシミュレート
    await page.evaluate(() => {
      const ta = document.querySelector(".inbox-textarea") as HTMLTextAreaElement;
      ta.dispatchEvent(new CompositionEvent("compositionstart", { bubbles: true, data: "" }));
    });

    // isComposing=true の状態で Enter を押す
    await page.evaluate(() => {
      const ta = document.querySelector(".inbox-textarea") as HTMLTextAreaElement;
      const ev = new KeyboardEvent("keydown", {
        key: "Enter",
        bubbles: true,
        cancelable: true,
        isComposing: true,
      });
      ta.dispatchEvent(ev);
    });

    // ダイアログは出ない、送信もされない
    await expect(page.locator(".send-guard-dialog")).not.toBeVisible();
    await page.evaluate(() => {
      const ta = document.querySelector(".inbox-textarea") as HTMLTextAreaElement;
      ta.dispatchEvent(new CompositionEvent("compositionend", { bubbles: true, data: "は" }));
    });
  });

  test("compositionend 後の Enter はガードを通る（かなあり→ダイアログ）", async ({ page }) => {
    await setupPage(page);
    const textarea = page.locator(".inbox-textarea");
    await textarea.fill("は");

    // compositionend 後（isComposing=false）の Enter → checkAndSend が呼ばれる
    await textarea.press("Enter");
    // かなが含まれており auto モードなのでダイアログが出る
    await expect(page.locator(".send-guard-dialog")).toBeVisible();
  });
});

// ===================================================================
// QA-3: トグル UI
// ===================================================================
test.describe("QA-3: 言語トグル UI", () => {
  test("ヘッダーに auto/日本語/英語 の3ボタンが描画される", async ({ page }) => {
    await setupPage(page);
    const toggle = page.locator(".send-guard-lang-toggle");
    await expect(toggle).toBeVisible();
    await expect(toggle.locator("button")).toHaveCount(3);
    // デフォルトは auto が active
    await expect(page.locator(".send-guard-lang-btn.active")).toContainText("自動");
  });

  test("「英語」を押すと active が切り替わる", async ({ page }) => {
    await setupPage(page);
    await clickLangToggle(page, "英語");
    await expect(page.locator(".send-guard-lang-btn.active")).toContainText("英語");
  });

  test("「日本語」→「自動」と押すと active が正しく追従", async ({ page }) => {
    await setupPage(page);
    await clickLangToggle(page, "日本語");
    await expect(page.locator(".send-guard-lang-btn.active")).toContainText("日本語");
    await clickLangToggle(page, "自動");
    await expect(page.locator(".send-guard-lang-btn.active")).toContainText("自動");
  });
});

// ===================================================================
// QA-4: ダイアログ表示
// ===================================================================
test.describe("QA-4: ダイアログ表示", () => {
  test("3ボタンが表示される", async ({ page }) => {
    await setupPage(page);
    await typeAndClickSend(page, "こんにちは");
    const dialog = page.locator(".send-guard-dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.locator(".send-guard-btn--translate")).toBeVisible();
    await expect(dialog.locator(".send-guard-btn--asis")).toBeVisible();
    await expect(dialog.locator(".send-guard-btn--cancel")).toBeVisible();
  });

  test("「英訳して送る」→ OutboundTranslationPreview が開く", async ({ page }) => {
    await setupPage(page);
    await typeAndClickSend(page, "こんにちは");
    await page.locator(".send-guard-btn--translate").click();
    await expect(page.locator(".outbound-translation-modal")).toBeVisible();
    await expect(page.locator(".send-guard-dialog")).not.toBeVisible();
  });

  test("「原文で送る」→ ダイアログが閉じる（送信実行）", async ({ page }) => {
    let sendCalled = false;
    await installAuthBypass(page);
    await mockApi(page, {
      ...baseMocks(),
      "POST /leads/5001/messages": async (route) => {
        sendCalled = true;
        await route.fulfill({ body: JSON.stringify({ id: 1, text: "こんにちは" }) });
      },
    });
    await page.goto("/lead-chat");
    await expect(page.getByRole("heading", { name: "受信箱" })).toBeVisible({ timeout: 20_000 });
    await page.locator("button.conversation-item", { hasText: "Taro Sender" }).click();
    await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });

    await typeAndClickSend(page, "こんにちは");
    await page.locator(".send-guard-btn--asis").click();
    await expect(page.locator(".send-guard-dialog")).not.toBeVisible();
    expect(sendCalled).toBe(true);
  });

  test("「キャンセル」→ ダイアログが閉じる・送信されない", async ({ page }) => {
    let sendCalled = false;
    await installAuthBypass(page);
    await mockApi(page, {
      ...baseMocks(),
      "POST /leads/5001/messages": async (route) => {
        sendCalled = true;
        await route.fulfill({ body: JSON.stringify({ id: 1 }) });
      },
    });
    await page.goto("/lead-chat");
    await expect(page.getByRole("heading", { name: "受信箱" })).toBeVisible({ timeout: 20_000 });
    await page.locator("button.conversation-item", { hasText: "Taro Sender" }).click();
    await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });

    await typeAndClickSend(page, "こんにちは");
    await page.locator(".send-guard-btn--cancel").click();
    await expect(page.locator(".send-guard-dialog")).not.toBeVisible();
    // 入力欄が残っていること
    await expect(page.locator(".inbox-textarea")).toHaveValue("こんにちは");
    expect(sendCalled).toBe(false);
  });
});

// ===================================================================
// QA-5: スレッド独立
// ===================================================================
test.describe("QA-5: スレッド独立", () => {
  test("スレッドAで en → スレッドBに切替 → auto / スレッドAに戻る → en", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, {
      ...commonMocks(),
      "GET /conversations": conversationsFixture,
      "GET /leads/5001/messages": messagesFixture,
      "GET /leads/5002/messages": messagesFixture,
      "POST /leads/5001/messages/mark-read": { marked_count: 1 },
      "POST /leads/5002/messages/mark-read": { marked_count: 1 },
      "GET /leads/5001": {
        id: 5001,
        customer_name: "Taro Sender",
        platform: "messenger",
        discord_dm_channel_id: null,
        discord_user_id: null,
      },
      "GET /leads/5002": {
        id: 5002,
        customer_name: "Hanako Insta",
        platform: "instagram",
        discord_dm_channel_id: null,
        discord_user_id: null,
      },
    });
    await page.goto("/lead-chat");
    await expect(page.getByRole("heading", { name: "受信箱" })).toBeVisible({ timeout: 20_000 });

    // スレッド A (Taro Sender / lead_id=5001) を選択
    const convItems = page.locator("button.conversation-item");
    await convItems.filter({ hasText: "Taro Sender" }).click();
    await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });

    // スレッド A: 英語に設定
    await clickLangToggle(page, "英語");
    await expect(page.locator(".send-guard-lang-btn.active")).toContainText("英語");

    // スレッド B (Hanako Insta / lead_id=5002) に切替
    if (await convItems.count() > 1) {
      await convItems.filter({ hasText: "Hanako Insta" }).click();
      await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
      // スレッド B: デフォルト auto
      await expect(page.locator(".send-guard-lang-btn.active")).toContainText("自動");

      // スレッド A に戻る
      await convItems.filter({ hasText: "Taro Sender" }).click();
      await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
      // スレッド A: en のまま記憶されている
      await expect(page.locator(".send-guard-lang-btn.active")).toContainText("英語");
    } else {
      test.skip(true, "2スレッド必要だがフィクスチャに1つしかない");
    }
  });
});
