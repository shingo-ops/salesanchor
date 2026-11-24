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
import { COUNTRIES } from "../src/constants/countries";
import { mockApi } from "./utils/api-mock";

const TOKEN = "test-token-ux-fix";

const VERIFY_OK = {
  valid: true,
  company_name: "テスト株式会社",
  lead_id: 42,
  token_type: "register",
};

const SUBMIT_OK = { success: true, message: "登録が完了しました" };

async function setupPage(page: Parameters<typeof mockApi>[0], postResponse?: object, lang?: string) {
  await mockApi(page, {
    "GET /public/register": VERIFY_OK,
    "POST /public/register": postResponse ?? SUBMIT_OK,
  });
  await page.goto(`/register?token=${TOKEN}${lang ? `&lang=${lang}` : ""}`);
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

test("B-3: City は1行・State と ZIP は同じ行に並ぶ（customer-address-form K3）", async ({ page }) => {
  await setupPage(page, undefined, "en");
  const billing = page.locator("fieldset").first();
  const line1 = await billing.getByLabel("Address Line 1").boundingBox();
  const city = await billing.getByLabel("City").boundingBox();
  const state = await billing.getByLabel("State / Province").boundingBox();
  const zip = await billing.getByLabel("ZIP / Postal Code").boundingBox();
  expect(line1 && city && state && zip).toBeTruthy();
  // City は1行を占め（住所1と同じ幅）、State と ZIP は City の下で上端が同じ
  expect(Math.abs(city!.width - line1!.width)).toBeLessThanOrEqual(1);
  expect(state!.y).toBeGreaterThan(city!.y);
  expect(Math.abs(state!.y - zip!.y)).toBeLessThanOrEqual(1);
  expect(zip!.x).toBeGreaterThan(state!.x);
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

test("C-6: API 422 detail が配列でも [object Object] にならず可読テキストになる", async ({ page }) => {
  await setupPage(page, {
    status: 422,
    body: { detail: [{ msg: "担当者名は必須です" }, { msg: "メールアドレスが不正です" }] },
  });
  const contactFieldset = page.locator("fieldset").first();
  await contactFieldset.locator("label", { hasText: "担当者名" }).locator("input").fill("テスト");
  await contactFieldset.locator("input[type=email]").fill("t@example.com");
  await page.locator("button[type=submit]").click();
  const banner = page.locator(".error-banner");
  await expect(banner).toBeVisible();
  await expect(banner).not.toContainText("[object Object]");
  await expect(banner).toContainText("担当者名");
});

// --- customer-address-form（K1・K2・K5〜K9）。画面は英語（?lang=en） ---

type Posted = { addresses?: Array<Record<string, string>>; address?: Record<string, string> };

async function setupWithPosts(page: Parameters<typeof mockApi>[0], path = "/register") {
  const posts: Posted[] = [];
  const record = (url: string) => async (route: import("@playwright/test").Route) => {
    posts.push(route.request().postDataJSON() as Posted);
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(SUBMIT_OK) });
    void url;
  };
  await mockApi(page, {
    "GET /public/register": VERIFY_OK,
    "POST /public/register": record("register"),
    "POST /public/register/change-billing": record("change-billing"),
  });
  await page.goto(`${path}?token=${TOKEN}&lang=en`);
  await page.waitForLoadState("networkidle");
  return posts;
}

async function fillBillingBasics(page: Parameters<typeof mockApi>[0], line1: string) {
  const billing = page.locator("fieldset").first();
  await billing.locator("input[required]").first().fill("Acme Billing"); // Billing Name（ヒント文つきのラベルなので位置で指す）
  await billing.locator("input[type=tel]").fill("5551234567");
  await billing.getByLabel("Email Address").fill("a@example.com");
  await billing.getByLabel("Address Line 1").fill(line1);
  return billing;
}

for (const path of ["/register", "/register/change-billing", "/register/address"]) {
  test(`K1: ${path} の言語切替が見出しと同じ行の右にある`, async ({ page }) => {
    await setupWithPosts(page, path);
    const h1 = await page.locator("h1").boundingBox();
    const toggle = await page.getByRole("button", { name: "Japanese" }).boundingBox();
    expect(h1 && toggle).toBeTruthy();
    const centerY = toggle!.y + toggle!.height / 2;
    expect(centerY).toBeGreaterThanOrEqual(h1!.y);
    expect(centerY).toBeLessThanOrEqual(h1!.y + h1!.height);
    expect(toggle!.x).toBeGreaterThan(h1!.x + h1!.width);
  });
}

test("K2: 国番号の欄は幅 80px で、全ての国番号が欠けずに入る", async ({ page }) => {
  test.setTimeout(180_000);
  await setupWithPosts(page);
  const input = page.locator("#billing-dial");
  const wrapper = page.locator(".field-w-xs").first();
  const box = await wrapper.boundingBox();
  expect(Math.round(box!.width)).toBe(80);
  for (const c of COUNTRIES) {
    await input.evaluate((el: HTMLInputElement) => el.blur()); // 前回の選択で焦点が残るため、開き直すのに外す
    await input.click();
    const label = `${c.dial} ${c.name}`;
    await page
      .locator(".register-combobox__option")
      .filter({ hasText: new RegExp(`^${label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`) })
      .first()
      .click();
    const fits = await input.evaluate((el: HTMLInputElement) => el.scrollWidth <= el.clientWidth);
    expect(fits, `${c.dial} (${c.name}) が欄に収まる`).toBe(true);
    expect(await input.inputValue()).toBe(c.dial);
  }
});

test("K5: 請求先の住所1の幅を測る（変更前との比べは evaluator が行う）", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await setupWithPosts(page);
  const billing = page.locator("fieldset").first();
  const line1 = await billing.getByLabel("Address Line 1").boundingBox();
  const line2 = await billing.getByLabel("Address Line 2").boundingBox();
  const outer = await page.locator(".page-container").first().boundingBox();
  console.log(`K5 width: line1=${line1!.width} line2=${line2!.width} outer=${outer!.width}`);
  expect(outer!.width).toBeLessThanOrEqual(600);
  expect(line1!.width).toBeGreaterThan(400);
  expect(line1!.width).toBeLessThanOrEqual(600);
});

