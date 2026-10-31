# 段 1 実装カード（写しの置き場・取り方・利用者が変わったら消す、の土台と K5 の試験）

- 対象: docs/handoff/line-like-speed/design.md §3-2（部品）・§3-3（触らない範囲）・§3-4 の段 1・§3-5 の K5・§3-7。ADR-1054（Accepted）。
- 根拠の写し: S=origin/main dc99a062e（Merge #4957）。行番号はすべてこの sha。実装の前に最新の origin/main で行を合わせ直す（§3(a)）。
- 読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/04-worktree.md・guards/05-pr.md・guards/10-executor.md・scripts/agent-hooks/cloud/rules.md。照合: 全命令は cd <W> で始める（00-common:5）・出力は tail/head で上限を付ける（00-common:10）・新しいファイルは丸ごとの全文で渡す（03-file:30）・作業場所は new-worktree.sh で作り出力をパイプに通さない（04-worktree:45・:55）・PR は実行役が作らない（05-pr。設計担当が手元で作る）。出力をファイルに残す命令と tail で読む命令は別の行に分けた（00-common:6）。
- 実行役はクラウドの Sonnet。作業場所の作り方はクラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）を正とする。.pr-number・gh-pr-create-safe.sh は使わない。出力には上限を付ける。待つために sleep を使わない。
- 状態: 第 1 版（審査前）。
- 受領確認: 実装役は着手の最初の報告に「段 1 カード 第 1 版を受け取った・S=dc99a062e」と書く。
- 段 1 は画面をまだ変えない。画面が useApiQuery を使い始めるのは段 2 から。

## 0. 設計からの直し・詳しくした点（V1。設計の合格線は変えない）
- V1-1 K5 の「画面の試験」: 段 1 では画面を変えないので、試しの部品（Probe）を本物の QueryClient・QueryAuthSync と一緒に描いて確かめる（§4-F の T4・T5）。本物の画面での K5 は、最初に画面を移す段 2 の受入で同じ流れを確かめる。
- V1-2 消す時刻: QueryAuthSync は useLayoutEffect で消す。理由: 画面の部品が写しを取りに行くのは描いた後の useEffect（passive）の中。useLayoutEffect はそれより先に動くので、新しい人の取りに行く前に消し終わる。React の StrictMode（S frontend/src/main.tsx:9）で 2 回動いても、前と同じ uid なら何もしない。
- V1-3 消した後に新しい人の写しが cache から外れたままにならないこと（消した写しを開いている部品が抱えたまま、取り直しが届かない形）を試験で確かめる（§4-F の T5。取り直しの関数で api.get がもう 1 回呼ばれる）。落ちたら直し方を自分で考えず停止する。
- V1-4 部品の版: `@tanstack/react-query` を **5.104.4 に固定**して入れる（`^` を付けない）。理由: 公開から 2 週間以上たった版にする（5.104.4 は 2026-10-17 公開、5.104.5 は 10-19、5.105.0 は 10-26・npm view の time の値。設計担当が 2026-11-01 に確かめた）。peerDependencies は react ^18 || ^19（docs/handoff/line-like-speed/sources.md C）で、今の react ^18.3.1（S frontend/package.json:86）に合う。
- V1-5 部品の動きの確かめ（設計担当・2026-11-01）: Context7 はこの月の上限で使えなかった（応答「Monthly quota exceeded」）。起動の決まりに従い、公式の文書を直接読んだ。
  - tanstack.com/query/v5/docs/reference/QueryClient: cancelQueries は「Cancels outgoing fetches」・既定 revert true・返す Promise は reject しない。resetQueries は初めの状態に戻し「Active queries among the matched set are then refetched」。clear() は「Clears both the query cache and the mutation cache」。
  - 同 guides/important-defaults: 既定は stale 扱い（staleTime 0）・使われない写しは 5 分で捨てる・失敗は 3 回送り直す。
  - 同 guides/query-invalidation: invalidateQueries は頭の一致（`['todos']` は `['todos', { page: 1 }]` も取り直す）。exact: true の時だけ完全一致。
  - clear() が開いている画面に知らせるかは公式の文書に書いていない（X4 の issue #2157 は知らせないと書く）。だから設計どおり cancel → reset → clear の順にする。clear() は mutation の写しも消すと文書にあるが、設計 §3-2 の順のとおり getMutationCache().clear() も残す（害はない）。

