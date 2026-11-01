# 運営者判定の写しカード（運営者かを確かめる部品 useSuperAdmin を写しの置き場に載せる）

- 対象: docs/handoff/line-like-speed/design.md §3-2（部品）・§3-4-8（権限の写しの受入と残り）・§3-4-9（このカード）・§3-5 の K1・K5。ADR-1054（Accepted）。
- 根拠の写し: S=origin/main 7cc0f25e3（Merge #4974）。行番号はすべてこの sha。実装の前に最新の origin/main で行を合わせ直す（§3(a)）。
- 読んだ節: 権限の写しカード（docs/handoff/line-like-speed/perm-cache-card.md:5）と同じ節（guards/00-common.md・03-file.md・04-worktree.md・05-pr.md・10-executor.md・scripts/agent-hooks/cloud/rules.md）。照合も同じ: 全命令は cd <W> で始める・出力は tail/head で上限・変えるファイルは丸ごとの全文・PR は実行役が作らない・出力をファイルに残す命令と tail で読む命令は別の行。
- 実行役はクラウドの Sonnet。作業場所の作り方はクラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）を正とする。.pr-number・gh-pr-create-safe.sh は使わない。待つために sleep を使わない。
- 状態: 第 3 版（設計担当 Claude Opus・2026-11-01）。第 2 版の実装（13b95d317・PR #4992）を審査役（Claude Opus）が REQUEST_CHANGES にした。取り直しが失敗すると前の「運営者である」が残り、§0 P7 と食い違うという指摘。第 3 版は §4-A で失敗の時を false にし、§4-B に 9 本目を足した。それより前の経緯: 第 2 版（2026-11-01）。第 1 版はクラウドの設計審査役が REVISE（docs/handoff/line-like-speed/review-superadmin-cache-card-v1.md・ブランチ release/line-like-speed-superadmin-cache-review-v1）。直す点 1〜6 を入れた。コード（§4-A）と試験（§4-B）は審査で型・lint・単体 8 本・全部の試験（177 ファイル・1997 本）・組み立てが通り、変えていない。
- 受領確認: 実装役は着手の最初の報告に「運営者判定の写しカード 第 3 版を受け取った・S=7cc0f25e3」と書く。

