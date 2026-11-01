# 段 2 実装カード（試しに 3 画面を「写しを先に出して裏で取り直す」形に変える）

- 対象: docs/handoff/line-like-speed/design.md §3-2（部品）・§3-3（触らない範囲）・§3-4 の段 2・§3-5 の K1・K2・K5・§3-7。ADR-1054（Accepted）。
- 根拠の写し: S=origin/main 508e86036（Merge #4965）。行番号はすべてこの sha。2026-11-01 に origin/main が 7df87ddd5 へ進んだが、増えた 2 commit は docs/adr だけで frontend/ と docs/handoff/line-like-speed/ は同じ（`git diff --stat 508e86036 7df87ddd5 -- frontend docs/handoff/line-like-speed` が空）。実装の前に最新の origin/main で行を合わせ直す（§3(a)）。
- 読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/04-worktree.md・guards/05-pr.md・guards/10-executor.md・scripts/agent-hooks/cloud/rules.md（段 1 カードと同じ節。照合も同じ: 全命令は cd <W> で始める・出力は tail/head で上限・新しいファイルは丸ごとの全文・作業場所は new-worktree.sh で作り出力をパイプに通さない・PR は実行役が作らない・出力をファイルに残す命令と tail で読む命令は別の行）。
- 実行役はクラウドの Sonnet。作業場所の作り方はクラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）を正とする。.pr-number・gh-pr-create-safe.sh は使わない。出力には上限を付ける。待つために sleep を使わない。
- 状態: 第 2 版（第 1 版の審査 REVISE を直した版・審査前）。第 1 版からの直し: §4-A の写しの関数の型（tsc が落ちた）・§4-F の react-i18next の mock（試験の読み込みで落ちた）・C3・C5・C6・G1 の行番号・P2 を K5 の守りを外すと落ちる形に強めた（P2a）。
- 受領確認: 実装役は着手の最初の報告に「段 2 カード 第 2 版を受け取った・S=508e86036」と書く。

## 0. 設計からの直し・詳しくした点（V2。設計の合格線は変えない）
- V2-1 3 つ目の画面は仕入先の一覧（frontend/src/pages/suppliers/SuppliersPage.tsx）にする。理由: 設計 §3-4 の段 2 は「中身を消す形の代表」。仕入先は `{loading ? <LoadingBlock /> : 表}`（S :232）でページ送りと検索のたびに通信する形で、取引先（検索だけ）・連絡手段（条件なし）と形が違う。3 画面とも本番の点検用の人（tenant 001・見るだけの役・ADR-1051 D6）で 403 なしに開ける（S の段 0a の回で 5 行とも 403 0 件）。
- V2-2 3 画面の本番の行は 5 行ある（連絡手段と仕入先は管理センターの中にもある・S frontend/src/App.tsx:370・:394 と管理センターの仕入先）。合格は 5 行すべてで見る（§5 B5）。基準は段 1 の受入の回（prod-ui-check run 41232464221・main 8a2baf838・2026-11-01 04:18:19 JST）。

  | 行 | 初めて開く秒 | 戻った時の秒（K1） |
  |---|---|---|
  | /suppliers | 0.2 | 0.20 |
  | /management-center/suppliers | 0.2 | 0.23 |
  | /crm/companies | 0.2 | 0.25 |
  | /admin/channel-masters | 0.2 | 0.19 |
  | /management-center/channel-masters | 0.2 | 0.22 |

- V2-3 条件を変えた時（仕入先のページ送り・検索、取引先の検索）は、前の条件の行を出したまま裏で取る（TanStack の placeholderData。公式 guides/paginated-queries の形）。今の取引先は初回の後に読み込み中へ戻さない（S CompaniesPage.tsx:202・:216。loading を true に戻す行が無い）ので、取引先は今と同じ見え方になる。仕入先は今もページを変えると前の行が出たまま（S SuppliersPage.tsx:63-75 も loading を true に戻さない）で、同じ。前の行を出している間は、仕入先の前へ・次へのボタンを押せなくする（2 回押して 2 ページ飛ぶのを防ぐ。公式の例の `disabled={isPlaceholderData || ...}` の形）。
- V2-4 K5 の守り（いちばん大事）: 前の条件の行を出す関数は、**同じ人の写しの時だけ**前の行を返す（`previousQuery?.queryKey[1] === uid`）。理由: 利用者が変わった最初の描画は、QueryAuthSync が写しを消す（描いた後の useLayoutEffect）より前に起きる。この時は前の人の写しがまだ残っていて、関数は前の人の行を受け取る。条件を付けないと、その描画で前の人の行が画面に出る。また TanStack は関数が同じ物なら前の結果をそのまま使い回す（S node_modules ではなく公開の query-core queryObserver の placeholderData の扱い。設計担当が 5.104.4 の写しで確かめた）ので、関数は uid が変わった時に作り直す（useCallback の依存に uid）。T12（試しの部品）と P2（本物の仕入先の画面）で守る。
- V2-5 useApiQuery は useQuery に queryClient を直接渡す（`useQuery(options, queryClient)`・5.104.4 の型の 2 つ目の引数）。理由: 今ある画面の試験（S frontend/src/components/MasterSearchButtonMigration.test.tsx・PageFormButtonMigration.test.tsx）は QueryClientProvider 無しで画面を描く。直接渡せば、その試験を包み直さずに済み、アプリでも同じ 1 個（apiQuery.ts の queryClient）を使うことが型で決まる。App.tsx の QueryClientProvider（同じ 1 個）はそのまま。
- V2-6 書いた後の取り直しは useInvalidateApi（新しく足す。今の人の uid を中で取り、頭の言葉が同じ写しを取り直す）。今の画面は書いた後に load() を呼んで読み直している。これを「頭の言葉が同じ写しを取り直す」に替える。開いている写しはその場で取り直される（invalidateQueries の既定 refetchType 'active'）。
- V2-7 取り直し中の印: 写しを出したまま裏で取り直している間は、見出しの横に小さな回る印（金型 components/loading の Spinner・size "sm"）を出す。置き場所は PageLayout の headerLeft（S frontend/src/components/PageLayout.tsx:46。包みなしで h2 の次にそのまま描く）。K1 の構造の印は `.sa-spinner` とその中を数えない（stage0-card.md V0-2）ので、この印は K1 の判定を変えない。新しい言葉・CSS・色は足さない（Spinner の読み上げは今ある common.loading）。
- V2-8 「取り直した後の中身が DB と一致（tenant 001）」は、受入で設計担当が本番の読むだけの道（ADR-1024）で tenant 001 の行を数え、画面に出る件数と比べる（§5 B6）。本番で 2 人の本物のログインを使う K5 の確かめはしない（本番でパスワードを打たない決まり）。K5 は本物の画面の試験 P2 と試しの部品の T12 で確かめ、そのことを受入の記録に書く。