## 1. 触るファイル（変更前→変更後）
| # | ファイル | 変更前 | 変更後 |
|---|---|---|---|
| 1 | frontend/package.json | dependencies に TanStack なし（S :72-92） | `"@tanstack/react-query": "5.104.4"` を 1 行足す（§4-A） |
| 2 | frontend/package-lock.json | 同上 | npm の命令で書き換わる分だけ（手で書かない） |
| 3 | frontend/src/lib/query/apiQuery.ts | 無い | 新しく作る。QueryClient 1 個・path の区切り・key・useApiQuery・invalidateApi（§4-B 全文） |
| 4 | frontend/src/lib/query/QueryAuthSync.tsx | 無い | 新しく作る。利用者が変わったら写しを全部消す（§4-C 全文） |
| 5 | frontend/src/App.tsx | AuthProvider の直下が BrowserRouter（S :151-152・:412-413） | 間に QueryClientProvider と QueryAuthSync を置く（§4-D） |
| 6 | frontend/src/lib/query/apiQuery.test.tsx | 無い | 新しく作る。T1〜T7（§4-F 全文） |
| 7 | docs/handoff/line-like-speed/stage1-card.md | 無い | このカード（設計担当が書いた。実装役は触らない） |
| 8 | docs/handoff/line-like-speed/design.md | §3-4-2 まで | §3-4-3 に段 1 のカードの場所を書き足し済み（設計担当が書いた。実装役は触らない） |
| 9 | .claude-pipeline/active-work.d/release-line-like-speed-stage1-card.md | 無い | 作業の札（設計担当が書いた。実装役は触らない） |

## 2. 触らない範囲
- backend/・migrations/・.github/workflows/・scripts/・tests/prod-check/・frontend/viewer/ は触らない（design §3-3）。
- frontend/src/lib/api.ts（通信・送り直し・401 の扱い）・frontend/src/contexts/AuthContext.tsx・frontend/src/lib/auth/ は触らない。
- 画面（frontend/src/pages/）・部品（frontend/src/components/）・CSS・ja.json・en.json は触らない（段 1 は画面を変えない）。
- App.tsx はルートの中身を変えない。足すのは import 3 行・コメント 1 行・包む 4 行だけ（BrowserRouter とその中の行は字下げが半角空白 2 つ深くなるだけ）。
- QueryClient を apiQuery.ts の外で作らない（試験の中でも作らない。試験は同じ 1 個を使い、毎回 clear する）。
- ブラウザの保存に写しを書く部品（persist）を入れない。staleTime を設定しない（既定 0）。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) 最新の origin/main で、§1 #1 の S :72-92、#5 の S :151-152・:412-413、S frontend/src/lib/api.ts:36・:99-155・:237-250、S frontend/src/contexts/AuthContext.tsx:29-34・:167-191 が S と同じか。行がずれただけなら合わせ直して報告に書く。中身が変わっていたら停止して報告する。
- (b) frontend/package.json に `@tanstack/react-query` がまだ無いこと。もう有れば停止して報告する（誰かが先に入れた）。
- (c) `npm view @tanstack/react-query@5.104.4 version peerDependencies --json` の出力を報告に書く。5.104.4 が無い・react 18 が peer に無い時は停止して報告する。
- (d) frontend/src/lib/query/ がまだ無いこと。有れば停止して報告する。
- (e) 試験で `Response` や `crypto.randomUUID` が無いと落ちたら（jsdom の差）、試験の中の偽の応答は §4-F のとおり素の物（status・ok・json）で作ってあるので、それ以外の原因なら停止して生の出力を報告する。
- (f) T5 が落ちたら（V1-3）、停止して NEEDS_DECISION: で生の出力を返す。消し方を自分で替えない。

## 4-A. #1・#2（部品を入れる）
- 命令は §4-G 手順2。`npm install @tanstack/react-query@5.104.4 --save-exact` で、package.json の dependencies に `"@tanstack/react-query": "5.104.4",` が `"@simplewebauthn/browser"` の次の行に入る（並びは npm が決める）。package-lock.json は npm が書き換えた物をそのまま使う。
- 入れた後、`git diff --stat frontend/package.json` が 1 行足しだけであることを確かめる。ほかの部品の版が変わっていたら停止して報告する。

