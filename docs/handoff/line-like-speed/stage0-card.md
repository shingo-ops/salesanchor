# 段 0a 実装カード（画面の中の記録係と、戻った時・押した時の秒の基準）

- 対象: docs/handoff/line-like-speed/design.md §3-4 の段 0・§3-5 の K1・K3・§3-7 のメモリの基準。ADR-1054（Accepted）・ADR-1053・ADR-1051。
- 根拠の写し: S=origin/main 9e2023359（Merge #4946）。行番号はすべてこの sha。実装の前に最新の origin/main で行を合わせ直す（§3(a)）。
- 読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/04-worktree.md・guards/05-pr.md・guards/10-executor.md・scripts/agent-hooks/cloud/rules.md。実行役はクラウドの Sonnet。作業場所の作り方はクラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）を正とする（§4-E）。.pr-number・gh-pr-create-safe.sh は使わない。出力には上限を付ける。待つために sleep を使わない。
- 状態: 第 2 版（第 1 版の審査 REVISE 14 件を反映。審査の報告: origin/release/line-like-speed-stage0-review-v1 の docs/handoff/line-like-speed/review-stage0-card-v1.md）。
- 受領確認: 実装役は着手の最初の報告に「段 0a カード 第 2 版を受け取った・S=9e2023359」と書く。

## 0. 設計からの直し（V0。段 0 の合格線のうち、動画の突き合わせを試しのページに替える（V0-1）。押した時の測り方を 2 通りにする（V0-3）。ほかの線は変えない）
- V0-1 動画の突き合わせをやめる: 設計 §3-4 の段 0 の合格線「試しの 3 画面で、記録係の時刻と動画のコマの時刻の差が 0.05 秒以内」は採れない。
  - 理由: 公開リポジトリなので trace・スクリーンショット・html レポートは作らない（S docs/adr/ADR-1051-prod-ui-black-box-check.md:25）。速さの記録の設定も動画を作らない（S tests/prod-check/page-speed.config.ts:5・:27）。本番の画面の動画には中身が映る。
  - 代わり: 本番に繋がない「試しのページ」（page.setContent で作る空の画面）で変化を起こし、正解の時刻と記録係が出した時刻との差を見る。戻った時の形を 3 つ・押した時の形を 1 つ、計 4 件。すべて差 50 ミリ秒（0.05 秒）以内で合格（§4-A の runRecorderProbe）。
  - 戻った時の形の正解は「描かれた時刻」（Element Timing の renderTime。試しのページの中だけで使う）。記録係のコマの時刻は、requestAnimationFrame の中で読んだ後、MessageChannel で投げて受けた時刻（その回の描く手順の後）にする。審査役の実測: この形で 4 回とも 4/4・差 3〜4.5 ms。わざと見る間隔を 200 ms にすると 1/4 に落ちる（歯がある）。
  - 限界: 画面の外の描き（ラスタ）が重い時は、記録係の時刻より遅れて描かれる（審査役の実測: 影とぼかし付きの要素 2000 個で約 0.24〜0.27 秒の差）。試しは軽い形だけを確かめる。重い画面の K1 は、描かれるのが記録係の時刻より遅れうる（数は甘めに出る）。
  - 精度の試しは毎朝の記録の中でも毎回流す。不合格の朝は戻った時・押した時の秒を出さず、「精度の試しが不合格」と書く（数を出さない。誤った数を基準にしない）。
  - 記録係の重さ: 1 コマ約 0.8 ms（400 要素・審査役の実測）。入れた日から今の秒（K2）が少し動きうる。設計担当は入れる前後の日の秒を比べ、design.md §3-4 に書く。
