/**
 * 本番の全画面の速さを毎日記録する（ADR-1053。判定なし・知らせなし）
 *
 * 点検用の人で 1 回ログインし、表の画面をアプリの中の画面切り替え（読み込み直しなし）で 1 つずつ開いて、
 * 開き終わるまでの秒を測る。結果は遅い順の表にして tests/prod-check/page-speed.md に書く（ワークフローが要約に足す）。
 * 実行記録は公開されるので、表には画面の道すじの形・秒・数だけを出す。画面の文字・応答の中身・番号は出さない。
 * 本番に書き込まないよう、読み取りとログイン以外の送信はブラウザの中で止める（設計 5-5）。
 */

import { test, type Page, type Request } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { BASE_URL, authPace, creds, login } from "./login";
import { isTrackedApi, trackApi, waitSettled, type ApiTracker } from "./settle";
import { SPEED_TARGETS, type SpeedTarget } from "./page-speed-targets";

/** 1 画面の待ちの上限 */
const CAP_MS = 45_000;
/** 段の全体の上限。超えたら残りは測らずに表を出す */
const STAGE_LIMIT_MS = 40 * 60 * 1000;
/** ワークフローはリポジトリの根から動かす */
const OUT_FILE = "tests/prod-check/page-speed.md";

type Status = "測れた" | "時間切れ" | "番号を拾えず" | "別の画面へ移った" | "エラー" | "時間切れで未測定";
type Row = {
  route: string;
  seconds: number | null;
  status: Status;
  api: number;
  forbidden: number;
  serverError: number;
  slowest: string;
  slowestSeconds: number | null;
};
type ApiHit = { shape: string; ms: number; status: number };

/** 番号らしい区切りを :id にする（数字だけ・UUID・16 文字以上の英数字・3 桁以上の数字を含む） */
function pathShape(pathname: string): string {
  return pathname
    .split("/")
    .map((seg) =>
      /^\d+$/.test(seg) ||
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(seg) ||
      /^[A-Za-z0-9]{16,}$/.test(seg) ||
      /\d{3,}/.test(seg)
        ? ":id"
        : seg,
    )
    .join("/");
}

/** API の道すじの形。問い合わせ文字は名前だけ残し、値は出さない */
function apiShape(url: string): string {
  try {
    const u = new URL(url);
    const names = [...new Set(u.searchParams.keys())].sort();
    return names.length > 0 ? `${pathShape(u.pathname)}?${names.join("&")}` : pathShape(u.pathname);
  } catch {
    return "(読めない道すじ)";
  }
}

/** アプリの中で画面を切り替える（読み込み直しなし）。react-router の BrowserRouter は popstate で location を読み直す */
async function goInApp(page: Page, url: string): Promise<void> {
  await page.evaluate((to) => {
    const prev = window.history.state as { idx?: unknown } | null;
    const idx = (prev && typeof prev.idx === "number" ? prev.idx : 0) + 1;
    window.history.pushState({ usr: null, key: Math.random().toString(36).slice(2, 10), idx }, "", to);
    window.dispatchEvent(new PopStateEvent("popstate", { state: window.history.state }));
  }, url);
}

function currentUrl(page: Page): string {
  const u = new URL(page.url());
  return u.pathname + u.search;
}

/** 開いた先が目当ての画面か（道すじが同じで、目当ての問い合わせ文字がそのまま残っている） */
function landed(page: Page, url: string): boolean {
  const want = new URL(url, BASE_URL);
  const got = new URL(page.url());
  if (got.pathname.replace(/\/$/, "") !== want.pathname.replace(/\/$/, "")) return false;
  for (const [k, v] of want.searchParams) {
    if (got.searchParams.get(k) !== v) return false;
  }
  return true;
}

