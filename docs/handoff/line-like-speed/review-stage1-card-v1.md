HEAD: a10c1ba91f2442b2e5548d4c91c7a978229d47fc（origin/release/line-like-speed-stage1-card。S=origin/main=dc99a062e2c409aeb1a851a01b8bd0fa09ac3b64）
判定: REVISE

# 段 1 実装カード 第 1 版の審査（設計審査役・2026-10-31）

- 審査した文書: docs/handoff/line-like-speed/stage1-card.md（以下「カード」）。照合: design.md §3-2〜§3-5・§3-7、docs/adr/ADR-1054-screen-data-cache.md。
- 試した場所: リポジトリの外の写し（`git archive HEAD frontend` を scratchpad に展開）。製品コード・設計文書は変えていない。本番には接続していない。
- 行番号: 「カード:N」は stage1-card.md の行、「試験:N」は §4-F の全文を当てたファイルの行（試験:N = カード:178+N）。S の行は `git show origin/main:<path>` で確かめた。

## 項目 1. カードの全文を当てて流した結果 — ×（そのままでは 7 件中 5 件）

流した命令と結果（node v22.23.4・npm 10.9.9）:

| 命令 | 結果 |
|---|---|
| npm ci | 終了コード 0 |
| npm view @tanstack/react-query@5.104.4 version peerDependencies --json | version 5.104.4・peer は react `^18 \|\| ^19` と @types/react `^18 \|\| ^19` |
| npm install @tanstack/react-query@5.104.4 --save-exact | 終了コード 0。package.json は `"@simplewebauthn/browser"` の次に 1 行足しだけ。package-lock.json は +33 行（node_modules/@tanstack/query-core と node_modules/@tanstack/react-query の 2 つが増えただけ） |
| vitest（カードの全文のまま） | **Tests 2 failed / 5 passed (7)**。T4 と T5 が落ちる |
| tsc --noEmit -p .（カードの全文のまま） | 1 回目は終了コード 2（`src/api/generated/schema` が無い・型を作る前のため）。`npm run generate:api-types` の後は 0 |
| eslint --max-warnings=0 src/lib/query src/App.tsx | 0（カードの全文のまま・直した後とも） |
| npm run build | 0（大きい chunk の警告だけ。今の main と同じ） |

落ちた場所と原因:
- T4: 試験:131（カード:309）`expect(screen.getByTestId("k5").textContent).toBe("")` で、受け取った値は `secret-uid-A`。
- T5: 試験:162（カード:340）の waitFor が `uid-A:/companies` のまま時間切れ。
- 原因（試してわかったこと）: カード:293・:330・:355 で `const tree = (<Tree>…</Tree>)` を 1 回だけ作り、カード:308・:313・:339・:365 の `rerender(tree)` に**同じ要素の物**を渡している。React は前と同じ要素の物を受け取ると下の部品を描き直さない。偽の useAuth（カード:194-196）は `auth.user` という外の値を読むだけなので、`auth.user` を変えても QueryAuthSync と Probe が描き直されず、利用者が変わったことが伝わらない。`tree` を「呼ぶたびに作る関数」に変えただけで（直し 1）、**7 件中 7 件が合格**した。実装の側（§4-B・§4-C）は変えていない。
- T6 も同じ形なので、カードのままでは描き直しが起きず、見かけだけ合格していた（項目 2 の M4b で、直した後は歯があることを確かめた）。

直した後の数（直し 1〜3 を当てた後・9 件）:
- 試験 1 ファイル: **Tests 9 passed (9)**（T1〜T7 と、足した T8・T9）。直し 1 だけでは 7 passed (7)。
- T3 の fetch の回数: **4 回**（試験の中で `fetchMock.mock.calls.length` を出して確かめた。`COUNT_T3_FETCH=4`）。
- T4 の A の中身の出た回数（seenA）: **0 回**（`COUNT_T4_SEENA=0`）。
- npm run test:unit（全部）: Test Files 171 passed (171)・Tests 1942 passed (1942)。注: 写しに backend/ を入れていなかった最初の回は TcgProductImportPanel.test.tsx:127 が `../backend/app/services/tcg_product_import_svc.py` を読めず 1 件落ちた。backend/ を並べると 55 passed (55)。作業場所（リポジトリ全体がある）では起きない。カードの問題ではない。
- tsc: 0・eslint: 0・build: 0。