- V0-2 「A の画面の部品が描かれた」の見分け方（設計 §3-5 K1 で段 0 に決めるとした点）:
  - 構造の印: 中身の場所（S frontend/src/components/DesktopShell.tsx:400 main.app-content・S frontend/src/components/MobileShell.tsx:201 main.mobile-content）の要素を、上から幅優先で最大 400 個・深さ 6 まで並べる。各要素の「タグ名とクラス名（並べ替えたもの）」だけを 1 つの数に縮める。文字・値・属性は読まない。取り直し中の小さな印（.sa-spinner・S frontend/src/components/loading/Spinner.tsx:30・:33）とその中は印に入れない（design §3-2 の「Spinner は K1 を邪魔しない」と合わせる）。
  - 「A が描かれた」= A へ切り替える命令の後で、中身の場所の中の読み込み中の印（S tests/prod-check/settle.ts:13-14 の LOADING_SELECTOR）が 0 個で、構造の印が「A を最初に開き終えた時の構造の印」と同じになった最初のコマ。
  - 測れない時は数を出さず、訳を書く: 行き先 B と A の構造の印が同じ時は「見分けられず（行き先と同じ形）」。A に中身の場所が無い時は「中身の場所が無い」。10 秒のうちに同じにならない時は「10 秒で見分けられず」（時刻で変わる部品などで構造が毎回変わる画面）。
  - B の選び方: その回で測れた・403 なし・道すじが固定（kind ""）の画面のうち、今の秒がいちばん短い画面（A と同じ画面は除く）。無ければ SPEED_TARGETS の最初の kind "" の画面。重い画面を 135 回開かないため・断りの画面同士で同じ形になるのを避けるため。
  - 点検用の人で 403 がある画面の K1 は、中身ではなく断りの画面が戻る秒になる。表は今どおり 403 ありの行を分けて数える（S page-speed.spec.ts:167・:189）。説明の行に書く。
- V0-3 K3 の測り方（2 通り。どちらも道すじが固定の画面 kind ""・94 件すべてを対象にする）:
  - 事実: 今の PC の横のメニューで押せる項目は a.sidebar-item だけで、kind "" の画面は最大 7 件（S DesktopShell.tsx:227-378）。まとめ（S :70-74 button.sidebar-accordion-btn）は項目が空で描かれない（S :201 `const moreItems: NavItem[] = [];`・S :66 の items.length === 0 なら null）。
  - (ア) 横のメニューにある画面: その項目を本当に押す。時間は押した時刻（pointerdown）から、中身の場所の DOM が最初に変わった時刻まで。項目に指を乗せて横のメニューが広がる動き（S :154-158）は数えない。押した後は指を中身の場所へ移して横のメニューを閉じる（S :148-152）。まとめのボタンを開く道は、将来項目が入った時のために残す（今は通らない）。
  - (イ) 横のメニューに無い画面（権限で出ない項目を含む）: アプリの中で画面を切り替える命令（goInApp）の直前の時刻から、中身の場所の DOM が最初に変わった時刻まで。画面の中のリンクを押した時に動く仕組み（react-router が location を読み直して描き直す）と同じ所から測る。押す指の動き（数 ms）は入らない。
  - 表の訳の列に、(イ) で測った行は「命令で切り替え」と書く。合計の行は (ア) と (イ) を分けて数える。
  - 押す前（切り替える前）の 1 秒のうちに中身の場所が動いていた時は、押したせいの変化と分けられないので「押す前も動いていた」と書き、数を出さない。
  - K3 は本体の 135 画面を一巡した後に測るので、どの画面も 2 回目以降に開いた時の秒になる（説明の行に書く）。
  - スマホの下のメニューは段 0a では測らない（速さの記録は PC の画面だけで動く・S page-speed.config.ts:34-37）。
