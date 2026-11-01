# 最初の画面の写しカード（最初の画面 / の 5 か所の取り方を写しの置き場に載せる）

- 対象: docs/handoff/line-like-speed/design.md §3-2（部品）・§3-4-10（運営者の判定の写しの受入と残り）・§3-4-11（このカード）・§3-5 の K1・K5。ADR-1054（Accepted）。
- 根拠の写し: S=origin/main e4aada182（Merge #4998）。行番号はすべてこの sha。実装の前に最新の origin/main で行を合わせ直す（§3(a)）。
- 読んだ節と照合は運営者判定の写しカード（docs/handoff/line-like-speed/superadmin-cache-card.md:5）と同じ。全命令は cd <W> で始める・出力は tail/head で上限・PR は実行役が作らない・出力をファイルに残す命令と tail で読む命令は別の行。
- 実行役はクラウドの Sonnet。作業場所の作り方はクラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）を正とする。.pr-number・gh-pr-create-safe.sh は使わない。待つために sleep を使わない。
- 状態: 第 1 版（設計担当 Claude Opus・2026-11-02）。
- 受領確認: 実装役は着手の最初の報告に「最初の画面の写しカード 第 1 版を受け取った・S=e4aada182」と書く。

## 0. 何のための変更か（設計の合格線は変えない）
- P1 運営者の判定の写しの受入（design §3-4-10・prod-ui-check run 41316493378・2026-11-01 23:33 JST）の後も、最初の画面（/）の戻った時の秒（K1）は 0.59 秒。同じ回でこの行の API の数は 16、いちばん遅い API は /api/v1/me/permissions 0.6 秒。設計担当の手元の写しは /tmp/CC報告ファイル/slow-two/measure-rows.txt（リポジトリには入れない）。
- P2 / の 16 本の内訳（S のコードを読んで数えた）: 画面の本体 5 本（S frontend/src/pages/dashboard/DashboardPage.tsx:339-362・:373-385）・優先の見込み客の一覧 1 本と、一覧に出た人ごとの /leads/:id（S frontend/src/pages/dashboard/PriorityProspectsSection.tsx:142-181。本番の数は 16 から逆算すると 4 人）・今週の助言 1 本（S frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx:130-152）・成約の要因 1 本（S frontend/src/pages/dashboard/LeadConversionFactorsSection.tsx:21-36）・数字の漏斗 3 本（S frontend/src/pages/dashboard/FunnelSection.tsx:458-473）・権限 1 本。本番の組み立てでは数字の漏斗が出る（本番の /assets/main-DwNaGf09.js に `Iq="live",Lq=Iq==="mock"` があり、FUNNEL_MODE は "live"）。
- P3 5 か所とも useState と useEffect で api.get を呼び、写しの置き場を使わない。部品が出るたびに loading が true から始まり、返るまで読み込み中の印（LoadingBlock）を出す（S DashboardPage.tsx:487・:556・:592・:667、FunnelSection.tsx:496-502、PriorityProspectsSection.tsx:329-330、WeeklyAdvisorSection.tsx:300-301 付近、LeadConversionFactorsSection.tsx:82）。このため戻った時も、16 本が返るまで読み込み中の印が出たままになる。
- P4 仮説（まだ確かめていない）: 5 か所を写しの置き場（useApiQuery・S frontend/src/lib/query/apiQuery.ts:51-73）に載せると、戻った時の最初の描画に前の中身が出て、/ の K1 が 0.1 秒以下になる。確かめ方は §5 C4。下がらなければ仮説は誤りと記録して止まる。
- P5 写しの名前は今までと同じ形（["api", uid, …path の言葉, { query }]・S apiQueryKey・apiQuery.ts:41-44）。送る path は今と 1 文字も変えない（§4-B の作り方の関数は今の関数と同じ文字を作る）。/leads/:id の写しは、ほかの画面が同じ path を useApiQuery で読めば同じ 1 つを読む。データを 2 か所に持たない。利用者が変わると QueryAuthSync が写しを全部消す（S frontend/src/lib/query/QueryAuthSync.tsx:18-28）。
- P6 一覧に出た人ごとの /leads/:id は、数が変わる並びなので、useApiQuery を並べて呼べない（React の決まりで、呼ぶ数を描画ごとに変えられない）。そのため写しの置き場に useApiQueries（§4-A）を 1 つ足す。中身は useApiQuery と同じ名前・同じ取り方で、TanStack Query 5.104.4 の useQueries を使う（useQueries(options, queryClient) の形は https://unpkg.com/@tanstack/react-query@5.104.4/build/modern/useQueries.d.ts で確かめた。Context7 の /tanstack/query の useQueries の項と同じ）。
- P7 変わることは 4 つだけ。(1) 戻った時は、前の中身を出したまま裏で取り直す。取り直しの間は、見出しの横に小さい回る印（Spinner）を出す（段 2 と同じ形・S frontend/src/pages/admin/ChannelMastersPage.tsx:78）。(2) 優先の見込み客で「次の行動を足す」を保存した後は、手元で中身を書き換えず、その人の /leads/:id を取り直す（S PriorityProspectsSection.tsx:279-325 の大きな既定値の塊は消える）。(3) 今週の助言で保存した後も、その人の /leads/:id の写しを取り直す（優先の見込み客の欄に出る同じ人の中身を古いままにしないため）。(4) 誤りの出方。今は 1 度出た誤りが画面を開いている間ずっと残る（S DashboardPage.tsx:337 の error は消さない）。変更後は、どれかの取り方が誤りの時だけ誤りの画面を出す。
- P8 数字の漏斗・優先の見込み客・今週の助言には、開発と E2E のための見本の動き（FUNNEL_MODE が "mock" の時・S frontend/src/api/funnel.ts:28-32）がある。見本の時は今と同じく通信せずに見本を出す（§4-B〜§4-F）。成約の要因は今も見本が無く、見本の時も通信する。これも変えない。
- P9 前の試験の写しが次の試験に残らないよう、新しい試験ファイルの afterEach で写しの置き場（queryClient）を消す。試験の共通の準備（S frontend/src/test-setup.ts）は変えない。今、最初の画面と 4 つの欄を描く試験は無い（`git grep -l -E "DashboardPage|FunnelSection|PriorityProspectsSection|WeeklyAdvisorSection|LeadConversionFactorsSection" -- 'frontend/src/**/*.test.*'` が 0 行）。

