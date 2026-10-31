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
import {
  CONTAINER_SELECTOR,
  PROBE_LIMIT_MS,
  RECORDER_SOURCE,
  lastMutationBefore,
  pointerAt,
  runRecorderProbe,
  sigNow,
  waitMatch,
  waitMutation,
  type ProbeResult,
} from "./screen-recorder";

/** 1 画面の待ちの上限 */
const CAP_MS = 45_000;
/** 段の全体の上限。超えたら残りは測らずに表を出す */
const STAGE_LIMIT_MS = 40 * 60 * 1000;
/** ワークフローはリポジトリの根から動かす */
const OUT_FILE = "tests/prod-check/page-speed.md";
/** 戻った時の秒を待つ上限（K1） */
const K1_CAP_MS = 10_000;
/** 押してから最初の変化を待つ上限（K3） */
const K3_CAP_MS = 5_000;
/** 押す前に中身の場所が動いていなかったと見なす長さ */
const K3_QUIET_MS = 1_000;
/** 段の始めからこの時間を過ぎたら K1 を測らない（今の秒の巡回の 40 分を削らないため・stage0-card.md V0-6） */
const K1_STAGE_LIMIT_MS = 25 * 60 * 1000;
/** 戻った時・押した時を測るあいだは、止めた送信と 403 の合計に数えない（今の表の合計を変えないため）。そのあいだの API の数は apis に別に数える（V0-7） */
const extra = { on: false, apis: 0 };

/** 番号の要る画面で、一覧から番号を拾えなかった理由（設計 5-8） */
type MissReason =
  | "番号を拾えず（一覧が 403）"
  | "番号を拾えず（一覧がほかの失敗）"
  | "番号を拾えず（一覧が空）"
  | "番号を拾えず（一覧の形が違う）"
  | "番号を拾えず（一覧の応答なし）";
type Status = "測れた" | "時間切れ" | MissReason | "別の画面へ移った" | "エラー" | "時間切れで未測定";
type ExtraNote =
  | ""
  | "見分けられず（行き先と同じ形）"
  | "中身の場所が無い"
  | "10 秒で見分けられず"
  | "命令で切り替え"
  | "押す前も動いていた"
  | "5 秒で変化なし"
  | "別の画面へ移った"
  | "時間切れで未測定"
  | "精度の試しが不合格"
  | "エラー";
