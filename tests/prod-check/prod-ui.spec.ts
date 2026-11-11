/**
 * 本番の画面点検 S1〜S13（S9 は通知の試験）（見るだけ。書き込み操作はしない）
 *
 * 各 test 名は通知文にそのまま出る。何が壊れたか分かる名前にする。
 */

import type { Page } from "@playwright/test";
import { test, expect, SKIP_REASON } from "./fixtures";
import { creds, login, signOut } from "./login";

const NO_ERROR_BANNER = ".error-banner";

// API の返事そのものを待つ。goto/click/fill の「前」に呼んで、あとで await する（返事の取りこぼし防止）
function apiOk(page: Page, pathRe: RegExp) {
  return page.waitForResponse(
    (r) => r.request().method() === "GET" && pathRe.test(new URL(r.url()).pathname),
    { timeout: 20_000 },
  );
}
const COMPANIES_API = /^\/api\/v1\/companies$/;
const LEADS_API = /^\/api\/v1\/leads$/;
const COMPANY_DETAIL_API = /^\/api\/v1\/companies\/[^/]+$/;
const INVENTORY_API = /^\/api\/v1\/inventory$/;
const LEAD_DETAIL_API = /^\/api\/v1\/leads\/\d+$/;
const CALENDAR_EVENTS_API = /^\/api\/v1\/calendar\/events$/;