## 1. 触るファイル（変更前→変更後）
| # | ファイル | 変更前 | 変更後 |
|---|---|---|---|
| 1 | frontend/src/lib/query/apiQuery.ts | useApiQuery・invalidateApi・useInvalidateApi | useApiQueries を 1 つ足す（§4-A） |
| 2 | frontend/src/api/funnel.ts | 6 本の取り出しの関数 | path の作り方を外に出す。最初の画面の欄だけが使う 3 本の関数を消す（§4-B） |
| 3 | frontend/src/pages/dashboard/DashboardPage.tsx | useState と useEffect で 5 本 | useApiQuery で 5 本・取り直しの印（§4-C） |
| 4 | frontend/src/pages/dashboard/FunnelSection.tsx | useState と useEffect で 3 本 | useApiQuery で 3 本（§4-D） |
| 5 | frontend/src/pages/dashboard/PriorityProspectsSection.tsx | useState と useEffect で一覧と人ごと | useApiQuery と useApiQueries・保存の後は取り直し（§4-E） |
| 6 | frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx | useState と useEffect で 1 本 | useApiQuery・保存の後に /leads/:id を取り直し（§4-F） |
| 7 | frontend/src/pages/dashboard/LeadConversionFactorsSection.tsx | useState と useEffect で 1 本 | useApiQuery（§4-G） |
| 8 | frontend/src/lib/query/dashboardPage.test.tsx | 無い | 6 本の試験（§4-H 全文） |
| 9 | docs/handoff/line-like-speed/dashboard-cache-card.md | 無い | このカード（設計担当が書いた。実装役は触らない） |
| 10 | docs/handoff/line-like-speed/design.md | §3-4-10 まで | §3-4-11 にこのカードの場所を書き足し済み（設計担当。実装役は触らない） |
| 11 | .claude-pipeline/active-work.d/release-line-like-speed-dashboard-card.md | 無い | 作業の札（設計担当。実装役は触らない） |

## 2. 触らない範囲
- backend/・migrations/・.github/workflows/・scripts/・tests/prod-check/・frontend/viewer/・frontend/tests-e2e/ は触らない。
- frontend/src/test-setup.ts・frontend/src/lib/api.ts・frontend/src/lib/query/QueryAuthSync.tsx・frontend/src/contexts/AuthContext.tsx・frontend/src/App.tsx・frontend/src/mocks/funnelFixtures.ts は触らない。apiQuery.ts は §4-A の足し算だけ。
- funnel.ts の getFunnel・getRevenueSummary・getFollowUps・getChannels・getReasons は残す（ほかの画面が使う。例: S frontend/src/pages/dashboard/FunnelRevenuePage.tsx:10・:36）。型の定義は 1 行も変えない。
- 4 つの欄と最初の画面の描き方（JSX・class の名前・言葉の鍵）は、§4 に書いた所のほかは変えない。CSS・ja.json・en.json・components/ は触らない。新しい言葉・色・寸法を足さない。
- 会話の画面（/lead-chat）は、このカードでは変えない（変更は一度に 1 つ。次のカードで扱う）。
- QueryClient を作らない。staleTime を設定しない。写しをブラウザの保存に書かない。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) 最新の origin/main で、§1 #1〜#7・frontend/src/test-setup.ts・frontend/src/mocks/funnelFixtures.ts が S と同じか（`git diff --stat e4aada182 origin/main -- frontend/src/lib/query frontend/src/api/funnel.ts frontend/src/pages/dashboard frontend/src/test-setup.ts frontend/src/mocks/funnelFixtures.ts` が空か）。違えば停止して、その出力を付けて BLOCKED: で報告する。
- (b) `cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json` が `"5.104.4"` の 1 行。違えば停止して報告する。
- (c) `cd <W> && git grep -n -E "getWeeklyAdvisorDefensive|getPriorityProspects|getLeadConversionFactors" -- frontend | head -10` の行が、funnel.ts と、それぞれを使う欄の 1 ファイル（Weekly・Priority・LeadConversionFactors）だけ。ほかの所に 1 行でもあれば停止して NEEDS_DECISION: で返す。
- (d) 手順 4 の全部の試験で、§1 #8 のほかの試験ファイルが落ちたら、試験もコードも直さずに停止し、NEEDS_DECISION: で落ちた試験の名前と生の出力（tail）を返す。
- (e) §4-H の 6 本のどれかが落ちたら、試験を書き換えて通さない。§4-A〜§4-H の写し違いを探し、写し違いが無ければ停止して NEEDS_DECISION: で生の出力を返す。とくに K5 の試験（5 本目）は、落ちたら直し方を自分で考えずに停止する。§4-H の見本の値（fixture）が型や描画に足りずに落ちた時だけ、見本の値に足りない項目を足してよい（画面のコードは変えない）。足した項目は報告に書く。
- (f) 手順 2 で、変える前の lint の警告の数を数えておく（§1 #1〜#7）。変えた後は、#1〜#8 を合わせてその数より増えないこと。増えたら直す。直せない時は停止する。
- (g) tsc が useApiQueries の戻りの型（UseQueryResult<T>[]）で誤りを出したら、型を as で曲げずに停止し、NEEDS_DECISION: で tsc の出力を返す。