## 項目 2. 試験に歯があるか — ×（useLayoutEffect を守る試験が無い）

直し 1 を当てた T1〜T7 に対して、1 つずつ壊して流した:

| 壊し方 | 落ちた試験 |
|---|---|
| M1 QueryAuthSync の消す 4 行を外す | T4・T5（A の写しの数が 0 でなく 1）。直し 2・3 の後は T4・T5・T8 |
| M2 useLayoutEffect → useEffect | **どれも落ちない（7 passed）** |
| M3 retry: 0 を外す（既定に戻す） | T3（10 秒の待ちで時間切れ）・T7 |
| 参考 M4 同じ uid なら何もしない 1 行だけ外す | どれも落ちない（StrictMode の初回の 2 回目は写しが空なので害が無い。直す点にはしない） |
| 参考 M4b その 1 行を外し、毎回の描画で消す形にする | T6 |
| 参考 M5 key から uid を外す | T1・T2・T5・T6・T8 |
| 参考 M6 gcTime を外す | T7 |

- M2 が落ちない理由（試してわかったこと）: T4・T5 の Tree（カード:214-221）は QueryAuthSync を Probe より**前**に置く。React は描いた後の useEffect を前の兄弟から順に動かすので、useEffect にしても Probe の取りに行くより先に消える。だから V1-2（カード:13）の「useLayoutEffect で先に消す」の理由を試験が守っていない。
- 足した T8（直し 3）: Probe を QueryAuthSync より**前**に置いて A → B に切り替える。useLayoutEffect ならすべての useEffect より先に消えるので合格。useEffect にすると**B の中身が出ないまま止まる**（`expected '' to be 'uid-B:/companies'`）。これは V1-3（カード:14）が心配した「新しい人の写しが cache から外れたまま」が、useEffect だと実際に起きることを示す。T8 は M1・M2 の両方で落ちる。

## 項目 3. 設計・TanStack 5.104.4 の実物との照合 — ×（1 点食い違いの原因あり。ほかは ○）

| 照らした点 | 結果 | 根拠 |
|---|---|---|
| 部品の置き場（AuthProvider の内側・BrowserRouter の外側・QueryClient 1 個） | ○ | design.md §3-2・カード:150-169。当てた後の `git diff -w` は import 3 行・コメント 1 行・包む 4 行の足しだけで消えた行 0 |
| 消す順 cancel → reset → clear → mutation | ○（設計どおり） | design.md:44・カード:139-143 |
| key の形 `["api", uid, ...言葉, { query }]` | ○ | design.md §3-2・カード:83-94・T1 合格 |
| invalidateApi の頭の一致 | ○ | utils.js:61-66（exact が無ければ partialMatchKey）・utils.js:132-140（配列は要素ごとに比べ、filter の方が短ければ一致）。T2 合格 |
| gcTime 30 分・retry 0・staleTime 未設定 | ○ | カード:72-79・T7 合格。既定は gcTime 3e5（removable.js:35）・retry 3（retryer.js:129）・staleTime 0（query.js:243） |
| V1-5 cancelQueries（既定 revert true・reject しない） | ○ | queryClient.js:303-310 |
| V1-5 resetQueries（初めに戻し、active を取り直す） | ○ | queryClient.js:272-284（query.reset() の後 `refetchQueries({ type: "active" })`） |
| V1-5 clear（query と mutation の両方を消す） | ○ | queryClient.js:717-720。queryCache.clear は各 query を remove（queryCache.js:117-123）し、remove は cache の聞き手に "removed" を送るだけで、開いている画面の observer の状態は変えない（queryCache.js:98-107）。V1-5 の「知らせない」は実物と合う |
| V1-5 invalidateQueries（頭の一致・exact の時だけ完全一致） | ○ | queryClient.js:329-339・utils.js:63-66 |
| **resetQueries を消す時に使う害** | **×** | 下に書く |

