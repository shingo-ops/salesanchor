import { expect, test } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi, type MockMap } from "./utils/api-mock";

const importId = "11111111-1111-4111-8111-111111111111";

const progress = {
  scope: { type: "import", import_job_id: importId },
  as_of: "2026-09-10T00:00:00Z",
  coverage: "complete",
  review_status: "ok",
  reason: null,
  messages: { unit: "source_message", total: 51, created: 51, reused: 0, inactive: 0, without_extraction_job: 0 },
  extraction: { unit: "extraction_job", total: 51, completed: 51, pending: 0, running: 0, unknown: 0, succeeded: 37, empty: 14, failed: 0, residual_items_on_error: 0, residual_results_on_error: 0 },
  analysis: { unit: "extraction_item", total: 1019, results_present: 1019, results_missing: 0, needs_review: 313, execution_state: "unrecorded" },
};

const items = (offset: number) => ({
  scope: { type: "import", import_job_id: importId },
  as_of: "2026-09-10T00:00:00Z",
  coverage: "complete",
  review_status: "ok",
  reason: null,
  total: 50,
  limit: 25,
  offset,
  filter: "all",
  unit: "extraction_item",
  items: Array.from({ length: 25 }, (_, index) => ({
    id: `item-${offset + index}`,
    extraction_job_id: "22222222-2222-4222-8222-222222222222",
    source_message_id: "33333333-3333-4333-8333-333333333333",
    extraction_status: "done",
    analysis_result_id: "44444444-4444-4444-8444-444444444444",
    note_ja: `fixture NOTE_JA ${offset + index}`,
    needs_review: index === 0,
    review_reasons: index === 0 ? "pid_unresolved,multi_candidate,note_unmatched" : null,
    raw_product_name: "fixture product",
    raw_quantity: "1",
    raw_price: "1000",
    raw_unit: "個",
    raw_state: null,
    raw_memo: null,
    analysis_status: "done",
    exclusion: null,
    quantity_normalized: "1",
    price_normalized: "1000",
    analysis_execution_state: "unrecorded",
    created_at: "2026-09-10T00:00:00Z",
  })),
});

const baseMocks = (isSuperAdmin: boolean): MockMap => ({
  "GET /me/permissions": { permissions: ["dashboard.view"], is_super_admin: isSuperAdmin },
  "GET /staff/me": {
    id: 1,
    primary_email: "review@salesanchor.jp",
    ui_preferences: { dark_mode: false, show_chat_menu: true, show_sales_menu: true, show_settings_menu: true, show_admin_menu: true, show_sidebar: true },
  },
  "GET /tcg/line-import/history": [{
    id: importId,
    filename: "fixture.txt",
    raw_sha256: "fixture",
    message_count: 50,
    provider_count: 1,
    unresolved_count: 0,
    uploaded_by: "review@salesanchor.jp",
    status: "imported",
    review_status: "ok",
    created_at: "2026-09-10T00:00:00Z",
  }],
  "GET /tcg/line-import/pending": [],
  "GET /tcg/distribution/targets": [],
  "GET /tcg/distribution/preview": {
    output_count: 1,
    note: "fixture",
    exclusion: { flag_series: 0, pid_unresolved_only: 0, unit_unresolved_only: 0, both_unresolved: 0, price_unresolved: 0 },
    flag_gate: { include_flag_single: false, gate_status: "ok", gate_message: "fixture", flag_single_count: null },
    settings: {},
  },
});

