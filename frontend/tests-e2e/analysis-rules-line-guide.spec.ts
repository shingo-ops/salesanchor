import { mkdirSync } from "node:fs";
import type { Page } from "@playwright/test";
import { expect, test } from "@playwright/test";
import { installAuthBypass } from "./utils/auth";
import { mockApi } from "./utils/api-mock";

// CARD07 observed 24–25s cold gotos with four concurrent cases; avoid simultaneous cold loads in this spec.
test.describe.configure({ mode: "default" });

const REPORT_DIR = "/tmp/reports/card-line-guide-01";

type Configuration = {
  width: 390 | 1440;
  locale: "ja" | "en";
  theme: "light" | "dark";
};

const configurations: Configuration[] = [
  { width: 1440, locale: "ja", theme: "light" },
  { width: 1440, locale: "en", theme: "dark" },
  { width: 390, locale: "ja", theme: "light" },
  { width: 390, locale: "en", theme: "dark" },
];

async function prepare(page: Page, configuration: Configuration) {
  await page.setViewportSize({ width: configuration.width, height: 900 });
  await installAuthBypass(page);
  await mockApi(page, {
    "GET /me/permissions": { permissions: ["dashboard.view"], is_super_admin: true },
    "GET /staff/me": {
      id: 1,
      primary_email: "review@salesanchor.jp",
      locale: configuration.locale,
      theme: configuration.theme,
      ui_preferences: {
        dark_mode: configuration.theme === "dark",
        show_chat_menu: true,
        show_sales_menu: true,
        show_settings_menu: true,
        show_admin_menu: true,
        show_sidebar: true,
      },
    },
    "GET /super-admin/suppliers": [],
    "GET /tcg/line-import/history": [],
    "GET /tcg/line-import/pending": [],
    "GET /tcg/distribution/targets": [],
    "GET /tcg/distribution/preview": {
      output_count: 0,
      exclusion: {},
      flag_gate: {},
      settings: {},
    },
  });
}

async function captureMobileViewportEvidence(page: Page, configuration: Configuration) {
  if (configuration.width !== 390) return;

  const suffix = `${configuration.locale}-${configuration.theme}`;
  const guideHeading = page.getByRole("heading", {
    name: configuration.locale === "ja" ? "LINE解析の業務手順" : "LINE analysis workflow guide",
  });
  await guideHeading.scrollIntoViewIfNeeded();
  await expect(guideHeading).toBeInViewport();
  await page.screenshot({
    path: `${REPORT_DIR}/guide-390-${suffix}-viewport-start.png`,
    fullPage: false,
  });

  const checks = [
    {
      step: 1,
      action: configuration.locale === "ja" ? "取込画面を開く" : "Open import",
    },
    {
      step: 7,
      action: configuration.locale === "ja" ? "配信画面を開く" : "Open distribution",
    },
  ] as const;

  for (const check of checks) {
    const heading = page.locator(`#line-workflow-step-${check.step}`);
    const card = page.getByTestId("line-workflow-step").filter({ has: heading });
    const action = card.getByRole("button", { name: check.action });
    await card.scrollIntoViewIfNeeded();
    await expect(heading).toBeInViewport();
    await expect(action).toBeInViewport();
    await action.click({ trial: true });
    await page.screenshot({
      path: `${REPORT_DIR}/guide-390-${suffix}-viewport-step${check.step}.png`,
      fullPage: false,
    });
  }
}

for (const configuration of configurations) {
  test(`system menu opens the guide without business writes: ${configuration.width} ${configuration.locale} ${configuration.theme}`, async ({ page }) => {
    const businessWrites: string[] = [];
    page.on("request", (request) => {
      if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) {
        businessWrites.push(`${request.method()} ${new URL(request.url()).pathname}`);
      }
    });
    await prepare(page, configuration);

    await page.goto("/super-admin/analysis-rules");
    const guideMenu = page.getByTestId("analysis-subnav-line-workflow-guide");
    await guideMenu.focus();
    await expect(guideMenu).toBeFocused();
    await page.keyboard.press("Enter");

    await expect(page).toHaveURL(/\/super-admin\/analysis-rules\?section=line-workflow-guide$/);
    await expect(page.getByTestId("analysis-subnav-line-workflow-guide")).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByRole("heading", {
      name: configuration.locale === "ja" ? "LINE解析の業務手順" : "LINE analysis workflow guide",
    })).toBeVisible();
    await expect(page.getByTestId("line-workflow-step")).toHaveCount(7);
    await expect(page.locator("html")).toHaveClass(configuration.theme === "dark" ? /force-dark/ : /^(?!.*force-dark)/);
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    expect(businessWrites).toEqual([]);

    mkdirSync(REPORT_DIR, { recursive: true });
    await captureMobileViewportEvidence(page, configuration);
    await page.screenshot({
      path: `${REPORT_DIR}/guide-${configuration.width}-${configuration.locale}-${configuration.theme}.png`,
      fullPage: true,
    });
  });
}

test("guide actions keep hub query navigation and use existing external paths", async ({ page }) => {
  await prepare(page, { width: 1440, locale: "ja", theme: "light" });
  await page.goto("/super-admin/analysis-rules?section=line-workflow-guide");

  const supplierStep = page.getByTestId("line-workflow-step").filter({
    has: page.locator("#line-workflow-step-2"),
  });
  const supplierButton = supplierStep.getByRole("button", { name: "仕入元マスタを開く" });
  await supplierButton.focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/super-admin\/analysis-rules\?section=supplier-master$/);
  await expect(page.getByRole("heading", { name: "LINE解析の業務手順" })).toHaveCount(0);
  await expect(page.getByTestId("suppliers-search")).toBeVisible();

  await page.getByTestId("analysis-subnav-line-workflow-guide").click();
  await page.getByRole("button", { name: "取込画面を開く" }).first().click();
  await expect(page).toHaveURL(/\/super-admin\/tcg-line-import$/);
  await expect(page.getByRole("heading", { name: "LINE解析の業務手順" })).toHaveCount(0);
  await expect(page.getByText(".txt ファイルをドロップ、またはクリックして選択")).toBeVisible();

  await page.goto("/super-admin/analysis-rules?section=line-workflow-guide");
  await page.getByRole("button", { name: "配信画面を開く" }).click();
  await expect(page).toHaveURL(/\/super-admin\/tcg-distribution$/);
  await expect(page.getByRole("heading", { name: "LINE解析の業務手順" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "配信先管理" })).toBeVisible();
});

test("table of contents keyboard link targets the matching section id", async ({ page }) => {
  await prepare(page, { width: 390, locale: "en", theme: "dark" });
  await page.goto("/super-admin/analysis-rules?section=line-workflow-guide");

  const finalStepLink = page.getByRole("link", { name: "Review and run distribution" });
  await finalStepLink.focus();
  await expect(finalStepLink).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#line-workflow-step-7$/);
  await expect(page.locator("#line-workflow-step-7")).toBeFocused();
  await expect(page.locator("#line-workflow-step-7")).toBeInViewport();
});