test("K6: 送り先の住所1が36文字なら赤＋文が出て送れず、35文字なら送れる", async ({ page }) => {
  const posts = await setupWithPosts(page);
  const billing = await fillBillingBasics(page, "x".repeat(36)); // 「同じ住所へ」が既定 → 請求先にも決まりが効く
  await expect(billing.getByText("Please enter 35 characters or fewer.")).toBeVisible();
  await page.getByRole("button", { name: "Register" }).click();
  await page.waitForTimeout(300);
  expect(posts).toHaveLength(0);
  await billing.getByLabel("Address Line 1").fill("x".repeat(35));
  await expect(billing.getByText("Please enter 35 characters or fewer.")).toHaveCount(0);
  await page.getByRole("button", { name: "Register" }).click();
  await expect(page.locator("h1")).toContainText("Registration Complete");
  expect(posts).toHaveLength(1);
});

test("K7: 日本語・é は「英字・数字・記号で入力してください」で送れない", async ({ page }) => {
  const posts = await setupWithPosts(page);
  const billing = await fillBillingBasics(page, "東京");
  await expect(billing.getByText("Please use English letters, numbers and symbols only.")).toBeVisible();
  await billing.getByLabel("Address Line 1").fill("Café");
  await expect(billing.getByText("Please use English letters, numbers and symbols only.")).toBeVisible();
  await page.getByRole("button", { name: "Register" }).click();
  await page.waitForTimeout(300);
  expect(posts).toHaveLength(0);
});

test("K8: 請求先は「同じ住所へ」の時だけ決まりが効く（Proceed なら36文字でも送れる）", async ({ page }) => {
  const posts = await setupWithPosts(page);
  const billing = await fillBillingBasics(page, "y".repeat(36));
  await expect(billing.getByText("Please enter 35 characters or fewer.")).toBeVisible();
  await page.getByLabel("Proceed to register.").check();
  await expect(billing.getByText("Please enter 35 characters or fewer.")).toHaveCount(0);
  const shipping = page.locator("fieldset").nth(1);
  await shipping.getByLabel("Recipient Name").fill("Recv Person");
  await shipping.getByLabel("Address Line 1").fill("1-2 Main St, #3");
  await page.getByRole("button", { name: "Register" }).click();
  await expect(page.locator("h1")).toContainText("Registration Complete");
  expect(posts).toHaveLength(1);
  const sent = posts[0].addresses ?? [];
  expect(sent.find((a) => a.address_type === "billing")?.address_line_1).toBe("y".repeat(36));
  expect(sent.find((a) => a.address_type === "delivery")?.address_line_1).toBe("1-2 Main St, #3");
});

test("K9: 請求先に住所3の欄があり、送る中身に address_line_3 が入る（/register・/register/change-billing）", async ({ page }) => {
  const posts = await setupWithPosts(page);
  const billing = await fillBillingBasics(page, "1 Main St");
  await billing.getByLabel("Address Line 3").fill("Building C");
  await page.getByRole("button", { name: "Register" }).click();
  await expect(page.locator("h1")).toContainText("Registration Complete");
  expect(posts[0].addresses?.find((a) => a.address_type === "billing")?.address_line_3).toBe("Building C");

  const page2Posts = await setupWithPosts(page, "/register/change-billing");
  const form = await fillBillingBasics(page, "2 Side St");
  await form.getByLabel("Address Line 3").fill("Floor 9");
  await page.locator("button[type=submit]").click();
  await expect(page.locator("h1")).toBeVisible();
  await expect.poll(() => page2Posts.length).toBe(1);
  expect(page2Posts[0].address?.address_line_3).toBe("Floor 9");
});