- V0-4 段 0 を 2 つに分ける（変更は一度に 1 つ）: 段 0a=このカード（記録係と基準の記録・tests/prod-check だけ）。段 0b=次のカード（135 画面とファイルの対応表・u1-count.py の流し直し・書類だけ）。段 2 へ進むのは、段 0a と段 0b の両方の受入が合格してから（設計 §3-4 の段 0 の合格線は変えない）。
- V0-5 メモリの基準（設計 §3-7）: 毎朝の記録の最後に、ブラウザの JS ヒープの使用量を 1 つ書く（Chromium だけが持つ performance.memory.usedJSHeapSize）。値は粗く丸められることがある。無ければ「測れず」と書く。段 3 の比べる相手にする。
- V0-6 時間の守り: K1 は本体の 135 画面の巡回の中で測るので、遅いと今の秒（K2）の残りの画面を削りうる。K1 は段の始めから 25 分を過ぎたら「時間切れで未測定」にして、今の秒の巡回（40 分の上限・S page-speed.spec.ts:19・:271）を守る。
  - 見込み（審査役の見積もり・推測を含む）: 今の段 約 3 分 16 秒（1 画面 約 1.45 秒）に、K1 で 1 画面あたり B を開く・A へ戻るの 2 回分（約 6.5 分）、K3 で 94 画面 ×（静けさ 1 秒＋開き終わり 約 1.5 秒）（約 4 分）が足され、合計 約 14 分。悪い時（全画面が 10 秒で見分けられず）は K1 が 25 分で止まり、合計は 40 分（S :19）・試験の上限 45 分（S page-speed.config.ts:19）・段の 46 分（S .github/workflows/prod-ui-check.yml:149）の中に収まる。
- V0-7 本番の読み取りの量: K1 で 1 画面につき B と A を開き直し、K3 でもう 1 回開くので、毎朝の本番への読み取りは今の約 3〜4 倍になる（推測。画面ごとの通信の数は未確認）。ADR-1053 の Negative「135 画面ぶんの読み取りがサーバーの記録に混ざる」は、量が増えるだけで種類（1 日 1 回・読むだけ・点検用の人・書き込みは関所で止める）は変わらない。ADR は直さない。量は A10 で実測して design.md §3-4 に書く。

## 1. 触るファイル（変更前→変更後）
| # | ファイル | 変更前 | 変更後 |
|---|---|---|---|
| 1 | tests/prod-check/screen-recorder.ts | 無い | 新しく作る。記録係の script と読み出し・精度の試し（§4-A） |
| 2 | tests/prod-check/page-speed.spec.ts | 開き終わるまでの秒だけを測る（S :1-323） | 精度の試しの test を足す。各画面で戻った時の秒を測る。最後に押した時の秒とメモリを測る。表に 3 列と説明を足す（§4-B） |
| 3 | docs/handoff/line-like-speed/design.md | 段 0 の合格線に動画の突き合わせ | このカードの V0 を反映済み（設計担当が書いた。実装役は触らない） |
| 4 | docs/handoff/line-like-speed/stage0-card.md | 無い | このカード（設計担当が書いた。実装役は触らない） |

## 2. 触らない範囲
- frontend/・backend/・migrations/・.github/workflows/・scripts/ は触らない。
- tests/prod-check の playwright.config.ts・prod-ui.spec.ts・fixtures.ts・login.ts・settle.ts・page-speed-targets.ts・page-speed.config.ts は触らない。
- page-speed.spec.ts の今の秒の決め方（S :291-312 の navStart と :311 の式）・表の今の 9 列の並びと説明の行（S :170-197）・関所の通す／止めるの判定（S :216-242 の isRead・writesOnRead・authCall と route.continue／fulfill／abort）は変えない。足すのは「数えるか」の切り替えだけ（§4-B(e)）。
- 表に出すのは、道すじの形・秒・数・決まった訳の言葉だけ。構造の印の数そのもの・画面の文字・番号は出さない（ADR-1053:22・:29）。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) 最新の origin/main で、§1 #2 と §2 の行番号が S と同じか。違えば、中身が同じ行に合わせ直して報告に書く。中身が変わっていたら停止して報告する。
- (b) tests/prod-check/page-speed-targets.ts の SPEED_TARGETS が 135 件・kind "" が 94 件か（審査役の数: "" 94・section 25・needs-id 10・carrier 3・redirect 3）。違えば数を報告に書き、そのまま進める（押した時の秒の対象は kind "" の数になる）。
- (c) Context7 で Playwright の次の 4 点を確かめ、出典を報告に書く: page.addInitScript({ content }) が次の画面読み込みから効くこと／page.waitForFunction(fn, arg, { timeout, polling: 数 }) の形／page.evaluate に文字の式を渡せること／locator.count・hover・click・waitFor の形／playwright test の `--output <dir>` で試験の結果の置き場を替えられること。合わなければ、合う形に直して報告に書く。Context7 が使えなければ公式文書（playwright.dev）で確かめ、その旨を書く。
- (d) MDN で次を確かめ、出典を報告に書く: Event.timeStamp と performance.now() が同じ時計か／performance.memory が Chromium だけの値か／Element Timing（elementtiming 属性・PerformanceObserver の type "element"・renderTime）が Chromium にあるか／MessageChannel の受け取りが requestAnimationFrame の後に動く仕事（タスク）になるか。違えば停止して報告する。
- (e) DesktopShell が使われる横幅か: 速さの記録は Desktop Chrome（S page-speed.config.ts:36）。frontend の中で PC とスマホの殻を分ける幅の値を読み、1280 が PC 側か確かめる。PC 側でなければ停止して報告する。
- (f) 自分の写しで Playwright の chromium を入れられるか（§4-D 手順2）。入れられない時・入れても「Executable doesn't exist」で落ちる時は、§4-D 手順4b の一時の設定（/tmp に置く・commit しない）で、置いてある chromium（`ls /opt/pw-browsers` で場所を確かめる）を使って流す（審査役がこのクラウドで 1 passed・1 skipped を確かめた形）。それでも流せなければ、試験を流さずに §4-D の残りを進め、報告に「BLOCKED: chromium を動かせない」と生の出力を書く。