/** 今いる画面と同じ道すじへは切り替えても読み直さないので、先に別の画面へ移っておく */
async function leaveIfSame(page: Page, api: ApiTracker, url: string): Promise<void> {
  if (currentUrl(page) !== url) return;
  const other = SPEED_TARGETS.find((t) => t.kind === "" && t.route !== url);
  if (!other) return;
  await goInApp(page, other.route);
  await waitSettled(page, api, { capMs: CAP_MS });
}

function emptyRow(target: SpeedTarget, status: Status): Row {
  return {
    route: target.route,
    seconds: null,
    status,
    api: 0,
    forbidden: 0,
    serverError: 0,
    slowest: "",
    slowestSeconds: null,
  };
}

/** 一覧画面を開き、一覧 API の応答の先頭の id を拾う。番号はメモリの中だけで使い、表にも記録にも出さない */
async function pickId(
  page: Page,
  api: ApiTracker,
  target: Extract<SpeedTarget, { kind: "needs-id" }>,
): Promise<string | null> {
  await leaveIfSame(page, api, target.listPage);
  const responseP = page
    .waitForResponse(
      (r) => {
        if (r.request().method() !== "GET" || r.status() !== 200) return false;
        try {
          return new URL(r.url()).pathname === target.listApi;
        } catch {
          return false;
        }
      },
      { timeout: CAP_MS },
    )
    .catch(() => null);
  await goInApp(page, target.listPage);
  const response = await responseP;
  await waitSettled(page, api, { capMs: CAP_MS });
  if (!response) return null;
  const body: unknown = await response.json().catch(() => null);
  if (!Array.isArray(body) || body.length === 0) return null;
  const first: unknown = body[0];
  if (typeof first !== "object" || first === null) return null;
  const id = (first as { id?: unknown }).id;
  if (typeof id !== "string" && typeof id !== "number") return null;
  return String(id);
}

function render(rows: Row[], blocked: Map<string, number>, auth429: number, startedAt: Date, loggedIn: boolean): string {
  const measured = rows.filter((r) => r.status === "測れた");
  const bySecondsDesc = (a: Row, b: Row) => (b.seconds ?? 0) - (a.seconds ?? 0);
  const clean = measured.filter((r) => r.forbidden === 0).sort(bySecondsDesc);
  const withForbidden = measured.filter((r) => r.forbidden > 0).sort(bySecondsDesc);
  const others = rows.filter((r) => r.status !== "測れた");
  const sec = (v: number | null) => (v === null ? "—" : v.toFixed(1));
  const line = (r: Row) =>
    `| \`${r.route}\` | ${sec(r.seconds)} | ${r.status} | ${r.api} | ${r.forbidden} | ${r.serverError} | ${r.slowest ? `\`${r.slowest}\`` : "—"} | ${sec(r.slowestSeconds)} |`;
  const when = startedAt.toLocaleString("ja-JP", { timeZone: "Asia/Tokyo" });
  const out: string[] = [
    "## 画面の速さ（判定なし・遅い順）",
    "",
    `- 測った日時（日本時間）: ${when}`,
    `- 画面の数: ${rows.length}（測れた・403 なし ${clean.length}／測れた・403 あり ${withForbidden.length}／測れなかった ${others.length}）`,
    "- 秒 = 画面切り替えの命令から「最後の API の応答が終わった時刻」と「読み込み中の印が消えた時刻」の遅い方まで",
    "- 最初に開いた画面だけ、部品の読み込みの時間が入る。測るあいだはブラウザの保存（キャッシュ）を使わない",
    "",
  ];
  if (!loggedIn) out.push("**ログインできなかったため、画面は測っていない。**", "");
  out.push(
    "| 画面 | 秒 | 状態 | API の数 | 403 | 5xx | いちばん遅い API | その秒 |",
    "|---|---|---|---|---|---|---|---|",
    ...clean.map(line),
    ...withForbidden.map(line),
    ...others.map(line),
    "",
    `- 止めた送信: ${[...blocked.values()].reduce((a, b) => a + b, 0)} 件`,
  );
  for (const [k, n] of [...blocked.entries()].sort()) out.push(`  - \`${k}\`: ${n} 件`);
  out.push(`- ログイン関係の 429: ${auth429} 件`, "");
  return out.join("\n");
}