## 4-A. #1 frontend/src/lib/query/apiQuery.ts（2 か所を変える）
(1) S :9-14 の import を、次で置き換える。
```ts
import {
  QueryClient,
  useQueries,
  useQuery,
  type QueryKey,
  type UseQueryResult,
} from "@tanstack/react-query";
```
(2) S :73（useApiQuery の閉じ括弧 `}`）の次の空行の後、S :75 の invalidateApi の説明の前に、次を足す（前後に空行を 1 つずつ）。
```ts
/**
 * 数が変わる path の並びを、1 本ずつ写しの置き場で取る（例: 一覧に出た人ごとの /leads/:id）。
 * 写しの名前と取り方は useApiQuery と同じ。ログインしていない間は取りに行かない。
 */
export function useApiQueries<T>(paths: readonly string[]): UseQueryResult<T>[] {
  const { user } = useAuth();
  const uid = user?.uid ?? null;
  return useQueries(
    {
      queries: paths.map((path) => ({
        queryKey: apiQueryKey(uid ?? "", path),
        queryFn: () => api.get<T>(path),
        enabled: uid !== null,
      })),
    },
    queryClient,
  );
}
```

## 4-B. #2 frontend/src/api/funnel.ts（4 か所を変える）
(1) S :11-19 の見本の import から `MOCK_PRIORITY_PROSPECTS,` の 1 行を消す（優先の見込み客の欄が直接読む・§4-E）。
(2) S :30 `const MOCK_MODE = FUNNEL_MODE === "mock";` の次の行に、次の 1 行を足す。
```ts
export const FUNNEL_MOCK = MOCK_MODE;
```
(3) S :161-179（getFunnel・getRevenueSummary・getFollowUps）を、次で置き換える。
```ts
export function funnelPath(month: string, scope?: "mine"): string {
  const params = new URLSearchParams({ month });
  if (scope) params.set("scope", scope);
  return `/analytics/funnel?${params}`;
}

export function revenueSummaryPath(month: string, scope?: "mine"): string {
  const params = new URLSearchParams({ month });
  if (scope) params.set("scope", scope);
  return `/analytics/revenue-summary?${params}`;
}

export function followUpsPath(scope?: "mine"): string {
  const params = scope ? new URLSearchParams({ scope }) : new URLSearchParams();
  return `/analytics/follow-ups?${params}`;
}

export const WEEKLY_ADVISOR_DEFENSIVE_PATH = `/analytics/weekly-advisor-defensive?${new URLSearchParams({ scope: "mine", period: "3m" })}`;

export const PRIORITY_PROSPECTS_PATH = `/analytics/priority-prospects?${new URLSearchParams({ scope: "mine" })}`;

export const LEAD_CONVERSION_FACTORS_PATH = "/analytics/lead-conversion-factors";

export function getFunnel(month: string, scope?: "mine"): Promise<FunnelResponse> {
  if (MOCK_MODE) return Promise.resolve(MOCK_FUNNEL);
  return api.get<FunnelResponse>(funnelPath(month, scope));
}

export function getRevenueSummary(month: string, scope?: "mine"): Promise<RevenueSummaryResponse> {
  if (MOCK_MODE) return Promise.resolve(MOCK_REVENUE_SUMMARY);
  return api.get<RevenueSummaryResponse>(revenueSummaryPath(month, scope));
}

export function getFollowUps(scope?: "mine"): Promise<FollowUpsResponse> {
  if (MOCK_MODE) return Promise.resolve(MOCK_FOLLOW_UPS);
  return api.get<FollowUpsResponse>(followUpsPath(scope));
}
```
(4) S :197-219（getWeeklyAdvisorDefensive・getPriorityProspects）と S :249-251（getLeadConversionFactors）を消す。前後の空行は 1 つにする。型（WeeklyAdvisorResponse・PriorityProspectsResponse・LeadConversionFactorsResponse ほか）は残す。

## 4-C. #3 frontend/src/pages/dashboard/DashboardPage.tsx（5 か所を変える）
(1) S :20 `import { useEffect, useMemo, useState } from "react";` を `import { useMemo, useState } from "react";` にする。
(2) S :33 `import { api } from "../../lib/api";` を `import { useApiQuery } from "../../lib/query/apiQuery";` にする。
(3) S :43 `import { LoadingBlock } from "../../components/loading";` を `import { LoadingBlock, Spinner } from "../../components/loading";` にする。
(4) S :328-362（5 つの useState・4 つの loading と error の useState・2 つの useEffect）を、次で置き換える。S :364-371（チャートの書式の関数）はそのまま残す。
```tsx
  const goalsQuery = useApiQuery<GoalSummary>(`/goals/summary?tab=${toApiTab(tab)}`);
  const forecastQuery = useApiQuery<Forecast>("/analytics/forecast");
  const followupsQuery = useApiQuery<FollowUps>("/analytics/followups");
  const summaryQuery = useApiQuery<DashboardSummary>(`/analytics/summary?period=${period}&tab=${toApiTab(tab)}`);
  // 受注グラフ: リードビューでは不要。タブ・期間変更時に再取得
  const chartQuery = useApiQuery<RevenueChartResponse>(`/analytics/monthly-revenue?period=${period}`, {
    enabled: tab !== "lead",
  });
  const queries = [goalsQuery, forecastQuery, followupsQuery, summaryQuery, chartQuery];

  const goals = goalsQuery.data ?? null;
  const forecast = forecastQuery.data ?? null;
  const followups = followupsQuery.data ?? null;
  const summary = summaryQuery.data ?? null;
  const revenueChart = chartQuery.data ?? null;

  const loadingFixed = goalsQuery.isPending || forecastQuery.isPending || followupsQuery.isPending;
  const loadingPeriod = summaryQuery.isPending;
  const loadingChart = tab !== "lead" && chartQuery.isPending;
  const refreshing = queries.some((q) => q.isFetching && !q.isPending);
  const error = queries.find((q) => q.error)?.error?.message ?? "";
```
  S :372-385（「受注グラフ」の説明の行と、その useEffect）は消す。消した後、S :371 の空行と S :386 の `const fmt` の間の空行は 1 つにする。