## 1. 触るファイル（変更前→変更後）
| # | ファイル | 変更前 | 変更後 |
|---|---|---|---|
| 1 | frontend/src/lib/query/apiQuery.ts | useApiQuery(path, {enabled}) と invalidateApi（S 全 58 行） | keepPrevious を足し・queryClient を直接渡し・useInvalidateApi を足す（§4-A 全文） |
| 2 | frontend/src/pages/admin/ChannelMastersPage.tsx | useState と useEffect で読む（S :28-47） | useApiQuery で読む（§4-B 全文） |
| 3 | frontend/src/pages/suppliers/SuppliersPage.tsx | 同上（S :44・:53・:58・:62-77） | 同上（§4-C の置き換え 9 か所） |
| 4 | frontend/src/pages/companies/CompaniesPage.tsx | 同上（S :189・:202・:206-221） | 同上（§4-D の置き換え 6 か所） |
| 5 | frontend/src/lib/query/apiQuery.test.tsx | T1〜T9 | T11〜T13 を足す（§4-E） |
| 6 | frontend/src/lib/query/stage2Pages.test.tsx | 無い | 新しく作る。P1〜P4（§4-F 全文） |
| 7 | frontend/src/components/MasterSearchButtonMigration.test.tsx | afterEach で写しを消さない | afterEach で queryClient.clear()（§4-G） |
| 8 | frontend/src/components/PageFormButtonMigration.test.tsx | 同上 | 同上（§4-G） |
| 9 | docs/handoff/line-like-speed/stage2-card.md | 無い | このカード（設計担当が書いた。実装役は触らない） |
| 10 | docs/handoff/line-like-speed/design.md | §3-4-4 まで | §3-4-5 に段 2 のカードの場所を書き足し済み（設計担当。実装役は触らない） |
| 11 | .claude-pipeline/active-work.d/release-line-like-speed-stage2-card.md | 無い | 作業の札（設計担当。実装役は触らない） |

## 2. 触らない範囲
- backend/・migrations/・.github/workflows/・scripts/・tests/prod-check/・frontend/viewer/ は触らない（design §3-3）。
- frontend/src/lib/api.ts・frontend/src/contexts/AuthContext.tsx・frontend/src/lib/auth/・frontend/src/lib/query/QueryAuthSync.tsx・frontend/src/App.tsx は触らない。
- frontend/src/components/（PageLayout・Spinner・LoadingBlock を含む）・CSS・ja.json・en.json は触らない。新しい言葉・色・寸法を足さない。
- 3 画面の中の、読み方（path の作り方）・書き方（post・patch・delete の path と中身）・書き出し（getBlob）・表の列・ボタン・モーダル・ドロワーは変えない。変えるのは §4-B〜§4-D に書いた行だけ。
- QueryClient を apiQuery.ts の外で作らない（試験の中でも作らない）。staleTime を設定しない。写しをブラウザの保存に書かない。
- 3 画面のほかの画面は変えない（段 3 で 10 画面ずつ）。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) 最新の origin/main で、§1 #1〜#4・#7・#8 が S と同じか（`git diff --stat 508e86036 origin/main -- frontend/src` が空か）。空でなければ、変わったファイルの名前と行数を報告に書く。#1〜#8 のどれかが変わっていたら停止して報告する。ほかのファイルだけなら続ける。
- (b) `cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json` が `"5.104.4"` の 1 行。違えば停止して報告する。
- (c) `cd <W>/frontend && grep -n 'export function useQuery' node_modules/@tanstack/react-query/build/modern/useQuery.d.ts` で、2 つ目の引数 `queryClient?: QueryClient` があること。無ければ停止して報告する（V2-5 が成り立たない）。
- (d) `cd <W>/frontend && grep -n 'PlaceholderDataFunction' node_modules/@tanstack/query-core/build/modern/hydration-*.d.ts | head -3` で型があること（ファイル名は版で違う。0 行なら `grep -rln 'type PlaceholderDataFunction' node_modules/@tanstack/query-core/build/modern | head -3` で探し、出たファイルの該当行を報告に書く）。どこにも無ければ停止して報告する。
- (e) 試験の中では import.meta.env.DEV が true で、AuthProvider 無しの useAuth は uid "e2e-test-user-uid" の人を返す（S frontend/src/contexts/AuthContext.tsx:167-189）。手順 4 の #7・#8 の試験が「uid が null で取りに行かない」理由で落ちたら（get が 1 回も呼ばれない）、停止して NEEDS_DECISION: で生の出力を返す。試験を包み直して直さない。
- (f) 手順 2 で、変える前の 3 画面の lint の警告の数を数えておく（手順 2 の命令）。変えた後は、その数より増えないこと（0 になってもよい）。増えたら直す。直せない時は停止する。
- (g) P1〜P4・T11〜T13 のどれかが落ちたら、試験を書き換えて通さない。画面か apiQuery.ts の §4 の写し違いを探し、写し違いが無ければ停止して NEEDS_DECISION: で生の出力を返す。とくに T12・P2（K5）は、落ちたら直し方を自分で考えずに停止する。