## 0. 何のための変更か（設計の合格線は変えない）
- P1 権限の写しの受入（design §3-4-8・prod-ui-check run 41297663070・2026-11-01 19:32 JST）の後も、戻った時の秒（K1）が 0.1 秒を超える画面が残る。そのうち運営者の画面（/super-admin/ で始まる行）は、画面ごとの行が 14 行（0.17〜0.18 秒）と、分析の決まりの画面の区切りの行（/super-admin/analysis-rules?section=・0.16〜0.20 秒）。区切りの行は、要約の見出しでは 21 行で、秒が並ぶ区切りの名前は 25 個ある。この数の違いはまだ確かめていない。そのため受入（§5 C4）は数ではなく「/super-admin/ で始まる行すべて」で判定する。どの行も「いちばん遅い API」は /api/v1/me/permissions か、API が 0 本。同じく /me/permissions だけを読む /admin/tenant-policy などの行は 0.01〜0.02 秒。設計担当の手元の写しは /tmp/CC報告ファイル/stage3/k1-over-0.1.txt（リポジトリには入れない）。
- P2 今の useSuperAdmin（S frontend/src/hooks/useSuperAdmin.ts:19-43）は、権限の写しの前の usePermissions と同じ形。写しを使わず、部品が出るたびに loading が true から始まり、useEffect で /me/permissions を取り直す。
- P3 運営者の画面の多く（14 画面のうち 12）は、loading の間は中身の代わりに LoadingBlock を出す。例: S frontend/src/pages/super-admin/AnalysisRulesPage.tsx:101・:117-123、S frontend/src/pages/super-admin/TcgProductImportPage.tsx:12-14。このため戻った時も、/me/permissions が返るまで「読み込み中の印」が出たままになる。
- P4 仮説（まだ確かめていない）: useSuperAdmin を写しの置き場（useApiQuery・S frontend/src/lib/query/apiQuery.ts:51-73）に載せると、戻った時の最初の描画に前の判定が出て、P1 の運営者の行の K1 が 0.1 秒以下になる。確かめ方は §5 C4。下がらなければ仮説は誤りと記録して止まる。
- P4b 判定の後に自分の API を取る画面（FxRatePage.tsx:51-55・ViewerAccountsPage.tsx:148-152・ViewerTemplatesPage.tsx:71-76・TcgLineImportPage.tsx:146-150・SupplierExtractionRulesPage.tsx:189-193・AnalysisRules の区切りの NeedsReviewTabsPanel.tsx:113・SoldOutResultsPanel.tsx:55）は、変更後に K1 がその API の秒で決まる見込みがある。C4 で 0.1 秒を超えた行があれば、その行の「いちばん遅い API」を要約から書き写し、仮説の誤りがどの画面かを記録する。また TcgDistributionPage（:22-28 文字の読み込み中）と SupplierExtractionRulesPage（:456 何も出さない）は LoadingBlock を出さない。
- P5 写しの名前は usePermissions と同じ ["api", uid, "me", "permissions", { query: "" }]（S apiQueryKey・apiQuery.ts:41-44）。同じ 1 つの写しを 2 つの部品が読むだけで、データを 2 か所に持たない。外側の枠（S frontend/src/components/DesktopShell.tsx:112）も useSuperAdmin を使うので、同じ画面の中の通信は 1 回に束ねられる。利用者が変わると QueryAuthSync が写しを全部消す（S frontend/src/lib/query/QueryAuthSync.tsx:18-28）。
- P6 useSuperAdmin を使う部品は、どれもログインの後にしか描かれない（perm-cache-card.md §0 P5 と同じ根拠。外側の枠（DesktopShell・MobileShell.tsx:78）と SecretaryChat は ProtectedRoute の内側）。
- P7 返す形 { isSuperAdmin, loading } は変えない。使い手 21 行（`git grep -n 'useSuperAdmin()' -- frontend/src ':!*.test.*'` の 22 行から定義の useSuperAdmin.ts:19 を除いた数）は触らない。違いは 2 つだけ。(1) 取り直しの間は loading が true に戻らない。(2) 取り直しの間は前の判定のまま。運営者の権限を外された人には、取り直しが返るまでの間（今の秒で最大約 0.7 秒）運営者の画面の枠が出得る。中のデータは backend が断る（運営者の API は backend で is_super_admin を確かめる）ので、見えてはいけない中身は出ない。取り直しが失敗した時は、今と同じく運営者ではない扱い（isSuperAdmin false）にする。前に true だった後の取り直しの失敗も false にする（useApiQuery は失敗しても前の data を残し error を立てるため、error を見て false にする。§4-B 9 本目）。
- P8 前の試験の写しが次の試験に残らないよう、新しい試験ファイルの afterEach で写しの置き場（queryClient）を消す。試験の共通の準備（S frontend/src/test-setup.ts）は変えない（perm-cache-card.md §0 P7 と同じ理由）。useSuperAdmin を使う画面の試験 13 ファイルは、どれも useSuperAdmin を vi.mock で差し替えている（`git grep -l "useSuperAdmin" -- 'frontend/src/**/*.test.*'`）ので、この変更の影響を受けない。
- P8b InventoryPage（S frontend/src/pages/inventory/InventoryPage.tsx:146）の試験 8 ファイル（InventoryPage.*.test.tsx）は useSuperAdmin を差し替えず、api だけを差し替える。変更後はこの 8 ファイルで写しが試験の間に残る（rowdrawer は試験ごとに is_super_admin を変える・InventoryPage.rowdrawer.test.tsx:44-55）。審査で 3 回流して全部合格した。手順 4 の全部の試験でここが落ちたら §3(d) に従い、試験に queryClient.clear() を足すなどの直しを自分で考えずに停止する。

## 1. 触るファイル（変更前→変更後）
| # | ファイル | 変更前 | 変更後 |
|---|---|---|---|
| 1 | frontend/src/hooks/useSuperAdmin.ts | 第 2 版の写し（13b95d317・失敗の後も前の true が残る） | useApiQuery で取り、error の時は false（§4-A 全文） |
| 2 | frontend/src/hooks/useSuperAdmin.test.ts | 第 2 版の 8 本（13b95d317） | 9 本（§4-B 全文） |
| 3 | docs/handoff/line-like-speed/superadmin-cache-card.md | 無い | このカード（設計担当が書いた。実装役は触らない） |
| 4 | docs/handoff/line-like-speed/design.md | §3-4-8 まで | §3-4-9 にこのカードの場所を書き足し済み（設計担当。実装役は触らない） |
| 5 | .claude-pipeline/active-work.d/release-line-like-speed-superadmin-cache.md | 無い | 作業の札（設計担当。実装役は触らない） |