resetQueries の害（試してわかったこと）:
- QueryAuthSync の useLayoutEffect が動く時、画面の部品の observer はまだ**前の人の key** に付いている（observer の付け替えは useBaseQuery の useEffect の中・react-query useBaseQuery.js:49）。だから `resetQueries()` は前の人の写しを active と見て、**その場で取り直す**（queryClient.js:280-283）。
- 取り直しの間に api.get が呼ばれた回数を数える試験（T9 の元）で、ログアウトの直後に `api.get("/companies")` が利用者 null のまま **1 回**呼ばれた（記録 `["uid-A:/companies","--logout","null:/companies","--loginB","uid-B:/companies"]`）。T4 の偽の api.get（カード:286-292）はこの呼び出しも `releases` に積むので、カード:315 の `waitFor(releases.length > 0)` は B の取りに行きでなくこの呼び出しでも満たされる。
- 本番で何が起きるか（コードから読める道。実地は未確認）: Firebase の時は getAccessToken が「ログインしていない」で投げる（S frontend/src/lib/auth/selfAuth.ts:163-167）だけで通信は無い。自社ログインの時は ensureSelfToken → selfRefresh（selfAuth.ts:144-147）で /auth/refresh を送る。更新用 Cookie がまだ有効なまま expireSession になる道（S api.ts:96-100 の「refresh は通ったが送り直しも 401」）では、refresh が通ると adoptAccessToken → notify（selfAuth.ts:61-63）で**ログインし直した状態に戻る**。段 1 では useApiQuery を使う画面が 0 なので起きない。段 2 で画面を移すと起き得る。
- 直し方（直し 2）: `resetQueries()` を、各写しを初めに戻すだけで取り直さない `getQueryCache().getAll().forEach((query) => query.reset())` に替える。Query.reset は公開の型にある（query-core の型 `declare class Query` の `reset(): void`）、中身は `destroy()` の後 `setState(resetState)`（query.js:165-168）で、開いている observer に知らせる点は resetQueries と同じ（X4 の狙いは残る）。替えた後、上の記録は `["uid-A:/companies","--logout","--loginB","uid-B:/companies"]` になり、9 件すべて合格・tsc 0・eslint 0。カードのままの QueryAuthSync に T9 を当てると `expected "get" to not be called at all, but actually been called 1 times` で落ちる。
- この直しは design.md:44 の「cancelQueries → resetQueries → clear」の言い方を変える。設計の書き直しは設計担当の仕事なので、design.md §3-2 の該当の行も同じ便で直すこと（直す点 2）。

## 項目 4. api.ts の送り直しと T3 の偽の応答 — ○

- 送り直しは GET だけ 3 回（S frontend/src/lib/api.ts:36 MAX_RETRIES=3・:108-109）。503 は RETRYABLE_STATUS（:34）なので、待ち 500・1000・2000 ms（:114-117）の後に計 4 回。T3 の実測 4 回と合う。
- 偽の応答から読む物: `res.status`（:83・:134・:149）、`res.ok`（:139）、`res.json()`（:140・:150）だけ。fetchWithReauth（:81-102）は 401 で自社ログインの時だけ `init.headers`（送る側の物）を読む。応答の headers・text・blob は request の道では読まない（requestBlob は :170 以降の別の関数）。○。
- 行の指し方の小さなずれ: カード:44 の「api.ts:99-155」は fetchWithReauth の終わり（:99-102）から request の途中（:155）までで、request の全体は S :104-167。直す点 5。
- 試験の中の偽でないもの: getClientId（S frontend/src/lib/realtime/clientId.ts:2 で crypto.randomUUID）は本物のまま動いた。§3(e) の心配は起きなかった。

## 項目 5. 触らない範囲・分岐・手順がクラウドで動くか — △（動くが 3 点足りない）

