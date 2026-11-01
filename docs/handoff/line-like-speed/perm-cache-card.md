# 権限の写しカード（権限を読む部品 usePermissions を写しの置き場に載せる）

- 対象: docs/handoff/line-like-speed/design.md §3-2（部品）・§3-4-6（段 2 の受入で B5 が 5 行中 4 行不合格・遅い理由の仮説）・§3-5 の K1・K5。ADR-1054（Accepted）。
- 根拠の写し: S=origin/main fbee46fce（Merge #4980）。行番号はすべてこの sha。実装の前に最新の origin/main で行を合わせ直す（§3(a)）。
- 読んだ節: 段 2 カード（docs/handoff/line-like-speed/stage2-card.md）と同じ節（guards/00-common.md・03-file.md・04-worktree.md・05-pr.md・10-executor.md・scripts/agent-hooks/cloud/rules.md）。照合も同じ: 全命令は cd <W> で始める・出力は tail/head で上限・変えるファイルは丸ごとの全文・作業場所は new-worktree.sh で作り出力をパイプに通さない・PR は実行役が作らない・出力をファイルに残す命令と tail で読む命令は別の行。
- 実行役はクラウドの Sonnet。作業場所の作り方はクラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）を正とする。.pr-number・gh-pr-create-safe.sh は使わない。待つために sleep を使わない。
- 状態: 第 2 版。第 1 版の審査（2026-11-01 クラウドの Opus・REVISE）の指摘 3 つを直した。(1) 8 本目の reload は結果を waitFor で待つ。(2) test-setup.ts は変えない（§1 から外し、写しを消すのは usePermissions.test.ts の中だけにした）。(3) 使い手の数を 53 行に直した。
- 受領確認: 実装役は着手の最初の報告に「権限の写しカード 第 2 版を受け取った・S=fbee46fce」と書く。

## 0. 何のための変更か（設計の合格線は変えない）
- P1 段 2 の受入（design §3-4-6）で、戻った時の秒（K1）が 0.1 秒を超えたのは 5 行中 4 行。4 行とも、画面か外側の枠が権限で出し分ける部分を描く（SuppliersPage.tsx・CompaniesPage.tsx・ManagementCenterPage.tsx・CustomerHubPage.tsx が usePermissions を使う）。速かった 1 行（/admin/channel-masters）は usePermissions を使わない。
- P2 今の usePermissions（S frontend/src/hooks/usePermissions.ts:16-53）は、写しを使わず、部品が出るたびに useState の空の Set から始めて useEffect で /me/permissions を取り直す。このため戻った時も、通信が返るまで権限で出す部分が無い。
- P3 仮説（まだ確かめていない）: usePermissions を写しの置き場（useApiQuery・S frontend/src/lib/query/apiQuery.ts:51-73）に載せると、戻った時の最初の描画に前の権限が出て、4 行の K1 が 0.1 秒以下になる。確かめ方は §5 C4。4 行が下がらなければ仮説は誤りと記録して止まる。
- P4 権限の写しの名前は ["api", uid, "me", "permissions", { query: "" }]（S apiQueryKey・apiQuery.ts:41-44）。利用者（uid）ごとに分かれる。利用者が変わると QueryAuthSync が写しを全部消す（S frontend/src/lib/query/QueryAuthSync.tsx:18-28）。api.ts は会社を選ぶ見出しを送らない（S frontend/src/lib/api.ts:61 は X-Client-Id だけ）。このため同じ uid で別の会社の権限が混ざる道は無い。
- P5 usePermissions を使う部品は、どれもログインの後にしか描かれない。外側の枠 DesktopShell・MobileShell と SecretaryChat は ProtectedRoute の内側（S frontend/src/App.tsx:182-187・:147-149）。ProtectedRoute は user が無い間は中身を描かない（S frontend/src/components/ProtectedRoute.tsx:15-21）。このため「ログインしていない間は取りに行かない（loading が true のまま）」の振る舞いは画面に出ない。
- P6 返す形（permissions・loading・error・hasPermission・hasAny・reload）は変えない。使い手 53 行（`git grep -n 'usePermissions()' -- frontend/src ':!*.test.*'` の行数）は触らない。違いは 2 つだけ。(1) 取り直しの間は loading が true に戻らない（写しを出したまま裏で取る）。(2) 取り直しが失敗しても前の権限は消えない。
- P7 前の試験の写しが次の試験に残らないよう、usePermissions.test.ts の afterEach で写しの置き場（queryClient）を消す。試験の共通の準備（S frontend/src/test-setup.ts）は変えない。理由（第 1 版の審査で実測）: 共通の準備の afterEach で apiQuery を読むと api.ts が `../i18n` を読み込み、react-i18next を差し替えたほかの 8 ファイル 52 本が落ちた（main では 0 本）。usePermissions.test.ts の中だけで消す形では、全部の試験 1979 本が通った。ほかの試験ファイルの中で写しが次の試験に残り得る点は、次の段の課題として design.md に残す。