## 4-A. #1 の中身（tests/prod-check/screen-recorder.ts・新しく作る・全文）
```ts
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
```

## 4-B. #2 の中身（tests/prod-check/page-speed.spec.ts の直し）
- (a) import（S :13 の次の行）に足す:
```ts
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
```
- (b) 定数（S :21 の次）に足す:
```ts
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
```
- (c) 型（S :30 の Status の次）と Row（S :31-42）に足す:
```ts
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
```
  Row に `k1Seconds: number | null; k1Note: ExtraNote; k3Seconds: number | null; k3Note: ExtraNote;` を足す。emptyRow（S :106-118）は `k1Seconds: null, k1Note: "", k3Seconds: null, k3Note: ""` を足す。
- (d) goInApp（S :72-79）を、切り替えの命令の直前のページの時計の時刻を返す形にする（ほかの呼び出しは戻り値を使わないので、そのまま動く）:
```ts
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
```
  "命令で切り替え" は失敗の訳ではなく、K3 を (イ) の測り方で測れた印（k3Seconds に数が入る）。
- (e) 関所（S :233-235）と requestfinished（S :246-252）は、数えるかだけを切り替える。止める／通す動きは同じ:
```ts
    const key = `${method} ${pathShape(path)}`;
    if (!extra.on) {
      blocked.set(key, (blocked.get(key) ?? 0) + 1);
      blockedTotal += 1;
    }
```
  requestfinished は、数えるかを await より前（入口）で同期に読む。S :247 の `const bucket = hits;` の次に 2 行足し、S :252 の条件を counted にする:
```ts
    const counted = !extra.on;
    if (!counted) extra.apis += 1;
```
```ts
    if (status === 403 && counted) forbiddenApis.set(shape, (forbiddenApis.get(shape) ?? 0) + 1);
```
  （S :248 の `await req.response()` の後で extra.on を読むと、K1・K3 の通信の終わりが届く前に extra.on が false に戻った時に今の合計に入るため。）
- (f) 戻った時の秒を測る関数を、emptyRow の次に足す:
```ts
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
```
- (g) 押した時の秒を測る関数を、measureReturn の次に足す:
```ts
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
```
- (h) 精度の試しの test を、S :201 の test の前に足す（秘密情報が無くても流れる。実装役が手元で流せる）:
```ts
test("記録係の精度を確かめる（本番に繋がない）", async ({ page }) => {
  const r = await runRecorderProbe(page);
  if (r.passed !== r.total) {
    throw new Error(`記録係の精度の試し: ${r.total} 件中 ${r.passed} 件合格・いちばん大きい差 ${r.maxDiffMs} ms（合格線 ${PROBE_LIMIT_MS} ms）`);
  }
});
```
- (i) 本体の test（S :201-323）に足す:
  - S :242（関所の終わり）の次に、記録係を入れて精度の試しを流す:
```ts
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
```
  - S :312（秒を入れる else の閉じ）と S :313（rows.push）のあいだに、戻った時の秒を足す:
```ts
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
```
  - S :319（for の閉じ）の次に、押した時の秒とメモリを足す（rows は SPEED_TARGETS と同じ順に 1 件ずつ入っている）:
```ts
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
```
  - S :321 の render の呼び出しに `probe, heapMb, extra.apis` を足す。
- (j) render（S :156-199）に足す（今の 9 列と説明の行はそのまま。後ろに足すだけ）:
  - 引数に `probe: ProbeResult, heapMb: number | null, extraApis: number` を足す。`const sec2 = (v: number | null) => (v === null ? "—" : v.toFixed(2));` を足す。
  - 各行の最後に 3 列 `| ${sec2(r.k1Seconds)} | ${sec2(r.k3Seconds)} | ${[r.k1Note, r.k3Note].filter(Boolean).join("・") || "—"} |` を足す。見出しの行に `| 戻った時の秒 | 押して最初の変化の秒 | 戻った時・押した時の訳 |`、区切りの行に `|---|---|---|` を足す。
  - 説明の行（S :181 の次）に足す:
```ts
    "- 戻った時の秒 = 開き終えた画面 A から別の画面 B へ移り、また A へ切り替えた命令から、中身の場所に読み込み中の印が無く、A を開き終えた時と同じ構造（タグとクラス名だけで比べる）が描かれた最初のコマまで（K1）",
    "- 戻った時の秒の行き先 B = その回で測れた・403 なしの画面のうち、いちばん速い画面。403 ありの行の戻った時の秒は、中身ではなく断りの画面が戻る秒",
    "- 押して最初の変化の秒 = 横のメニューにある画面は、項目を押した時刻から、中身の場所が最初に変わった時刻まで（K3）。メニューを開く操作と指を乗せる動きは数えない。横のメニューに無い画面は、アプリの中で切り替える命令の時刻から測り、訳に「命令で切り替え」と書く。道すじが固定の画面だけ。どの画面も 2 回目以降に開いた時の秒",
    "- 記録係を入れた日から、開き終わるまでの秒が少し動きうる（記録係の 1 コマ約 0.8 ms）",
    `- 記録係の精度の試し（本番に繋がない）: ${probe.total} 件中 ${probe.passed} 件合格・いちばん大きい差 ${Number.isFinite(probe.maxDiffMs) ? `${probe.maxDiffMs.toFixed(1)} ms` : "見つからず"}（合格線 ${PROBE_LIMIT_MS} ms）`,
```
  - 最後の合計の行（S :197 の次）に足す:
```ts
  out.push(
    `- 戻った時の秒を測れた画面: ${rows.filter((r) => r.k1Seconds !== null).length}`,
    `- 押して最初の変化の秒を測れた画面: メニューを押した ${rows.filter((r) => r.k3Seconds !== null && r.k3Note !== "命令で切り替え").length}・命令で切り替え ${rows.filter((r) => r.k3Seconds !== null && r.k3Note === "命令で切り替え").length}`,
    `- 戻った時・押した時を測るあいだの API の数（今の表の数とは別）: ${extraApis}`,
    `- ブラウザのメモリ（JS ヒープ・測り終えた時）: ${heapMb === null ? "測れず" : `${heapMb.toFixed(0)} MB`}`,
    "",
  );
```
  ただし S :197 の最後の "" は、この out.push の前で 1 つにまとめる（空行が 2 つ続かないように、S :197 の `""` を消してここに置く）。

## 4-C. 試験
- 精度の試しの test（§4-B(h)）が、実装役の手元で 4 件中 4 件合格すること。
- 本体の test は秘密情報が無いと skip される（S :203）。実装役は本番に繋がない。本番の記録は、マージの後に設計担当が毎朝の記録を手で 1 回動かして確かめる（§5）。