## 4-B. #3 frontend/src/lib/query/apiQuery.ts（新しく作る・全文）
```ts
/**
 * ADR-1054: 画面が取ったデータの写しの置き場（この 1 か所だけ）。
 * - QueryClient はここで 1 個だけ作る。ほかの場所で作らない。
 * - 取り方は useApiQuery だけ。中で今の api.get を呼ぶ（通信・送り直し・401 の扱いは api.ts のまま）。
 * - 写しは出すだけ。staleTime は既定の 0 のままにし、開くたび・タブに戻るたびに取り直す。
 * - 写しはメモリだけに持つ（ブラウザの保存に書かない）。
 */
import { QueryClient, useQuery, type UseQueryResult } from "@tanstack/react-query";

import { useAuth } from "../../contexts/AuthContext";
import { api } from "../api";

/** 使われない写しを捨てるまでの時間（30 分・ADR-1054。既定の 5 分だと 5 分を過ぎて戻った画面が初回と同じになる） */
const GC_TIME_MS = 30 * 60 * 1000;

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // api.ts が GET を 3 回まで送り直す（api.ts の MAX_RETRIES）。ここでも送り直すと最大 16 回になる
      retry: 0,
      gcTime: GC_TIME_MS,
    },
  },
});

/** path を最初の「?」で分け、前を「/」で区切った言葉（空は捨てる）と後ろ（無ければ空文字）にする。 */
export function splitApiPath(path: string): { words: string[]; query: string } {
  const at = path.indexOf("?");
  const head = at === -1 ? path : path.slice(0, at);
  const query = at === -1 ? "" : path.slice(at + 1);
  return { words: head.split("/").filter((word) => word !== ""), query };
}

/** 写しの名前。例: /companies?status=a → ["api", uid, "companies", { query: "status=a" }] */
export function apiQueryKey(uid: string, path: string): readonly unknown[] {
  const { words, query } = splitApiPath(path);
  return ["api", uid, ...words, { query }];
}

/** 写しを出してから裏で取り直す取り方。ログインしていない間は取りに行かない。 */
export function useApiQuery<T>(path: string, options?: { enabled?: boolean }): UseQueryResult<T> {
  const { user } = useAuth();
  const uid = user?.uid ?? null;
  return useQuery({
    queryKey: apiQueryKey(uid ?? "", path),
    queryFn: () => api.get<T>(path),
    enabled: uid !== null && (options?.enabled ?? true),
  });
}

/**
 * 頭の言葉が同じ写しを全部取り直す（条件や id が違う写しも含む）。
 * 例: invalidateApi(uid, ["companies"]) は /companies?… も /companies/5 も取り直す。
 */
export function invalidateApi(uid: string, head: readonly string[]): Promise<void> {
  const { words } = splitApiPath(head.join("/"));
  return queryClient.invalidateQueries({ queryKey: ["api", uid, ...words] });
}
```

## 4-C. #4 frontend/src/lib/query/QueryAuthSync.tsx（新しく作る・全文）
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
    // clear() だけでは開いている画面に知らせないので、取り消し → 初めに戻す → 消す の順にする
    void queryClient.cancelQueries();
    void queryClient.resetQueries();
    queryClient.clear();
    queryClient.getMutationCache().clear();
  }, [uid, queryClient]);

  return null;
}
```

## 4-D. #5 frontend/src/App.tsx の直し
- import を 3 行足す。S :3 の `import { AuthProvider } from "./contexts/AuthContext";` の次の行に:
```tsx
import { QueryClientProvider } from "@tanstack/react-query";
import { QueryAuthSync } from "./lib/query/QueryAuthSync";
import { queryClient } from "./lib/query/apiQuery";
```
- S :151-152 と S :412-413 を次の形にする（中の S :152-412 の行は、行頭に半角空白 2 つを足すだけ）。
```tsx
    <AuthProvider>
      {/* ADR-1054: 写しの置き場は 1 か所。AuthProvider の内側・BrowserRouter の外側 */}
      <QueryClientProvider client={queryClient}>
        <QueryAuthSync />
        <BrowserRouter>
          …（S :153-411 の中身。行頭に空白 2 つを足すだけ）
        </BrowserRouter>
      </QueryClientProvider>
    </AuthProvider>