(5) S :407-409 の `<PageLayout` の属性に、`subtitleKey="dashboard.subtitle"` の次の行として、次の 1 行を足す（S :396-401 の誤りの時の PageLayout は変えない）。
```tsx
      headerLeft={refreshing ? <Spinner size="sm" /> : undefined}
```

## 4-D. #4 frontend/src/pages/dashboard/FunnelSection.tsx（3 か所を変える）
(1) S :7 `import { type KeyboardEvent, type ReactNode, useEffect, useState } from "react";` を `import { type KeyboardEvent, type ReactNode } from "react";` にする。S :452-473 を消した後に useState・useEffect を使う所がファイルに残っていれば、その名前だけ残す（`grep -n "useState\|useEffect" src/pages/dashboard/FunnelSection.tsx` で確かめる。S では :452-458 だけ）。
(2) S :10-17 の import を、次で置き換える。続けて S :19 の `import { LoadingBlock } from "../../components/loading";` の次の行に `import { useApiQuery } from "../../lib/query/apiQuery";` と `import { MOCK_FUNNEL, MOCK_FOLLOW_UPS, MOCK_REVENUE_SUMMARY } from "../../mocks/funnelFixtures";` の 2 行を足す。
```tsx
import {
  FUNNEL_MOCK,
  followUpsPath,
  funnelPath,
  revenueSummaryPath,
  type FunnelResponse,
  type RevenueSummaryResponse,
  type FollowUpsResponse,
} from "../../api/funnel";
```
(3) S :452-473（5 つの useState と useEffect）を、次で置き換える。S :496 以降（`if (loading)` と `if (error || !funnel || !revenue || !followUps)` と本体）はそのまま残す。
```tsx
  // 見本の時（開発・E2E）は今までどおり通信しない
  const funnelQuery = useApiQuery<FunnelResponse>(funnelPath(month, scope), { enabled: !FUNNEL_MOCK });
  const revenueQuery = useApiQuery<RevenueSummaryResponse>(revenueSummaryPath(month, scope), { enabled: !FUNNEL_MOCK });
  const followUpsQuery = useApiQuery<FollowUpsResponse>(followUpsPath(scope), { enabled: !FUNNEL_MOCK });

  const funnel: FunnelResponse | null = FUNNEL_MOCK ? MOCK_FUNNEL : funnelQuery.data ?? null;
  const revenue: RevenueSummaryResponse | null = FUNNEL_MOCK ? MOCK_REVENUE_SUMMARY : revenueQuery.data ?? null;
  const followUps: FollowUpsResponse | null = FUNNEL_MOCK ? MOCK_FOLLOW_UPS : followUpsQuery.data ?? null;
  const loading = !FUNNEL_MOCK && (funnelQuery.isPending || revenueQuery.isPending || followUpsQuery.isPending);
  const error = FUNNEL_MOCK ? "" : [funnelQuery, revenueQuery, followUpsQuery].find((q) => q.error)?.error?.message ?? "";
```
  MOCK_FUNNEL などの型が FunnelResponse などに合わず tsc が誤りを出したら、§3(g) と同じく as で曲げずに停止する（S funnel.ts:162 で `Promise.resolve(MOCK_FUNNEL)` を FunnelResponse として返せているので、合う見込み）。

## 4-E. #5 frontend/src/pages/dashboard/PriorityProspectsSection.tsx（6 か所を変える）
(1) S :1 `import { useCallback, useEffect, useState } from "react";` を `import { useCallback, useMemo, useState } from "react";` にする。
(2) S :3 `import { api } from "../../lib/api";` は残す（保存の patch で使う）。S :8-12 の import を、次で置き換える。続けて S :16 の `import { LoadingBlock } …` の次の行に、`import { useApiQueries, useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` と `import { MOCK_PRIORITY_PROSPECTS } from "../../mocks/funnelFixtures";` の 2 行を足す。
```tsx
import {
  FUNNEL_MOCK,
  PRIORITY_PROSPECTS_PATH,
  type PriorityProspectAxisBreakdown,
  type PriorityProspectItem,
  type PriorityProspectsResponse,
} from "../../api/funnel";
```
(3) S :119-123 の 5 つの useState を、次で置き換える。
```tsx
  const invalidate = useInvalidateApi();
  // 見本の時（開発・E2E）は今までどおり一覧を通信せずに出す
  const listQuery = useApiQuery<PriorityProspectsResponse>(PRIORITY_PROSPECTS_PATH, { enabled: !FUNNEL_MOCK });
  const items: PriorityProspectItem[] = FUNNEL_MOCK ? MOCK_PRIORITY_PROSPECTS.items : listQuery.data?.items ?? [];
  const detailQueries = useApiQueries<LeadDetail>(items.map((item) => `/leads/${item.lead_id}`));
  // 一覧と、一覧に出た人の中身がそろうまで読み込み中にする（今と同じ）。取れなかった人は名前の代わりの言葉を出す（今と同じ）
  const loading = (!FUNNEL_MOCK && listQuery.isPending) || detailQueries.some((q) => q.isPending);
  const error = FUNNEL_MOCK ? null : listQuery.error ? listQuery.error.message || t("common.errorLoad") : null;
  const leadDetails = useMemo(() => {
    const byLeadId: Record<number, LeadDetail> = {};
    items.forEach((item, index) => {
      const detail = detailQueries[index]?.data;
      if (detail) byLeadId[item.lead_id] = detail;
    });
    return byLeadId;
  }, [items, detailQueries]);
  const [composerByLeadId, setComposerByLeadId] = useState<Record<number, ComposerState>>({});
```
  `detailQueries` は描画ごとに新しい配列になり、useMemo は毎回作り直す。中身は小さい（本番で 4 人）ので、このままにする。lint の react-hooks の警告（exhaustive-deps など）が出て §3(f) の数を超えたら、useMemo を外して同じ式の const にする。