## 2. 触らない範囲
- backend/・migrations/・.github/workflows/・scripts/・tests/prod-check/・frontend/viewer/ は触らない。
- frontend/src/test-setup.ts・frontend/src/lib/query/・frontend/src/lib/api.ts・frontend/src/contexts/AuthContext.tsx・frontend/src/App.tsx・frontend/src/hooks/usePermissions.ts は触らない。
- useSuperAdmin の使い手（画面・枠・SecretaryChat）は 1 本も変えない。ほかの試験ファイルも変えない。
- /me/permissions を別に取る useFeatures.ts・GoalSettingPage.tsx は、このカードでは変えない（変更は一度に 1 つ）。
- components/・CSS・ja.json・en.json は触らない。新しい言葉・色・寸法を足さない。
- QueryClient を作らない。staleTime を設定しない。写しをブラウザの保存に書かない。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) 最新の origin/main で、§1 #1・frontend/src/test-setup.ts・frontend/src/lib/query/・frontend/src/hooks/usePermissions.ts が S と同じか（`git diff --stat 7cc0f25e3 origin/main -- frontend/src/hooks/useSuperAdmin.ts frontend/src/test-setup.ts frontend/src/lib/query frontend/src/hooks/usePermissions.ts` が空か）。frontend/src/hooks/useSuperAdmin.test.ts がブランチにあること（第 2 版の実装・13b95d317）。どちらかが違えば停止して報告する。
- (b) `cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json` が `"5.104.4"` の 1 行。違えば停止して報告する。
- (c) `cd <W> && git grep -n -E "vi\.mock\(['\"]@tanstack" -- frontend/src | head -5` が 0 行。1 行でもあれば停止して NEEDS_DECISION: で返す。
- (d) 手順 4 の全部の試験で、§1 #2 のほかの試験ファイルが落ちたら、試験もコードも直さずに停止し、NEEDS_DECISION: で落ちた試験の名前と生の出力（tail）を返す。
- (e) §4-B の 9 本のどれかが落ちたら、試験を書き換えて通さない。§4-A・§4-B の写し違いを探し、写し違いが無ければ停止して NEEDS_DECISION: で生の出力を返す。とくに K5 の試験（8 本目）は、落ちたら直し方を自分で考えずに停止する。
- (f) 手順 2 で、変える前の lint の警告の数を数えておく（useSuperAdmin.ts だけ）。変えた後は、2 つのファイルを合わせてその数より増えないこと。増えたら直す。直せない時は停止する。

## 4-A. #1 frontend/src/hooks/useSuperAdmin.ts（全文で置き換える）
```ts
/**
 * 現在のユーザーが is_super_admin かどうかを判定するフック。
 *
 * spec.md v1.1 F2 (Sprint 2):
 *   /api/v1/me/permissions レスポンスに is_super_admin を含めて返す。
 *   そのレスポンスを再利用して /super-admin/masters への導線判定に使用。
 *
 * 変更履歴:
 *   2026-05-21: 初版（Sprint 2）
 *   2026-11-01: 写しの置き場（useApiQuery）に載せた（ADR-1054）。usePermissions と同じ写しを読む。戻った時は前の判定を先に出し、裏で取り直す。
 */
import { useApiQuery } from "../lib/query/apiQuery";

interface MePermissionsResponse {
  permissions: string[];
  is_super_admin: boolean;
}

export function useSuperAdmin() {
  const { data, isPending, error } = useApiQuery<MePermissionsResponse>("/me/permissions");

  // 取得に失敗した時は false（運営者ではない扱い・今と同じ）。取り直しが失敗すると前の data が残るので error も見る
  return { isSuperAdmin: !error && Boolean(data?.is_super_admin), loading: isPending };
}
```

