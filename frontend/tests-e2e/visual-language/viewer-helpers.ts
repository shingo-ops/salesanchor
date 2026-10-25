/**
 * visual-language/viewer-helpers.ts — 閲覧ページ（/viewer/）のスマホ絞り込み検査で使う mock と開き方
 *
 * mock の中身を複数の spec に分けて書くと片方だけ古くなるため、ここを唯一の置き場にする
 * （frontend/tests-e2e/visual-language/inventory-helpers.ts の書き方に倣う）。
 * このファイルは `.spec.ts` ではないので Playwright のテスト収集対象にはならない。
 *
 * 認証: 閲覧ページはアプリ本体の Firebase Auth（installAuthBypass）を使わない
 * （frontend/src/pages/viewer/main.tsx がアプリ本体の CSS・辞書を読まないのと同じ理由）。
 * localStorage の `viewer_access_token`（キー名は frontend/src/pages/viewer/api.ts:7）を
 * addInitScript で入れるだけで、frontend/src/pages/viewer/ViewerApp.tsx:60 が
 * 「トークンが有れば loading → 在庫取得」に分岐する。
 *
 * API mock のキーは "GET /viewer/inventory"（frontend/src/pages/viewer/api.ts:8 の
 * `/api/v1/viewer/inventory` から frontend/tests-e2e/utils/api-mock.ts が `/api/v1` を外した形）。
 */

import { expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import { mockApi } from "../utils/api-mock";
import type { ViewerInventoryResponse, ViewerRow } from "../../src/pages/viewer/types";

/** frontend/src/pages/viewer/api.ts:7 の TOKEN_KEY と同じ値 */
const TOKEN_KEY = "viewer_access_token";
const DUMMY_TOKEN = "e2e-viewer-dummy-token";

/** 仕入元の名前を n 件作る（value と label は同じ文字列。InventoryView.tsx の distinctValues().map(v=>({value:v,label:v})) に合わせる） */
export function makeProviderNames(n: number): string[] {
  return Array.from({ length: n }, (_, i) => `Provider${String(i + 1).padStart(2, "0")}`);
}

/** コンディションの種類を n 件作る（DB 由来の値。画面文言ではない） */
export function makeConditionValues(n: number): string[] {
  const all = ["sealed", "used", "damaged", "opened"];
  return all.slice(0, Math.max(2, Math.min(n, all.length)));
}

/** 現在時刻を posted_at の形（タイムゾーン無しの日本時間 'YYYY-MM-DD HH:MM:SS'）にする */
function jstNow(): string {
  return new Date(Date.now() + 9 * 3600 * 1000).toISOString().slice(0, 19).replace("T", " ");
}

/**
 * 在庫の行データを n 件作る。仕入元とコンディションを順番に割り当てて全件に行き渡らせる
 * （design.md 4-5: 仕入元20件以上・コンディション2種類以上・行50件以上が空振りしないための形）。
 * posted_at は常に「今」にする（InventoryView の freshOnly 既定 true で落ちないように）。
 */
export function makeViewerRows(n: number, providers: string[], conditions: string[]): ViewerRow[] {
  return Array.from({ length: n }, (_, i) => ({
    posted_at: jstNow(),
    mark: `M${i + 1}`,
    japanese_title: `商品 ${i + 1}`,
    english_title: `item-${String(i + 1).padStart(3, "0")}`,
    condition: conditions[i % conditions.length],
    unit_price: String(1000 + i * 10),
    quantity: String(1 + (i % 5)),
    note_ja: "",
    status: "In Stock",
    release_date: "",
    series: "",
    provider: providers[i % providers.length],
    search_keywords: "",
    ship_ja: "",
    offer_type: "in_stock" as const,
  }));
}

export interface ViewerFixtureOptions {
  providerCount?: number;
  conditionCount?: number;
  rowCount?: number;
}

export interface ViewerFixture {
  providers: string[];
  conditions: string[];
  response: ViewerInventoryResponse;
}

/** 仕入元20件以上・コンディション2種類以上・行50件以上の fixture を作る（既定値も基準を満たす） */
export function makeViewerFixture(opts?: ViewerFixtureOptions): ViewerFixture {
  const providers = makeProviderNames(opts?.providerCount ?? 25);
  const conditions = makeConditionValues(opts?.conditionCount ?? 2);
  const rows = makeViewerRows(opts?.rowCount ?? 60, providers, conditions);
  return {
    providers,
    conditions,
    response: {
      updated_at: new Date().toISOString(),
      fresh_window_hours: 24,
      rows,
    },
  };
}

/** トークンだけ先に入れる（ページ遷移前に addInitScript で呼ぶ） */
async function installViewerToken(page: Page): Promise<void> {
  await page.addInitScript(
    ({ key, token }) => {
      try {
        window.localStorage.setItem(key, token);
      } catch {
        /* noop */
      }
    },
    { key: TOKEN_KEY, token: DUMMY_TOKEN },
  );
}

/** 認証トークンと在庫 API mock だけ入れる（viewport設定・ページ遷移はしない） */
export async function installViewerMocks(page: Page, fixture: ViewerFixture): Promise<void> {
  await installViewerToken(page);
  await mockApi(page, {
    "GET /viewer/inventory": fixture.response,
  });
}

/** 閲覧ページを開き、viewport設定→mock→遷移→表が見えるまで待つ、をまとめて行う */
export async function gotoViewer(
  page: Page,
  opts?: { width?: number; height?: number; fixtureOpts?: ViewerFixtureOptions },
): Promise<ViewerFixture> {
  const width = opts?.width ?? 390;
  const height = opts?.height ?? 844;
  const fixture = makeViewerFixture(opts?.fixtureOpts);
  await page.setViewportSize({ width, height });
  await installViewerMocks(page, fixture);
  await page.goto("/viewer/");
  await expect(page.getByTestId("viewer-filter-toggle").or(page.getByTestId("viewer-provider-filter-button"))).toBeVisible();
  return fixture;
}
