/**
 * 画面の中の記録係（docs/handoff/line-like-speed/design.md §3-5・stage0-card.md §0）
 *
 * ブラウザの中で毎コマ、中身の場所（main）の「構造の印」と読み込み中の印の数を記録する。
 * あわせて、中身の場所の DOM が変わった時刻と、押した時刻（pointerdown）を残す。
 * 画面の文字・値は読まない。構造の印はタグ名とクラス名だけを数に縮めたもので、外へは時刻と数だけを返す（ADR-1053）。
 */

import type { Page } from "@playwright/test";
import { LOADING_SELECTOR } from "./settle";

/** 中身の場所（DesktopShell.tsx の main.app-content・MobileShell.tsx の main.mobile-content） */
export const CONTAINER_SELECTOR = "main.app-content, main.mobile-content";
/** 構造の印に入れない部品（取り直し中の小さな印・design.md §3-2 の Spinner）。その中も入れない */
export const SIG_SKIP_SELECTOR = ".sa-spinner";
/** 構造の印に入れる要素の数と深さの上限（毎コマの重さを抑える） */
const SIG_MAX_ELEMENTS = 400;
const SIG_MAX_DEPTH = 6;
/** 残すコマと DOM の変化の数の上限（60 コマ/秒で約 33 秒分） */
const KEEP = 2000;
/** 精度の試しの合格線（ミリ秒） */
export const PROBE_LIMIT_MS = 50;
/** 押した時の試しで、押してから中身を変えるまでの待ち（ミリ秒） */
const PROBE_TAP_DELAY_MS = 150;

type Rec = {
  sigNow: () => string;
  firstMatch: (since: number, want: string) => number;
  pointerAt: () => number;
  firstMutationAfter: (since: number) => number;
  lastMutationBefore: (until: number) => number;
};

declare global {
  interface Window {
    __saRec?: Rec;
  }
}

/** ブラウザの中で動く記録係。page.addInitScript({ content }) か page.evaluate で入れる */
export const RECORDER_SOURCE = `(() => {
  if (window.__saRec) return;
  const CONTAINER = ${JSON.stringify(CONTAINER_SELECTOR)};
  const LOADING = ${JSON.stringify(LOADING_SELECTOR)};
  const SKIP = ${JSON.stringify(SIG_SKIP_SELECTOR)};
  const MAX_EL = ${SIG_MAX_ELEMENTS};
  const MAX_DEPTH = ${SIG_MAX_DEPTH};
  const KEEP = ${KEEP};
  const frames = [];
  const mutations = [];
  let pointerAt = -1;
  const sig = (root) => {
    let h = 2166136261;
    let n = 0;
    const queue = [[root, 0]];
    for (let i = 0; i < queue.length && n < MAX_EL; i++) {
      const el = queue[i][0];
      const d = queue[i][1];
      if (el.matches(SKIP)) continue;
      const s = el.tagName + "." + Array.from(el.classList).sort().join(".") + "|";
      for (let k = 0; k < s.length; k++) { h ^= s.charCodeAt(k); h = Math.imul(h, 16777619); }
      n++;
      if (d < MAX_DEPTH) for (const c of el.children) queue.push([c, d + 1]);
    }
    return (h >>> 0).toString(16) + ":" + n;
  };
  const read = () => {
    const c = document.querySelector(CONTAINER);
    return c ? { sig: sig(c), loading: c.querySelectorAll(LOADING).length } : { sig: "", loading: -1 };
  };
  const keep = (arr, v) => { arr.push(v); if (arr.length > KEEP) arr.splice(0, arr.length - KEEP); };
  // 毎コマ requestAnimationFrame の中（描く前）で読み、MessageChannel で投げて受けた時刻（その回の描く手順の後）を残す
  const ch = new MessageChannel();
  let pending = null;
  ch.port1.onmessage = () => {
    if (pending) keep(frames, { t: performance.now(), sig: pending.sig, loading: pending.loading });
    pending = null;
  };
  const tick = () => {
    pending = read();
    ch.port2.postMessage(0);
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  new MutationObserver((records) => {
    const c = document.querySelector(CONTAINER);
    if (!c) return;
    if (records.some((r) => c === r.target || c.contains(r.target))) keep(mutations, performance.now());
  }).observe(document, { subtree: true, childList: true, attributes: true, characterData: true });
  window.addEventListener("pointerdown", (e) => { pointerAt = e.timeStamp; }, true);
  window.__saRec = {
    sigNow: () => read().sig,
    firstMatch: (since, want) => {
      const f = frames.find((x) => x.t >= since && x.loading === 0 && x.sig === want);
      return f ? f.t : -1;
    },
    pointerAt: () => pointerAt,
    firstMutationAfter: (since) => {
      const m = mutations.find((x) => x >= since);
      return m === undefined ? -1 : m;
    },
    lastMutationBefore: (until) => {
      let v = -1;
      for (const x of mutations) { if (x < until) v = x; else break; }
      return v;
    },
  };
})();`;

/** 今の中身の場所の構造の印。中身の場所が無ければ空文字 */
export async function sigNow(page: Page): Promise<string> {
  return page.evaluate(() => window.__saRec?.sigNow() ?? "");
}

/** since 以後で、読み込み中の印が 0 個かつ構造の印が want と同じ最初のコマの時刻。capMs で見つからなければ -1 */
export async function waitMatch(page: Page, since: number, want: string, capMs: number): Promise<number> {
  try {
    await page.waitForFunction(
      ({ s, w }) => (window.__saRec?.firstMatch(s, w) ?? -1) >= 0,
      { s: since, w: want },
      { timeout: capMs, polling: 100 },
    );
  } catch {
    return -1;
  }
  return page.evaluate(({ s, w }) => window.__saRec?.firstMatch(s, w) ?? -1, { s: since, w: want });
}

