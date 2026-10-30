/**
 * 本番の画面点検の「開き終わった」の決め方（ADR-1053）。点検と速さの記録の両方がここを使う。
 * networkidle は使わない（ログイン中は開いたままの通信があり成り立たないため）。
 */

import { expect } from "@playwright/test";
import type { Page, Request } from "@playwright/test";

/** 開いたままになる通信（SSE）の印。アプリはこの頭書きを付けて開く。終わっていない数に数えない */
export const STREAM_ACCEPT = "text/event-stream";

/** 読み込み中の印 */
export const LOADING_SELECTOR =
  '.sa-loading-block, .sa-skeleton, .loading-screen, .loading-indicator, [aria-busy="true"]';

export type ApiTracker = {
  /** 終わっていない /api/ の通信の数 */
  inFlight: () => number;
  /** 最後に /api/ の通信が始まった・終わった時刻（ミリ秒） */
  lastChangeAt: () => number;
};

function isTrackedApi(req: Request): boolean {
  let path: string;
  try {
    path = new URL(req.url()).pathname;
  } catch {
    return false;
  }
  if (!path.startsWith("/api/")) return false;
  return !(req.headers()["accept"] ?? "").includes(STREAM_ACCEPT);
}

/** page の /api/ の通信を数え始める。login() より前に呼ぶ */
export function trackApi(page: Page): ApiTracker {
  const pending = new Set<Request>();
  let lastChange = Date.now();
  page.on("request", (req) => {
    if (!isTrackedApi(req)) return;
    pending.add(req);
    lastChange = Date.now();
  });
  const done = (req: Request) => {
    if (pending.delete(req)) lastChange = Date.now();
  };
  page.on("requestfinished", done);
  page.on("requestfailed", done);
  return { inFlight: () => pending.size, lastChangeAt: () => lastChange };
}

export type SettleOptions = { minMs?: number; quietMs?: number; capMs?: number };
export type SettleResult = {
  settled: boolean;
  elapsedMs: number;
  /** 終わった時点の、終わっていない /api/ の通信の数 */
  inFlight: number;
  /** 終わった時点の、見えている読み込み中の印の数 */
  loading: number;
};

async function visibleLoadingCount(page: Page): Promise<number> {
  try {
    return await page.evaluate(
      (sel) =>
        Array.from(document.querySelectorAll(sel)).filter((el) => el.getClientRects().length > 0).length,
      LOADING_SELECTOR,
    );
  } catch {
    // 画面の切り替わりの途中は読めない。まだ開き終わっていない扱いにする
    return 1;
  }
}

/**
 * 次の 3 つが同時に成り立つまで待つ: 呼んでから minMs 以上たった／終わっていない /api/ の通信が 0 件の状態が quietMs 続いた／読み込み中の印が見えない。
 * capMs を超えたら settled: false を返す（例外は投げない）。
 */
export async function waitSettled(
  page: Page,
  tracker: ApiTracker,
  opts: SettleOptions = {},
): Promise<SettleResult> {
  const minMs = opts.minMs ?? 500;
  const quietMs = opts.quietMs ?? 1000;
  const capMs = opts.capMs ?? 30_000;
  const start = Date.now();
  for (;;) {
    const now = Date.now();
    const elapsedMs = now - start;
    if (elapsedMs >= minMs && tracker.inFlight() === 0 && now - tracker.lastChangeAt() >= quietMs) {
      const loading = await visibleLoadingCount(page);
      if (loading === 0) return { settled: true, elapsedMs, inFlight: 0, loading };
    }
    if (elapsedMs >= capMs) {
      return { settled: false, elapsedMs, inFlight: tracker.inFlight(), loading: await visibleLoadingCount(page) };
    }
    await page.waitForTimeout(100);
  }
}

/** 点検用: 開き終わらなければ、終わっていない通信と読み込み中の印の数を添えて失敗させる */
export async function expectSettled(page: Page, tracker: ApiTracker): Promise<void> {
  const r = await waitSettled(page, tracker);
  expect(
    r.settled,
    `画面が 30 秒で開き終わらない（終わっていない通信 ${r.inFlight} 件・読み込み中の印 ${r.loading} 件）`,
  ).toBe(true);
}
