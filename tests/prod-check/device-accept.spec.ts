/**
 * 本番の受入（ADR-1055 段C・C1）: 新しい機械の許可の流れを1本で試す。書き込みを伴う。
 *
 * 毎朝の点検には混ぜない（playwright.config.ts の testIgnore）。流すのは
 * device-accept.config.ts と .github/workflows/prod-device-accept.yml（手動のみ）。
 * 公開リポジトリなので、合言葉・番号・トークンはログに出さない（カード D-C5）:
 *   変数に持つだけ・console を使わない・test.step の題と expect に値を入れない・
 *   値を使う操作は try/catch で値を含まない決まった文に投げ直す。
 * 呼び出しの間隔は /api/v1/auth/ 向けに authPace() で8秒あける（カード D-C3）。
 */

import * as fs from "node:fs";
import * as path from "node:path";
import { expect, test, type APIRequestContext, type BrowserContext, type Page } from "@playwright/test";
import { authPace, BASE_URL, creds, login } from "./login";

const API = `${BASE_URL}/api/v1`;

type Res = { status: number; body: Record<string, unknown> };

/** 画面を使う文脈の準備（login.ts の init script と route と同じ） */
async function prepareScreenContext(context: BrowserContext): Promise<void> {
  await context.addInitScript(() => {
    Object.defineProperty(globalThis, "PublicKeyCredential", { value: undefined, configurable: true });
  });
  await context.route("**/api/v1/auth/recovery-codes/status", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ remaining: 10 }) }),
  );
}

/** API を1回呼ぶ。/api/v1/auth/ 向けは先に authPace()。Origin を付ける。応答本文は返すだけで出さない */
async function call(
  request: APIRequestContext,
  method: "GET" | "POST" | "DELETE",
  route: string,
  opts: { token?: string; data?: unknown } = {},
): Promise<Res> {
  if (route.startsWith("/auth/")) await authPace();
  const headers: Record<string, string> = { Origin: BASE_URL };
  if (opts.token) headers.Authorization = `Bearer ${opts.token}`;
  const res = await request.fetch(`${API}${route}`, {
    method,
    headers,
    data: opts.data,
    failOnStatusCode: false,
  });
  let body: Record<string, unknown> = {};
  try {
    const parsed: unknown = await res.json();
    if (parsed && typeof parsed === "object") body = parsed as Record<string, unknown>;
  } catch {
    body = {};
  }
  return { status: res.status(), body };
}

function tokenOf(res: Res): string {
  const t = res.body.access_token;
  return typeof t === "string" ? t : "";
}

type DeviceRow = { id: number; is_current: boolean; created_at?: unknown; label?: unknown; location?: unknown };

function devicesOf(res: Res): DeviceRow[] {
  const items = res.body.items;
  return Array.isArray(items) ? (items as DeviceRow[]) : [];
}

function idSet(rows: DeviceRow[]): string {
  return rows
    .map((r) => r.id)
    .sort((a, b) => a - b)
    .join(",");
}

/** ja.json の待ち画面の文言（K1 は文言の一致の真偽だけで見る・画面の写しは作らない） */
function waitingTitle(): string {
  const file = path.join(process.cwd(), "frontend/src/locales/ja.json");
  const ja = JSON.parse(fs.readFileSync(file, "utf-8")) as {
    login: { deviceApproval: { title: string; watcher: { title: string } } };
  };
  return ja.login.deviceApproval.title;
}
function watcherTitle(): string {
  const file = path.join(process.cwd(), "frontend/src/locales/ja.json");
  const ja = JSON.parse(fs.readFileSync(file, "utf-8")) as {
    login: { deviceApproval: { watcher: { title: string } } };
  };
  return ja.login.deviceApproval.watcher.title;
}

const FIXED_FAIL = "操作に失敗しました（値は出しません）";