## 4-A. #1 frontend/src/lib/query/apiQuery.ts（全文で置き換える）
```ts
/**
 * ADR-1054: 画面が取ったデータの写しの置き場（この 1 か所だけ）。
 * - QueryClient はここで 1 個だけ作る。ほかの場所で作らない。
 * - 取り方は useApiQuery だけ。中で今の api.get を呼ぶ（通信・送り直し・401 の扱いは api.ts のまま）。
 * - 写しは出すだけ。staleTime は既定の 0 のままにし、開くたび・タブに戻るたびに取り直す。
 * - 写しはメモリだけに持つ（ブラウザの保存に書かない）。
 */
import { useCallback } from "react";
import {
  QueryClient,
  useQuery,
  type QueryKey,
  type UseQueryResult,
} from "@tanstack/react-query";

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

/**
 * 写しを出してから裏で取り直す取り方。ログインしていない間は取りに行かない。
 * keepPrevious: 条件（ページ・検索）を変えた時、前の条件の中身を出したまま取る。
 * queryClient を直接渡すので、QueryClientProvider の外（画面の試験）でも同じ 1 個を使う。
 */
export function useApiQuery<T>(
  path: string,
  options?: { enabled?: boolean; keepPrevious?: boolean },
): UseQueryResult<T> {
  const { user } = useAuth();
  const uid = user?.uid ?? null;
  // 前の条件の中身は同じ人の写しの時だけ出す。利用者が変わった最初の描画では前の人の写しがまだ残っているため。
  // uid が変わったら関数を作り直す（同じ関数だと TanStack が前の結果を使い回す）。
  const keepSameUser = useCallback(
    <D,>(previousData: D | undefined, previousQuery: { queryKey: QueryKey } | undefined): D | undefined =>
      previousQuery?.queryKey[1] === uid ? previousData : undefined,
    [uid],
  );
  return useQuery(
    {
      queryKey: apiQueryKey(uid ?? "", path),
      queryFn: () => api.get<T>(path),
      enabled: uid !== null && (options?.enabled ?? true),
      placeholderData: options?.keepPrevious ? keepSameUser : undefined,
    },
    queryClient,
  );
}

/**
 * 頭の言葉が同じ写しを全部取り直す（条件や id が違う写しも含む）。
 * 例: invalidateApi(uid, ["companies"]) は /companies?… も /companies/5 も取り直す。
 */
export function invalidateApi(uid: string, head: readonly string[]): Promise<void> {
  const { words } = splitApiPath(head.join("/"));
  return queryClient.invalidateQueries({ queryKey: ["api", uid, ...words] });
}

/** 画面が書いた後に使う。今の人の写しのうち、頭の言葉が同じ物を取り直す。ログインしていない時は何もしない。 */
export function useInvalidateApi(): (head: readonly string[]) => Promise<void> {
  const { user } = useAuth();
  const uid = user?.uid ?? null;
  return useCallback(
    (head: readonly string[]) => (uid === null ? Promise.resolve() : invalidateApi(uid, head)),
    [uid],
  );
}
```
- keepSameUser は型の指定を付けず、関数そのものを総称（`<D,>`）にする。理由: 5.104.4 の placeholderData の型は `PlaceholderDataFunction<NonFunctionGuard<TQueryData>, …>`（query-core の hydration-*.d.ts の placeholderData の行）で、中身の分からない T に `PlaceholderDataFunction<T, …>` を付けると TS2769 で落ちる（第 1 版の審査で実測）。`NonFunctionGuard` は外から使えない型。第 1 版の審査役がこの書き方で tsc 0 件・lint 0 件・T11〜T13 合格を確かめた。tsc がこの行で落ちたら、生の誤りを報告に書いて停止する（型を any で逃がさない）。

## 4-B. #2 frontend/src/pages/admin/ChannelMastersPage.tsx（全文で置き換える）
```tsx
/**
 * ChannelMastersPage — テナント管理者用 手動チャネル管理
 *
 * 手動記録（SA-02 Stage 3）で使用するチャネルを追加・削除できる。
 * 自動連携チャネル（connection_type='auto'）は表示のみ（削除不可）。
 *
 * ルート: /admin/channel-masters
 * 権限: tenant.profile.edit（既存 admin 権限を流用）
 */
import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { TextFieldControl } from "../../components/TextField";
import { LoadingBlock, Spinner } from "../../components/loading";

interface ChannelMaster {
  id: number;
  platform: string;
  display_name: string;
  connection_type: "auto" | "manual";
  is_active: boolean;
}

/** 応答は配列か { data: 配列 } のどちらか（今までの読み方のまま） */
type ChannelMastersResponse = ChannelMaster[] | { data?: ChannelMaster[] };

/** 書いた後に取り直す写しの頭（ADR-1054） */
const CHANNEL_MASTERS_HEAD = ["channel-masters"] as const;

export default function ChannelMastersPage() {
  const { t } = useTranslation();
  // 写しを先に出して裏で取り直す（ADR-1054 段 2）
  const channelsQuery = useApiQuery<ChannelMastersResponse>("/channel-masters");
  const invalidate = useInvalidateApi();
  const channels: ChannelMaster[] = Array.isArray(channelsQuery.data)
    ? channelsQuery.data
    : channelsQuery.data?.data ?? [];
  const [newPlatform, setNewPlatform] = useState("");
  const [newDisplayName, setNewDisplayName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const shownError = error ?? (channelsQuery.isError ? t("channelMasters.loadError") : null);

  const handleAdd = useCallback(async () => {
    const platform = newPlatform.trim();
    const displayName = newDisplayName.trim();
    if (!platform || !displayName) return;
    setSaving(true);
    setError(null);
    try {
      await api.post("/admin/channel-masters", { platform, display_name: displayName });
      setNewPlatform("");
      setNewDisplayName("");
      void invalidate(CHANNEL_MASTERS_HEAD);
    } catch {
      setError(t("channelMasters.saveError"));
    } finally {
      setSaving(false);
    }
  }, [newPlatform, newDisplayName, invalidate, t]);

  const handleDelete = useCallback(async (id: number) => {
    setError(null);
    try {
      await api.delete(`/admin/channel-masters/${id}`);
      void invalidate(CHANNEL_MASTERS_HEAD);
    } catch {
      setError(t("channelMasters.deleteError"));
    }
  }, [invalidate, t]);

  return (
    <PageLayout
      navKey="nav.channelMasters"
      headerLeft={channelsQuery.isFetching && !channelsQuery.isPending ? <Spinner size="sm" /> : undefined}
    >
      {channelsQuery.isPending ? (
        <LoadingBlock />
      ) : (
        <>
          <table className="channel-masters-table">
            <thead>
              <tr>
                <th>{t("channelMasters.platform")}</th>
                <th>{t("channelMasters.displayName")}</th>
                <th>{t("channelMasters.type")}</th>
                <th>{t("channelMasters.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {channels.map((ch) => (
                <tr key={ch.id}>
                  <td>{ch.platform}</td>
                  <td>{ch.display_name}</td>
                  <td>{ch.connection_type === "auto" ? t("channelMasters.typeAuto") : t("channelMasters.typeManual")}</td>
                  <td>
                    {ch.connection_type === "manual" && (
                      <button
                        type="button"
                        onClick={() => handleDelete(ch.id)}
                        aria-label={t("channelMasters.deleteAriaLabel", { name: ch.display_name })}
                      >
                        {t("channelMasters.delete")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {shownError && <p role="alert" className="channel-masters-error">{shownError}</p>}

          <div className="channel-masters-add-form">
            <h3>{t("channelMasters.addTitle")}</h3>
            <TextFieldControl
              type="text"
              value={newPlatform}
              onChange={(e) => setNewPlatform(e.target.value)}
              placeholder={t("channelMasters.platformPlaceholder")}
              aria-label={t("channelMasters.platform")}
              disabled={saving}
              style={{ width: "auto" }}
            />
            <TextFieldControl
              type="text"
              value={newDisplayName}
              onChange={(e) => setNewDisplayName(e.target.value)}
              placeholder={t("channelMasters.displayNamePlaceholder")}
              aria-label={t("channelMasters.displayName")}
              disabled={saving}
              style={{ width: "auto" }}
            />
            <Button
              type="button"
              variant="primary"
              size="md"
              loading={saving}
              onClick={handleAdd}
              disabled={saving || !newPlatform.trim() || !newDisplayName.trim()}
              aria-label={t("channelMasters.add")}
            >
              {t("channelMasters.add")}
            </Button>
          </div>
        </>
      )}
    </PageLayout>
  );
}
```
- 変わったのは: import 2 行（apiQuery・Spinner）、型と頭の定数、読む所（S :28-29・:35-47 を useApiQuery に）、エラーの出し方（shownError）、書いた後の load() を invalidate に、PageLayout の headerLeft、`loading ?` を `channelsQuery.isPending ?` に。表とフォームの行は S :83-147 と同じ（`git diff -w` で確かめる・§5 B3）。

