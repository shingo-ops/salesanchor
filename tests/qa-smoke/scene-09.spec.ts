/**
 * ADR-038 / Scene 09: ADR-108 B-1 販売形態複数選択 + 周辺機能検収
 *
 * 目的:
 *   A. カルテ company tab 販売形態複数選択 UI の動作確認
 *   B. Redis tenant cache 無効化（論理削除後）— 検証専用テナントのみ
 *   C. Discord Auto Setup 疎通確認 — 安全な guild のみ
 *
 * 前提:
 *   - tenant_006 (tenant-review) で実行
 *   - sales_form_options は beforeAll で seed（migration は tenant_004 のみのため）
 *   - B / C は環境変数フラグで有効化（デフォルト: スキップ）
 *
 * 環境変数:
 *   QA_ADMIN_EMAIL / QA_ADMIN_PASSWORD   (必須)
 *   DATABASE_URL                          (必須: psql seed用)
 *   QA_RUN_SCENE_B=true                  (省略時スキップ)
 *   QA_RUN_SCENE_C=true                  (省略時スキップ)
 *   QA_SCENE_C_GUILD_ID                  (C実行時必須)
 *
 * 所要: 10〜20 分
 */

import { expect, test } from "@playwright/test";
import { login, logout, collectConsoleErrors } from "./utils/real-backend";
import { psqlRows, psqlCount } from "./utils/db-assert";

const TENANT_ID = Number(process.env.QA_TENANT_ID || "6");
const SCHEMA = `tenant_${String(TENANT_ID).padStart(3, "0")}`;
const RUN_B = process.env.QA_RUN_SCENE_B === "true";
const RUN_C = process.env.QA_RUN_SCENE_C === "true";
const GUILD_ID = process.env.QA_SCENE_C_GUILD_ID || "";

// ─────────────────────────────────────────────
// Setup: tenant_006 に sales_form_options を seed
// ─────────────────────────────────────────────
test.beforeAll(async () => {
  psqlRows(`
    INSERT INTO ${SCHEMA}.tenant_sales_form_options (tenant_id, label, value, sort_order)
    VALUES
      (${TENANT_ID}, '実店舗',    'physical_store',  1),
      (${TENANT_ID}, 'ECサイト',  'ec_site',          2),
      (${TENANT_ID}, 'ライブ配信', 'live_streaming',  3),
      (${TENANT_ID}, '卸・代理店', 'wholesale',       4),
      (${TENANT_ID}, 'その他',    'other',            5)
    ON CONFLICT (tenant_id, value) DO NOTHING
  `);
});