```
- 確かめ: `git diff -w origin/main -- frontend/src/App.tsx` で、足した行（import 3 行・コメント 1 行・包む 4 行）だけが出て、消えた行が 0 であること（§5 A4）。

## 4-E. 動きの説明（設計 §3-2 との対応）
- key: `["api", uid, ...言葉, { query }]`（§4-B apiQueryKey）。
- 取り直し: invalidateApi が `["api", uid, ...頭の言葉]` で頭の一致を使う（V1-5 の公式文書）。
- 消す: QueryAuthSync が uid の変化（null を含む）で cancel → reset → clear → mutation の写しを消す（§4-C）。
- 送り直し: TanStack は 0（§4-B）。api.ts の 3 回（S api.ts:36）だけなので、1 回の取りに行きで fetch は最大 4 回（T3）。

## 4-F. #6 frontend/src/lib/query/apiQuery.test.tsx（新しく作る・全文）
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
    const tree = (
      <Tree>
        <Probe path="/companies" testId="k5" />
      </Tree>
    );
    const { rerender } = render(tree);
    await waitFor(() => expect(screen.getByTestId("k5").textContent).toBe("secret-uid-A"));

    let seenA = 0;
    const observer = new MutationObserver(() => {
      if (document.body.textContent?.includes("secret-uid-A")) seenA += 1;
    });
    observer.observe(document.body, { subtree: true, childList: true, characterData: true });

    auth.user = null;
    rerender(tree);
    expect(screen.getByTestId("k5").textContent).toBe("");
    expect(keysWithUid("uid-A")).toBe(0);

    auth.user = { uid: "uid-B" };
    rerender(tree);
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
    const tree = (
      <Tree>
        <Probe path="/companies" testId="sw" />
      </Tree>
    );
    const { rerender } = render(tree);
    await waitFor(() => expect(screen.getByTestId("sw").textContent).toBe("uid-A:/companies"));

    auth.user = { uid: "uid-B" };
    rerender(tree);
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
    const tree = (
      <StrictMode>
        <Tree>
          <Probe path="/companies" testId="same" />
        </Tree>
      </StrictMode>
    );
    const { rerender } = render(tree);
    await waitFor(() => expect(screen.getByTestId("same").textContent).toBe("keep:/companies"));
    auth.user = { uid: "uid-A" };
    rerender(tree);
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
```
- 試験の文字は英語だけにする（frontend/eslint.config.js:31 の local/no-japanese-literal。コメントの日本語は今のファイルと同じく可）。
- 落ちた時に、試験の期待（数・文字）を実装に合わせて書き換えない。§3 の分岐に従う。型の誤り（tsc）で `as never` などの書き方が通らない時だけ、期待を変えずに型の書き方を直してよい（報告に差分を書く）。

## 4-G. 実装役の手順（1 手順 1 命令。<W> は手順1 で作られた作業場所の絶対パス）
手順1. クラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）どおり、作業場所を作り、push 済みの枝の先頭に合わせる（設計担当が §1 #7〜#9 を push 済み）。
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/line-like-speed-stage1-card
  （出力に出た作業場所の絶対パスを <W> として報告に書く。）
  cd <W> && git fetch origin release/line-like-speed-stage1-card
  cd <W> && git switch -C release/line-like-speed-stage1-card origin/release/line-like-speed-stage1-card
  cd <W> && git rev-parse HEAD origin/release/line-like-speed-stage1-card
  （2 行が同じことを確かめる。違えば停止して BLOCKED: で報告する。main は取り込まない。reset・rebase・force・merge・pull は使わない）
手順2. 依存を入れ、TanStack を足す。
  cd <W>/frontend && npm ci > /tmp/stage1-ci.txt 2>&1
  cd <W> && tail -5 /tmp/stage1-ci.txt
  cd <W>/frontend && npm view @tanstack/react-query@5.104.4 version peerDependencies --json
  cd <W>/frontend && npm install @tanstack/react-query@5.104.4 --save-exact > /tmp/stage1-install.txt 2>&1
  cd <W> && tail -5 /tmp/stage1-install.txt
  cd <W> && git diff --stat frontend/package.json frontend/package-lock.json
手順3. §4-B・§4-C・§4-F の全文で #3・#4・#6 を作り、§4-D のとおり #5 を直す。
手順4. 試験を流す（この 1 ファイルだけ・全部の試験・型・lint）。
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/lib/query > /tmp/stage1-unit.txt 2>&1
  cd <W> && tail -30 /tmp/stage1-unit.txt
  cd <W>/frontend && npm run test:unit > /tmp/stage1-unit-all.txt 2>&1
  cd <W> && tail -15 /tmp/stage1-unit-all.txt
  cd <W>/frontend && npx tsc --noEmit -p . > /tmp/stage1-tsc.txt 2>&1
  cd <W> && tail -20 /tmp/stage1-tsc.txt
  cd <W>/frontend && npx eslint --max-warnings=0 src/lib/query src/App.tsx > /tmp/stage1-lint.txt 2>&1
  cd <W> && tail -20 /tmp/stage1-lint.txt
  （tsc が generate:api-types の型が無くて落ちる時は、先に `cd <W>/frontend && npm run generate:api-types` を流してからもう一度。）
手順5. 本番と同じ形で組み立てられるか確かめる。
  cd <W>/frontend && npm run build > /tmp/stage1-build.txt 2>&1
  cd <W> && tail -15 /tmp/stage1-build.txt
手順6. 変わったファイルが §1 の #1〜#6 だけか確かめる（#7〜#9 は設計担当の commit 済み）。
  cd <W> && git status --short | head -20
  cd <W> && git diff -w origin/main -- frontend/src/App.tsx | head -60