(4) S :142-181（一覧と人ごとを取る useEffect）を消す。
(5) S :206-218（beginFollowUp の中の `if (!currentLead) { … }` の塊）を、次で置き換える。S :220 の依存の並び `[leadDetails, updateComposer]` は `[invalidate, leadDetails, updateComposer]` にする。
```tsx
    if (!currentLead) {
      void invalidate(["leads", String(item.lead_id)]).finally(() => {
        updateComposer(item.lead_id, { loadingLead: false });
      });
    }
```
(6) S :257-303（saveFollowUp の中の `setLeadDetails((prev) => ({ … }));` の塊・大きな既定値を含む）を、次の 1 行で置き換える。S :316 の依存の並び `[composerByLeadId, leadDetails, t, updateComposer]` は `[composerByLeadId, invalidate, leadDetails, t, updateComposer]` にする。
```tsx
      void invalidate(["leads", String(item.lead_id)]);
```
- S :329 以降の描画（`loading ? … : error ? … : items.length === 0 ? … : …`）はそのまま残す。

## 4-F. #6 frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx（5 か所を変える）
(1) S :1 `import { useCallback, useEffect, useState } from "react";` を `import { useCallback, useState } from "react";` にする。
(2) S :9 `import { getWeeklyAdvisorDefensive, type WeeklyAdvisorAction } from "../../api/funnel";` を、次で置き換える。続けて S :12 の `import { LoadingBlock } …` の次の行に `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` の 1 行を足す。
```tsx
import {
  FUNNEL_MOCK,
  WEEKLY_ADVISOR_DEFENSIVE_PATH,
  type WeeklyAdvisorAction,
  type WeeklyAdvisorResponse,
} from "../../api/funnel";
```
(3) S :120-122（actions・loading・error の 3 つの useState）を、次で置き換える。
```tsx
  const invalidate = useInvalidateApi();
  // 見本の時（開発・E2E）は今までどおり通信せずに空の並びを出す
  const listQuery = useApiQuery<WeeklyAdvisorResponse>(WEEKLY_ADVISOR_DEFENSIVE_PATH, { enabled: !FUNNEL_MOCK });
  const actions: WeeklyAdvisorAction[] = FUNNEL_MOCK ? [] : listQuery.data?.actions ?? [];
  const loading = !FUNNEL_MOCK && listQuery.isPending;
  const error = FUNNEL_MOCK ? null : listQuery.error ? listQuery.error.message || t("common.errorLoad") : null;
```
(4) S :130-152（一覧を取る useEffect）を消す。
(5) saveFollowUp の中の S :255-261（`setLeadSnapshots((prev) => ({ … }));`）の次の行に、次の 1 行を足す。S :277 の依存の並び `[composerByCompanyId, leadSnapshots, t, updateComposer]` は `[composerByCompanyId, invalidate, leadSnapshots, t, updateComposer]` にする。
```tsx
      void invalidate(["leads", String(action.lead_id)]);
```

## 4-G. #7 frontend/src/pages/dashboard/LeadConversionFactorsSection.tsx（3 か所を変える）
(1) S :1 `import { useEffect, useState } from "react";` の 1 行を消す。
(2) S :6-10 の import を、次で置き換え、その次の行に `import { useApiQuery } from "../../lib/query/apiQuery";` の 1 行を足す。
```tsx
import {
  LEAD_CONVERSION_FACTORS_PATH,
  type LeadConversionFactorItem,
  type LeadConversionFactorsResponse,
} from "../../api/funnel";
```
(3) S :17-36（3 つの useState と useEffect）を、次で置き換える。S :82-83 の `if (loading)`・`if (failed || !data)` はそのまま残す。
```tsx
  const factorsQuery = useApiQuery<LeadConversionFactorsResponse>(LEAD_CONVERSION_FACTORS_PATH);
  const data = factorsQuery.data ?? null;
  const loading = factorsQuery.isPending;
  const failed = factorsQuery.isError;
```