test("全画面の速さを記録する（判定なし）", async ({ page, context }) => {
  const c = creds();
  test.skip(!c, "点検用の人の秘密情報が未登録");
  if (!c) return;

  const startedAt = new Date();
  const stageStart = Date.now();
  const rows: Row[] = [];
  const blocked = new Map<string, number>();
  let auth429 = 0;
  let loggedIn = false;

  // 関所（設計 5-5）。ログインより先に置く
  await context.route("**/*", async (route) => {
    const req = route.request();
    const method = req.method();
    let path = "";
    try {
      path = new URL(req.url()).pathname;
    } catch {
      path = "";
    }
    const isRead = method === "GET" || method === "HEAD" || method === "OPTIONS";
    const writesOnRead =
      method === "GET" && (path.includes("/attachment-url") || path === "/api/v1/tenant-commission-settings");
    const authCall = method === "POST" && (path === "/api/v1/auth/login" || path === "/api/v1/auth/refresh");
    if ((isRead && !writesOnRead) || authCall) {
      await route.continue();
      return;
    }
    const key = `${method} ${pathShape(path)}`;
    blocked.set(key, (blocked.get(key) ?? 0) + 1);
    await route.abort();
  });

  let hits: ApiHit[] = [];
  page.on("requestfinished", async (req: Request) => {
    if (!isTrackedApi(req)) return;
    const bucket = hits;
    const res = await req.response().catch(() => null);
    const t = req.timing();
    bucket.push({ shape: apiShape(req.url()), ms: t.responseEnd >= 0 ? t.responseEnd : 0, status: res ? res.status() : 0 });
  });
  page.on("response", (res) => {
    try {
      if (res.status() === 429 && new URL(res.url()).pathname.startsWith("/api/v1/auth/")) auth429 += 1;
    } catch {
      // 読めない道すじは数えない
    }
  });

  const api = trackApi(page);
  try {
    await authPace();
    await login(page, c.email, c.password);
    loggedIn = true;
    await waitSettled(page, api, { capMs: CAP_MS });

    for (const target of SPEED_TARGETS) {
      if (Date.now() - stageStart > STAGE_LIMIT_MS) {
        rows.push(emptyRow(target, "時間切れで未測定"));
        continue;
      }
      try {
        let url = target.route;
        if (target.kind === "needs-id") {
          const id = await pickId(page, api, target);
          if (id === null) {
            rows.push(emptyRow(target, "番号を拾えず"));
            continue;
          }
          url = target.route.replace(":id", encodeURIComponent(id));
        }
        await leaveIfSame(page, api, url);
        const bucket: ApiHit[] = [];
        hits = bucket;
        const navStart = Date.now();
        await goInApp(page, url);
        const r = await waitSettled(page, api, { capMs: CAP_MS });
        hits = [];
        const row = emptyRow(target, "測れた");
        row.api = bucket.length;
        row.forbidden = bucket.filter((h) => h.status === 403).length;
        row.serverError = bucket.filter((h) => h.status >= 500).length;
        const slow = bucket.reduce<ApiHit | null>((m, h) => (m === null || h.ms > m.ms ? h : m), null);
        if (slow) {
          row.slowest = slow.shape;
          row.slowestSeconds = slow.ms / 1000;
        }
        if (!r.settled) {
          row.status = "時間切れ";
        } else if (!landed(page, url)) {
          row.status = "別の画面へ移った";
        } else {
          row.seconds = (Math.max(navStart, r.lastApiEndAt, r.loadingGoneAt) - navStart) / 1000;
        }
        rows.push(row);
      } catch {
        // 例外の文は道すじを含むことがあるので出さない
        hits = [];
        rows.push(emptyRow(target, "エラー"));
      }
    }
  } finally {
    writeFileSync(OUT_FILE, render(rows, blocked, auth429, startedAt, loggedIn), "utf8");
  }
});