test.describe.serial("本番の受入: 新しい機械の許可（ADR-1055 段C）", () => {
  test.setTimeout(10 * 60_000);

  const c = creds();
  const email = c?.email ?? "";
  const password = c?.password ?? "";

  let tPage: Page | null = null;
  let tCtx: BrowserContext;
  let nCtx: BrowserContext;
  let bCtx: BrowserContext;
  let cCtx: BrowserContext;
  let dCtx: BrowserContext;
  let eCtx: BrowserContext;

  let tToken = "";
  let initialSet = "";
  let matchNumber = "";
  let nToken = "";
  let nDeviceId = -1;
  let n202At = 0;
  let dDeviceId = -1;
  let dToken = "";
  let recoveryCode = "";
  let started = false;

  test.beforeAll(async ({ browser }) => {
    test.skip(!c, "SMOKE_E2E_EMAIL / SMOKE_E2E_PASSWORD が未設定");
    const start = new Date().toISOString();
    if (process.env.GITHUB_STEP_SUMMARY) {
      fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, `受入の開始時刻（UTC）: ${start}\n`);
    }
    started = true;
    tCtx = await browser.newContext();
    nCtx = await browser.newContext();
    bCtx = await browser.newContext();
    cCtx = await browser.newContext();
    dCtx = await browser.newContext();
    eCtx = await browser.newContext();
    // B だけは T と同じ印の Cookie を付ける
    const deviceToken = process.env.SMOKE_E2E_DEVICE_TOKEN;
    if (deviceToken) {
      await bCtx.addCookies([
        {
          name: "sa_device",
          value: deviceToken,
          domain: new URL(BASE_URL).hostname,
          path: "/api/v1/auth",
          secure: true,
          httpOnly: true,
          sameSite: "Strict",
        },
      ]);
    }
  });

  test("段1 K5: いつもの機械は聞かれない", async () => {
    tPage = await tCtx.newPage();
    let loginStatus = 0;
    let tokenRead: Promise<void> = Promise.resolve();
    tPage.on("response", (r) => {
      if (r.url().endsWith("/api/v1/auth/login") && r.request().method() === "POST") {
        loginStatus = r.status();
        tokenRead = (async () => {
          try {
            const j = (await r.json()) as Record<string, unknown>;
            tToken = typeof j.access_token === "string" ? j.access_token : "";
          } catch {
            tToken = "";
          }
        })();
      }
    });
    try {
      await authPace();
      await login(tPage, email, password);
    } catch {
      throw new Error(FIXED_FAIL);
    }
    expect(loginStatus).toBe(200);
    // T の API 用のトークンは login の応答から受ける（カード D-C6）
    await tokenRead;
    expect(tToken.length > 0).toBe(true);
    const list = await call(tCtx.request, "GET", "/auth/devices", { token: tToken });
    expect(list.status).toBe(200);
    initialSet = idSet(devicesOf(list));
    expect(initialSet.length > 0).toBe(true);
  });

  test("段2 K1: 新しい機械は許可待ちになる", async () => {
    await prepareScreenContext(nCtx);
    const page = await nCtx.newPage();
    let status = 0;
    let match = "";
    let hasToken = true;
    page.on("response", async (r) => {
      if (r.url().endsWith("/api/v1/auth/login") && r.request().method() === "POST") {
        status = r.status();
        if (status === 202) n202At = Date.now();
        try {
          const j = (await r.json()) as Record<string, unknown>;
          match = typeof j.match_number === "string" ? j.match_number : String(j.match_number ?? "");
          hasToken = typeof j.access_token === "string" && j.access_token.length > 0;
        } catch {
          match = "";
        }
      }
    });
    try {
      await authPace();
      await page.goto("/login");
      await page.getByLabel("メールアドレス").fill(email);
      await page.getByLabel("パスワード", { exact: true }).fill(password);
      await authPace();
      await page.getByRole("button", { name: "ログイン", exact: true }).click();
      await page.getByText(waitingTitle(), { exact: true }).waitFor({ timeout: 30_000 });
    } catch {
      throw new Error(FIXED_FAIL);
    }
    const sawTitle = await page.getByText(waitingTitle(), { exact: true }).isVisible();
    // 15秒ごとの確認が走る前に画面を閉じる（文脈は残す）
    await page.close();
    expect(status).toBe(202);
    matchNumber = match;
    expect(matchNumber.length > 0).toBe(true);
    expect(hasToken).toBe(false);
    expect(sawTitle).toBe(true);
    const cookies = await nCtx.cookies();
    expect(cookies.some((k) => k.name === "sa_login_pending")).toBe(true);
  });

  test("段3 K2（画面）: 許可の小窓が60秒以内に出る", async () => {
    const page = tPage;
    expect(page).not.toBeNull();
    const t0 = n202At > 0 ? n202At : Date.now();
    try {
      await page!.getByText(watcherTitle(), { exact: true }).waitFor({ timeout: 60_000 });
    } catch {
      throw new Error(FIXED_FAIL);
    }
    expect(Date.now() - t0 <= 60_000).toBe(true);
    const dialog = page!.getByRole("dialog");
    const fields = await dialog.locator("dd").allTextContents();
    expect(fields.length).toBe(3);
    expect(fields.every((f) => f.trim().length > 0)).toBe(true);
  });

  test("段4 K3: 番号を選ぶと新しい機械が入れる", async () => {
    const page = tPage!;
    try {
      await authPace();
      await page.getByRole("dialog").getByRole("button", { name: matchNumber, exact: true }).click();
      await page.getByText(watcherTitle(), { exact: true }).waitFor({ state: "hidden", timeout: 30_000 });
    } catch {
      throw new Error(FIXED_FAIL);
    }
    const poll = await call(nCtx.request, "POST", "/auth/login-requests/poll");
    expect(poll.status).toBe(200);
    nToken = tokenOf(poll);
    expect(nToken.length > 0).toBe(true);
  });

  test("段5 K5: 許可した機械は次から聞かれない", async () => {
    const out = await call(nCtx.request, "POST", "/auth/logout", { token: nToken });
    expect(out.status).toBe(200);
    const again = await call(nCtx.request, "POST", "/auth/login", { data: { email, password } });
    expect(again.status).toBe(200);
    nToken = tokenOf(again);
    expect(nToken.length > 0).toBe(true);
  });

  test("段6 K8: 一覧に新しい機械が出る", async () => {
    const t = await call(tCtx.request, "GET", "/auth/devices", { token: tToken });
    const n = await call(nCtx.request, "GET", "/auth/devices", { token: nToken });
    expect(t.status).toBe(200);
    expect(n.status).toBe(200);
    const mine = devicesOf(n).find((r) => r.is_current);
    expect(mine === undefined).toBe(false);
    nDeviceId = mine ? mine.id : -1;
    const tRows = devicesOf(t);
    const row = tRows.find((r) => r.id === nDeviceId);
    expect(row === undefined).toBe(false);
    expect(row !== undefined && "created_at" in row && "label" in row && "location" in row).toBe(true);
  });

  test("段7 K8: 取り消すと締め出される", async () => {
    const del = await call(tCtx.request, "DELETE", `/auth/devices/${nDeviceId}`, { token: tToken });
    expect(del.status).toBe(204);
    const pending = await call(nCtx.request, "GET", "/login-approvals/pending", { token: nToken });
    expect(pending.status).toBe(401);
    nDeviceId = -1;
  });

  test("段8 K4: 私ではない、で拒否される", async () => {
    const b = await call(bCtx.request, "POST", "/auth/login", { data: { email, password } });
    expect(b.status).toBe(200);
    const bToken = tokenOf(b);
    expect(bToken.length > 0).toBe(true);
    const cLogin = await call(cCtx.request, "POST", "/auth/login", { data: { email, password } });
    expect(cLogin.status).toBe(202);
    const page = tPage!;
    try {
      await page.getByText(watcherTitle(), { exact: true }).waitFor({ timeout: 60_000 });
      await authPace();
      await page.getByRole("button", { name: "私ではない", exact: true }).click();
      await page.getByText(watcherTitle(), { exact: true }).waitFor({ state: "hidden", timeout: 30_000 });
    } catch {
      throw new Error(FIXED_FAIL);
    }
    const poll = await call(cCtx.request, "POST", "/auth/login-requests/poll");
    expect(poll.status).toBe(200);
    expect(poll.body.status === "rejected").toBe(true);
    const bPending = await call(bCtx.request, "GET", "/login-approvals/pending", { token: bToken });
    expect(bPending.status).toBe(401);
    const tPending = await call(tCtx.request, "GET", "/login-approvals/pending", { token: tToken });
    expect(tPending.status).toBe(200);
  });

  test("段9 K6: 予備の合言葉を作り直す", async () => {
    const made = await call(tCtx.request, "POST", "/auth/recovery-codes", { token: tToken });
    expect(made.status).toBe(200);
    const codes = made.body.codes;
    expect(Array.isArray(codes) && codes.length === 10).toBe(true);
    recoveryCode = Array.isArray(codes) && typeof codes[0] === "string" ? codes[0] : "";
    expect(recoveryCode.length > 0).toBe(true);
  });

  test("段10 K6: 合言葉1個で入れる", async () => {
    const d = await call(dCtx.request, "POST", "/auth/login", { data: { email, password } });
    expect(d.status).toBe(202);
    let res: Res;
    try {
      res = await call(dCtx.request, "POST", "/auth/login-requests/recovery", { data: { code: recoveryCode } });
    } catch {
      throw new Error(FIXED_FAIL);
    }
    expect(res.status).toBe(200);
    dToken = tokenOf(res);
    expect(dToken.length > 0).toBe(true);
  });

  test("段11 K6: 同じ合言葉は2回目は使えない", async () => {
    const e = await call(eCtx.request, "POST", "/auth/login", { data: { email, password } });
    expect(e.status).toBe(202);
    let res: Res;
    try {
      res = await call(eCtx.request, "POST", "/auth/login-requests/recovery", { data: { code: recoveryCode } });
    } catch {
      throw new Error(FIXED_FAIL);
    }
    expect(res.status).toBe(400);
    expect(res.body.detail === "recovery_code_wrong").toBe(true);
  });

  test.afterAll(async () => {
    test.setTimeout(3 * 60_000);
    if (!started) return;
    const errors: string[] = [];
    // 最初に T の画面を閉じる（画面が裏で refresh するのを止める）
    try {
      if (tPage) await tPage.close();
    } catch {
      errors.push("画面を閉じられなかった");
    }
    try {
      // 段1 のトークンは900秒で切れるので取り直す
      const refreshed = await call(tCtx.request, "POST", "/auth/refresh");
      if (refreshed.status === 200 && tokenOf(refreshed)) tToken = tokenOf(refreshed);
      // D の機械を取り消す
      if (dToken) {
        const dList = await call(dCtx.request, "GET", "/auth/devices", { token: dToken });
        const dMine = devicesOf(dList).find((r) => r.is_current);
        if (dMine) dDeviceId = dMine.id;
      }
      if (dDeviceId >= 0) {
        await call(tCtx.request, "DELETE", `/auth/devices/${dDeviceId}`, { token: tToken });
      }
      // 段7 で取り消せなかった N の機械が残っていれば取り消す（取り消し済みなら -1）
      if (nDeviceId >= 0) {
        await call(tCtx.request, "DELETE", `/auth/devices/${nDeviceId}`, { token: tToken });
      }
      // 残った pending（E など）は T から reject で閉じる
      const pending = await call(tCtx.request, "GET", "/login-approvals/pending", { token: tToken });
      const items = Array.isArray(pending.body.items) ? (pending.body.items as { id: string }[]) : [];
      for (const it of items) {
        await call(tCtx.request, "POST", `/auth/login-requests/${it.id}/reject`, { token: tToken, data: {} });
      }
      // 最後に始めの集まりと比べる（B-0 の印が入っていること）
      const list = await call(tCtx.request, "GET", "/auth/devices", { token: tToken });
      if (initialSet.length > 0 && idSet(devicesOf(list)) !== initialSet) {
        errors.push("機械の集まりが始めと違う");
      }
    } catch {
      errors.push("後片付けに失敗した");
    }
    for (const ctx of [tCtx, nCtx, bCtx, cCtx, dCtx, eCtx]) {
      try {
        await ctx?.close();
      } catch {
        // 閉じられなくても続ける
      }
    }
    if (errors.length > 0) throw new Error(`後片付け: ${errors.join(" / ")}`);
  });
});