## 4-D. 実装役の手順（1 手順 1 命令。<W> は手順1 で作られた作業場所の絶対パス）
手順1. クラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）どおり、作業場所を作り、push 済みの枝の先頭に合わせる（設計担当が §1 #3・#4 を push 済み）。
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/line-like-speed-stage0
  （出力に出た作業場所の絶対パスを <W> として報告に書く。）
  cd <W> && git fetch origin release/line-like-speed-stage0
  cd <W> && git switch -C release/line-like-speed-stage0 origin/release/line-like-speed-stage0
  cd <W> && git rev-parse HEAD origin/release/line-like-speed-stage0
  （2 行が同じことを確かめる。違えば停止して BLOCKED: で報告する。main は取り込まない。reset・rebase・force・merge・pull は使わない）
手順2. frontend の依存と chromium を入れる。入れられなければ §3(f) に従う。
  cd <W>/frontend && npm ci
  cd <W>/frontend && npx playwright install chromium
手順3. §4-A の全文で <W>/tests/prod-check/screen-recorder.ts を作る。§4-B のとおり <W>/tests/prod-check/page-speed.spec.ts を直す。
手順4. 精度の試しだけを流し、出力をファイルに残す（試験の結果の置き場は /tmp にして、作業場所に残さない）。
  cd <W> && NODE_PATH="<W>/frontend/node_modules" ./frontend/node_modules/.bin/playwright test --config tests/prod-check/page-speed.config.ts --output /tmp/stage0a-results -g "記録係の精度" > /tmp/stage0a-probe.txt 2>&1
  cd <W> && tail -20 /tmp/stage0a-probe.txt
手順4b.（手順4 が「Executable doesn't exist」などで chromium を動かせなかった時だけ）次の一時の設定を /tmp/stage0a.config.ts に書き（commit しない）、手順4・5 の `--config` をこのファイルに替え、命令の頭に `PW_HEADLESS="$(ls -d /opt/pw-browsers/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell | tail -1)"` を足して流す。置いてある chromium の場所は `ls /opt/pw-browsers` で確かめて報告に書く。
```ts
// /tmp/stage0a.config.ts（commit しない）
import base from "<W>/tests/prod-check/page-speed.config.ts";
import { defineConfig } from "@playwright/test";
export default defineConfig({
  ...base,
  testDir: "<W>/tests/prod-check",
  outputDir: "/tmp/stage0a-results",
  projects: base.projects?.map((p) => ({
    ...p,
    use: {
      ...p.use,
      launchOptions: {
        executablePath: process.env.PW_HEADLESS,
      },
    },
  })),
});
```
手順5. 本体の test が秘密情報なしで skip されることを確かめる。
  cd <W> && NODE_PATH="<W>/frontend/node_modules" ./frontend/node_modules/.bin/playwright test --config tests/prod-check/page-speed.config.ts --output /tmp/stage0a-results > /tmp/stage0a-all.txt 2>&1
  cd <W> && tail -20 /tmp/stage0a-all.txt
手順6. 変わったファイルが §1 の #1・#2 だけか確かめる。試験が作る tests/prod-check/test-results/（.last-run.json）が出ていたら add しない（.gitignore に入っていない・審査役の確認）。
  cd <W> && git status --short | head -20
手順7. commit する。
  cd <W> && git add tests/prod-check/screen-recorder.ts tests/prod-check/page-speed.spec.ts
  cd <W> && git commit -m "test: 画面の中の記録係と戻った時・押した時の秒の基準（段0a）"
手順8. commit が在ることを確かめてから push する（--no-verify は使わない。push の前の検査が × なら直してから push。fast-forward でないと断られたら直さず BLOCKED:）。
  cd <W> && git log -3 --oneline
  cd <W> && git push -u origin release/line-like-speed-stage0
手順9. 報告を返す。PR は作らない（設計担当が手元で作る）。報告の 1 つの発言は 600 文字以内にして、番号付きの発言に分ける。