## 4-C. #3 frontend/src/pages/suppliers/SuppliersPage.tsx（置き換え 9 か所。ほかの行は変えない）
- C1 S :1-2 の 2 行を次の 2 行に替える。
```tsx
import { LoadingBlock, Spinner } from "../../components/loading";
import { useRef, useState, FormEvent } from "react";
```
- C2 S :8 `import { api } from "../../lib/api";` の次に 1 行足す。
```tsx
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
```
- C3 S :38（空行）と S :39 `export default function SuppliersPage() {` の間に 2 行足す（S :37 は `});`。:38 の空行は残し、足した 2 行の後にも空行を 1 つ置く）。
```tsx
/** 書いた後に取り直す写しの頭（ADR-1054） */
const SUPPLIERS_HEAD = ["suppliers"] as const;

```
- C4 S :44 `  const [suppliers, setSuppliers] = useState<Supplier[]>([]);`・S :53 `  const [loading, setLoading] = useState(true);`・S :58 `  const [hasNext, setHasNext] = useState(false);` の 3 行を消す。
- C5 S :63-77（`  const load = async () => {` から `  useEffect(() => { load(); }, [page, search]);` まで。間の eslint-disable の行も含む。S :62 の空行は残す）を次に替える。
```tsx
  const params = new URLSearchParams({ page: String(page), per_page: String(PER_PAGE) });
  if (search.trim()) params.set("search", search.trim());
  // 写しを先に出して裏で取り直す。ページや検索を変えた時は前の行を出したまま取る（ADR-1054 段 2）
  const suppliersQuery = useApiQuery<Supplier[]>(`/suppliers?${params.toString()}`, { keepPrevious: true });
  const invalidate = useInvalidateApi();
  const suppliers = suppliersQuery.data ?? [];
  const hasNext = suppliers.length === PER_PAGE;
  const shownError = error || (suppliersQuery.error
    ? (suppliersQuery.error instanceof Error ? suppliersQuery.error.message : t("common.fetchError"))
    : "");
  /** 書いた後に一覧を取り直す（ページ・検索の違う写しも含む） */
  const load = () => { void invalidate(SUPPLIERS_HEAD); };
```
  - 書いた後の 3 か所（S :86・:98・:105 の `load();`）はそのまま（load の中身が取り直しに替わる）。
- C6 S :130-132 の `<PageLayout` の中、S :132 `subtitleKey="suppliers.subtitle"` の次の行に 1 行足す。
```tsx
      headerLeft={suppliersQuery.isFetching && !suppliersQuery.isPending ? <Spinner size="sm" /> : undefined}
```
- C7 S :153 を替える。
```tsx
      {shownError && <div className="error-message">{shownError}</div>}
```
- C8 S :232 の `      {loading ? <LoadingBlock /> : (() => {` を `      {suppliersQuery.isPending ? <LoadingBlock /> : (() => {` に、S :259 の `      {!loading && suppliers.length > 0 && (` を `      {!suppliersQuery.isPending && suppliers.length > 0 && (` に替える。
- C9 ページ送りのボタン（V2-3）: S :280 `              disabled={page <= 1}` を `              disabled={page <= 1 || suppliersQuery.isPlaceholderData}` に、S :293 `              disabled={!hasNext}` を `              disabled={!hasNext || suppliersQuery.isPlaceholderData}` に替える。
- 終わったら `grep -n 'setSuppliers\|setHasNext\|setLoading\|useEffect' frontend/src/pages/suppliers/SuppliersPage.tsx` が 0 行であること。

## 4-D. #4 frontend/src/pages/companies/CompaniesPage.tsx（置き換え 6 か所。ほかの行は変えない）
- D1 S :12 `import { useEffect, useState, FormEvent } from "react";` を `import { useState, FormEvent } from "react";` に、S :31 `import { LoadingBlock } from "../../components/loading";` を `import { LoadingBlock, Spinner } from "../../components/loading";` に替え、S :15 `import { api } from "../../lib/api";` の次に 1 行足す。
```tsx
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
```
- D2 S :185 `export default function CompaniesPage() {` の直前（前の行が空行であることを確かめる。空行でなければ空行を 1 つ入れてから）に 3 行足す。
```tsx
/** 書いた後に取り直す写しの頭（ADR-1054） */
const COMPANIES_HEAD = ["companies"] as const;

```
- D3 S :189 `  const [companies, setCompanies] = useState<Company[]>([]);` と S :202 `  const [loading, setLoading] = useState(true);` の 2 行を消す。
- D4 S :206-221（`  const loadCompanies = async () => {` から `  useEffect(() => { loadCompanies(); }, [search]);` まで。間の空行と eslint-disable の行も含む）を次に替える。
```tsx
  // per_page=100 で全件を一画面に表示（highlife-jpn: 49 社、将来の増加余地あり）
  const parts: string[] = ["per_page=100"];
  if (search) parts.push(`search=${encodeURIComponent(search)}`);
  // 写しを先に出して裏で取り直す。検索を変えた時は前の行を出したまま取る（ADR-1054 段 2）
  const companiesQuery = useApiQuery<Company[]>(`/companies?${parts.join("&")}`, { keepPrevious: true });
  const invalidate = useInvalidateApi();
  const companies = companiesQuery.data ?? [];
  const shownError = error || (companiesQuery.error
    ? (companiesQuery.error instanceof Error ? companiesQuery.error.message : t("common.fetchError"))
    : "");
  /** 書いた後に一覧を取り直す（検索の違う写しも含む） */
  const loadCompanies = () => { void invalidate(COMPANIES_HEAD); };
```
  - 書いた後の 3 か所（S :313・:335・:346 の `loadCompanies();`）はそのまま。