- §2 触らない範囲: 当てたのは §1 #1〜#6 の 6 ファイルだけで、§2 の場所は 1 つも変えずに 9 件合格・build 合格した。○。
- §3(a): S の行を確かめた。App.tsx :3・:151-152・:412-413・main.tsx:9（`<React.StrictMode>`）・AuthContext.tsx:29-34・:53・:167 は合う。package.json の dependencies は **S :71-91**（:71 が `"dependencies": {`・:91 が閉じ）で、カード:25・:44 の :72-92 は 1 行ずれ。直す点 5。
- §3(b)(d): S に @tanstack も frontend/src/lib/query/ も無い。○。
- §3(c): 出力に @types/react の peer も出る。今の @types/react は ^18.3.18（S frontend/package.json:102）で合う。カード:15・:46 は react だけを条件にしている。直す点 6。
- §4-G 手順1: このクラウドで `bash scripts/new-worktree.sh release/line-like-speed-stage1-review-v1` を流し、作業場所 /root/worktrees/salesanchor/release-line-like-speed-stage1-review-v1 ができた（警告「本店が main 以外（HEAD）」は出たが続行）。その中で `git switch -C … origin/release/line-like-speed-stage1-card` の後、HEAD と origin の 2 行が a10c1ba91 で一致した。○。
- §4-G 手順2: npm ci・npm view・npm install は上の表のとおり動いた。○。
- §4-G 手順4: 手を付けたばかりの作業場所では schema.d.ts が無いので（.gitignore:128 で frontend/src/api/generated/ を除く）、tsc は**必ず**1 回落ちる。カード:408 は「落ちる時は」と条件にしているが、毎回のことなので、手順4 の前に必ず流す形にする。build（`tsc && vite build`・S frontend/package.json:8）も同じ型が要る。直す点 7。
- 起動前の確かめ: AGENTS.md「作業の型」は実行役に `./scripts/dev/executor-preflight.sh || exit 1` を求めるが、カードに手順が無い。このクラウドで流すと `[FAIL] gh auth switch --hostname github.com --user shingo-cc に失敗` で `PREFLIGHT FAIL` になる（gh の名義がクラウドに無いため）。クラウドの実行役がこれをどう扱うかはカードにも cloud/rules.md にも書いていない（未確認）。直す点 8。
- 手順7・8 の commit・push は流していない（指示どおり）。

## 項目 6. card-lint — ○

- `bash scripts/card-lint.sh docs/handoff/line-like-speed/stage1-card.md` の出力は 1 行で、終了コード 0: `L24 警告 1行200字超が 27件（閾値は暫定・止めない）`。

## 項目 7. 新しい抜け・矛盾と、実装役に渡せるか — 今のままでは渡せない

- 渡せない理由: カードの全文どおりに作ると T4・T5 が落ち、カード:446 の「7 件中 7 件にならない時は停止」で実装役は止まる。原因は試験の書き方（項目 1）で、実装役は §4-F の期待を変えられない（カード:381）ので自分では進めない。
- 抜け 1（項目 2）: V1-2 の useLayoutEffect を守る試験が無い。
- 抜け 2（項目 3）: resetQueries がログアウトの直後に前の人の写しを取り直す。段 2 以降で自社ログインの「ログインし直し」につながる道がコードから読める（実地は未確認）。
- 抜け 3（小）: T4 の seenA は MutationObserver の知らせが来た時の body 全体を見る（カード:302-304）ので、同じ一続きの描き直しの中で出て消えた A は数えない。A が DOM に出ないことの主な守りは key の uid（M5 で 5 件落ちる）と、A の写しの数 0（keysWithUid）なので、今回は直す点にしない。
- 矛盾は、設計 §3-2 の「resetQueries」とカードの直し 2 の食い違い（直す点 2 で設計も同時に直す）のほかに見つけていない。

## 直す点（8 件）