## 1. 触るファイル（変更前→変更後）
| # | ファイル | 変更前 | 変更後 |
|---|---|---|---|
| 1 | frontend/src/hooks/usePermissions.ts | useState と useEffect で毎回取る（S 全 53 行） | useApiQuery で取る（§4-A 全文） |
| 2 | frontend/src/hooks/usePermissions.test.ts | 9 本（S 全 120 行） | 12 本（§4-B 全文） |
| 3 | docs/handoff/line-like-speed/perm-cache-card.md | 無い | このカード（設計担当が書いた。実装役は触らない） |
| 4 | docs/handoff/line-like-speed/design.md | §3-4-6 まで | §3-4-7 にこのカードの場所を書き足し済み（設計担当。実装役は触らない） |
| 5 | .claude-pipeline/active-work.d/release-line-like-speed-perm-cache.md | 無い | 作業の札（設計担当。実装役は触らない） |

## 2. 触らない範囲
- backend/・migrations/・.github/workflows/・scripts/・tests/prod-check/・frontend/viewer/ は触らない。
- frontend/src/test-setup.ts・frontend/src/lib/query/（apiQuery.ts・QueryAuthSync.tsx）・frontend/src/lib/api.ts・frontend/src/contexts/AuthContext.tsx・frontend/src/App.tsx は触らない。
- usePermissions の使い手（画面・枠・SecretaryChat）は 1 本も変えない。ほかの試験ファイルも変えない。
- /me/permissions を別に取る useFeatures.ts・useSuperAdmin.ts・GoalSettingPage.tsx は、このカードでは変えない（次の段の候補）。
- components/・CSS・ja.json・en.json は触らない。新しい言葉・色・寸法を足さない。
- QueryClient を作らない。staleTime を設定しない。写しをブラウザの保存に書かない。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) 最新の origin/main で、§1 #1〜#2・frontend/src/test-setup.ts・frontend/src/lib/query/ が S と同じか（`git diff --stat fbee46fce origin/main -- frontend/src/hooks/usePermissions.ts frontend/src/hooks/usePermissions.test.ts frontend/src/test-setup.ts frontend/src/lib/query` が空か）。空でなければ停止して報告する。
- (b) `cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json` が `"5.104.4"` の 1 行。違えば停止して報告する。
- (c) `cd <W> && git grep -n -E "vi\.mock\(['\"]@tanstack" -- frontend/src | head -5` が 0 行。1 行でもあれば停止して NEEDS_DECISION: で返す（その試験では写しの置き場が差し替わり、§4-B の afterEach が別の物を消す）。
- (d) 手順 4 の全部の試験で、§1 #2 のほかの試験ファイルが落ちたら、試験もコードも直さずに停止し、NEEDS_DECISION: で落ちた試験の名前と生の出力（tail）を返す。理由: 落ちる理由が「前の試験の写しが残った」か「同じ画面の 2 つの部品が 1 回の通信を分け合うようになった（get の回数が減った）」かを、設計担当が見て決めるため。
- (e) §4-B の 12 本のどれかが落ちたら、試験を書き換えて通さない。§4-A・§4-B の写し違いを探し、写し違いが無ければ停止して NEEDS_DECISION: で生の出力を返す。とくに K5 の試験（12 本目）は、落ちたら直し方を自分で考えずに停止する。
- (f) 手順 2 で、変える前の lint の警告の数を数えておく。変えた後は、その数より増えないこと。増えたら直す。直せない時は停止する。