- D5 S :380-384 の `<PageLayout` の中、`subtitleKey="companies.subtitle"` の次の行に 1 行足す。
```tsx
      headerLeft={companiesQuery.isFetching && !companiesQuery.isPending ? <Spinner size="sm" /> : undefined}
```
- D6 S :386 `      {error && <div className="error-banner">{error}</div>}` を `      {shownError && <div className="error-banner">{shownError}</div>}` に、S :400 `      {loading ? (` を `      {companiesQuery.isPending ? (` に替える。
- 終わったら `grep -n 'setCompanies\|setLoading\|useEffect' frontend/src/pages/companies/CompaniesPage.tsx` が 0 行であること。

## 4-E. #5 frontend/src/lib/query/apiQuery.test.tsx（T11〜T13 を足す）
- E1 S :12 の import を次に替える。
```tsx
import { apiQueryKey, invalidateApi, queryClient, splitApiPath, useApiQuery, useInvalidateApi } from "./apiQuery";
```
- E2 S :34 の Probe の閉じ `}` の次（S :35 の空行の後）に足す。
```tsx
/** keepPrevious を使う試しの部品。描いた中身を全部 renderedData に残す（K5 で描画の途中も数える） */
const renderedData: Array<string | undefined> = [];
function KeepProbe({ path, testId }: { path: string; testId: string }) {
  const q = useApiQuery<string>(path, { keepPrevious: true });
  renderedData.push(q.data);
  return (
    <div>
      <div data-testid={testId}>{q.data ?? ""}</div>
      <div data-testid={`${testId}-placeholder`}>{String(q.isPlaceholderData)}</div>
    </div>
  );
}

let latestInvalidate: ((head: readonly string[]) => Promise<void>) | null = null;
function InvalidateProbe() {
  latestInvalidate = useInvalidateApi();
  return null;
}

```
- E3 S :52-57 の afterEach の `auth.user = { uid: "uid-A" };` の次の行に 2 行足す。
```tsx
  renderedData.length = 0;
  latestInvalidate = null;
```
- E4 ファイルの最後（S :248 の後）に足す。
```tsx

describe("keepPrevious keeps the same user's rows while the next ones load (T11)", () => {
  it("old rows stay until the new rows arrive", async () => {
    let release: (value: string) => void = () => {};
    vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === "/companies?page=2") return new Promise<string>((resolve) => { release = resolve; }) as never;
      return `rows:${path}` as never;
    });
    const tree = (path: string) => (
      <Tree>
        <KeepProbe path={path} testId="keep" />
      </Tree>
    );
    const { rerender } = render(tree("/companies?page=1"));
    await waitFor(() => expect(screen.getByTestId("keep").textContent).toBe("rows:/companies?page=1"));

    rerender(tree("/companies?page=2"));
    expect(screen.getByTestId("keep").textContent).toBe("rows:/companies?page=1");
    expect(screen.getByTestId("keep-placeholder").textContent).toBe("true");

    await act(async () => {
      release("rows:/companies?page=2");
    });
    await waitFor(() => expect(screen.getByTestId("keep").textContent).toBe("rows:/companies?page=2"));
    expect(screen.getByTestId("keep-placeholder").textContent).toBe("false");
  });
});

describe("K5: keepPrevious never carries A's rows to B (T12)", () => {
  it("A -> B with a slow B fetch renders A's rows 0 times", async () => {
    let releaseB: (value: string) => void = () => {};
    vi.spyOn(api, "get").mockImplementation(async () => {
      const uid = auth.user?.uid;
      if (uid === "uid-B") return new Promise<string>((resolve) => { releaseB = resolve; }) as never;
      return `secret-${uid}` as never;
    });
    const tree = () => (
      <Tree>
        <KeepProbe path="/companies" testId="k5keep" />
      </Tree>
    );
    const { rerender } = render(tree());
    await waitFor(() => expect(screen.getByTestId("k5keep").textContent).toBe("secret-uid-A"));

    const from = renderedData.length;
    auth.user = { uid: "uid-B" };
    rerender(tree());
    expect(screen.getByTestId("k5keep").textContent).toBe("");

    await act(async () => {
      releaseB("secret-uid-B");
    });
    await waitFor(() => expect(screen.getByTestId("k5keep").textContent).toBe("secret-uid-B"));
    expect(renderedData.slice(from).filter((data) => data === "secret-uid-A").length).toBe(0);
    expect(keysWithUid("uid-A")).toBe(0);
  });
});

describe("useInvalidateApi (T13)", () => {
  it("refetches the current user's copies and does nothing when logged out", async () => {
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) => `${auth.user?.uid}:${path}` as never);
    const tree = () => (
      <Tree>
        <Probe path="/companies?x=1" testId="inv" />
        <InvalidateProbe />
      </Tree>
    );
    const { rerender } = render(tree());
    await waitFor(() => expect(screen.getByTestId("inv").textContent).toBe("uid-A:/companies?x=1"));
    spy.mockClear();

    await act(async () => {
      await latestInvalidate?.(["companies"]);
    });
    expect(spy.mock.calls.map((call) => call[0])).toEqual(["/companies?x=1"]);

    auth.user = null;
    rerender(tree());
    spy.mockClear();
    await act(async () => {
      await latestInvalidate?.(["companies"]);
    });
    expect(spy).not.toHaveBeenCalled();
  });
});
```
- ファイルの頭のコメント（S :2）の `（T1〜T9）` を `（T1〜T9・段 2 で T11〜T13）` に替える。