type Row = {
  route: string;
  seconds: number | null;
  status: Status;
  api: number;
  forbidden: number;
  serverError: number;
  /** その画面を開くあいだに関所が止めた数 */
  blocked: number;
  slowest: string;
  slowestSeconds: number | null;
  k1Seconds: number | null;
  k1Note: ExtraNote;
  k3Seconds: number | null;
  k3Note: ExtraNote;
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

/** アプリの中で画面を切り替える（読み込み直しなし）。react-router の BrowserRouter は popstate で location を読み直す。切り替えの直前のページの時計（performance.now）を返す */
async function goInApp(page: Page, url: string): Promise<number> {
  return page.evaluate((to) => {
    const prev = window.history.state as { idx?: unknown } | null;
    const idx = (prev && typeof prev.idx === "number" ? prev.idx : 0) + 1;
    const at = performance.now();
    window.history.pushState({ usr: null, key: Math.random().toString(36).slice(2, 10), idx }, "", to);
    window.dispatchEvent(new PopStateEvent("popstate", { state: window.history.state }));
    return at;
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
    blocked: 0,
    slowest: "",
    slowestSeconds: null,
    k1Seconds: null,
    k1Note: "",
    k3Seconds: null,
    k3Note: "",
  };
}

/** 戻った時の秒（K1・設計 §3-5・stage0-card.md V0-2）。A を開き終えた今の状態から、別の画面 B へ移り、また A へ切り替える */
async function measureReturn(
  page: Page,
  api: ApiTracker,
  rows: Row[],
  url: string,
  expected: string,
  row: Row,
): Promise<void> {
  const want = await sigNow(page);
  if (want === "") {
    row.k1Note = "中身の場所が無い";
    return;
  }
  // B = その回で測れた・403 なし・道すじが固定の画面のうち、今の秒がいちばん短い画面（stage0-card.md V0-2）
  const kindEmpty = new Set(SPEED_TARGETS.filter((t) => t.kind === "").map((t) => t.route));
  const fast = rows
    .filter((r) => r.status === "測れた" && r.forbidden === 0 && r.seconds !== null && kindEmpty.has(r.route))
    .filter((r) => r.route !== url && r.route !== expected)
    .sort((a, b) => (a.seconds ?? 0) - (b.seconds ?? 0))[0];
  const other = fast
    ? { route: fast.route }
    : SPEED_TARGETS.find((t) => t.kind === "" && t.route !== url && t.route !== expected);
  if (!other) {
    row.k1Note = "見分けられず（行き先と同じ形）";
    return;
  }
  await goInApp(page, other.route);
  await waitSettled(page, api, { capMs: CAP_MS });
  if ((await sigNow(page)) === want) {
    row.k1Note = "見分けられず（行き先と同じ形）";
    return;
  }
  const t0 = await goInApp(page, url);
  const at = await waitMatch(page, t0, want, K1_CAP_MS);
  await waitSettled(page, api, { capMs: CAP_MS });
  if (!landed(page, expected)) {
    row.k1Note = "別の画面へ移った";
    return;
  }
  if (at < 0) {
    row.k1Note = "10 秒で見分けられず";
    return;
  }
  row.k1Seconds = (at - t0) / 1000;
}

/** 押してから最初の変化の秒（K3・設計 §3-5・stage0-card.md V0-3 (ア)）。メニューを開く操作と指を乗せる動きは数えない。メニューに無ければ measureSwitch（(イ)）へ */
async function measureTap(page: Page, api: ApiTracker, route: string, row: Row): Promise<void> {
  await leaveIfSame(page, api, route);
  const link = page
    .locator(
      `aside#sidebar-panel a.sidebar-item[href="${route}"], aside#sidebar-panel a.sidebar-sub-item[href="${route}"]`,
    )
    .first();
  if ((await link.count()) === 0) {
    const buttons = page.locator("aside#sidebar-panel button.sidebar-accordion-btn");
    const n = await buttons.count();
    for (let i = 0; i < n && (await link.count()) === 0; i++) {
      if ((await buttons.nth(i).getAttribute("aria-expanded")) !== "true") await buttons.nth(i).click();
      await link.waitFor({ state: "attached", timeout: 1_000 }).catch(() => undefined);
    }
  }
  if ((await link.count()) === 0) {
    // 横のメニューに無い画面（権限で出ない項目を含む）は、アプリの中の切り替えの命令から測る（V0-3 (イ)）
    await measureSwitch(page, api, route, row);
    return;
  }
  await link.hover();
  await page.locator("aside#sidebar-panel.sidebar-expanded").waitFor({ timeout: 2_000 }).catch(() => undefined);
  // 前の画面の動きが止むのを待つ（最大 5 秒）。止まなければ下で「押す前も動いていた」になる
  await waitQuiet(page, K3_QUIET_MS);
  const before = await pointerAt(page);
  await link.click();
  const pointer = await pointerAt(page);
  const last = pointer > before ? await lastMutationBefore(page, pointer) : -1;
  const mut = pointer > before ? await waitMutation(page, pointer, K3_CAP_MS) : -1;
  await waitSettled(page, api, { capMs: CAP_MS });
  const box = await page.locator(CONTAINER_SELECTOR).first().boundingBox();
  if (box) await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  if (pointer <= before) {
    row.k3Note = "エラー";
  } else if (!landed(page, route)) {
    row.k3Note = "別の画面へ移った";
  } else if (last >= 0 && pointer - last < K3_QUIET_MS) {
    row.k3Note = "押す前も動いていた";
  } else if (mut < 0) {
    row.k3Note = "5 秒で変化なし";
  } else {
    row.k3Seconds = (mut - pointer) / 1000;
  }
}

/** 中身の場所の DOM が q ミリ秒動いていないのを待つ（最大 5 秒）。止まなければ呼び出し側で「押す前も動いていた」になる */
async function waitQuiet(page: Page, q: number): Promise<void> {
  await page
    .waitForFunction(
      (ms) => {
        const now = performance.now();
        const last = window.__saRec?.lastMutationBefore(now) ?? -1;
        return last < 0 || now - last >= ms;
      },
      q,
      { timeout: 5_000, polling: 100 },
    )
    .catch(() => undefined);
}

/** 横のメニューに無い画面の K3（V0-3 (イ)）。アプリの中の切り替えの命令の直前の時刻から、中身の場所が最初に変わった時刻まで */
async function measureSwitch(page: Page, api: ApiTracker, route: string, row: Row): Promise<void> {
  await waitQuiet(page, K3_QUIET_MS);
  const t0 = await goInApp(page, route);
  const last = await lastMutationBefore(page, t0);
  const mut = await waitMutation(page, t0, K3_CAP_MS);
  await waitSettled(page, api, { capMs: CAP_MS });
  if (!landed(page, route)) {
    row.k3Note = "別の画面へ移った";
  } else if (last >= 0 && t0 - last < K3_QUIET_MS) {
    row.k3Note = "押す前も動いていた";
  } else if (mut < 0) {
    row.k3Note = "5 秒で変化なし";
  } else {
    row.k3Seconds = (mut - t0) / 1000;
    row.k3Note = "命令で切り替え";
  }
}

/** 一覧画面を開き、一覧 API の応答の先頭の id を拾う。番号はメモリの中だけで使い、表にも記録にも出さない。拾えなければ理由を返す */
async function pickId(
  page: Page,
  api: ApiTracker,
  target: Extract<SpeedTarget, { kind: "needs-id" }>,
): Promise<{ id: string } | { miss: MissReason }> {
  await leaveIfSame(page, api, target.listPage);
  const responseP = page
    .waitForResponse(
      (r) => {
        if (r.request().method() !== "GET") return false;
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
  if (!response) return { miss: "番号を拾えず（一覧の応答なし）" };
  if (response.status() === 403) return { miss: "番号を拾えず（一覧が 403）" };
  if (response.status() !== 200) return { miss: "番号を拾えず（一覧がほかの失敗）" };
  const body: unknown = await response.json().catch(() => null);
  if (!Array.isArray(body)) return { miss: "番号を拾えず（一覧の形が違う）" };
  if (body.length === 0) return { miss: "番号を拾えず（一覧が空）" };
  const first: unknown = body[0];
  if (typeof first !== "object" || first === null) return { miss: "番号を拾えず（一覧の形が違う）" };
  const id = (first as { id?: unknown }).id;
  if (typeof id !== "string" && typeof id !== "number") return { miss: "番号を拾えず（一覧の形が違う）" };
  return { id: String(id) };
}

function render(
  rows: Row[],
  blocked: Map<string, number>,
  forbiddenApis: Map<string, number>,
  auth429: number,
  startedAt: Date,
  loggedIn: boolean,
  probe: ProbeResult,
  heapMb: number | null,
  extraApis: number,
): string {
  const measured = rows.filter((r) => r.status === "測れた");
  const bySecondsDesc = (a: Row, b: Row) => (b.seconds ?? 0) - (a.seconds ?? 0);
  const clean = measured.filter((r) => r.forbidden === 0).sort(bySecondsDesc);
  const withForbidden = measured.filter((r) => r.forbidden > 0).sort(bySecondsDesc);
  const others = rows.filter((r) => r.status !== "測れた");
  const sec = (v: number | null) => (v === null ? "—" : v.toFixed(1));
  const sec2 = (v: number | null) => (v === null ? "—" : v.toFixed(2));
  const line = (r: Row) =>
    `| \`${r.route}\` | ${sec(r.seconds)} | ${r.status} | ${r.api} | ${r.forbidden} | ${r.serverError} | ${r.blocked} | ${r.slowest ? `\`${r.slowest}\`` : "—"} | ${sec(r.slowestSeconds)} | ${sec2(r.k1Seconds)} | ${sec2(r.k3Seconds)} | ${[r.k1Note && `戻: ${r.k1Note}`, r.k3Note && `押: ${r.k3Note}`].filter(Boolean).join("・") || "—"} |`;
  const when = startedAt.toLocaleString("ja-JP", { timeZone: "Asia/Tokyo" });
  const out: string[] = [
    "## 画面の速さ（判定なし・遅い順）",
    "",
    `- 測った日時（日本時間）: ${when}`,
    `- 画面の数: ${rows.length}（測れた・403 なし ${clean.length}／測れた・403 あり ${withForbidden.length}／測れなかった ${others.length}）`,
    "- 秒 = 画面切り替えの命令から「最後の API の応答が終わった時刻」と「読み込み中の印が消えた時刻」の遅い方まで",
    "- 最初に開いた画面だけ、部品の読み込みの時間が入る。測るあいだはブラウザの保存（キャッシュ）を使わない",
    "- 止めた送信 = その画面を開くあいだに、本番を守るために止めた通信の数。止めた通信の本当の時間は秒に入っていない",
    "- `A → B` の行は、A を開くと中の B へ移る画面。B に着くまでの秒",
    "- 戻った時の秒 = 開き終えた画面 A から別の画面 B へ移り、また A へ切り替えた命令から、中身の場所に読み込み中の印が無く、A を開き終えた時と同じ構造（タグとクラス名だけで比べる）が描かれた最初のコマまで（K1）",
    "- 戻った時の秒の行き先 B = その回で測れた・403 なしの画面のうち、いちばん速い画面。403 ありの行の戻った時の秒は、中身ではなく断りの画面が戻る秒",
    "- 押して最初の変化の秒 = 横のメニューにある画面は、項目を押した時刻から、中身の場所が最初に変わった時刻まで（K3）。メニューを開く操作と指を乗せる動きは数えない。横のメニューに無い画面は、アプリの中で切り替える命令の時刻から測り、訳に「命令で切り替え」と書く。命令で切り替えた行には押された部品の click の処理が入らないので、メニューを押した行と秒を並べて比べない。道すじが固定の画面だけ。どの画面も 2 回目以降に開いた時の秒",
    "- 訳の列の「戻:」は戻った時の訳、「押:」は押した時の訳",
    "- 記録係を入れた日から、開き終わるまでの秒が少し動きうる（記録係の 1 コマ約 0.8 ms）",
    `- 記録係の精度の試し（本番に繋がない）: ${probe.total} 件中 ${probe.passed} 件合格・いちばん大きい差 ${Number.isFinite(probe.maxDiffMs) ? `${probe.maxDiffMs.toFixed(1)} ms` : "見つからず"}（合格線 ${PROBE_LIMIT_MS} ms）`,
    "",
  ];
  if (!loggedIn) out.push("**ログインできなかったため、画面は測っていない。**", "");
  out.push(
    "| 画面 | 秒 | 状態 | API の数 | 403 | 5xx | 止めた送信 | いちばん遅い API | その秒 | 戻った時の秒 | 押して最初の変化の秒 | 戻った時・押した時の訳 |",
    "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ...clean.map(line),
    ...withForbidden.map(line),
    ...others.map(line),
    "",
    `- 止めた送信: ${[...blocked.values()].reduce((a, b) => a + b, 0)} 件`,
  );
  for (const [k, n] of [...blocked.entries()].sort()) out.push(`  - \`${k}\`: ${n} 件`);
  out.push(`- 403 が返った API（応答の数）: ${[...forbiddenApis.values()].reduce((a, b) => a + b, 0)} 件`);
  for (const [k, n] of [...forbiddenApis.entries()].sort()) out.push(`  - \`${k}\`: ${n} 件`);
  out.push(`- ログイン関係の 429: ${auth429} 件`);
  out.push(
    `- 戻った時の秒を測れた画面: ${rows.filter((r) => r.k1Seconds !== null).length}`,
    `- 押して最初の変化の秒を測れた画面: メニューを押した ${rows.filter((r) => r.k3Seconds !== null && r.k3Note !== "命令で切り替え").length}・命令で切り替え ${rows.filter((r) => r.k3Seconds !== null && r.k3Note === "命令で切り替え").length}`,
    `- 戻った時・押した時を測るあいだの API の数（今の表の数とは別）: ${extraApis}`,
    `- ブラウザのメモリ（JS ヒープ・測り終えた時）: ${heapMb === null ? "測れず" : `${heapMb.toFixed(0)} MB`}`,
    "",
  );
  return out.join("\n");
}

test("記録係の精度を確かめる（本番に繋がない）", async ({ page }) => {
  const r = await runRecorderProbe(page);
  if (r.passed !== r.total) {
    throw new Error(`記録係の精度の試し: ${r.total} 件中 ${r.passed} 件合格・いちばん大きい差 ${r.maxDiffMs} ms（合格線 ${PROBE_LIMIT_MS} ms）`);
  }
});

test("全画面の速さを記録する（判定なし）", async ({ page, context }) => {
  const c = creds();
  test.skip(!c, "点検用の人の秘密情報が未登録");
  if (!c) return;

  const startedAt = new Date();
  const stageStart = Date.now();
  const rows: Row[] = [];
  const blocked = new Map<string, number>();
  const forbiddenApis = new Map<string, number>();
  let blockedTotal = 0;
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
    if (!extra.on) {
      blocked.set(key, (blocked.get(key) ?? 0) + 1);
      blockedTotal += 1;
    }
    if (writesOnRead) {
      // abort すると、アプリは通信の失敗として 0.5・1・2 秒待って送り直し、その待ちが秒に入る。409 は送り直さない（設計 5-8）
      await route.fulfill({ status: 409, contentType: "application/json", body: "{}" });
      return;
    }
    await route.abort();
  });

  await page.addInitScript({ content: RECORDER_SOURCE });
  let probe: ProbeResult = { passed: 0, total: 4, maxDiffMs: Number.POSITIVE_INFINITY };
  try {
    const probePage = await context.newPage();
    try {
      probe = await runRecorderProbe(probePage);
    } finally {
      await probePage.close();
    }
  } catch {
    // 精度の試しが動かなければ不合格として扱う（表は必ず書く）
  }
  const recorderOk = probe.passed === probe.total;
  let heapMb: number | null = null;

  let hits: ApiHit[] = [];
  page.on("requestfinished", async (req: Request) => {
    if (!isTrackedApi(req)) return;
    const bucket = hits;
    const counted = !extra.on;
    if (!counted) extra.apis += 1;
    const res = await req.response().catch(() => null);
    const t = req.timing();
    const shape = apiShape(req.url());
    const status = res ? res.status() : 0;
    if (status === 403 && counted) forbiddenApis.set(shape, (forbiddenApis.get(shape) ?? 0) + 1);
    bucket.push({ shape, ms: t.responseEnd >= 0 ? t.responseEnd : 0, status });
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
          const picked = await pickId(page, api, target);
          if ("miss" in picked) {
            rows.push(emptyRow(target, picked.miss));
            continue;
          }
          url = target.route.replace(":id", encodeURIComponent(picked.id));
        }
        // 中の画面へ移るだけの道すじは、移った先に着いたかで確かめる
        const expected = target.kind === "redirect" ? target.to : url;
        await leaveIfSame(page, api, url);
        const bucket: ApiHit[] = [];
        hits = bucket;
        const blockedBefore = blockedTotal;
        const navStart = Date.now();
        await goInApp(page, url);
        const r = await waitSettled(page, api, { capMs: CAP_MS });
        hits = [];
        const row = emptyRow(target, "測れた");
        if (target.kind === "redirect") row.route = `${target.route} → ${target.to}`;
        row.blocked = blockedTotal - blockedBefore;
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
        } else if (!landed(page, expected)) {
          row.status = "別の画面へ移った";
        } else {
          row.seconds = (Math.max(navStart, r.lastApiEndAt, r.loadingGoneAt) - navStart) / 1000;
        }
        if (row.status === "測れた" && !recorderOk) {
          row.k1Note = "精度の試しが不合格";
        } else if (row.status === "測れた" && Date.now() - stageStart > K1_STAGE_LIMIT_MS) {
          row.k1Note = "時間切れで未測定";
        } else if (row.status === "測れた") {
          extra.on = true;
          try {
            await measureReturn(page, api, rows, url, expected, row);
          } catch {
            row.k1Note = "エラー";
          } finally {
            extra.on = false;
          }
        }
        rows.push(row);
      } catch {
        // 例外の文は道すじを含むことがあるので出さない
        hits = [];
        rows.push(emptyRow(target, "エラー"));
      }
    }
    for (let i = 0; i < SPEED_TARGETS.length && i < rows.length; i++) {
      const target = SPEED_TARGETS[i];
      const row = rows[i];
      if (target.kind !== "" || row.status !== "測れた") continue;
      if (!recorderOk) {
        row.k3Note = "精度の試しが不合格";
        continue;
      }
      if (Date.now() - stageStart > STAGE_LIMIT_MS) {
        row.k3Note = "時間切れで未測定";
        continue;
      }
      extra.on = true;
      try {
        await measureTap(page, api, target.route, row);
      } catch {
        row.k3Note = "エラー";
      } finally {
        extra.on = false;
      }
    }
    heapMb = await page
      .evaluate(() => {
        const m = (performance as unknown as { memory?: { usedJSHeapSize: number } }).memory;
        return m ? m.usedJSHeapSize / 1048576 : null;
      })
      .catch(() => null);
  } finally {
    writeFileSync(
      OUT_FILE,
      render(rows, blocked, forbiddenApis, auth429, startedAt, loggedIn, probe, heapMb, extra.apis),
      "utf8",
    );
  }
});