## 4-B. #2 frontend/src/hooks/useSuperAdmin.test.ts（全文で置き換える）
- 形は usePermissions.test.ts（perm-cache-card.md §4-B）に合わせる。
```ts
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useSuperAdmin } from "./useSuperAdmin";
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

describe("useSuperAdmin", () => {
  it("initial state: loading=true, isSuperAdmin=false", () => {
    mockGet.mockResolvedValueOnce({ permissions: [], is_super_admin: true });
    const { result } = renderHook(() => useSuperAdmin());

    expect(result.current.loading).toBe(true);
    expect(result.current.isSuperAdmin).toBe(false);
  });

  it("is_super_admin true: isSuperAdmin becomes true and loading becomes false", async () => {
    mockGet.mockResolvedValueOnce({ permissions: [], is_super_admin: true });

    const { result } = renderHook(() => useSuperAdmin());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.isSuperAdmin).toBe(true);
  });

  it("is_super_admin false: isSuperAdmin stays false and loading becomes false", async () => {
    mockGet.mockResolvedValueOnce({ permissions: [], is_super_admin: false });

    const { result } = renderHook(() => useSuperAdmin());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.isSuperAdmin).toBe(false);
  });

  it("on API failure: isSuperAdmin is false and loading becomes false", async () => {
    mockGet.mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => useSuperAdmin());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.isSuperAdmin).toBe(false);
  });

  it("calls the /me/permissions endpoint", async () => {
    mockGet.mockResolvedValueOnce({ permissions: [], is_super_admin: false });

    renderHook(() => useSuperAdmin());
    await waitFor(() => expect(mockGet).toHaveBeenCalledOnce());

    expect(mockGet).toHaveBeenCalledWith("/me/permissions");
  });

  it("shares one /me/permissions call with usePermissions on the same screen", async () => {
    mockGet.mockResolvedValueOnce({ permissions: ["read:customers"], is_super_admin: true });

    const { result } = renderHook(() => ({ s: useSuperAdmin(), p: usePermissions() }));
    await waitFor(() => expect(result.current.s.loading).toBe(false));

    expect(result.current.s.isSuperAdmin).toBe(true);
    expect(result.current.p.hasPermission("read:customers")).toBe(true);
    expect(mockGet).toHaveBeenCalledOnce();
  });

  it("reopening shows the previous result on the first render (ADR-1054 K1)", async () => {
    mockGet
      .mockResolvedValueOnce({ permissions: [], is_super_admin: true })
      .mockResolvedValueOnce({ permissions: [], is_super_admin: true });

    const first = renderHook(() => useSuperAdmin());
    await waitFor(() => expect(first.result.current.loading).toBe(false));
    first.unmount();

    const second = renderHook(() => useSuperAdmin());
    expect(second.result.current.loading).toBe(false);
    expect(second.result.current.isSuperAdmin).toBe(true);

    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(2));
  });

  it("after the user changes, the previous user's result is never returned (ADR-1054 K5)", async () => {
    mockGet
      .mockResolvedValueOnce({ permissions: [], is_super_admin: true })
      .mockReturnValueOnce(new Promise(() => {}));

    const { result, rerender } = renderHook(() => useSuperAdmin());
    await waitFor(() => expect(result.current.isSuperAdmin).toBe(true));

    auth.user = { uid: "user-b" };
    rerender();

    expect(result.current.isSuperAdmin).toBe(false);
    expect(result.current.loading).toBe(true);

    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(2));
  });

  it("when a refetch fails after a previous true, isSuperAdmin becomes false (fail closed)", async () => {
    mockGet
      .mockResolvedValueOnce({ permissions: [], is_super_admin: true })
      .mockRejectedValueOnce(new Error("network"));

    const first = renderHook(() => useSuperAdmin());
    await waitFor(() => expect(first.result.current.isSuperAdmin).toBe(true));
    first.unmount();

    const { result } = renderHook(() => useSuperAdmin());
    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(result.current.isSuperAdmin).toBe(false));
    expect(result.current.loading).toBe(false);
  });
});
```