## 4-F. #6 frontend/src/lib/query/stage2Pages.test.tsx（新しく作る・全文）
```tsx
/**
 * ADR-1054 段 2: 本物の 3 画面の試験（P1〜P4）。
 * P1 戻った時に写しを先に出す・P2 利用者が変わっても前の人の中身を出さない（K5）・
 * P3 書いた後に取り直す・P4 検索を変えた時は前の行を出したまま取る。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ChannelMastersPage from "../../pages/admin/ChannelMastersPage";
import CompaniesPage from "../../pages/companies/CompaniesPage";
import SuppliersPage from "../../pages/suppliers/SuppliersPage";
import { api } from "../api";
import { QueryAuthSync } from "./QueryAuthSync";
import { queryClient } from "./apiQuery";

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
vi.mock("../../hooks/usePermissions", () => ({ usePermissions: () => ({ hasPermission: () => true }) }));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
  // api.ts が i18n.ts を読み、i18n.ts が initReactI18next を使う（同じ書き方: src/pages/leads/LeadFormFields.test.tsx:6）
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

const supplier = { id: 63, name: "Fixture supplier", supplier_code: "S63", contact_name: null, email: null, phone: null, address: null, notes: null, is_active: true, created_at: "2026-11-01T00:00:00Z" };
const company = { id: 41, company_code: "C41", name: "Fixture company", status: "active", addresses: [], industry: null, priority_focus: null, notes: null };
const channel = { id: 1, platform: "line", display_name: "Fixture channel", connection_type: "manual", is_active: true };
const added = { id: 2, platform: "fixture_new", display_name: "Fixture new", connection_type: "manual", is_active: true };

const pages = {
  suppliers: { Page: SuppliersPage, path: "/suppliers?page=1&per_page=100", rows: [supplier], text: "Fixture supplier" },
  companies: { Page: CompaniesPage, path: "/companies?per_page=100", rows: [company], text: "Fixture company" },
  channels: { Page: ChannelMastersPage, path: "/channel-masters", rows: [channel], text: "Fixture channel" },
};
type Kind = keyof typeof pages;

function Tree({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <QueryAuthSync />
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(() => { throw new Error("Unexpected real network request"); }));
});

afterEach(() => {
  cleanup();
  queryClient.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  auth.user = { uid: "uid-A" };
});

describe("revisit shows the copy first (P1)", () => {
  it.each(Object.keys(pages) as Kind[])("%s shows the previous rows at once on revisit", async (kind) => {
    const c = pages[kind], Page = c.Page;
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === c.path) return c.rows as never;
      throw new Error("Unexpected GET " + path);
    });
    const first = render(<Tree><Page /></Tree>);
    await screen.findByText(c.text);
    first.unmount();

    spy.mockClear();
    spy.mockImplementation(() => new Promise<never>(() => {}));
    const { container } = render(<Tree><Page /></Tree>);
    expect(screen.getByText(c.text)).toBeTruthy();
    expect(container.querySelector(".sa-loading-block")).toBeNull();
    await waitFor(() => expect(container.querySelector(".page-layout-title-row .sa-spinner")).not.toBeNull());
    expect(spy).toHaveBeenCalledWith(c.path);
  });
});

describe("K5 on the real supplier screen (P2)", () => {
  // P2a: 写しを消す部品（QueryAuthSync）を置かずに人を変える。前の人の行を出さないのは keepSameUser の守りだけになる。
  // 守りを外す（previousData をそのまま返す）と、B の取り直しを待つ間に A の行が出てこの試験が落ちる。
  it("without the cache clear, the uid guard alone hides A's rows (P2a)", async () => {
    let releaseB: (rows: unknown) => void = () => {};
    vi.spyOn(api, "get").mockImplementation(async () => {
      const uid = auth.user?.uid;
      if (uid === "uid-B") return new Promise((resolve) => { releaseB = resolve; }) as never;
      return [{ ...supplier, name: `secret-${uid}` }] as never;
    });
    const bare = () => (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter><SuppliersPage /></MemoryRouter>
      </QueryClientProvider>
    );
    const { rerender, container } = render(bare());
    await screen.findByText("secret-uid-A");

    auth.user = { uid: "uid-B" };
    rerender(bare());
    expect(screen.queryByText("secret-uid-A")).toBeNull();
    expect(container.querySelector(".sa-loading-block")).not.toBeNull();

    await act(async () => {
      releaseB([{ ...supplier, id: 64, name: "secret-uid-B" }]);
    });
    await screen.findByText("secret-uid-B");
    expect(screen.queryByText("secret-uid-A")).toBeNull();
  });

  it("A -> B never shows A's rows on SuppliersPage", async () => {
    let releaseB: (rows: unknown) => void = () => {};
    vi.spyOn(api, "get").mockImplementation(async () => {
      const uid = auth.user?.uid;
      if (uid === "uid-B") return new Promise((resolve) => { releaseB = resolve; }) as never;
      return [{ ...supplier, name: `secret-${uid}` }] as never;
    });
    const tree = () => <Tree><SuppliersPage /></Tree>;
    const { rerender, container } = render(tree());
    await screen.findByText("secret-uid-A");

    auth.user = { uid: "uid-B" };
    rerender(tree());
    expect(screen.queryByText("secret-uid-A")).toBeNull();
    expect(container.querySelector(".sa-loading-block")).not.toBeNull();

    await act(async () => {
      releaseB([{ ...supplier, id: 64, name: "secret-uid-B" }]);
    });
    await screen.findByText("secret-uid-B");
    expect(screen.queryByText("secret-uid-A")).toBeNull();
    expect(queryClient.getQueryCache().getAll().filter((query) => query.queryKey[1] === "uid-A").length).toBe(0);
  });
});

describe("channel screen refetches after a write (P3)", () => {
  it("add and delete show the server rows again", async () => {
    let rows: unknown[] = [channel];
    const get = vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === "/channel-masters") return rows as never;
      throw new Error("Unexpected GET " + path);
    });
    const post = vi.spyOn(api, "post").mockImplementation(async () => {
      rows = [channel, added];
      return {} as never;
    });
    const del = vi.spyOn(api, "delete").mockImplementation(async () => {
      rows = [channel];
      return {} as never;
    });
    render(<Tree><ChannelMastersPage /></Tree>);
    await screen.findByText("Fixture channel");

    fireEvent.change(screen.getByRole("textbox", { name: "channelMasters.platform" }), { target: { value: "fixture_new" } });
    fireEvent.change(screen.getByRole("textbox", { name: "channelMasters.displayName" }), { target: { value: "Fixture new" } });
    const readCount = get.mock.calls.length;
    fireEvent.click(screen.getByRole("button", { name: "channelMasters.add" }));
    await screen.findByText("Fixture new");
    expect(post).toHaveBeenCalledExactlyOnceWith("/admin/channel-masters", { platform: "fixture_new", display_name: "Fixture new" });
    expect(get.mock.calls.length).toBeGreaterThan(readCount);

    fireEvent.click(screen.getAllByRole("button", { name: "channelMasters.deleteAriaLabel" })[1]);
    await waitFor(() => expect(screen.queryByText("Fixture new")).toBeNull());
    expect(del).toHaveBeenCalledExactlyOnceWith("/admin/channel-masters/2");
    expect(screen.getByText("Fixture channel")).toBeTruthy();
  });
});

describe("company search keeps the previous rows while the next ones load (P4)", () => {
  it("old rows stay with the small spinner, then the new rows replace them", async () => {
    let release: (rows: unknown) => void = () => {};
    vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === "/companies?per_page=100") return [company] as never;
      if (path === "/companies?per_page=100&search=Z") return new Promise((resolve) => { release = resolve; }) as never;
      throw new Error("Unexpected GET " + path);
    });
    const { container } = render(<Tree><CompaniesPage /></Tree>);
    await screen.findByText("Fixture company");

    fireEvent.change(screen.getByPlaceholderText("companies.searchPlaceholder"), { target: { value: "Z" } });
    expect(screen.getByText("Fixture company")).toBeTruthy();
    expect(container.querySelector(".sa-loading-block")).toBeNull();
    await waitFor(() => expect(container.querySelector(".page-layout-title-row .sa-spinner")).not.toBeNull());

    await act(async () => {
      release([{ ...company, id: 42, company_code: "C42", name: "Zeta company" }]);
    });
    await screen.findByText("Zeta company");
    expect(screen.queryByText("Fixture company")).toBeNull();
  });
});
```
- P1 の LoadingBlock の見分けは `.sa-loading-block`（S frontend/src/components/loading/LoadingBlock.tsx:18）。回る印の見分けは `.page-layout-title-row .sa-spinner`（S PageLayout.tsx:44・:46 と Spinner.tsx の class）。