## 4-H. #8 frontend/src/lib/query/dashboardPage.test.tsx（新しいファイル・全文）
```tsx
/**
 * ADR-1054 最初の画面の写し（dashboard-cache-card.md）の試験。
 * 1〜4 本目 戻った時に写しを先に出す（K1）・5 本目 利用者が変わっても前の人の中身を出さない（K5）・
 * 6 本目 次の行動を保存した後にその人の中身を取り直す。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DashboardPage from "../../pages/dashboard/DashboardPage";
import { FunnelSection } from "../../pages/dashboard/FunnelSection";
import { PriorityProspectsSection } from "../../pages/dashboard/PriorityProspectsSection";
import { MOCK_FOLLOW_UPS, MOCK_FUNNEL, MOCK_PRIORITY_PROSPECTS, MOCK_REVENUE_SUMMARY } from "../../mocks/funnelFixtures";
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
  useTranslation: () => ({ t: (key: string) => key, i18n: { language: "ja" } }),
  // api.ts が i18n.ts を読み、i18n.ts が initReactI18next を使う（同じ書き方: src/lib/query/stage2Pages.test.tsx:32-36）
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

const prospect = MOCK_PRIORITY_PROSPECTS.items[0];
const prospects = { scope: "mine", items: [prospect] };
const leadPath = `/leads/${prospect.lead_id}`;
const lead = (name: string, nextAction: string | null = null) => ({
  id: prospect.lead_id,
  customer_name: name,
  company_name: null,
  next_action: nextAction,
  next_action_date: null,
});
const kpi = { pct: null, direction: "flat" };
const pageRows: Record<string, unknown> = {
  "/goals/summary?tab=sales": { monthly: [], weekly: [] },
  "/analytics/forecast": { forecast_amount: 0, open_deal_count: 0, won_amount: 0, period_start: "2026-11-01", period_end: "2026-11-30" },
  "/analytics/followups": { overdue: [], due_today: [], upcoming: [] },
  "/analytics/summary?period=1m&tab=sales": {
    period: "1m",
    start_date: "2026-10-02",
    end_date: "2026-11-01",
    leads: { total: 7, converted: 2, excluded: 1, conversion_rate: 28.6 },
    orders: { total_revenue: 0, order_count: 0, active_count: 0 },
    comparison: { leads_total: kpi, leads_cv_rate: kpi, orders_revenue: kpi, orders_count: kpi },
  },
  "/analytics/monthly-revenue?period=1m": { granularity: "monthly", entries: [] },
  "/analytics/priority-prospects?scope=mine": prospects,
  "/analytics/weekly-advisor-defensive?scope=mine&period=3m": { period: "3m", scope: "mine", stale_days: 14, actions: [] },
  "/analytics/lead-conversion-factors": {
    status: "insufficient",
    included_count: 0,
    won_count: 0,
    lost_count: 0,
    required_per_item: 10,
    item_count: 6,
    excluded: { by_status: 0, other_values: 0, no_inbound: 0, no_outbound: 0, no_reply_pair: 0, no_sales_form: 0, missing_scale_or_type: 0 },
    items: [],
  },
  [leadPath]: lead("Fixture lead"),
};
const funnelRows: Record<string, unknown> = {
  "/analytics/funnel?month=2026-11": MOCK_FUNNEL,
  "/analytics/revenue-summary?month=2026-11": MOCK_REVENUE_SUMMARY,
  "/analytics/follow-ups?": MOCK_FOLLOW_UPS,
};

function answer(rows: Record<string, unknown>) {
  return async (path: string) => {
    if (path in rows) return rows[path] as never;
    throw new Error("Unexpected GET " + path);
  };
}

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

describe("dashboard revisit shows the copy first (K1)", () => {
  it("1: the whole page shows the previous contents at once, with the small spinner", async () => {
    const spy = vi.spyOn(api, "get").mockImplementation(answer(pageRows));
    const first = render(<Tree><DashboardPage /></Tree>);
    await screen.findByText("Fixture lead");
    await waitFor(() => expect(first.container.querySelector(".sa-loading-block")).toBeNull());
    first.unmount();

    spy.mockClear();
    spy.mockImplementation(() => new Promise<never>(() => {}));
    const { container } = render(<Tree><DashboardPage /></Tree>);
    expect(screen.getByText("Fixture lead")).toBeTruthy();
    expect(screen.getByText("7")).toBeTruthy();
    expect(container.querySelector(".sa-loading-block")).toBeNull();
    await waitFor(() => expect(container.querySelector(".page-layout-title-row .sa-spinner")).not.toBeNull());
    expect(spy).toHaveBeenCalledWith("/analytics/summary?period=1m&tab=sales");
    expect(spy).toHaveBeenCalledWith(leadPath);
  });

  it("2: the first open sends the same paths as before", async () => {
    const spy = vi.spyOn(api, "get").mockImplementation(answer(pageRows));
    render(<Tree><DashboardPage /></Tree>);
    await screen.findByText("Fixture lead");
    const sent = new Set(spy.mock.calls.map((call) => call[0]));
    expect([...sent].sort()).toEqual(Object.keys(pageRows).sort());
  });

  it("3: the funnel section shows the previous contents at once", async () => {
    const spy = vi.spyOn(api, "get").mockImplementation(answer(funnelRows));
    const first = render(<Tree><FunnelSection month="2026-11" viewMode="management" /></Tree>);
    await waitFor(() => expect(first.container.querySelector(".fn-funnel-row")).not.toBeNull());
    first.unmount();

    spy.mockClear();
    spy.mockImplementation(() => new Promise<never>(() => {}));
    const { container } = render(<Tree><FunnelSection month="2026-11" viewMode="management" /></Tree>);
    expect(container.querySelector(".fn-funnel-row")).not.toBeNull();
    expect(container.querySelector(".sa-loading-block")).toBeNull();
    await waitFor(() => expect(spy).toHaveBeenCalledWith("/analytics/funnel?month=2026-11"));
  });

  it("4: the lead lookup that failed still shows the fallback label, not a loading mark", async () => {
    vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === "/analytics/priority-prospects?scope=mine") return prospects as never;
      throw new Error("lead lookup failed");
    });
    const { container } = render(<Tree><PriorityProspectsSection /></Tree>);
    await screen.findByText("dashboard.priorityFallbackLead");
    expect(container.querySelector(".sa-loading-block")).toBeNull();
  });
});

describe("K5 on the priority section", () => {
  it("5: A -> B never shows A's lead name", async () => {
    let releaseB: (rows: unknown) => void = () => {};
    vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      const uid = auth.user?.uid;
      if (uid === "uid-B" && path === "/analytics/priority-prospects?scope=mine") {
        return new Promise((resolve) => { releaseB = resolve; }) as never;
      }
      if (path === "/analytics/priority-prospects?scope=mine") return prospects as never;
      if (path === leadPath) return lead(`secret-${uid}`) as never;
      throw new Error("Unexpected GET " + path);
    });
    const tree = () => <Tree><PriorityProspectsSection /></Tree>;
    const { rerender, container } = render(tree());
    await screen.findByText("secret-uid-A");

    auth.user = { uid: "uid-B" };
    rerender(tree());
    expect(screen.queryByText("secret-uid-A")).toBeNull();
    expect(container.querySelector(".sa-loading-block")).not.toBeNull();

    await act(async () => {
      releaseB(prospects);
    });
    await screen.findByText("secret-uid-B");
    expect(screen.queryByText("secret-uid-A")).toBeNull();
    expect(queryClient.getQueryCache().getAll().filter((query) => query.queryKey[1] === "uid-A").length).toBe(0);
  });
});

describe("priority follow-up refetches the lead after saving", () => {
  it("6: save sends the patch, then the lead is read again", async () => {
    let current = lead("Fixture lead");
    const get = vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === "/analytics/priority-prospects?scope=mine") return prospects as never;
      if (path === leadPath) return current as never;
      throw new Error("Unexpected GET " + path);
    });
    const patch = vi.spyOn(api, "patch").mockImplementation(async () => {
      current = lead("Fixture lead renamed", prospect.suggested_action);
      return current as never;
    });
    render(<Tree><PriorityProspectsSection /></Tree>);
    await screen.findByText("Fixture lead");

    fireEvent.click(screen.getByRole("button", { name: "dashboard.weeklyAddFollowUp" }));
    const leadReads = get.mock.calls.filter((call) => call[0] === leadPath).length;
    fireEvent.click(screen.getByRole("button", { name: "common.add" }));
    await screen.findByText("Fixture lead renamed");
    expect(patch).toHaveBeenCalledTimes(1);
    expect(patch.mock.calls[0][0]).toBe(leadPath);
    expect(get.mock.calls.filter((call) => call[0] === leadPath).length).toBeGreaterThan(leadReads);
  });
});
```
- 2 本目は、送る path が今と 1 文字も変わらないこと（§0 P5）を確かめる。pageRows の鍵は、S の DashboardPage と 3 つの欄が tab=sales・period=1m の初めの描画で送る 9 本（画面の本体 5・優先の見込み客の一覧 1・人ごと 1・今週の助言 1・成約の要因 1）。FUNNEL_MODE は試験では "off"（.env に VITE_FUNNEL_DASHBOARD が無い）ので、数字の漏斗は 3 本目で直接描く。
- 6 本目の「次の行動を足す」と「追加」のボタンの名前は、S PriorityProspectsSection.tsx の t("dashboard.weeklyAddFollowUp")・t("common.add")。名前でボタンが見つからずに落ちた時は §3(e) に従う。