## 4-A. #1 frontend/src/hooks/usePermissions.ts（全文で置き換える）
```ts
/**
 * 現在のユーザーの有効権限をAPIから取得し、キャッシュするフック。
 * UIのメニュー・ボタン表示制御に使用する。
 *
 * 変更履歴:
 *   2026-04-16: 初版作成（Phase 1）
 *   2026-11-01: 写しの置き場（useApiQuery）に載せた（ADR-1054）。戻った時は前の権限を先に出し、裏で取り直す。
 */

import { useCallback, useMemo } from "react";
import { useApiQuery } from "../lib/query/apiQuery";

interface PermissionsResponse {
  permissions: string[];
}

export function usePermissions() {
  const { data, isPending, error: queryError, refetch } = useApiQuery<PermissionsResponse>("/me/permissions");

  const permissions = useMemo(() => new Set(data?.permissions ?? []), [data]);
  const loading = isPending;

  let error: string | null = null;
  if (queryError) {
    // eslint-disable-next-line local/no-japanese-literal -- TODO: i18n対応（ADR-027 既知負債）
    error = queryError instanceof Error ? queryError.message : "権限情報の取得に失敗しました";
  }

  const load = useCallback(async () => {
    await refetch();
  }, [refetch]);

  const hasPermission = useCallback(
    (key: string) => permissions.has(key),
    [permissions],
  );

  const hasAny = useCallback(
    (...keys: string[]) => keys.some((k) => permissions.has(k)),
    [permissions],
  );

  return useMemo(
    () => ({ permissions, loading, error, hasPermission, hasAny, reload: load }),
    [permissions, loading, error, hasPermission, hasAny, load],
  );
}
```