## 4-G. #7・#8 今ある画面の試験の後片付け
- G1 frontend/src/components/MasterSearchButtonMigration.test.tsx: S :12 `import en from '../locales/en.json';` の次に `import { queryClient } from '../lib/query/apiQuery';` を足し、S :40 の afterEach の `cleanup();` の直後に ` queryClient.clear();` を足す（同じ行の中。`afterEach(() => { cleanup(); queryClient.clear(); expect(fetch)...`）。
- G2 frontend/src/components/PageFormButtonMigration.test.tsx: S :7 `import SuppliersPage from '../pages/suppliers/SuppliersPage';` の次に `import { queryClient } from '../lib/query/apiQuery';` を足し、S :94 `  cleanup();` の次の行に `  queryClient.clear();` を足す。
- 理由: 画面が同じ 1 個の写しの置き場を使うので、前の試験の写しが次の試験に残らないようにする。ほかの行は変えない。

## 4-H. 実装役の手順（1 手順 1 命令。<W> は手順1 で作られた作業場所の絶対パス）
手順1. クラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）どおり、作業場所を作り、push 済みの枝の先頭に合わせる（設計担当が §1 #9〜#11 を push 済み）。
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/line-like-speed-stage2-card
  （出力に出た作業場所の絶対パスを <W> として報告に書く。）
  cd <W> && git fetch origin release/line-like-speed-stage2-card
  cd <W> && git switch -C release/line-like-speed-stage2-card origin/release/line-like-speed-stage2-card
  cd <W> && git rev-parse HEAD origin/release/line-like-speed-stage2-card
  （2 行が同じことを確かめる。違えば停止して BLOCKED: で報告する。main は取り込まない。reset・rebase・force・merge・pull は使わない）
  cd <W> && ./scripts/dev/executor-preflight.sh > /tmp/stage2-preflight.txt 2>&1
  cd <W> && grep -n "FAIL" /tmp/stage2-preflight.txt | head -20
  cd <W> && grep -n "origin/main は存在" /tmp/stage2-preflight.txt | head -3
  （FAIL の行が次の 3 つのうちのどれかだけなら続ける: `GitHub API に到達不可` の 1 件・`gh auth switch --hostname github.com --user shingo-cc` の失敗の 1 件・その結果の `PREFLIGHT FAIL` の行。理由は段 1 カード §4-G 手順1 と同じ（クラウドには gh の名義が無く、api.github.com への HEAD の問い合わせは 400 になるが、git の取り寄せと push は通る）。続ける時は `[OK]   origin/main は存在` の行があることを 2 つ目の grep で確かめ、無ければ停止する。ほかの FAIL が 1 件でもあれば停止し、BLOCKED: で grep の出力を報告する。）
  cd <W> && git fetch origin main
  cd <W> && git diff --stat 508e86036 origin/main -- frontend/src | tail -5
  （§3(a) の確かめ。）
手順2. 依存を入れ、§3(b)〜(d) を確かめ、変える前の lint の警告を数える。
  cd <W>/frontend && npm ci > /tmp/stage2-ci.txt 2>&1
  cd <W> && tail -5 /tmp/stage2-ci.txt
  cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json
  cd <W>/frontend && grep -n 'export function useQuery' node_modules/@tanstack/react-query/build/modern/useQuery.d.ts
  cd <W>/frontend && grep -rln 'type PlaceholderDataFunction' node_modules/@tanstack/query-core/build/modern | head -3
  cd <W>/frontend && npx eslint src/pages/admin/ChannelMastersPage.tsx src/pages/suppliers/SuppliersPage.tsx src/pages/companies/CompaniesPage.tsx > /tmp/stage2-lint-before.txt 2>&1
  cd <W> && tail -5 /tmp/stage2-lint-before.txt
手順3. §4-A・§4-B の全文で #1・#2 を置き換え、§4-C・§4-D・§4-E・§4-G のとおり #3・#4・#5・#7・#8 を直し、§4-F の全文で #6 を作る。終わったら §4-C・§4-D の最後の grep を流す。
  cd <W> && grep -n 'setSuppliers\|setHasNext\|setLoading\|useEffect' frontend/src/pages/suppliers/SuppliersPage.tsx | head -5
  cd <W> && grep -n 'setCompanies\|setLoading\|useEffect' frontend/src/pages/companies/CompaniesPage.tsx | head -5
手順4. 型を作ってから試験を流す（写しの置き場の試験・今ある画面の試験 2 本・全部の試験・型・lint）。作る型（frontend/src/api/generated/）は .gitignore で除かれるので commit に入らない。
  cd <W>/frontend && npm run generate:api-types > /tmp/stage2-gen.txt 2>&1
  cd <W> && tail -3 /tmp/stage2-gen.txt
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/lib/query > /tmp/stage2-unit.txt 2>&1
  cd <W> && tail -30 /tmp/stage2-unit.txt
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/components/MasterSearchButtonMigration.test.tsx src/components/PageFormButtonMigration.test.tsx > /tmp/stage2-pages.txt 2>&1
  cd <W> && tail -20 /tmp/stage2-pages.txt
  cd <W>/frontend && npm run test:unit > /tmp/stage2-unit-all.txt 2>&1
  cd <W> && tail -15 /tmp/stage2-unit-all.txt
  cd <W>/frontend && npx tsc --noEmit -p . > /tmp/stage2-tsc.txt 2>&1
  cd <W> && tail -20 /tmp/stage2-tsc.txt
  cd <W>/frontend && npx eslint src/lib/query src/pages/admin/ChannelMastersPage.tsx src/pages/suppliers/SuppliersPage.tsx src/pages/companies/CompaniesPage.tsx src/components/MasterSearchButtonMigration.test.tsx src/components/PageFormButtonMigration.test.tsx > /tmp/stage2-lint.txt 2>&1
  cd <W> && tail -20 /tmp/stage2-lint.txt
  （lint の警告が手順2 の数より増えていないこと・誤りが 0 であること。§3(f)。）