// ─────────────────────────────────────────────
// A. カルテ company tab 販売形態複数選択
// ─────────────────────────────────────────────
test.describe("Scene 09-A: 販売形態複数選択 (ADR-108 B-1)", { tag: ["@scene-09"] }, () => {
  test.afterEach(async ({ page }) => {
    await logout(page).catch(() => {/* best-effort */});
  });

  test("A-1: company tab に SalesFormMultiSelect が表示される", async ({ page }) => {
    const { errors } = collectConsoleErrors(page);
    await login(page, "admin");

    // QA-LD-001 リードを開く
    await page.goto("/inbox");
    await page.waitForLoadState("networkidle");

    // リード一覧から QA-LD-001 を探してクリック
    const leadLink = page.getByText(/QA-LD-001|QA-CO-001/i).first();
    await expect(leadLink).toBeVisible({ timeout: 15_000 });
    await leadLink.click();

    // company タブをクリック
    const companyTab = page.getByRole("tab", { name: /company|会社/i });
    await expect(companyTab).toBeVisible({ timeout: 10_000 });
    await companyTab.click();

    // SalesFormMultiSelect が表示されること（data-testid）
    const dropdown = page.locator("[data-testid='sales-form-dropdown-trigger']");
    await expect(dropdown).toBeVisible({ timeout: 10_000 });

    // console error なし
    expect(errors.filter(e => !/favicon/i.test(e)), "console error が出ています").toHaveLength(0);
  });

  test("A-2: 複数選択 + 保存 + 再表示で選択が復元される", async ({ page }) => {
    const { errors } = collectConsoleErrors(page);
    await login(page, "admin");

    // QA-LD-002 を開く（別リードでクリーンな状態から）
    await page.goto("/inbox");
    await page.waitForLoadState("networkidle");

    const leadLink = page.getByText(/QA-LD-002/i).first();
    if (await leadLink.count() === 0) {
      test.skip(true, "QA-LD-002 が見つかりません — seed を確認してください");
      return;
    }
    await leadLink.click();

    const companyTab = page.getByRole("tab", { name: /company|会社/i });
    await companyTab.click();

    const trigger = page.locator("[data-testid='sales-form-dropdown-trigger']");
    await expect(trigger).toBeVisible({ timeout: 10_000 });
    await trigger.click();

    // ドロップダウンが開く
    const dropdown = page.locator("[data-testid='sales-form-dropdown']");
    await expect(dropdown).toBeVisible({ timeout: 5_000 });

    // 実店舗 を選択
    const opt1 = dropdown.getByText("実店舗");
    await expect(opt1).toBeVisible();
    await opt1.click();

    // ECサイト を選択
    const opt2 = dropdown.getByText("ECサイト");
    await opt2.click();

    // 外クリックでドロップダウンを閉じる
    await page.locator("body").click({ position: { x: 10, y: 10 } });
    await expect(dropdown).toBeHidden({ timeout: 3_000 });

    // 保存（カルテの自動保存 or 保存ボタン）
    // PATCH が走るまで少し待つ（自動保存の場合）
    await page.waitForTimeout(1_500);
    const saveBtn = page.getByRole("button", { name: /保存|save/i });
    if (await saveBtn.isVisible()) await saveBtn.click();
    await page.waitForLoadState("networkidle");

    // ページリロードして復元確認
    await page.reload({ waitUntil: "networkidle" });
    const companyTabAfter = page.getByRole("tab", { name: /company|会社/i });
    await companyTabAfter.click();

    // 選択ラベルが残っていること（ピルまたは trigger テキストで確認）
    await expect(page.getByText("実店舗")).toBeVisible({ timeout: 8_000 });
    await expect(page.getByText("ECサイト")).toBeVisible({ timeout: 8_000 });

    expect(errors.filter(e => !/favicon/i.test(e)), "console error が出ています").toHaveLength(0);
  });

  test("A-3: 「その他」選択時のみ自由記述欄が表示される", async ({ page }) => {
    await login(page, "admin");

    await page.goto("/inbox");
    await page.waitForLoadState("networkidle");

    const leadLink = page.getByText(/QA-LD-003/i).first();
    if (await leadLink.count() === 0) {
      test.skip(true, "QA-LD-003 が見つかりません");
      return;
    }
    await leadLink.click();

    const companyTab = page.getByRole("tab", { name: /company|会社/i });
    await companyTab.click();

    const trigger = page.locator("[data-testid='sales-form-dropdown-trigger']");
    await trigger.click();
    const dropdown = page.locator("[data-testid='sales-form-dropdown']");

    // 「その他」以外を選択 → 自由記述欄が出ないこと
    await dropdown.getByText("実店舗").click();
    const otherInput = page.locator("[data-testid='sales-form-other-input']");
    await expect(otherInput).toBeHidden({ timeout: 3_000 });

    // 「その他」を選択 → 自由記述欄が出ること
    await dropdown.getByText("その他").click();
    await expect(otherInput).toBeVisible({ timeout: 3_000 });

    // 自由記述を入力して保存
    await otherInput.fill("QA検収テスト自由記述");
    await page.locator("body").click({ position: { x: 10, y: 10 } });
    await page.waitForTimeout(1_500);

    const saveBtn = page.getByRole("button", { name: /保存|save/i });
    if (await saveBtn.isVisible()) await saveBtn.click();
    await page.waitForLoadState("networkidle");

    // リロードして復元確認
    await page.reload({ waitUntil: "networkidle" });
    const tab2 = page.getByRole("tab", { name: /company|会社/i });
    await tab2.click();
    await expect(page.getByText("QA検収テスト自由記述")).toBeVisible({ timeout: 8_000 });
  });

  test("A-4: DB で選択内容が正しく保存されている", async ({ page }) => {
    // A-2 で保存したデータを DB で確認
    const count = psqlCount(`
      SELECT COUNT(*) FROM ${SCHEMA}.lead_sales_form_selections s
      JOIN ${SCHEMA}.tenant_sales_form_options o ON o.id = s.option_id
      WHERE o.value IN ('physical_store', 'ec_site')
    `);
    expect(count, "lead_sales_form_selections に保存データがありません").toBeGreaterThanOrEqual(1);
  });
});