## 4-I. 実装役の手順（1 手順 1 命令。<W> は手順1 で作られた作業場所の絶対パス）
手順1. クラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）どおり、作業場所を作り、push 済みの枝の先頭に合わせる（設計担当が §1 #9〜#11 を push 済み）。
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/line-like-speed-dashboard-card
  （出力に出た作業場所の絶対パスを <W> として報告に書く。）
  cd <W> && git fetch origin release/line-like-speed-dashboard-card
  cd <W> && git switch -C release/line-like-speed-dashboard-card origin/release/line-like-speed-dashboard-card
  cd <W> && git rev-parse HEAD origin/release/line-like-speed-dashboard-card
  （2 行が同じことを確かめる。違えば停止して BLOCKED: で報告する。main は取り込まない。reset・rebase・force・merge・pull は使わない）
  cd <W> && ./scripts/dev/executor-preflight.sh > /tmp/db-preflight.txt 2>&1
  cd <W> && grep -n "FAIL" /tmp/db-preflight.txt | head -20
  cd <W> && grep -n "origin/main は存在" /tmp/db-preflight.txt | head -3
  （FAIL の行の扱いは superadmin-cache-card.md §4-H 手順1 と同じ。`GitHub API に到達不可` の 1 件・`gh auth switch --hostname github.com --user shingo-cc` の失敗の 1 件・その結果の `PREFLIGHT FAIL` の行だけなら、`[OK]   origin/main は存在` の行があることを確かめて続ける。ほかの FAIL が 1 件でもあれば停止し、BLOCKED: で grep の出力を報告する。）
  cd <W> && git fetch origin main
  cd <W> && git diff --stat e4aada182 origin/main -- frontend/src/lib/query frontend/src/api/funnel.ts frontend/src/pages/dashboard frontend/src/test-setup.ts frontend/src/mocks/funnelFixtures.ts | tail -5
  （§3(a) の確かめ。空が正しい。）
手順2. 依存を入れ、§3(b)(c) を確かめ、変える前の lint の警告を数える。
  cd <W>/frontend && npm ci > /tmp/db-ci.txt 2>&1
  cd <W> && tail -5 /tmp/db-ci.txt
  cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json
  cd <W> && git grep -n -E "getWeeklyAdvisorDefensive|getPriorityProspects|getLeadConversionFactors" -- frontend | head -10
  cd <W>/frontend && npx eslint src/lib/query/apiQuery.ts src/api/funnel.ts src/pages/dashboard/DashboardPage.tsx src/pages/dashboard/FunnelSection.tsx src/pages/dashboard/PriorityProspectsSection.tsx src/pages/dashboard/WeeklyAdvisorSection.tsx src/pages/dashboard/LeadConversionFactorsSection.tsx > /tmp/db-lint-before.txt 2>&1
  cd <W> && tail -8 /tmp/db-lint-before.txt