手順5. 本番と同じ形で組み立てられるか確かめる。
  cd <W>/frontend && npm run build > /tmp/stage2-build.txt 2>&1
  cd <W> && tail -15 /tmp/stage2-build.txt
手順6. 変わったファイルが §1 の #1〜#8 だけか確かめ、3 画面の表とフォームの行が変わっていないことを見る。
  cd <W> && git status --short | head -20
  cd <W> && git diff -w --stat origin/release/line-like-speed-stage2-card | tail -12
  cd <W> && git diff -w origin/release/line-like-speed-stage2-card -- frontend/src/pages | head -260
手順7. commit する。
  cd <W> && git add frontend/src/lib/query/apiQuery.ts frontend/src/lib/query/apiQuery.test.tsx frontend/src/lib/query/stage2Pages.test.tsx frontend/src/pages/admin/ChannelMastersPage.tsx frontend/src/pages/suppliers/SuppliersPage.tsx frontend/src/pages/companies/CompaniesPage.tsx frontend/src/components/MasterSearchButtonMigration.test.tsx frontend/src/components/PageFormButtonMigration.test.tsx
  cd <W> && git commit -m "feat: 連絡手段・仕入先・取引先の一覧を写しを先に出して裏で取り直す形に（ADR-1054 段2）"
手順8. commit が在ることを確かめてから push する（--no-verify は使わない。push の前の検査が × なら直してから push。fast-forward でないと断られたら直さず BLOCKED:）。
  cd <W> && git log -3 --oneline
  cd <W> && git push -u origin release/line-like-speed-stage2-card
手順9. 報告を返す。PR は作らない（設計担当が手元で作る）。報告の 1 つの発言は 600 文字以内にして、番号付きの発言に分ける。

## 4. GO と承認・PO の操作
- PO の実装承認: 2026-11-01 PO 選択「1」（段 2 の作業指示書から本番に出すところまで止まらずに進める）。ADR-1054 は Accepted。このカードの審査合格の後に、設計担当がクラウドの Sonnet へ渡す。
- 触るのは frontend の画面 3 つ・写しの取り方・試験と書類だけで、migrations・deploy.yml・本番 scripts を含まない（番号付き GO の要る危ない PR ではない）。main へのマージで本番の画面に出る（deploy.yml が main への push で動く）。マージは PO の委任に基づき設計担当（Claude Opus）が、マージ前の審査役の APPROVE と必須の確認 16 件の pass の後に行う。
- PO が操作することはない。

## 5. 受入（○×）
| # | 基準 | 検証方法 |
|---|---|---|
| B1 | T1〜T13（T10 は無い）と P1〜P4 がすべて合格（K5: T12 で B に変えた後の描画に A の中身 0 回・P2 で本物の仕入先の画面に A の中身 0 件（P2a は写しを消す部品なしで守りだけ・P2 は部品ありで A の写し 0）／P1: 3 画面とも戻った時に LoadingBlock 0 個で前の行が出て、見出しの横に回る印／P3: 足す・消すの後に取り直した行が出る／P4: 検索中も前の行が出たまま） | /tmp/stage2-unit.txt の最後（2 files・19 passed。内訳: apiQuery.test.tsx 12・stage2Pages.test.tsx 7）と、PR の CI の unit-run が success |
| B2 | 今ある画面の試験（MasterSearchButtonMigration・PageFormButtonMigration）・全部の試験・型・lint・組み立てが通る | /tmp/stage2-pages.txt・stage2-unit-all.txt・stage2-tsc.txt・stage2-lint.txt・stage2-build.txt の最後と、PR の必須の確認 16 件が pass |
| B3 | 変わったのは §1 の 11 ファイルだけ。3 画面の表・フォーム・書く path と中身は変わっていない | gh pr diff --name-only と git diff -w（§4-H 手順6） |
| B4 | QueryClient を作るのは apiQuery.ts の 1 か所だけ・staleTime を設定していない・写しをブラウザの保存に書かない | `git grep -n "new QueryClient" -- frontend/src` が 1 行、`git grep -n "staleTime:" -- frontend/src` が 0 行、`git grep -n -i "persist" -- frontend/src/lib/query frontend/package.json` が 0 行 |
| B5 | マージの後、毎朝の画面の記録を手で 1 回動かし、§0 V2-2 の 5 行で K1（戻った時の秒）≤0.1 秒、K2（初めて開く秒）≤2 秒、403・5xx が 0 件。ほかの 130 行は K2 の最大と 2 秒を超えた画面の数が段 1 の受入（design §3-4-4）から悪化していない | prod-ui-check の実行の要約（設計担当。`gh workflow run prod-ui-check.yml --ref main` の後に要約の表を読む） |
| B6 | 取り直した後の中身が DB と一致（tenant 001）: 3 画面の一覧の件数が、本番 DB の同じ条件の件数と同じ | 設計担当が本番の読むだけの道（ADR-1024）で数える。仕入先: tenant_001 の suppliers で is_active が true の行（S backend の suppliers 一覧の条件・1 ページ 100 件）。取引先: tenant_001 の companies の行（1 ページ 100 件）。連絡手段: tenant_001 の channel_masters で is_active が true の行。画面の件数は、PO のログイン済みの Chrome が開ける時はそこで数える。開けない時は「画面の件数はまだ確かめていない」と記録し、P3（書いた後に取り直した行が出る）と、backend を変えていないこと（B3）を根拠にする |
| B7 | マージの後、deploy が成功し、本番の画面が開く | deploy.yml の実行の結論 success と時刻。本番 https://app.salesanchor.jp/ が開き、ブラウザの誤りの記録に TanStack 由来の誤りが無い（設計担当） |

- B5〜B7 の結果は docs/handoff/line-like-speed/design.md §3-4 に設計担当が書き足す。
- K5 を本番で 2 人のログインで確かめることはしない（本番でパスワードを打たない決まり）。K5 は B1 の T12・P2 で確かめたと記録に書く。

## 6. 戻し方
- マージの commit を git revert する PR を 1 つ出す。3 画面は今の読み方（useState と useEffect）に戻る。写しはメモリだけなので、戻した後に残る物は無い。DB には何も入っていない。

## 停止と報告
- §3 で「停止」とした時、試験が全部合格にならない時、§2 の触らない範囲を変えないと進めない時は、そこで停止する。
- 停止したら、何を実行し何が返ったかの生の出力（/tmp の報告ファイルの tail）を付けて、BLOCKED: か NEEDS_DECISION: で始まる報告を返す。推測で直さない。
- 終わったら DONE: で始まる報告に、§3 の確かめた結果、手順2・4・5 の tail、手順6 の git status、push した sha を書く。

END OF CARD