/** since 以後で、中身の場所の DOM が最初に変わった時刻。capMs で見つからなければ -1 */
export async function waitMutation(page: Page, since: number, capMs: number): Promise<number> {
  try {
    await page.waitForFunction((s) => (window.__saRec?.firstMutationAfter(s) ?? -1) >= 0, since, {
      timeout: capMs,
      polling: 100,
    });
  } catch {
    return -1;
  }
  return page.evaluate((s) => window.__saRec?.firstMutationAfter(s) ?? -1, since);
}

/** until より前で、中身の場所の DOM が最後に変わった時刻。無ければ -1 */
export async function lastMutationBefore(page: Page, until: number): Promise<number> {
  return page.evaluate((u) => window.__saRec?.lastMutationBefore(u) ?? -1, until);
}

/** 押した時刻（pointerdown の Event.timeStamp）。まだ押していなければ -1 */
export async function pointerAt(page: Page): Promise<number> {
  return page.evaluate(() => window.__saRec?.pointerAt() ?? -1);
}

export type ProbeResult = { passed: number; total: number; maxDiffMs: number };

const PROBE_HTML =
  '<!doctype html><html><body><aside id="sidebar-panel"><a class="sidebar-item" href="#probe">probe</a></aside>' +
  '<main class="app-content"></main></body></html>';

/**
 * 記録係の精度の試し（本番に繋がない・stage0-card.md V0-1）。
 * 戻った時の形 3 つ（部品が少ない・表 200 行・深い入れ子）は、描かれた時刻（Element Timing の renderTime）と記録係の時刻の差を見る。
 * 押した時の形 1 つは、ページの中の時計で書き換えた時刻と、記録係の DOM の変化の時刻・押した時刻の差を見る。差が PROBE_LIMIT_MS 以内で合格。
 * 新しいページで 1 回だけ呼ぶ（同じページで 2 回目を呼ぶと 3/4 になる・審査役の実測）。
 */
export async function runRecorderProbe(page: Page): Promise<ProbeResult> {
  await page.setContent(PROBE_HTML);
  await page.evaluate(RECORDER_SOURCE);
  const diffs: number[] = [];
  for (const shape of ["few", "rows", "deep"] as const) {
    const r = await page.evaluate(
      (s) =>
        new Promise<{ since: number; want: string; changedAt: number }>((resolve) => {
          const main = document.querySelector("main.app-content") as HTMLElement;
          const htmlA =
            s === "few"
              ? '<div class="a-card"></div><div class="a-card"></div><div class="a-card"></div>'
              : s === "rows"
                ? `<table class="a-table"><tbody>${'<tr class="a-row"><td></td><td></td></tr>'.repeat(200)}</tbody></table>`
                : `${'<div class="a-level">'.repeat(10)}${"</div>".repeat(10)}`;
          const mark = '<p elementtiming="probe-a" class="a-mark">x</p>';
          main.innerHTML = mark + htmlA;
          const want = window.__saRec?.sigNow() ?? "";
          main.innerHTML = '<section class="b-page"><p class="b-line"></p></section>';
          const since = performance.now();
          setTimeout(() => {
            main.innerHTML = '<div class="sa-loading-block"></div>';
            setTimeout(() => {
              new PerformanceObserver((list, obs) => {
                for (const e of list.getEntries() as unknown as { identifier: string; renderTime: number }[]) {
                  if (e.identifier === "probe-a") {
                    obs.disconnect();
                    resolve({ since, want, changedAt: e.renderTime });
                  }
                }
              }).observe({ type: "element", buffered: false });
              main.innerHTML = mark + htmlA;
            }, 300);
          }, 200);
        }),
      shape,
    );
    const at = await waitMatch(page, r.since, r.want, 5_000);
    // 記録係は描かれた時刻より数 ms 早く出ることがあるので、差は絶対値で見る
    diffs.push(at < 0 ? Number.POSITIVE_INFINITY : Math.abs(at - r.changedAt));
  }
  await page.evaluate((delay) => {
    const link = document.querySelector("a.sidebar-item") as HTMLElement;
    link.addEventListener(
      "click",
      (e) => {
        e.preventDefault();
        setTimeout(() => {
          const main = document.querySelector("main.app-content") as HTMLElement;
          main.replaceChildren(document.createElement("div"));
          (window as unknown as { __probeChangedAt?: number }).__probeChangedAt = performance.now();
        }, delay);
      },
      { once: true },
    );
  }, PROBE_TAP_DELAY_MS);
  const before = await pointerAt(page);
  await page.click("a.sidebar-item");
  const pointer = await pointerAt(page);
  const mut = pointer > before ? await waitMutation(page, pointer, 5_000) : -1;
  const changedAt = await page.evaluate(
    () => (window as unknown as { __probeChangedAt?: number }).__probeChangedAt ?? -1,
  );
  diffs.push(
    pointer <= before || mut < 0 || changedAt < 0
      ? Number.POSITIVE_INFINITY
      : Math.max(Math.abs(mut - changedAt), Math.abs(changedAt - pointer - PROBE_TAP_DELAY_MS)),
  );
  const passed = diffs.filter((d) => d >= 0 && d <= PROBE_LIMIT_MS).length;
  return { passed, total: diffs.length, maxDiffMs: Math.max(...diffs) };
}