手順3. §4-A〜§4-G のとおり #1〜#7 を変え、§4-H の全文で #8 を作る。frontend/src/test-setup.ts は変えない。
手順4. 型を作ってから試験を流す（この試験・全部の試験・型・lint）。作る型（frontend/src/api/generated/）は .gitignore で除かれるので commit に入らない。
  cd <W>/frontend && npm run generate:api-types > /tmp/db-gen.txt 2>&1
  cd <W> && tail -3 /tmp/db-gen.txt
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/lib/query/dashboardPage.test.tsx > /tmp/db-unit.txt 2>&1
  cd <W> && tail -30 /tmp/db-unit.txt
  cd <W>/frontend && npm run test:unit > /tmp/db-unit-all.txt 2>&1
  cd <W> && tail -15 /tmp/db-unit-all.txt
  （落ちた試験があれば、次の命令の出力で名前を見て §3(d) に従う。）
  cd <W> && grep -n -E "FAIL|✗|×" /tmp/db-unit-all.txt | head -40
  cd <W>/frontend && npx tsc --noEmit -p . > /tmp/db-tsc.txt 2>&1
  cd <W> && tail -20 /tmp/db-tsc.txt
  cd <W>/frontend && npx eslint src/lib/query/apiQuery.ts src/api/funnel.ts src/pages/dashboard/DashboardPage.tsx src/pages/dashboard/FunnelSection.tsx src/pages/dashboard/PriorityProspectsSection.tsx src/pages/dashboard/WeeklyAdvisorSection.tsx src/pages/dashboard/LeadConversionFactorsSection.tsx src/lib/query/dashboardPage.test.tsx > /tmp/db-lint.txt 2>&1
  cd <W> && tail -20 /tmp/db-lint.txt
  （lint の警告が手順2 の数より増えていないこと・誤りが 0 であること。§3(f)。）
手順5. 本番と同じ形で組み立てられるか確かめる。
  cd <W>/frontend && npm run build > /tmp/db-build.txt 2>&1
  cd <W> && tail -15 /tmp/db-build.txt
手順6. 変わったファイルが §1 の #1〜#8 だけか確かめる。
  cd <W> && git status --short | head -20
  （#1〜#7 は M、#8 は ?? で出る。ほかが出たら停止して BLOCKED: で報告する。）
手順7. commit する。
  cd <W> && git add frontend/src/lib/query/apiQuery.ts frontend/src/api/funnel.ts frontend/src/pages/dashboard/DashboardPage.tsx frontend/src/pages/dashboard/FunnelSection.tsx frontend/src/pages/dashboard/PriorityProspectsSection.tsx frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx frontend/src/pages/dashboard/LeadConversionFactorsSection.tsx frontend/src/lib/query/dashboardPage.test.tsx
  cd <W> && git commit -m "perf: 最初の画面の取り方を写しの置き場に載せる（ADR-1054）"
手順8. commit が在ることを確かめてから push する（--no-verify は使わない。push の前の検査が × なら直してから push。fast-forward でないと断られたら直さず BLOCKED:）。
  cd <W> && git log -3 --oneline
  cd <W> && git push -u origin release/line-like-speed-dashboard-card
手順9. 報告を返す。PR は作らない（設計担当が手元で作る）。報告の 1 つの発言は 600 文字以内にして、番号付きの発言に分ける。

## 4-J. GO と承認・PO の操作
- PO の実装承認: 2026-11-01 PO 選択「1」（会話の画面と最初の画面が遅い理由を調べて、直して本番まで進める）。ADR-1054 は Accepted。このカードの審査合格の後に、設計担当がクラウドの Sonnet へ渡す。
- 触るのは frontend の画面 1 つと 4 つの欄・写しの置き場の足し算・その試験と書類だけで、migrations・deploy.yml・本番 scripts を含まない（番号付き GO の要る危ない PR ではない）。main へのマージで本番の画面に出る。マージは PO の委任に基づき設計担当（Claude Opus）が、マージ前の審査役の APPROVE と必須の確認すべての pass の後に行う。
- PO が操作することはない。

## 5. 受入（○×）
| # | 基準 | 検証方法 |
|---|---|---|
| C1 | §4-H の 6 本がすべて合格（K1: 1・3 本目で戻った時の読み込み中の印 0 件／送る path が今と同じ: 2 本目／K5: 5 本目で利用者を変えた後の描画に前の人の名前 0 件／保存の後に取り直す: 6 本目） | /tmp/db-unit.txt の最後（1 file・6 passed）と、PR の CI の unit-run が success |
| C2 | 全部の試験・型・lint・組み立てが通る | /tmp/db-unit-all.txt・db-tsc.txt・db-lint.txt・db-build.txt の最後と、PR の必須の確認すべてが pass |
| C3 | 変わったのは §1 の 11 ファイルだけ | gh pr diff --name-only |
| C4 | マージの後、毎朝の画面の記録を手で 1 回動かし、/ の行で K1（戻った時の秒）≤0.1 秒、403・5xx が 0 件。ほかの行は K2 の最大と 2 秒を超えた画面の数が §3-4-10 から悪化していない。/ の K1 が下がらなければ §0 P4 の仮説は誤りと記録して止まる | prod-ui-check の実行の要約（設計担当。`gh workflow run prod-ui-check.yml --ref main` の後に要約の表を読む）。測る前に、その時の本番の反映が終わっていることを確かめる |
| C5 | マージの後、deploy が成功し、本番の画面が開く | deploy.yml の実行の結論 success と時刻。本番 https://app.salesanchor.jp/ が開く（設計担当） |

- C4・C5 の結果は docs/handoff/line-like-speed/design.md §3-4 に設計担当が書き足す。
- K5 を本番で 2 人のログインで確かめることはしない（本番でパスワードを打たない決まり）。K5 は C1 の 5 本目と、P5（写しの名前に uid が入る・利用者が変わると消える）で確かめたと記録に書く。

## 6. 戻し方
- マージの commit を git revert する PR を 1 つ出す。5 か所は今の読み方（useState と useEffect）に戻る。写しはメモリだけなので、戻した後に残る物は無い。DB には何も入っていない。

## 停止と報告
- §3 で「停止」とした時、試験が全部合格にならない時、§2 の触らない範囲を変えないと進めない時は、そこで停止する。
- 停止したら、何を実行し何が返ったかの生の出力（/tmp の報告ファイルの tail）を付けて、BLOCKED: か NEEDS_DECISION: で始まる報告を返す。推測で直さない。
- 終わったら DONE: で始まる報告に、§3 の確かめた結果、手順2・4・5 の tail、手順6 の git status、push した sha を書く。

END OF CARD