## 4-E. 作業場所の決まり
- 作業場所の作り方は、クラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）を正とする。guards の文書（手元の作業場所の決まり）と違う所は、クラウドの決まりに従う。
- .pr-number・gh-pr-create-safe.sh・gh-pr-merge-safe.sh は使わない。PR の作成・審査・マージは設計担当が手元で行う。

## 4. GO と承認・PO の操作
- PO の実装承認: 設計と ADR-1054 の採用・作り始め（2026-10-31 PO 選択「1」）。このカードの審査合格の後に、設計担当がクラウドの Sonnet へ渡す。
- 触るのは tests/prod-check と書類だけで、migrations・deploy.yml・本番 scripts を含まない（番号付き GO の要る危ない PR ではない）。マージは PO の委任に基づき設計担当（Claude Opus）が、マージ前の審査役の APPROVE の後に行う。
- PO が操作することはない。

## 5. 受入（○×）
| # | 基準 | 検証方法 |
|---|---|---|
| A1 | 精度の試しが手元で 4 件中 4 件合格 | 実装役の /tmp/stage0a-probe.txt の最後の行（passed） |
| A2 | 秘密情報なしで本体の test が skip され、精度の試しが pass | /tmp/stage0a-all.txt に「1 passed」「1 skipped」 |
| A3 | 変わったのは §1 の 4 ファイルだけ | gh pr diff --name-only |
| A4 | 今の秒の式（S :311）・関所の判定（S :225-232）・今の 9 列が変わっていない | gh pr diff で該当行に - が無い（例外: S :252 の 403 を数える条件の 1 行だけは counted に替わる） |
| A5 | マージの後、毎朝の記録を手で 1 回動かし、精度の試しが 4/4 合格と表に出る | 実行記録の要約の「記録係の精度の試し」の行 |
| A6 | 同じ回で、「測れた」行のすべてが「戻った時の秒」に数か訳を持つ。kind "" の「測れた」行のすべてが「押して最初の変化の秒」に数か訳を持つ（メニューを押した・命令で切り替えのどちらか、または失敗の訳） | 要約の表を数える（設計担当） |
| A7 | 同じ回で、画面の速さの段が 40 分の上限の中で終わり、今の秒の列（状態）に「時間切れで未測定」が 0 行。K1 の「時間切れで未測定」の行数は別に数えて書く | 要約の表と段の時間 |
| A8 | 要約に画面の文字・番号・構造の印の数が出ていない | 新しい 3 列が数字・「—」・§4-B(c) の決まった言葉だけ |
| A9 | 同じ回で、メモリの行が MB か「測れず」で出る | 要約の最後の行 |
| A10 | 同じ回で、「戻った時・押した時を測るあいだの API の数」の行が数で出る | 要約の最後の行（V0-7 の読み取りの量の実測） |

- A5〜A10 の回の値を、K1・K3・メモリ・読み取りの量の基準として docs/handoff/line-like-speed/design.md §3-4 に設計担当が書き足す（段 0b のカードと同じ PR にしない）。記録係を入れる前後の日の今の秒も並べて書く（V0-1 の記録係の重さ）。

## 6. 戻し方
- マージの commit を git revert する PR を 1 つ出す。本番の画面・DB には何も入っていないので、戻すのはこの記録だけ。
- 毎朝の記録の段は continue-on-error（S .github/workflows/prod-ui-check.yml:146）なので、この段が失敗しても朝の画面点検の合否と知らせは変わらない。

## 停止と報告
- §3 で「停止」とした時、試験が 4 件中 4 件にならない時、§2 の触らない範囲を変えないと進めない時は、そこで停止する。
- 停止したら、何を実行し何が返ったかの生の出力（/tmp の報告ファイルの tail）を付けて、BLOCKED: か NEEDS_DECISION: で始まる報告を返す。推測で直さない。
- 終わったら DONE: で始まる報告に、§3 の確かめた結果・出典、手順4・5 の tail、push した sha を書く。

END OF CARD