## 4-B. #2 frontend/src/hooks/usePermissions.test.ts（全文で置き換える）
- 1〜9 本目は今の 9 本と同じ。変えるのは 4 か所: (1) 利用者を試験の中で変えられるよう AuthContext を差し替える。(2) 試験ごとに写しの置き場を消す（§0 P7）。(3) 8 本目（reload）は、取り直しの間に loading が true に戻らない。TanStack は結果の知らせを少し後にまとめて送るので、新しい権限は waitFor で待ってから見る。(4) 10〜12 本目を足す。
```ts
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { usePermissions } from "./usePermissions";
import { queryClient } from "../lib/query/apiQuery";

// 試験の中で利用者を変えるため、今の人を差し替えられるようにする（ADR-1054 K5）
const auth = vi.hoisted(() => ({ user: { uid: "user-a" } as { uid: string } | null }));

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => auth,
}));

vi.mock("../lib/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

import { api } from "../lib/api";
const mockGet = vi.mocked(api.get);

afterEach(() => {
  vi.clearAllMocks();
  auth.user = { uid: "user-a" };
  // 前の試験の写しが次の試験に残らないようにする（ADR-1054）
  queryClient.clear();
});

describe("usePermissions", () => {
  it("initial state: loading=true, empty permissions, error=null", () => {
    mockGet.mockResolvedValueOnce({ permissions: [] });
    const { result } = renderHook(() => usePermissions());

    expect(result.current.loading).toBe(true);
    expect(result.current.permissions.size).toBe(0);
    expect(result.current.error).toBeNull();
  });

  it("on API success: permissions are stored in a Set and loading becomes false", async () => {
    mockGet.mockResolvedValueOnce({
      permissions: ["read:customers", "write:orders"],
    });

    const { result } = renderHook(() => usePermissions());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.permissions.has("read:customers")).toBe(true);
    expect(result.current.permissions.has("write:orders")).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it("on API failure: error is set and loading becomes false", async () => {
    mockGet.mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => usePermissions());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error).toBe("Network error");
    expect(result.current.permissions.size).toBe(0);
  });

  it("hasPermission returns true for a held permission", async () => {
    mockGet.mockResolvedValueOnce({
      permissions: ["read:customers", "write:orders"],
    });

    const { result } = renderHook(() => usePermissions());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.hasPermission("read:customers")).toBe(true);
    expect(result.current.hasPermission("write:orders")).toBe(true);
  });

  it("hasPermission returns false for a permission not held", async () => {
    mockGet.mockResolvedValueOnce({ permissions: ["read:customers"] });

    const { result } = renderHook(() => usePermissions());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.hasPermission("admin:superadmin")).toBe(false);
  });

  it("hasAny returns true when at least one permission is held", async () => {
    mockGet.mockResolvedValueOnce({ permissions: ["write:orders"] });

    const { result } = renderHook(() => usePermissions());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(
      result.current.hasAny("read:customers", "write:orders"),
    ).toBe(true);
  });

  it("hasAny returns false when none of the permissions are held", async () => {
    mockGet.mockResolvedValueOnce({ permissions: ["write:orders"] });

    const { result } = renderHook(() => usePermissions());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(
      result.current.hasAny("read:customers", "admin:superadmin"),
    ).toBe(false);
  });

  it("reload triggers a second API call and updates permissions", async () => {
    mockGet
      .mockResolvedValueOnce({ permissions: ["read:customers"] })
      .mockResolvedValueOnce({ permissions: ["read:customers", "write:orders"] });

    const { result } = renderHook(() => usePermissions());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.permissions.has("write:orders")).toBe(false);

    await act(async () => {
      await result.current.reload();
    });

    expect(mockGet).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(result.current.permissions.has("write:orders")).toBe(true));
  });

  it("calls the /me/permissions endpoint", async () => {
    mockGet.mockResolvedValueOnce({ permissions: [] });

    renderHook(() => usePermissions());
    await waitFor(() => expect(mockGet).toHaveBeenCalledOnce());

    expect(mockGet).toHaveBeenCalledWith("/me/permissions");
  });

  it("two consumers on the same screen share one /me/permissions call", async () => {
    mockGet.mockResolvedValueOnce({ permissions: ["read:customers"] });

    const { result } = renderHook(() => ({ a: usePermissions(), b: usePermissions() }));
    await waitFor(() => expect(result.current.b.loading).toBe(false));

    expect(result.current.a.hasPermission("read:customers")).toBe(true);
    expect(result.current.b.hasPermission("read:customers")).toBe(true);
    expect(mockGet).toHaveBeenCalledOnce();
  });

  it("reopening shows the previous permissions on the first render (ADR-1054 K1)", async () => {
    mockGet
      .mockResolvedValueOnce({ permissions: ["write:orders"] })
      .mockResolvedValueOnce({ permissions: ["write:orders"] });

    const first = renderHook(() => usePermissions());
    await waitFor(() => expect(first.result.current.loading).toBe(false));
    first.unmount();

    const second = renderHook(() => usePermissions());
    expect(second.result.current.loading).toBe(false);
    expect(second.result.current.hasPermission("write:orders")).toBe(true);

    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(2));
  });

  it("after the user changes, the previous user's permissions are never returned (ADR-1054 K5)", async () => {
    mockGet
      .mockResolvedValueOnce({ permissions: ["admin:a-only"] })
      .mockReturnValueOnce(new Promise(() => {}));

    const { result, rerender } = renderHook(() => usePermissions());
    await waitFor(() => expect(result.current.hasPermission("admin:a-only")).toBe(true));

    auth.user = { uid: "user-b" };
    rerender();

    expect(result.current.hasPermission("admin:a-only")).toBe(false);
    expect(result.current.permissions.size).toBe(0);
    expect(result.current.loading).toBe(true);

    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(2));
  });
});
```