// ─────────────────────────────────────────────
// B. Redis tenant cache 無効化
// ─────────────────────────────────────────────
test.describe("Scene 09-B: Redis tenant cache 無効化", { tag: ["@scene-09-b"] }, () => {
  test("B-1: 論理削除後に Redis cache が無効化される", async ({ page }) => {
    if (!RUN_B) {
      test.skip(true, "QA_RUN_SCENE_B=true が未設定のためスキップ（本番稼働テナントへの実施禁止）");
      return;
    }

    // この test は検証専用テナント (tenant_006) 専用。
    // 論理削除 → 再ログイン試行 → 403 を確認する。
    // 注意: このテスト実行後 tenant_006 は論理削除状態になるため、
    //       reset-tenant.sh で必ず復元すること。

    await login(page, "admin");

    // 論理削除 API 呼び出し（super-admin 権限が必要）
    const apiUrl = process.env.QA_SMOKE_API_URL || "https://api.salesanchor.jp";
    const tokenResult = await page.evaluate(() =>
      (window as unknown as { __firebaseGetToken?: () => Promise<string> }).__firebaseGetToken?.()
    );

    if (!tokenResult) {
      test.skip(true, "Firebase token 取得不可");
      return;
    }

    // 論理削除実行（tenant_006 限定）
    const deleteRes = await page.request.delete(`${apiUrl}/api/v1/super-admin/tenants/${TENANT_ID}/logical`, {
      headers: { Authorization: `Bearer ${tokenResult}` },
    });
    expect(deleteRes.status()).toBe(200);

    // 少し待って Redis cache 反映
    await page.waitForTimeout(3_000);

    // 削除後に API アクセスが 403 になること
    const checkRes = await page.request.get(`${apiUrl}/api/v1/leads`, {
      headers: { Authorization: `Bearer ${tokenResult}` },
    });
    expect(checkRes.status(), "論理削除後に403が返っていません（Redisキャッシュが残っている可能性）").toBe(403);

    // DB で is_active=false 確認
    const isActive = psqlCount(`
      SELECT COUNT(*) FROM public.tenants WHERE id=${TENANT_ID} AND is_active=TRUE
    `);
    expect(isActive).toBe(0);
  });
});

// ─────────────────────────────────────────────
// C. Discord Auto Setup
// ─────────────────────────────────────────────
test.describe("Scene 09-C: Discord Auto Setup", { tag: ["@scene-09-c"] }, () => {
  test("C-1: Auto Setup が安全な guild で冪等実行できる", async ({ page }) => {
    if (!RUN_C || !GUILD_ID) {
      test.skip(
        true,
        "QA_RUN_SCENE_C=true かつ QA_SCENE_C_GUILD_ID が未設定のためスキップ",
      );
      return;
    }

    await login(page, "admin");

    // Discord 設定画面へ
    await page.goto("/settings/discord");
    await page.waitForLoadState("networkidle");

    // Auto Setup ボタンを探す
    const setupBtn = page.getByRole("button", { name: /auto setup|自動セットアップ/i });
    await expect(setupBtn).toBeVisible({ timeout: 10_000 });
    await setupBtn.click();

    // 成功 toast または結果表示
    await expect(
      page.getByText(/成功|完了|success|created|スキップ|skipped/i)
    ).toBeVisible({ timeout: 30_000 });

    // 2回目実行（冪等性確認）
    await setupBtn.click();
    await expect(
      page.getByText(/成功|完了|success|スキップ|skipped|冪等/i)
    ).toBeVisible({ timeout: 30_000 });
  });
});
