/**
 * 本番の受入（ADR-1055 段C・C5）: K7 の待つ側。書き込みを伴う。
 *
 * 点検の人（印の無い文脈）で依頼を1件作り、PO が管理画面「ログインの許可待ち」で許可するのを待つ。
 * 入れたら管理者の口が 403 であることを確かめ、自分の機械を取り消して終わる。
 * 値（番号・トークン）はログに出さない（カード D-C5）。流すのは device-accept.config.ts（手動の workflow のみ）。
 */

import * as fs from "node:fs";
import { expect, test, type APIRequestContext, type APIResponse } from "@playwright/test";
import { authPace, BASE_URL, creds } from "./login";

const API = `${BASE_URL}/api/v1`;
const POLL_EVERY_MS = 30_000;
const WAIT_MAX_MS = 25 * 60_000;

const FIXED_FAIL = "操作に失敗しました（値は出しません）";

type Res = { status: number; body: Record<string, unknown> };

async function call(
  request: APIRequestContext,
  method: "GET" | "POST" | "DELETE",
  route: string,
  opts: { token?: string; data?: unknown } = {},
): Promise<Res> {
  if (route.startsWith("/auth/")) await authPace();
  const headers: Record<string, string> = { Origin: BASE_URL };
  if (opts.token) headers.Authorization = `Bearer ${opts.token}`;
  let res: APIResponse;
  try {
    res = await request.fetch(`${API}${route}`, { method, headers, data: opts.data, failOnStatusCode: false });
  } catch {
    throw new Error(FIXED_FAIL);
  }
  let body: Record<string, unknown> = {};
  try {
    const parsed: unknown = await res.json();
    if (parsed && typeof parsed === "object") body = parsed as Record<string, unknown>;
  } catch {
    body = {};
  }
  return { status: res.status(), body };
}

test("K7: 管理者の許可で入り、403 を確かめ、自分の機械を取り消す", async ({ browser }) => {
  test.setTimeout(28 * 60_000);
  const c = creds();
  test.skip(!c, "SMOKE_E2E_EMAIL / SMOKE_E2E_PASSWORD が未設定");
  const email = c?.email ?? "";
  const password = c?.password ?? "";

  if (process.env.GITHUB_STEP_SUMMARY) {
    fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, `K7 の開始時刻（UTC）: ${new Date().toISOString()}\n`);
  }

  // 印の無い文脈（Cookie を持たない）
  const ctx = await browser.newContext();
  let token = "";
  try {
    const first = await call(ctx.request, "POST", "/auth/login", { data: { email, password } });
    expect(first.status).toBe(202);

    // PO が許可するまで30秒ごとに poll（最大25分）
    const until = Date.now() + WAIT_MAX_MS;
    let state = "pending";
    while (Date.now() < until) {
      const poll = await call(ctx.request, "POST", "/auth/login-requests/poll");
      expect(poll.status).toBe(200);
      state = typeof poll.body.status === "string" ? poll.body.status : "pending";
      if (state === "completed" && typeof poll.body.access_token === "string") {
        token = poll.body.access_token;
        break;
      }
      if (state !== "pending") break;
      await new Promise((resolve) => setTimeout(resolve, POLL_EVERY_MS));
    }
    expect(state === "completed").toBe(true);
    expect(token.length > 0).toBe(true);

    // 点検の人は super admin でないので、管理者の口は 403
    const admin = await call(ctx.request, "GET", "/super-admin/login-requests", { token });
    expect(admin.status).toBe(403);
  } finally {
    // 自分の機械を取り消す（入れていなければ何もしない）
    if (token) {
      try {
        const list = await call(ctx.request, "GET", "/auth/devices", { token });
        const rows = Array.isArray(list.body.items) ? (list.body.items as { id: number; is_current: boolean }[]) : [];
        const mine = rows.find((r) => r.is_current);
        if (mine) await call(ctx.request, "DELETE", `/auth/devices/${mine.id}`, { token });
      } catch {
        // 取り消せなかったときは §8 の手で消す
      }
    }
    await ctx.close();
  }
});