## 4-H. 実装役の手順（1 手順 1 命令。<W> は手順1 で作られた作業場所の絶対パス）
手順1. クラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）どおり、作業場所を作り、push 済みの枝の先頭に合わせる（設計担当が §1 #3〜#5 を push 済み）。
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/line-like-speed-perm-cache
  （出力に出た作業場所の絶対パスを <W> として報告に書く。）
  cd <W> && git fetch origin release/line-like-speed-perm-cache
  cd <W> && git switch -C release/line-like-speed-perm-cache origin/release/line-like-speed-perm-cache
  cd <W> && git rev-parse HEAD origin/release/line-like-speed-perm-cache
  （2 行が同じことを確かめる。違えば停止して BLOCKED: で報告する。main は取り込まない。reset・rebase・force・merge・pull は使わない）
  cd <W> && ./scripts/dev/executor-preflight.sh > /tmp/perm-preflight.txt 2>&1
  cd <W> && grep -n "FAIL" /tmp/perm-preflight.txt | head -20
  cd <W> && grep -n "origin/main は存在" /tmp/perm-preflight.txt | head -3
  （FAIL の行の扱いは段 2 カード §4-H 手順1 と同じ。`GitHub API に到達不可` の 1 件・`gh auth switch --hostname github.com --user shingo-cc` の失敗の 1 件・その結果の `PREFLIGHT FAIL` の行だけなら、`[OK]   origin/main は存在` の行があることを確かめて続ける。ほかの FAIL が 1 件でもあれば停止し、BLOCKED: で grep の出力を報告する。）
  cd <W> && git fetch origin main
  cd <W> && git diff --stat fbee46fce origin/main -- frontend/src/hooks/usePermissions.ts frontend/src/hooks/usePermissions.test.ts frontend/src/test-setup.ts frontend/src/lib/query | tail -5
  （§3(a) の確かめ。）
手順2. 依存を入れ、§3(b)(c) を確かめ、変える前の lint の警告を数える。
  cd <W>/frontend && npm ci > /tmp/perm-ci.txt 2>&1
  cd <W> && tail -5 /tmp/perm-ci.txt
  cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json
  cd <W> && git grep -n -E "vi\.mock\(['\"]@tanstack" -- frontend/src | head -5
  cd <W>/frontend && npx eslint src/hooks/usePermissions.ts src/hooks/usePermissions.test.ts > /tmp/perm-lint-before.txt 2>&1
  cd <W> && tail -5 /tmp/perm-lint-before.txt
手順3. §4-A・§4-B の全文で #1〜#2 を置き換える。frontend/src/test-setup.ts は変えない。
手順4. 型を作ってから試験を流す（権限の部品の試験・全部の試験・型・lint）。作る型（frontend/src/api/generated/）は .gitignore で除かれるので commit に入らない。
  cd <W>/frontend && npm run generate:api-types > /tmp/perm-gen.txt 2>&1
  cd <W> && tail -3 /tmp/perm-gen.txt
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/hooks/usePermissions.test.ts > /tmp/perm-unit.txt 2>&1
  cd <W> && tail -30 /tmp/perm-unit.txt
  cd <W>/frontend && npm run test:unit > /tmp/perm-unit-all.txt 2>&1
  cd <W> && tail -15 /tmp/perm-unit-all.txt
  （落ちた試験があれば、次の命令で名前を出して §3(d) に従う: cd <W> && grep -n -E "FAIL|✗|×" /tmp/perm-unit-all.txt | head -40）
  cd <W>/frontend && npx tsc --noEmit -p . > /tmp/perm-tsc.txt 2>&1
  cd <W> && tail -20 /tmp/perm-tsc.txt
  cd <W>/frontend && npx eslint src/hooks/usePermissions.ts src/hooks/usePermissions.test.ts > /tmp/perm-lint.txt 2>&1
  cd <W> && tail -20 /tmp/perm-lint.txt
  （lint の警告が手順2 の数より増えていないこと・誤りが 0 であること。§3(f)。）
手順5. 本番と同じ形で組み立てられるか確かめる。
  cd <W>/frontend && npm run build > /tmp/perm-build.txt 2>&1
  cd <W> && tail -15 /tmp/perm-build.txt
手順6. 変わったファイルが §1 の #1〜#2 だけか確かめる。
  cd <W> && git status --short | head -20
  cd <W> && git diff --stat origin/release/line-like-speed-perm-cache | tail -6