test.describe("TCG import workflow", () => {
  test("URL の選択を復元し、25件ページングで NOTE_JA を表示する", async ({ page }) => {
    await installAuthBypass(page);
    const itemRequests: string[] = [];
    await mockApi(page, {
      ...baseMocks(true),
      [`GET /tcg/line-import/${importId}/progress`]: progress,
      [`GET /tcg/line-import/${importId}/items`]: (route) => {
        const url = new URL(route.request().url());
        itemRequests.push(url.search);
        return route.fulfill({ contentType: "application/json", body: JSON.stringify(items(Number(url.searchParams.get("offset") ?? "0"))) });
      },
    });

    await page.goto(`/super-admin/tcg-line-import?import_job_id=${importId}`);
    await expect(page).toHaveURL(new RegExp(`import_job_id=${importId}`));
    await expect(page.getByText("fixture NOTE_JA 0")).toBeVisible();
    await expect(page.getByText("商品を特定できない, 商品候補が複数, メモの変換先が見つからない")).toBeVisible();
    await expect(page.locator(".pmg-workflow__table tbody tr")).toHaveCount(25);
    await expect(page.getByText("抽出終了")).toBeVisible();
    await expect(page.getByRole("button", { name: "要確認の明細を見る" })).toBeVisible();
    await page.screenshot({ path: "/tmp/reports/pmg-progress-visual/tcg-import-workflow-desktop-ja.png", fullPage: true });
    await page.screenshot({ path: "/tmp/reports/pmg-progress-visual/tcg-import-workflow-desktop-ja-viewport.png" });
    await page.locator(".pmg-workflow__table tbody tr").first().scrollIntoViewIfNeeded();
    await page.screenshot({ path: "/tmp/reports/pmg-progress-visual/desktop-table-ja.png" });
    await page.getByText("配信対象：現在の全体データ").scrollIntoViewIfNeeded();
    await expect(page.getByRole("button", { name: "全アクティブ配信先へ配信を実行" })).toBeVisible();
    await page.screenshot({ path: "/tmp/reports/pmg-progress-visual/desktop-distribution-ja.png" });
    await expect.poll(() => itemRequests).toContain("?limit=25&offset=0&filter=all");

    const nextPage = page.getByRole("button", { name: /次へ|Next/ });
    await nextPage.click();
    await expect.poll(() => itemRequests).toContain("?limit=25&offset=25&filter=all");
    await expect(page.locator(".pmg-workflow__table tbody tr")).toHaveCount(25);
    await expect(nextPage).toBeDisabled();
  });

  test("非管理者は進捗・明細・配信 API を要求しない", async ({ page }) => {
    await installAuthBypass(page);
    const newApiRequests: string[] = [];
    page.on("request", (request) => {
      const url = new URL(request.url());
      if (/\/tcg\/(line-import\/[^/]+\/(progress|items)|distribution\/)/.test(url.pathname)) {
        newApiRequests.push(`${request.method()} ${url.pathname}${url.search}`);
      }
    });
    await mockApi(page, baseMocks(false));

    await page.goto(`/super-admin/tcg-line-import?import_job_id=${importId}`);
    await expect(page.getByText(/中央 admin 権限|central admin permission/i)).toBeVisible();
    await expect.poll(() => newApiRequests).toEqual([]);
  });

  test("配信は選択取込 ID を送らず、確認前には POST しない", async ({ page }) => {
    await installAuthBypass(page);
    let distributionPosts = 0;
    await mockApi(page, {
      ...baseMocks(true),
      [`GET /tcg/line-import/${importId}/progress`]: progress,
      [`GET /tcg/line-import/${importId}/items`]: items(0),
      "GET /tcg/distribution/targets": [],
      "GET /tcg/distribution/preview": {
        output_count: 1,
        note: "fixture",
        exclusion: { flag_series: 0, pid_unresolved_only: 0, unit_unresolved_only: 0, both_unresolved: 0, price_unresolved: 0 },
        flag_gate: { include_flag_single: false, gate_status: "ok", gate_message: "fixture", flag_single_count: null },
        settings: {},
      },
      "POST /tcg/distribution/run": (route) => {
        distributionPosts += 1;
        const url = new URL(route.request().url());
        expect(url.searchParams.has("import_job_id")).toBe(false);
        expect(route.request().postDataJSON()).toEqual({});
        return route.fulfill({ contentType: "application/json", body: JSON.stringify({ started_at: "2026-09-10T00:00:00Z", output_count: 1, results: [], errors: [] }) });
      },
    });

    await page.goto(`/super-admin/tcg-line-import?import_job_id=${importId}`);
    const runAll = page.getByRole("button", { name: /全アクティブ配信先へ配信を実行|Run distribution to all active targets/ });
    await expect(runAll).toBeVisible();
    await expect.poll(() => distributionPosts).toBe(0);

    await runAll.click();
    await page.locator(".dist-dialog").getByRole("button", { name: /全件配信|Run All/ }).click();
    await expect.poll(() => distributionPosts).toBe(1);
  });

  test("配信 POST の失敗後に自動再送しない", async ({ page }) => {
    await installAuthBypass(page);
    let distributionPosts = 0;
    await mockApi(page, {
      ...baseMocks(true),
      [`GET /tcg/line-import/${importId}/progress`]: progress,
      [`GET /tcg/line-import/${importId}/items`]: items(0),
      "GET /tcg/distribution/targets": [],
      "GET /tcg/distribution/preview": {
        output_count: 1,
        note: "fixture",
        exclusion: { flag_series: 0, pid_unresolved_only: 0, unit_unresolved_only: 0, both_unresolved: 0, price_unresolved: 0 },
        flag_gate: { include_flag_single: false, gate_status: "ok", gate_message: "fixture", flag_single_count: null },
        settings: {},
      },
      "POST /tcg/distribution/run": (route) => {
        distributionPosts += 1;
        return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "fixture distribution failure" }) });
      },
    });

    await page.goto(`/super-admin/tcg-line-import?import_job_id=${importId}`);
    await page.getByRole("button", { name: /全アクティブ配信先へ配信を実行|Run distribution to all active targets/ }).click();
    await page.locator(".dist-dialog").getByRole("button", { name: /全件配信|Run All/ }).click();
    await expect.poll(() => distributionPosts).toBe(1);
    await expect(page.locator(".dist-preview-card")).toContainText(/エラー|Error/i);
    await page.waitForTimeout(5_000);
    expect(distributionPosts).toBe(1);
  });

  test("390px のダーク英語画面で横 overflow なく、全体配信と登録操作を使える", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.emulateMedia({ colorScheme: "dark" });
    await installAuthBypass(page);
    await mockApi(page, {
      ...baseMocks(true),
      "GET /staff/me": {
        id: 1,
        primary_email: "review@salesanchor.jp",
        locale: "en",
        theme: "dark",
        ui_preferences: { dark_mode: false, show_chat_menu: true, show_sales_menu: true, show_settings_menu: true, show_admin_menu: true, show_sidebar: true },
      },
      [`GET /tcg/line-import/${importId}/progress`]: progress,
      [`GET /tcg/line-import/${importId}/items`]: items(0),
      "GET /tcg/distribution/targets": [],
      "GET /tcg/distribution/preview": (route) => {
        expect(new URL(route.request().url()).searchParams.has("import_job_id")).toBe(false);
        return route.fulfill({ contentType: "application/json", body: JSON.stringify({
          output_count: 1,
          note: "fixture",
          exclusion: { flag_series: 0, pid_unresolved_only: 0, unit_unresolved_only: 0, both_unresolved: 0, price_unresolved: 0 },
          flag_gate: { include_flag_single: false, gate_status: "ok", gate_message: "fixture", flag_single_count: null },
          settings: {},
        }) });
      },
    });

    await page.goto(`/super-admin/tcg-line-import?import_job_id=${importId}`);
    await expect(page.locator("html")).toHaveClass(/force-dark/);
    await expect(page.getByText("Distribution scope: current global data")).toBeVisible();
    await expect(page.getByText(/Last fetched \(JST\)/)).toBeVisible();
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: "/tmp/reports/pmg-progress-visual/tcg-import-workflow-mobile-dark-en-overview-viewport.png" });
    const menuBackdrop = page.locator(".mobile-more-backdrop");
    if (await menuBackdrop.isVisible()) {
      await menuBackdrop.click({ position: { x: 1, y: 1 } });
      await expect(menuBackdrop).toHaveCount(0);
    }
    await page.locator(".pmg-workflow__table tbody tr").first().scrollIntoViewIfNeeded();
    await page.screenshot({ path: "/tmp/reports/pmg-progress-visual/mobile-table-en.png" });
    await page.screenshot({ path: "/tmp/reports/pmg-progress-visual/tcg-import-workflow-mobile-dark-en.png", fullPage: true });
    await page.screenshot({ path: "/tmp/reports/pmg-progress-visual/tcg-import-workflow-mobile-dark-en-viewport.png" });

    await page.getByRole("button", { name: "New Target" }).click();
    await expect(page.getByRole("heading", { name: "Register Target" })).toBeVisible();
  });

  test("未選択では取込フォームを開き、入力値を保ったまま開閉できる", async ({ page }) => {
    await installAuthBypass(page);
    await mockApi(page, baseMocks(true));

    await page.goto("/super-admin/tcg-line-import");
    const uploadDetails = page.locator("details").filter({ has: page.getByText("新しいファイルを取り込む") });
    await expect(uploadDetails).toHaveAttribute("open", "");
    const hours = uploadDetails.locator('input[type="number"]');
    await hours.fill("48");
    await uploadDetails.locator("summary").click();
    await expect(uploadDetails).not.toHaveAttribute("open", "");
    await uploadDetails.locator("summary").press("Enter");
    await expect(uploadDetails).toHaveAttribute("open", "");
    await expect(hours).toHaveValue("48");
  });

  test("選択済みでは概要を先に表示し、要確認導線が filter を初期offsetで選択する", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await installAuthBypass(page);
    const itemRequests: string[] = [];
    await mockApi(page, {
      ...baseMocks(true),
      [`GET /tcg/line-import/${importId}/progress`]: progress,
      [`GET /tcg/line-import/${importId}/items`]: (route) => {
        const url = new URL(route.request().url());
        itemRequests.push(url.search);
        return route.fulfill({ contentType: "application/json", body: JSON.stringify(items(Number(url.searchParams.get("offset") ?? "0"))) });
      },
    });

    await page.goto(`/super-admin/tcg-line-import?import_job_id=${importId}`);
    const uploadDetails = page.locator("details").filter({ has: page.getByText("新しいファイルを取り込む") });
    await expect(uploadDetails).not.toHaveAttribute("open", "");
    const reviewAction = page.getByRole("button", { name: "要確認の明細を見る" });
    await expect(reviewAction).toBeVisible();
    expect(await reviewAction.evaluate((element) => element.getBoundingClientRect().bottom <= window.innerHeight)).toBe(true);
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: "/tmp/reports/pmg-progress-visual/tcg-import-workflow-mobile-overview-ja-viewport.png" });
    await page.getByRole("button", { name: "新しいファイルを取り込む" }).click();
    await expect(uploadDetails).toHaveAttribute("open", "");
    await expect(uploadDetails.locator("summary")).toBeFocused();
    await reviewAction.click();
    await expect.poll(() => itemRequests).toContain("?limit=25&offset=0&filter=needs_review");
    await expect(page.getByLabel("絞り込み")).toHaveValue("needs_review");
  });

  test("info light と neutral dark の Badge は本文色で読める", async ({ page, browser }) => {
    await installAuthBypass(page);
    await mockApi(page, {
      ...baseMocks(true),
      [`GET /tcg/line-import/${importId}/progress`]: { ...progress, extraction: { ...progress.extraction, completed: 1, total: 3, succeeded: 1, empty: 0, pending: 1, running: 1 } },
      [`GET /tcg/line-import/${importId}/items`]: items(0),
    });
    await page.goto(`/super-admin/tcg-line-import?import_job_id=${importId}`);
    const readableColor = (selector: string) => page.locator(selector).evaluate((element) => {
      const reference = document.createElement("span");
      reference.style.color = "var(--text-primary)";
      document.body.append(reference);
      const color = getComputedStyle(element).color;
      const primary = getComputedStyle(reference).color;
      const values = (value: string) => value.match(/\d+(?:\.\d+)?/g)?.slice(0, 3).map(Number) ?? [];
      const luminance = (rgb: number[]) => rgb.map((value) => {
        const normalized = value / 255;
        return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
      }).reduce((total, value, index) => total + value * [0.2126, 0.7152, 0.0722][index], 0);
      const background = getComputedStyle(element).backgroundColor;
      const ratio = (first: number, second: number) => (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
      return { color, primary, contrast: ratio(luminance(values(color)), luminance(values(background))) };
    });
    const infoColors = await readableColor(".pmg-workflow__badge-readable.comp-badge--info");
    expect(infoColors.color).toBe(infoColors.primary);
    expect(infoColors.contrast).toBeGreaterThanOrEqual(4.5);

    const darkContext = await browser.newContext({ colorScheme: "dark", viewport: { width: 390, height: 844 } });
    const darkPage = await darkContext.newPage();
    await installAuthBypass(darkPage);
    await mockApi(darkPage, {
      ...baseMocks(true),
      "GET /staff/me": {
        id: 1,
        primary_email: "review@salesanchor.jp",
        locale: "en",
        theme: "dark",
        ui_preferences: { dark_mode: false, show_chat_menu: true, show_sales_menu: true, show_settings_menu: true, show_admin_menu: true, show_sidebar: true },
      },
      [`GET /tcg/line-import/${importId}/progress`]: { ...progress, coverage: "legacy_unknown" },
      [`GET /tcg/line-import/${importId}/items`]: items(0),
    });
    await darkPage.goto(`/super-admin/tcg-line-import?import_job_id=${importId}`);
    await expect(darkPage.locator("html")).toHaveClass(/force-dark/);
    const neutralColors = await darkPage.locator(".pmg-workflow__badge-readable.comp-badge--neutral").evaluate((element) => {
      const reference = document.createElement("span");
      reference.style.color = "var(--text-primary)";
      document.body.append(reference);
      return { color: getComputedStyle(element).color, primary: getComputedStyle(reference).color };
    });
    expect(neutralColors.color).toBe(neutralColors.primary);
    await darkContext.close();
  });
});