test.describe("本番の画面点検", () => {
  test("S1 画面が開く（ログイン画面）", async ({ page }) => {
    const res = await page.goto("/login");
    expect(res?.status(), "ログイン画面の応答").toBe(200);
    await expect(page.getByLabel("メールアドレス")).toBeVisible();
    await expect(page.getByLabel("パスワード", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "ログイン", exact: true })).toBeVisible();
  });

  test("S2 ログイン", async ({ page }) => {
    const c = creds();
    test.skip(!c, SKIP_REASON);
    const { email, password } = c!;
    await login(page, email, password);
    await expect(page).toHaveURL(/\/(dashboard)?$/);
  });

  test("S3 ダッシュボードにエラーが出ない", async ({ authedPage: page }) => {
    // ログイン済みの page を作ったあとから数える（/login を開いたときの refresh 401 は正常な動き）
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    await page.goto("/");
    // 画面は常時接続（新着の知らせ）を持つため networkidle にならない。読み込み完了＋5秒の間に出たエラーを数える
    await page.waitForLoadState("load");
    await expect(page.locator("main")).toBeVisible();
    await page.waitForTimeout(5_000);
    expect(errors, `console.error が ${errors.length} 件`).toHaveLength(0);
  });

  test("S4 会社一覧とリード一覧が開く", async ({ authedPage: page }) => {

    const companies = apiOk(page, COMPANIES_API);
    await page.goto("/crm/companies");
    expect((await companies).status(), "会社一覧の API の応答").toBeLessThan(400);
    await expect(page.getByPlaceholder("顧客名・コードで検索...")).toBeVisible();
    await expect(page.locator(NO_ERROR_BANNER)).toHaveCount(0);
    await expect(page.locator(".error-message")).toHaveCount(0);

    const leads = apiOk(page, LEADS_API);
    await page.goto("/crm/leads");
    expect((await leads).status(), "リード一覧の API の応答").toBeLessThan(400);
    await page.waitForURL((url) => url.pathname === "/crm/leads");
    await expect(page.locator("main")).toBeVisible();
    await expect(page.locator(NO_ERROR_BANNER)).toHaveCount(0);
    await expect(page.locator(".error-message")).toHaveCount(0);
  });

  test("S5 会社一覧の検索", async ({ authedPage: page }) => {
    const first = apiOk(page, COMPANIES_API);
    await page.goto("/crm/companies");
    expect((await first).status(), "会社一覧の API の応答").toBeLessThan(400);
    const box = page.getByPlaceholder("顧客名・コードで検索...");
    await expect(box).toBeVisible();
    const searched = page.waitForResponse(
      (r) => {
        const u = new URL(r.url());
        return r.request().method() === "GET" && COMPANIES_API.test(u.pathname) && u.searchParams.get("search") === "テスト";
      },
      { timeout: 20_000 },
    );
    await box.fill("テスト");
    expect((await searched).status(), "会社検索の API の応答").toBeLessThan(400);
    await expect(box).toHaveValue("テスト");
    await expect(page.locator(NO_ERROR_BANNER)).toHaveCount(0);
  });

  test("S6 会社の詳細が開く", async ({ authedPage: page }) => {
    const list = apiOk(page, COMPANIES_API);
    await page.goto("/crm/companies");
    expect((await list).status(), "会社一覧の API の応答").toBeLessThan(400);
    await expect(page.getByPlaceholder("顧客名・コードで検索...")).toBeVisible();
    await expect(page.locator("main .sa-loading-block")).toHaveCount(0);
    const link = page.locator('main a[href^="/companies/"]').first();
    test.skip((await link.count()) === 0, "会社 0 件");
    const detail = apiOk(page, COMPANY_DETAIL_API);
    await link.click();
    expect((await detail).status(), "会社詳細の API の応答").toBeLessThan(400);
    await page.waitForURL(/\/crm\/companies\/[^/]+$/);
    await expect(page.locator("main .sa-loading-block")).toHaveCount(0);
    await expect(page.locator(NO_ERROR_BANNER)).toHaveCount(0);
    await expect(page.locator("main")).toBeVisible();
  });

  // 点検用の人のメールでは行わない（失敗を重ねると締め出されるため）
  test("S7 間違ったパスワードでは入れない", async ({ page }) => {
    await page.goto("/login");
    // .invalid は EmailStr が形の誤りとして弾く（422）。弾かれない予約ドメイン example.com を使う
    await page.getByLabel("メールアドレス").fill("prod-ui-check-nobody@example.com");
    await page.getByLabel("パスワード", { exact: true }).fill("prod-ui-check-wrong-password-0");
    const loginRes = page.waitForResponse(
      (r) => r.request().method() === "POST" && new URL(r.url()).pathname === "/api/v1/auth/login",
      { timeout: 20_000 },
    );
    await page.getByRole("button", { name: "ログイン", exact: true }).click();
    expect((await loginRes).status(), "ログイン API の応答（パスワード違いは 401）").toBe(401);
    await expect(page.locator(".error-message")).toBeVisible();
    expect(new URL(page.url()).pathname).toBe("/login");
  });

  test("S8 ログアウト", async ({ page }) => {
    const c = creds();
    test.skip(!c, SKIP_REASON);
    const { email, password } = c!;
    await login(page, email, password);
    await signOut(page);
    await expect(page).toHaveURL(/\/login$/);
  });

  test("S10 在庫表が開く", async ({ authedPage: page }) => {
    const inv = apiOk(page, INVENTORY_API);
    await page.goto("/inventory");
    expect((await inv).status(), "在庫表の API の応答").toBeLessThan(400);
    await expect(page.locator("main")).toBeVisible();
    await expect(page.locator("main [data-testid=inventory-loading]")).toBeHidden();
    await expect(page.locator(NO_ERROR_BANNER)).toHaveCount(0);
    await expect(page.locator(".error-message")).toHaveCount(0);
  });

  test("S11 リードの詳細が開く", async ({ authedPage: page }) => {
    const list = apiOk(page, LEADS_API);
    await page.goto("/crm/leads");
    const listRes = await list;
    expect(listRes.status(), "リード一覧の API の応答").toBeLessThan(400);
    const rows = (await listRes.json()) as Array<{ id: number }>;
    test.skip(!Array.isArray(rows) || rows.length === 0, "リード 0 件");
    const detail = apiOk(page, LEAD_DETAIL_API);
    await page.goto(`/crm/leads/${rows[0].id}/edit`);
    expect((await detail).status(), "リード詳細の API の応答").toBeLessThan(400);
    await expect(page.locator("main")).toBeVisible();
    await expect(page.locator("main .sa-loading-block")).toHaveCount(0);
    await expect(page.locator(NO_ERROR_BANNER)).toHaveCount(0);
    await expect(page.locator(".error-message")).toHaveCount(0);
  });

  test("S12 予定表が開きエラーが出ない", async ({ authedPage: page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    const events = apiOk(page, CALENDAR_EVENTS_API);
    await page.goto("/schedule");
    expect((await events).status(), "予定の API の応答").toBeLessThan(400);
    await expect(page.locator("main .comp-calendar")).toBeVisible();
    await expect(page.locator("main .schedule-loading")).toHaveCount(0);
    await expect(page.locator("main .schedule-error")).toHaveCount(0);
    await page.waitForTimeout(5_000);
    expect(errors, `console.error が ${errors.length} 件`).toHaveLength(0);
  });

  test("S13 予定表の作る小窓と全画面の編集が開いて閉じる（保存しない）", async ({ authedPage: page }) => {
    // 書き込みは送らせない。ログインの札の更新（/api/v1/auth/refresh）以外の GET でない通信は止めて数える
    const blockedWrites: string[] = [];
    await page.route("**/api/**", (route) => {
      const req = route.request();
      const path = new URL(req.url()).pathname;
      if (req.method() !== "GET" && path !== "/api/v1/auth/refresh") {
        blockedWrites.push(`${req.method()} ${path}`);
        return route.abort();
      }
      return route.continue();
    });
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });

    const events = apiOk(page, CALENDAR_EVENTS_API);
    await page.goto("/schedule");
    expect((await events).status(), "予定の API の応答").toBeLessThan(400);
    await expect(page.locator("main .comp-calendar")).toBeVisible();
    await expect(page.locator("main .schedule-loading")).toHaveCount(0);
    const viewButton = page.locator('main button[aria-haspopup="menu"]').first();
    const viewBefore = (await viewButton.innerText()).trim();

    // 1. キー c で作る小窓を開き、題名を入れる
    await page.keyboard.press("c");
    const popover = page.locator(".schedule-popover--create");
    await expect(popover, "キー c で作る小窓が開く").toBeVisible();
    const popoverTitle = popover.getByRole("textbox", { name: "タイトル", exact: true });
    await popoverTitle.fill("prod-ui-check-s13");

    // 2. Google Meet の名前の付いた切り替えスイッチは無い
    await expect(page.getByRole("switch", { name: /Google Meet/ }), "Meet のスイッチは 0 個").toHaveCount(0);

    // 3. Meet の行（Google をつないだ管理者だけに出る）。出たときだけ押して外す
    const addMeet = popover.getByRole("button", { name: "Google Meet のビデオ会議を追加", exact: true });
    if ((await addMeet.count()) > 0) {
      await addMeet.click();
      await expect(popover.getByText("Google Meet のビデオ会議（保存すると参加用のリンクができます）", { exact: true })).toBeVisible();
      await popover.getByRole("button", { name: "Google Meet を外す", exact: true }).click();
      await expect(addMeet).toBeVisible();
    } else {
      test.info().annotations.push({ type: "note", description: "Meet の行は出ない（点検用の人は管理者でない）" });
    }

    // 4. その他のオプションで窓いっぱいの編集画面が開き、題名が引き継がれる
    await popover.getByRole("button", { name: "その他のオプション", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "予定の編集", exact: true });
    await expect(dialog, "全画面の編集が開く").toBeVisible();
    const box = await dialog.boundingBox();
    // 比べる相手はスクロール帯を除いた窓の中の大きさ（審査の指摘 2）
    const viewport = await page.evaluate(() => ({ width: document.documentElement.clientWidth, height: window.innerHeight }));
    expect(box, "全画面の編集の大きさ").not.toBeNull();
    expect(Math.abs(box!.x), "左端").toBeLessThanOrEqual(1);
    expect(Math.abs(box!.y), "上端").toBeLessThanOrEqual(1);
    expect(Math.abs(box!.width - viewport.width), "幅が窓と同じ").toBeLessThanOrEqual(1);
    expect(Math.abs(box!.height - viewport.height), "高さが窓と同じ").toBeLessThanOrEqual(1);
    await expect(dialog.getByRole("textbox", { name: "タイトル", exact: true }), "題名の引き継ぎ").toHaveValue("prod-ui-check-s13");

    // 5. 編集画面では近道のキーが効かない（入力欄の外で m を押す）
    const closeButton = dialog.getByRole("button", { name: "閉じる", exact: true });
    await closeButton.focus();
    await page.keyboard.press("m");
    await expect(dialog, "m を押しても編集画面は開いたまま").toBeVisible();
    await expect(viewButton, "m を押しても表示は変わらない").toHaveText(viewBefore);

    // 6. Tab を 25 回押してもフォーカスは編集画面の中
    for (let i = 0; i < 25; i += 1) {
      await page.keyboard.press("Tab");
    }
    await expect(dialog.locator(":focus"), "フォーカスは編集画面の中").toHaveCount(1);

    // 7. Esc で編集画面が閉じ、作る小窓と題名が残る
    await page.keyboard.press("Escape");
    await expect(dialog, "Esc で編集画面が閉じる").toHaveCount(0);
    await expect(popover, "作る小窓は残る").toBeVisible();
    await expect(popoverTitle, "題名は残る").toHaveValue("prod-ui-check-s13");

    // 8. もう一度 Esc で作る小窓も閉じる（保存はしない）
    await page.keyboard.press("Escape");
    await expect(popover, "Esc で作る小窓も閉じる").toHaveCount(0);

    expect(blockedWrites, `止めた書き込み ${blockedWrites.length} 件`).toHaveLength(0);
    expect(errors, `console.error が ${errors.length} 件`).toHaveLength(0);
  });

  // 通知の試験用。PROD_CHECK_FORCE_FAIL=1 のときだけ足す（必ず落ちる）
  if (process.env.PROD_CHECK_FORCE_FAIL === "1") {
    test("S9 通知の試験（わざと落とす）", async ({ page }) => {
      await page.goto("/login");
      await expect(page.getByText("prod-ui-check-force-fail-zzz")).toBeVisible({ timeout: 3_000 });
    });
  }
});