1. **§4-F の tree を、呼ぶたびに作る関数にする**（カード:293・:298・:308・:313・:330・:335・:339・:355・:362・:365）。`const tree = (` → `const tree = () => (`、`render(tree)` → `render(tree())`、`rerender(tree)` → `rerender(tree())`。理由は項目 1。全文は下の「直した後の試験の全文」。
2. **§4-C の `void queryClient.resetQueries();`（カード:141）を `queryClient.getQueryCache().getAll().forEach((query) => query.reset());` に替える**。コメント（カード:139）も「取り消し → 写しを初めに戻す（開いている画面に知らせる・取り直さない）→ 消す」に直す。V1-5 に「resetQueries は active を取り直す（queryClient.js:280-283）ので使わない。Query.reset（query.js:165-168）で知らせだけ行う」を書き足す。§4-E（カード:174）の「cancel → reset → clear」も同じ言い方に直す。**design.md:44 の順の言い方も設計担当が同じ便で直す**（ADR-1054:19 の「開いている画面に知らせる順で写しを全部消す」は変わらないので ADR は直さなくてよい）。全文は下の「直した後の QueryAuthSync の全文」。
3. **§4-F に T8 と T9 を足す**（全文に入れた）。T8 = Probe を QueryAuthSync より前に置いて A → B（useLayoutEffect の歯）。T9 = ログアウトの後 50 ms の間に api.get が 0 回・取りに行き中の写し 0（直し 2 の歯）。
4. **件数を 7 → 9 に直す**: カード:30「T1〜T7」→「T1〜T9」、カード:180、カード:431（A1 の「7 passed」→「9 passed」と、T8・T9 の中身を足す）、カード:446「7 件中 7 件」→「9 件中 9 件」、カード:12 の V1-1 に T8・T9 を足す。
5. **行の指し方を直す**: カード:25・:44 の package.json「S :72-92」→「S :71-91」。カード:44 の api.ts「:99-155」→「:81-167」（fetchWithReauth と request の全体）。
6. **peer の条件に @types/react を足す**: カード:15 と §3(c)（カード:46）に「@types/react ^18 || ^19 で、今の ^18.3.18（S frontend/package.json:102）に合う。どちらかが外れたら停止」。
7. **§4-G 手順4 の先頭に 1 行足す**（条件つきの注をやめる）: `cd <W>/frontend && npm run generate:api-types > /tmp/stage1-gen.txt 2>&1` と `cd <W> && tail -3 /tmp/stage1-gen.txt`。カード:408 の注は消す。作ったファイルは .gitignore:128 で commit に入らないことも書く。
8. **起動前の確かめを書く**: §4-G 手順1 の後に `cd <W> && ./scripts/dev/executor-preflight.sh > /tmp/stage1-preflight.txt 2>&1` と tail を足し、クラウドで gh の名義の段だけが FAIL になる時にどうするか（続けてよいか・止めるか）を設計担当が決めて書く。今のクラウドでは `[FAIL] gh auth switch … shingo-cc に失敗` になる（項目 5）。

## 直した後の QueryAuthSync の全文（直し 2。§4-C をこれに替える）
```tsx
/**
 * ADR-1054: 利用者が変わったら（ログアウトを含む）写しを全部消す。画面は描かない。
 * user の変化は、Firebase の onAuthStateChanged・自社ログインの subscribeSession・
 * api.ts の 401 → expireSession の 3 つの道すべてから AuthContext の user に届く。
 * 画面の部品が取りに行く（描いた後の useEffect）より先に消すため、useLayoutEffect を使う。
 */
import { useLayoutEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../../contexts/AuthContext";

export function QueryAuthSync(): null {
  const { user } = useAuth();
  const uid = user?.uid ?? null;
  const queryClient = useQueryClient();
  const previousUid = useRef(uid);

  useLayoutEffect(() => {
    if (previousUid.current === uid) return;
    previousUid.current = uid;
    // clear() だけでは開いている画面に知らせないので、取り消し → 写しを初めに戻す → 消す の順にする。
    // resetQueries() は開いている写しをその場で取り直す（前の人の key で通信が出る）ので使わず、
    // 各写しの reset() で開いている画面に知らせるだけにする。
    void queryClient.cancelQueries();
    queryClient.getQueryCache().getAll().forEach((query) => query.reset());
    queryClient.clear();
    queryClient.getMutationCache().clear();
  }, [uid, queryClient]);

  return null;
}
```