手順7. commit する。
  cd <W> && git add frontend/package.json frontend/package-lock.json frontend/src/lib/query/apiQuery.ts frontend/src/lib/query/QueryAuthSync.tsx frontend/src/lib/query/apiQuery.test.tsx frontend/src/App.tsx
  cd <W> && git commit -m "feat: 画面のデータの写しの置き場と利用者が変わったら消す土台（ADR-1054 段1）"
手順8. commit が在ることを確かめてから push する（--no-verify は使わない。push の前の検査が × なら直してから push。fast-forward でないと断られたら直さず BLOCKED:）。
  cd <W> && git log -3 --oneline
  cd <W> && git push -u origin release/line-like-speed-stage1-card
手順9. 報告を返す。PR は作らない（設計担当が手元で作る）。報告の 1 つの発言は 600 文字以内にして、番号付きの発言に分ける。

## 4. GO と承認・PO の操作
- PO の実装承認: 2026-11-01 PO 選択「2」（作業指示書から本番に出すところまで止まらずに進める）。ADR-1054 は Accepted（2026-10-31 PO 選択「1」）。このカードの審査合格の後に、設計担当がクラウドの Sonnet へ渡す。
- 触るのは frontend の部品・画面の土台・試験と書類だけで、migrations・deploy.yml・本番 scripts を含まない（番号付き GO の要る危ない PR ではない）。main へのマージで本番の画面に出る（deploy.yml が main への push で動く・S .github/workflows/deploy.yml の on.push.branches）。マージは PO の委任に基づき設計担当（Claude Opus）が、マージ前の審査役の APPROVE と必須の確認 16 件の pass の後に行う。
- PO が操作することはない。

## 5. 受入（○×）
| # | 基準 | 検証方法 |
|---|---|---|
| A1 | T1〜T7 がすべて合格（K5: A の中身が B のログイン後に DOM に出た回数 0・A の写しの数 0／retry: fetch 4 回／invalidateApi: companies の 4 つが取り直され contacts は取り直されない） | /tmp/stage1-unit.txt の最後（7 passed）と、PR の CI「Lint & Dark Mode Check (ADR-067)」の中の unit-run が success |
| A2 | 全部の画面の試験・型・lint・組み立てが通る | /tmp/stage1-unit-all.txt・stage1-tsc.txt・stage1-lint.txt・stage1-build.txt の最後と、PR の必須の確認 16 件が pass |
| A3 | 変わったのは §1 の 9 ファイルだけ | gh pr diff --name-only |
| A4 | App.tsx は空白を除くと足した行だけ（消えた行 0・ルートの中身は同じ） | git diff -w origin/main -- frontend/src/App.tsx |
| A5 | QueryClient を作るのは apiQuery.ts の 1 か所だけ | `git grep -n "new QueryClient" -- frontend/src` が 1 行 |
| A6 | 写しをブラウザの保存に書く部品が無い・staleTime を設定していない | `git grep -n -i "persist" -- frontend/src/lib/query frontend/package.json` が 0 行、かつ `git grep -n "staleTime:" -- frontend/src` が 0 行 |
| A7 | マージの後、deploy が成功し、本番の画面が開く | deploy.yml の実行の結論 success と時刻。本番 https://app.salesanchor.jp/ を開いて、ログイン画面が出て、ブラウザの誤りの記録に TanStack 由来の誤りが無い（設計担当） |
| A8 | マージの後、毎朝の画面の記録を手で 1 回動かし、135 画面の今の秒（K2）が段 0a の基準から悪化していない・画面の点検の合否が今と同じ | prod-ui-check の実行の要約（設計担当） |

- A7・A8 の結果は docs/handoff/line-like-speed/design.md §3-4 に設計担当が書き足す（次の段のカードと一緒に）。

## 6. 戻し方
- マージの commit を git revert する PR を 1 つ出す。画面はまだ写しを使っていない（useApiQuery を呼ぶ画面 0）ので、戻しても画面の動きは今と同じ。DB には何も入っていない。

## 停止と報告
- §3 で「停止」とした時、試験が 7 件中 7 件にならない時、§2 の触らない範囲を変えないと進めない時は、そこで停止する。
- 停止したら、何を実行し何が返ったかの生の出力（/tmp の報告ファイルの tail）を付けて、BLOCKED: か NEEDS_DECISION: で始まる報告を返す。推測で直さない。
- 終わったら DONE: で始まる報告に、§3 の確かめた結果、手順2・4・5 の tail、push した sha を書く。

END OF CARD