## 4-H. 実装役の手順（1 手順 1 命令。<W> は手順1 で作られた作業場所の絶対パス）
手順1. クラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）どおり、作業場所を作り、push 済みの枝の先頭に合わせる（設計担当が §1 #3〜#5 を push 済み）。
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/line-like-speed-superadmin-cache
  （出力に出た作業場所の絶対パスを <W> として報告に書く。）
  cd <W> && git fetch origin release/line-like-speed-superadmin-cache
  cd <W> && git switch -C release/line-like-speed-superadmin-cache origin/release/line-like-speed-superadmin-cache
  cd <W> && git rev-parse HEAD origin/release/line-like-speed-superadmin-cache
  （2 行が同じことを確かめる。違えば停止して BLOCKED: で報告する。main は取り込まない。reset・rebase・force・merge・pull は使わない）
  cd <W> && ./scripts/dev/executor-preflight.sh > /tmp/sa-preflight.txt 2>&1
  cd <W> && grep -n "FAIL" /tmp/sa-preflight.txt | head -20
  cd <W> && grep -n "origin/main は存在" /tmp/sa-preflight.txt | head -3
  （FAIL の行の扱いは perm-cache-card.md §4-H 手順1 と同じ。`GitHub API に到達不可` の 1 件・`gh auth switch --hostname github.com --user shingo-cc` の失敗の 1 件・その結果の `PREFLIGHT FAIL` の行だけなら、`[OK]   origin/main は存在` の行があることを確かめて続ける。ほかの FAIL が 1 件でもあれば停止し、BLOCKED: で grep の出力を報告する。）
  cd <W> && git fetch origin main
  cd <W> && git diff --stat 7cc0f25e3 origin/main -- frontend/src/hooks/useSuperAdmin.ts frontend/src/test-setup.ts frontend/src/lib/query frontend/src/hooks/usePermissions.ts | tail -5
  cd <W> && ls frontend/src/hooks/useSuperAdmin.test.ts
  （§3(a) の確かめ。1 つ目は空、2 つ目はファイルの名前が出るのが正しい。）
  cd <W> && git log -5 --oneline | tail -5
  （13b95d317 の行が出ること。出なければ停止して BLOCKED: で報告する。）
手順2. 依存を入れ、§3(b)(c) を確かめ、変える前の lint の警告を数える。
  cd <W>/frontend && npm ci > /tmp/sa-ci.txt 2>&1
  cd <W> && tail -5 /tmp/sa-ci.txt
  cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json
  cd <W> && git grep -n -E "vi\.mock\(['\"]@tanstack" -- frontend/src | head -5
  cd <W>/frontend && npx eslint src/hooks/useSuperAdmin.ts > /tmp/sa-lint-before.txt 2>&1
  cd <W> && tail -5 /tmp/sa-lint-before.txt
手順3. §4-A の全文で #1 を置き換え、§4-B の全文で #2 を置き換える。frontend/src/test-setup.ts は変えない。
手順4. 型を作ってから試験を流す（この部品の試験・全部の試験・型・lint）。作る型（frontend/src/api/generated/）は .gitignore で除かれるので commit に入らない。
  cd <W>/frontend && npm run generate:api-types > /tmp/sa-gen.txt 2>&1
  cd <W> && tail -3 /tmp/sa-gen.txt
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/hooks/useSuperAdmin.test.ts > /tmp/sa-unit.txt 2>&1
  cd <W> && tail -30 /tmp/sa-unit.txt
  cd <W>/frontend && npm run test:unit > /tmp/sa-unit-all.txt 2>&1
  cd <W> && tail -15 /tmp/sa-unit-all.txt
  （落ちた試験があれば、次の命令の出力で名前を見て §3(d) に従う。）
  cd <W> && grep -n -E "FAIL|✗|×" /tmp/sa-unit-all.txt | head -40
  cd <W>/frontend && npx tsc --noEmit -p . > /tmp/sa-tsc.txt 2>&1
  cd <W> && tail -20 /tmp/sa-tsc.txt
  cd <W>/frontend && npx eslint src/hooks/useSuperAdmin.ts src/hooks/useSuperAdmin.test.ts > /tmp/sa-lint.txt 2>&1
  cd <W> && tail -20 /tmp/sa-lint.txt
  （lint の警告が手順2 の数より増えていないこと・誤りが 0 であること。§3(f)。）
手順5. 本番と同じ形で組み立てられるか確かめる。
  cd <W>/frontend && npm run build > /tmp/sa-build.txt 2>&1
  cd <W> && tail -15 /tmp/sa-build.txt
手順6. 変わったファイルが §1 の #1〜#2 だけか確かめる。
  cd <W> && git status --short | head -20
  cd <W> && git diff --stat origin/release/line-like-speed-superadmin-cache | tail -6
  （#1・#2 とも M で出る。第 2 版との違いは #1 の 2 行と #2 の 9 本目だけのはず。）
