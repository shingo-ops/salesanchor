/**
 * 公開登録フォーム UX是正 E2E（PR #1782 / ADR-SA-03）
 *
 * 検証観点:
 *   A. ラベル是正: billing=「支払い名義」、delivery=「宛名（送付先）」、
 *                  address email/tel = 「連絡用・任意」テキスト含む
 *   B. レイアウト: ContactInfo が最上部・都道府県が市区町村より上
 *   C. 担当者必須化: name空 or 連絡先両方空 → 送信ブロック
 *                   正常入力 → 登録完了。422 レスポンス → エラーバナー表示
 */

import { expect, test } from "@playwright/test";
import { mockApi } from "./utils/api-mock";

const TOKEN = "test-token-ux-fix";

const VERIFY_OK = {
  valid: true,
  company_name: "テスト株式会社",
  lead_id: 42,
  token_type: "register",
};

const SUBMIT_OK = { success: true, message: "登録が完了しました" };

async function setupPage(page: Parameters<typeof mockApi>[0], postResponse?: object) {
  await mockApi(page, {
    "GET /public/register": VERIFY_OK,
    "POST /public/register": postResponse ?? SUBMIT_OK,
  });
  await page.goto(`/register?token=${TOKEN}`);
  await page.waitForLoadState("networkidle");
}

// --- B. レイアウト ---

test("B-1: ContactInfo セクションがフォーム最上部（fieldset[0]）に表示される", async ({ page }) => {
  await setupPage(page);
  const legend = page.locator("fieldset").first().locator("legend");
  await expect(legend).toContainText("担当者");
});

test("B-2: ContactInfo がヒント文を表示する", async ({ page }) => {
  await setupPage(page);
  const firstFieldset = page.locator("fieldset").first();
  await expect(firstFieldset).toContainText("お一人で運営の場合");
});

test("B-3: 都道府県ラベルが市区町村ラベルより上に表示される（縦並び）", async ({ page }) => {
  await setupPage(page);
  // billing fieldset (2番目)
  const billingFieldset = page.locator("fieldset").nth(1);
  const stateLabel = billingFieldset.locator("label", { hasText: "都道府県" });
  const cityLabel = billingFieldset.locator("label", { hasText: "市区町村" });
  const stateBox = await stateLabel.boundingBox();
  const cityBox = await cityLabel.boundingBox();
  expect(stateBox).toBeTruthy();
  expect(cityBox).toBeTruthy();
  // state が city より上（y 座標が小さい）
  expect(stateBox!.y).toBeLessThan(cityBox!.y);
});

// --- A. ラベル是正 ---

test("A-1: billing の名前ラベルが「支払い名義」", async ({ page }) => {
  await setupPage(page);
  const billingFieldset = page.locator("fieldset").nth(1);
  await expect(billingFieldset).toContainText("支払い名義");
});

test("A-2: delivery の名前ラベルが「宛名（送付先）」", async ({ page }) => {
  await setupPage(page);
  const deliveryFieldset = page.locator("fieldset").nth(2);
  await expect(deliveryFieldset).toContainText("宛名（送付先）");
});

test("A-3: 住所の email/telephone が「連絡用・任意」テキストを含む", async ({ page }) => {
  await setupPage(page);
  const billingFieldset = page.locator("fieldset").nth(1);
  await expect(billingFieldset).toContainText("連絡用・任意");
});

// --- C. 担当者必須化 ---

test("C-1: 担当者名が空のまま送信ボタンを押すと送信ブロックされエラー表示", async ({ page }) => {
  await setupPage(page);
  await page.locator("button[type=submit]").click();
  const banner = page.locator(".error-banner");
  await expect(banner).toBeVisible();
  await expect(banner).toContainText("担当者名");
});

test("C-2: 担当者名を入力して連絡先（email/tel）が両方空の場合もブロック", async ({ page }) => {
  await setupPage(page);
  const contactFieldset = page.locator("fieldset").first();
  // 名前のみ入力（email/tel は空のまま）
  await contactFieldset.locator("label", { hasText: "担当者名" }).locator("input").fill("田中太郎");
  await page.locator("button[type=submit]").click();
  const banner = page.locator(".error-banner");
  await expect(banner).toBeVisible();
  await expect(banner).toContainText("メールアドレスまたは電話番号");
});

test("C-3: 担当者名 + email を入力して送信すると登録完了画面になる", async ({ page }) => {
  await setupPage(page);
  const contactFieldset = page.locator("fieldset").first();
  await contactFieldset.locator("label", { hasText: "担当者名" }).locator("input").fill("田中太郎");
  await contactFieldset.locator("input[type=email]").fill("tanaka@example.com");
  await page.locator("button[type=submit]").click();
  await expect(page.locator("h1")).toContainText("登録完了");
});

test("C-4: 担当者名 + 電話番号のみでも送信成功（email 不要）", async ({ page }) => {
  await setupPage(page);
  const contactFieldset = page.locator("fieldset").first();
  await contactFieldset.locator("label", { hasText: "担当者名" }).locator("input").fill("山田花子");
  await contactFieldset.locator("input[type=tel]").fill("09012345678");
  await page.locator("button[type=submit]").click();
  await expect(page.locator("h1")).toContainText("登録完了");
});

test("C-5: API 422 レスポンス → エラーバナー表示（500 でない）", async ({ page }) => {
  await setupPage(page, { status: 422, body: { detail: "担当者名は必須です" } });
  const contactFieldset = page.locator("fieldset").first();
  // フロントバリデーションを通過させる入力
  await contactFieldset.locator("label", { hasText: "担当者名" }).locator("input").fill("テスト");
  await contactFieldset.locator("input[type=email]").fill("t@example.com");
  await page.locator("button[type=submit]").click();
  const banner = page.locator(".error-banner");
  await expect(banner).toBeVisible();
  // 500 エラーは表示されない
  await expect(banner).not.toContainText("500");
});