## 直した後の試験の全文（直し 1・3。§4-F をこれに替える）
```tsx
/**
 * ADR-1054 段 1: 写しの置き場の土台の試験（T1〜T7）。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import { StrictMode, type ReactNode } from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "../api";
import { QueryAuthSync } from "./QueryAuthSync";
import { apiQueryKey, invalidateApi, queryClient, splitApiPath, useApiQuery } from "./apiQuery";

const auth = vi.hoisted(() => ({ user: { uid: "uid-A" } as { uid: string } | null }));

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: auth.user, loading: false }),
}));
vi.mock("../auth/provider", () => ({ isSelfAuth: () => false }));
vi.mock("../auth/selfAuth", () => ({
  getAccessToken: async () => "test-token",
  expireSession: vi.fn(),
  selfRefresh: vi.fn(),
}));

function Probe({ path, testId }: { path: string; testId: string }) {
  const q = useApiQuery<string>(path);
  return (
    <div>
      <div data-testid={testId}>{q.data ?? ""}</div>
      <div data-testid={`${testId}-status`}>{q.status}</div>
    </div>
  );
}

function Tree({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <QueryAuthSync />
      {children}
    </QueryClientProvider>
  );
}

function keysWithUid(uid: string): number {
  return queryClient
    .getQueryCache()
    .getAll()
    .filter((query) => query.queryKey[1] === uid).length;
}

afterEach(() => {
  queryClient.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  auth.user = { uid: "uid-A" };
});

describe("splitApiPath / apiQueryKey (T1)", () => {
  it("splits words and query like design §3-2", () => {
    expect(apiQueryKey("u", "/companies?status=a")).toEqual(["api", "u", "companies", { query: "status=a" }]);
    expect(apiQueryKey("u", "/companies/5")).toEqual(["api", "u", "companies", "5", { query: "" }]);
    expect(splitApiPath("//companies/")).toEqual({ words: ["companies"], query: "" });
    expect(splitApiPath("/a?b?c")).toEqual({ words: ["a"], query: "b?c" });
  });
});

describe("invalidateApi (T2)", () => {
  it("refetches all 4 companies copies and not contacts", async () => {
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) => `data:${path}` as never);
    const paths = ["/companies?status=a", "/companies?status=b", "/companies/5", "/companies/6", "/contacts?x=1"];
    render(
      <Tree>
        {paths.map((path, i) => (
          <Probe key={path} path={path} testId={`p${i}`} />
        ))}
      </Tree>,
    );
    for (let i = 0; i < paths.length; i++) {
      await waitFor(() => expect(screen.getByTestId(`p${i}`).textContent).toBe(`data:${paths[i]}`));
    }
    spy.mockClear();
    await act(async () => {
      await invalidateApi("uid-A", ["companies"]);
    });
    const called = spy.mock.calls.map((call) => call[0]).sort();
    expect(called).toEqual(paths.slice(0, 4).sort());
  });
});

describe("retry (T3)", () => {
  it("one failing request calls fetch at most 4 times", async () => {
    const fetchMock = vi.fn(async () => ({ status: 503, ok: false, json: async () => ({}) }) as unknown as Response);
    vi.stubGlobal("fetch", fetchMock);
    render(
      <Tree>
        <Probe path="/retry-check" testId="r" />
      </Tree>,
    );
    await waitFor(() => expect(screen.getByTestId("r-status").textContent).toBe("error"), { timeout: 10_000 });
    expect(fetchMock).toHaveBeenCalledTimes(4);
  }, 15_000);
});

describe("K5: user change clears copies (T4)", () => {
  it("A -> logout -> B never shows A's content", async () => {
    const releases: Array<() => void> = [];
    vi.spyOn(api, "get").mockImplementation(async () => {
      const uid = auth.user?.uid;
      if (uid === "uid-A") return `secret-${uid}` as never;
      return new Promise((resolve) => {
        releases.push(() => resolve(`secret-${uid}` as never));
      }) as never;
    });
    const tree = () => (
      <Tree>
        <Probe path="/companies" testId="k5" />
      </Tree>
    );
    const { rerender } = render(tree());
    await waitFor(() => expect(screen.getByTestId("k5").textContent).toBe("secret-uid-A"));

    let seenA = 0;
    const observer = new MutationObserver(() => {
      if (document.body.textContent?.includes("secret-uid-A")) seenA += 1;
    });
    observer.observe(document.body, { subtree: true, childList: true, characterData: true });

    auth.user = null;
    rerender(tree());
    expect(screen.getByTestId("k5").textContent).toBe("");
    expect(keysWithUid("uid-A")).toBe(0);

    auth.user = { uid: "uid-B" };
    rerender(tree());
    expect(screen.getByTestId("k5").textContent).toBe("");
    await waitFor(() => expect(releases.length).toBeGreaterThan(0));
    act(() => {
      releases.forEach((release) => release());
    });
    await waitFor(() => expect(screen.getByTestId("k5").textContent).toBe("secret-uid-B"));

    observer.disconnect();
    expect(seenA).toBe(0);
    expect(keysWithUid("uid-A")).toBe(0);
  });
});

describe("direct switch A -> B keeps B reachable (T5)", () => {
  it("after switching, invalidateApi for B refetches B", async () => {
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) => `${auth.user?.uid}:${path}` as never);
    const tree = () => (
      <Tree>
        <Probe path="/companies" testId="sw" />
      </Tree>
    );
    const { rerender } = render(tree());
    await waitFor(() => expect(screen.getByTestId("sw").textContent).toBe("uid-A:/companies"));

    auth.user = { uid: "uid-B" };
    rerender(tree());
    await waitFor(() => expect(screen.getByTestId("sw").textContent).toBe("uid-B:/companies"));
    expect(keysWithUid("uid-A")).toBe(0);
    expect(keysWithUid("uid-B")).toBe(1);

    spy.mockClear();
    await act(async () => {
      await invalidateApi("uid-B", ["companies"]);
    });
    expect(spy).toHaveBeenCalledWith("/companies");
  });
});

describe("same user does not clear (T6)", () => {
  it("rerender with the same uid under StrictMode keeps the copy", async () => {
    vi.spyOn(api, "get").mockImplementation(async (path: string) => `keep:${path}` as never);
    const tree = () => (
      <StrictMode>
        <Tree>
          <Probe path="/companies" testId="same" />
        </Tree>
      </StrictMode>
    );
    const { rerender } = render(tree());
    await waitFor(() => expect(screen.getByTestId("same").textContent).toBe("keep:/companies"));
    auth.user = { uid: "uid-A" };
    rerender(tree());
    expect(screen.getByTestId("same").textContent).toBe("keep:/companies");
    expect(keysWithUid("uid-A")).toBe(1);
  });
});

describe("defaults (T7)", () => {
  it("retry 0, gcTime 30 min, staleTime not set", () => {
    const defaults = queryClient.getDefaultOptions().queries;
    expect(defaults?.retry).toBe(0);
    expect(defaults?.gcTime).toBe(30 * 60 * 1000);
    expect(defaults?.staleTime).toBeUndefined();
  });
});

describe("clear runs before any passive effect (T8)", () => {
  it("a reader placed before QueryAuthSync still gets B after A -> B", async () => {
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) => `${auth.user?.uid}:${path}` as never);
    const tree = () => (
      <QueryClientProvider client={queryClient}>
        <Probe path="/companies" testId="early" />
        <QueryAuthSync />
      </QueryClientProvider>
    );
    const { rerender } = render(tree());
    await waitFor(() => expect(screen.getByTestId("early").textContent).toBe("uid-A:/companies"));

    auth.user = { uid: "uid-B" };
    rerender(tree());
    await waitFor(() => expect(screen.getByTestId("early").textContent).toBe("uid-B:/companies"));
    expect(keysWithUid("uid-A")).toBe(0);
    expect(keysWithUid("uid-B")).toBe(1);

    spy.mockClear();
    await act(async () => {
      await invalidateApi("uid-B", ["companies"]);
    });
    expect(spy).toHaveBeenCalledWith("/companies");
  });
});

describe("logout does not refetch the old user's copies (T9)", () => {
  it("api.get is not called between logout and the next login", async () => {
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) => `${auth.user?.uid}:${path}` as never);
    const tree = () => (
      <Tree>
        <Probe path="/companies" testId="nofetch" />
      </Tree>
    );
    const { rerender } = render(tree());
    await waitFor(() => expect(screen.getByTestId("nofetch").textContent).toBe("uid-A:/companies"));
    spy.mockClear();

    auth.user = null;
    rerender(tree());
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });
    expect(spy).not.toHaveBeenCalled();
    expect(queryClient.getQueryCache().getAll().filter((query) => query.state.fetchStatus === "fetching").length).toBe(0);
  });
});
```

- §4-B（apiQuery.ts）と §4-D（App.tsx の直し）は変えずに、上の 2 つと合わせて 9 passed (9)・tsc 0・eslint 0・build 0・npm run test:unit 1942 passed を確かめた。

## 見張りに止められた文面

- なし（この審査の間に止められた命令は無かった）。