手順7. commit する。
  cd <W> && git add frontend/src/hooks/useSuperAdmin.ts frontend/src/hooks/useSuperAdmin.test.ts
  cd <W> && git commit -m "fix: 運営者の判定の取り直しが失敗した時は運営者ではない扱いにする（ADR-1054・第 3 版）"
手順8. commit が在ることを確かめてから push する（--no-verify は使わない。push の前の検査が × なら直してから push。fast-forward でないと断られたら直さず BLOCKED:）。
  cd <W> && git log -3 --oneline
  cd <W> && git push -u origin release/line-like-speed-superadmin-cache
手順9. 報告を返す。PR は作らない（設計担当が手元で作る）。報告の 1 つの発言は 600 文字以内にして、番号付きの発言に分ける。

## 4-I. GO と承認・PO の操作
- PO の実装承認: 2026-11-01 PO 選択「1」（0.1 秒を超えて残る画面の遅い理由を調べて、直す作業指示書を作り、本番まで進める）。ADR-1054 は Accepted。このカードの審査合格の後に、設計担当がクラウドの Sonnet へ渡す。
- 触るのは frontend の部品 1 つ・その試験と書類だけで、migrations・deploy.yml・本番 scripts を含まない（番号付き GO の要る危ない PR ではない）。main へのマージで本番の画面に出る。マージは PO の委任に基づき設計担当（Claude Opus）が、マージ前の審査役の APPROVE と必須の確認 16 件の pass の後に行う。
- PO が操作することはない。

## 5. 受入（○×）
| # | 基準 | 検証方法 |
|---|---|---|
| C1 | §4-B の 9 本がすべて合格（取り直しの失敗の後は false: 9 本目）（K1: 7 本目／K5: 8 本目で利用者を変えた後の描画に前の人の判定 0 件／写しが 1 つ: 6 本目で通信 1 回） | /tmp/sa-unit.txt の最後（1 file・9 passed）と、PR の CI の unit-run が success |
| C2 | 全部の試験・型・lint・組み立てが通る | /tmp/sa-unit-all.txt・sa-tsc.txt・sa-lint.txt・sa-build.txt の最後と、PR の必須の確認 16 件が pass |
| C3 | 変わったのは §1 の 5 ファイルだけ | gh pr diff --name-only |
| C4 | マージの後、毎朝の画面の記録を手で 1 回動かし、/super-admin/ で始まる行すべて（区切りの行を含む）で K1（戻った時の秒）≤0.1 秒、403・5xx が 0 件。ほかの行は K2 の最大と 2 秒を超えた画面の数が §3-4-8 から悪化していない。それらの K1 が下がらなければ §0 P4 の仮説は誤りと記録して止まる | prod-ui-check の実行の要約（設計担当。`gh workflow run prod-ui-check.yml --ref main` の後に要約の表を読む）。測る前に、その時の本番の反映が終わっていることを確かめる |
| C5 | マージの後、deploy が成功し、本番の画面が開く | deploy.yml の実行の結論 success と時刻。本番 https://app.salesanchor.jp/ が開く（設計担当） |

- C4・C5 の結果は docs/handoff/line-like-speed/design.md §3-4 に設計担当が書き足す。
- K5 を本番で 2 人のログインで確かめることはしない（本番でパスワードを打たない決まり）。K5 は C1 の 8 本目と、P5（写しの名前に uid が入る・利用者が変わると消える）で確かめたと記録に書く。

## 6. 戻し方
- マージの commit を git revert する PR を 1 つ出す。useSuperAdmin は今の読み方（useState と useEffect）に戻る。写しはメモリだけなので、戻した後に残る物は無い。DB には何も入っていない。

## 停止と報告
- §3 で「停止」とした時、試験が全部合格にならない時、§2 の触らない範囲を変えないと進めない時は、そこで停止する。
- 停止したら、何を実行し何が返ったかの生の出力（/tmp の報告ファイルの tail）を付けて、BLOCKED: か NEEDS_DECISION: で始まる報告を返す。推測で直さない。
- 終わったら DONE: で始まる報告に、§3 の確かめた結果、手順2・4・5 の tail、手順6 の git status、push した sha を書く。

END OF CARD