手順7. commit する。
  cd <W> && git add frontend/src/hooks/usePermissions.ts frontend/src/hooks/usePermissions.test.ts
  cd <W> && git commit -m "feat: 権限の読み込みを写しの置き場に載せ、戻った時に前の権限を先に出す（ADR-1054）"
手順8. commit が在ることを確かめてから push する（--no-verify は使わない。push の前の検査が × なら直してから push。fast-forward でないと断られたら直さず BLOCKED:）。
  cd <W> && git log -3 --oneline
  cd <W> && git push -u origin release/line-like-speed-perm-cache
手順9. 報告を返す。PR は作らない（設計担当が手元で作る）。報告の 1 つの発言は 600 文字以内にして、番号付きの発言に分ける。

## 4. GO と承認・PO の操作
- PO の実装承認: 2026-11-01 PO 選択「1」（権限の読み込みを写しの置き場に載せる作業指示書を作り、本番まで進める）。ADR-1054 は Accepted。このカードの審査合格の後に、設計担当がクラウドの Sonnet へ渡す。
- 触るのは frontend の部品 1 つ・その試験と書類だけで、migrations・deploy.yml・本番 scripts を含まない（番号付き GO の要る危ない PR ではない）。main へのマージで本番の画面に出る。マージは PO の委任に基づき設計担当（Claude Opus）が、マージ前の審査役の APPROVE と必須の確認 16 件の pass の後に行う。
- PO が操作することはない。

## 5. 受入（○×）
| # | 基準 | 検証方法 |
|---|---|---|
| C1 | §4-B の 12 本がすべて合格（K1: 10・11 本目／K5: 12 本目で利用者を変えた後の描画に前の人の権限 0 件） | /tmp/perm-unit.txt の最後（1 file・12 passed）と、PR の CI の unit-run が success |
| C2 | 全部の試験・型・lint・組み立てが通る | /tmp/perm-unit-all.txt・perm-tsc.txt・perm-lint.txt・perm-build.txt の最後と、PR の必須の確認 16 件が pass |
| C3 | 変わったのは §1 の 5 ファイルだけ | gh pr diff --name-only |
| C4 | マージの後、毎朝の画面の記録を手で 1 回動かし、段 2 の 5 行（design §3-4-6 の表）で K1（戻った時の秒）≤0.1 秒、K2（初めて開く秒）≤2 秒、403・5xx が 0 件。ほかの 130 行は K2 の最大と 2 秒を超えた画面の数が §3-4-6 から悪化していない。4 行の K1 が下がらなければ §0 P3 の仮説は誤りと記録して止まる | prod-ui-check の実行の要約（設計担当。`gh workflow run prod-ui-check.yml --ref main` の後に要約の表を読む）。測る前に、その時の本番の反映が終わっていることを確かめる（§3-4-6 で測定中に別の反映が始まった反省） |
| C5 | マージの後、deploy が成功し、本番の画面が開く | deploy.yml の実行の結論 success と時刻。本番 https://app.salesanchor.jp/ が開き、ブラウザの誤りの記録に TanStack 由来の誤りが無い（設計担当） |

- C4・C5 の結果は docs/handoff/line-like-speed/design.md §3-4 に設計担当が書き足す。
- K5 を本番で 2 人のログインで確かめることはしない（本番でパスワードを打たない決まり）。K5 は C1 の 12 本目と、P4（写しの名前に uid が入る・利用者が変わると消える）で確かめたと記録に書く。

## 6. 戻し方
- マージの commit を git revert する PR を 1 つ出す。usePermissions は今の読み方（useState と useEffect）に戻る。写しはメモリだけなので、戻した後に残る物は無い。DB には何も入っていない。

## 停止と報告
- §3 で「停止」とした時、試験が全部合格にならない時、§2 の触らない範囲を変えないと進めない時は、そこで停止する。
- 停止したら、何を実行し何が返ったかの生の出力（/tmp の報告ファイルの tail）を付けて、BLOCKED: か NEEDS_DECISION: で始まる報告を返す。推測で直さない。
- 終わったら DONE: で始まる報告に、§3 の確かめた結果、手順2・4・5 の tail、手順6 の git status、push した sha を書く。

END OF CARD
