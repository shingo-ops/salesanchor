# 段 3 の 3 回目の実装カード（残りの 8 画面を「写しを先に出して裏で取り直す」形に変える）

- 対象: docs/handoff/line-like-speed/design.md §3-2（部品）・§3-3（触らない範囲）・§3-4 の段 3・§3-5 の K1・K2・K5・§3-7。ADR-1054（Accepted）。段 3 の 1 回目・2 回目のカード（docs/handoff/line-like-speed/batch3a-card.md・batch3b-card.md）の部品と形をそのまま使う。
- 根拠の写し: S=origin/main 5c76e9029e5889b6dfebe33a94036edd6f696856。行番号はすべてこの sha。2026-11-02 に設計担当が S の写しで行を読んだ。実装の前に最新の origin/main で行を合わせ直す（§3(a)）。
- 読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/04-worktree.md・guards/05-pr.md・guards/10-executor.md・scripts/agent-hooks/cloud/rules.md（段 3 の 1 回目・2 回目のカードと同じ節。照合も同じ: 全命令は cd <W> で始める・出力は tail/head で上限・新しいファイルは丸ごとの全文・作業場所は new-worktree.sh で作り出力をパイプに通さない・PR は実行役が作らない・出力をファイルに残す命令と tail で読む命令は別の行）。
- 実行役はクラウドの Sonnet。作業場所の作り方はクラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）を正とする。.pr-number・gh-pr-create-safe.sh は使わない。出力には上限を付ける。待つために sleep を使わない。
- 状態: 第 1 版（2026-11-02 設計担当 Claude Opus）。クラウド審査の前。
- 受領確認: 実装役は着手の最初の報告に「段 3 の 3 回目のカード 第 1 版を受け取った・S=5c76e9029」と書く。

## 0. 設計からの直し・詳しくした点（V3c。設計の合格線は変えない）
- V3c-1 対象は、段 3 の 2 回目の受入の回（prod-ui-check run 41409815435）で K1（戻った時の秒）が 0.1 秒を超えた残りの 8 画面（design §3-4-14-a の「残り」）。PO 選択「1」（残りの 8 画面も同じ形で、本番の測定まで直す）。/inventory は 10 秒で見分けられなかった行で、このカードの対象ではない。

  | 行 | 画面のファイル | K1 の基準（秒） |
  |---|---|---|
  | /suppliers/:id/edit | pages/suppliers/SupplierEditPage.tsx | 0.17 |
  | /own-inventory | pages/inventory/OwnInventoryPage.tsx | 0.16 |
  | /dashboard/follow-ups | pages/dashboard/FollowUpsPage.tsx | 0.16 |
  | /invoices/new | pages/invoice-create/InvoiceCreatePage.tsx | 0.16 |
  | /invoices | pages/invoices/InvoicesPage.tsx | 0.16 |
  | /teams/:id/edit | pages/teams/TeamEditPage.tsx | 0.16 |
  | /dashboard/revenue | pages/dashboard/FunnelRevenuePage.tsx | 0.16 |
  | /dashboard/reasons | pages/dashboard/FunnelReasonsPage.tsx・api/funnel.ts | 0.16 |

- V3c-2 写しの置き場の部品（S frontend/src/lib/query/apiQuery.ts）と、フォームの初めの値を写しから作る部品（S frontend/src/lib/query/useSeededForm.ts）は変えない。使うのは useApiQuery（keepPrevious つき）・useInvalidateApi・useSeededForm だけ。QueryClient を足さない・staleTime を設定しない・写しをブラウザの保存に書かない。
- V3c-3 一覧と詳しい画面（請求書一覧・自社在庫・要フォロー顧客・売上の内訳・成約と失注の理由）は段 3 の 1 回目・2 回目と同じ形にする: 写しがあればすぐ出す・読み込み中の印（LoadingBlock）は写しが無い初回（isPending）だけ・写しを出したまま裏で取り直している間は見出しの横に小さな回る印（金型 components/loading の Spinner・size "sm"・PageLayout の headerLeft）。条件（ページ・絞り込み）を変えた時は前の行を出したまま取る（keepPrevious。請求書一覧と自社在庫）。自社在庫は前の行を出している間「次へ」を押せなくする（isPlaceholderData）。
- V3c-4 編集の画面（チームの編集・仕入先の編集）は、段 3 の 1 回目の Bot の編集（S pages/bots/BotEditPage.tsx:35・:48-55・:70）と同じ形にする: useSeededForm で写しからフォームを作る・保存できた後に写しを古い印にしてから一覧へ戻る・回る印は出さない。取れなかった時の文は shownError の 1 か所。
- V3c-5 請求書を作る画面の「承認済みの見積の一覧」は、見積一覧で「承認済み」に絞った時と同じ path（`/quotes?status=approved`。S pages/quotes/QuotesPage.tsx の絞り込みが作る文字列）なので同じ写しを使う。見積を選ぶ形の時だけ取る（今と同じ）。見積を選ぶ形に戻した時に前の誤りの文を消す（今は effect の中の `setError("")`。S :100）のは、ボタンの中で消す形に移す。作る画面なので回る印は出さない。
- V3c-6 売上の内訳・成約と失注の理由・要フォロー顧客は、段 3 の 2 回目のリード流入（batch3b-card.md §4-B）と同じく、funnel の path を作る関数（revenueSummaryPath・followUpsPath と、このカードで足す reasonsPath）で写しの名前を決め、`enabled: !FUNNEL_MOCK` で取る。VITE_FUNNEL_DASHBOARD が mock の時は今と同じく見本（S frontend/src/mocks/funnelFixtures の MOCK_*）を出す。取れなかった時の出し方は今と同じ（売上と理由は common.errorLoad の文・要フォロー顧客は文を出さない）。
- V3c-7 成約と失注の理由の切り替え（won・lost）は keepPrevious を付けない（切り替えた先の中身が違うので、前の中身を出したままにしない）。1 度開いた側は写しからすぐ出る。
- V3c-8 今ある画面の試験のうち、CommerceSubmitButtonMigration.test.tsx だけ `cleanup();` の後に写しを消していないので、`queryClient.clear();` を足す（段 3 の 1 回目・2 回目の §4-K と同じ）。ほかの 4 本（TeamFormButtonMigration・FullPageFormButtonMigration・CommerceNavigationButtonMigration・AllLegacyButtonDynamicMigration）は S で消し済みなので変えない。
- V3c-9 受入（§5 B5）は、8 行すべてで K1 ≤0.1 秒・K2 ≤2 秒・403 と 5xx が 0 件。K5 は段 3 の 1 回目の Q2・Q3（Bot 編集と useSeededForm の試験）と、写しの名前に利用者が入る作りで確かめる（本番で 2 人のログインは使わない）。

## 1. 触るファイル（変更前→変更後）
| # | ファイル | 変更前 | 変更後 |
|---|---|---|---|
| 1 | frontend/src/api/funnel.ts | getReasons が path を中で作る（S :211-218） | reasonsPath を足し、getReasons がそれを使う（§4-A） |
| 2 | frontend/src/pages/dashboard/FunnelReasonsPage.tsx | useState と useEffect で読む（S :20-21・:28-33） | useApiQuery（§4-B） |
| 3 | frontend/src/pages/dashboard/FunnelRevenuePage.tsx | 同上（S :26-27・:34-39） | 同上（§4-C） |
| 4 | frontend/src/pages/dashboard/FollowUpsPage.tsx | 同上（S :63-64・:73-80） | 同上（§4-D） |
| 5 | frontend/src/pages/invoices/InvoicesPage.tsx | 同上（S :47・:49-50・:52-65） | 同上（§4-E） |
| 6 | frontend/src/pages/inventory/OwnInventoryPage.tsx | 同上（S :34・:36-37・:42-59） | 同上（§4-F） |
| 7 | frontend/src/pages/invoice-create/InvoiceCreatePage.tsx | 同上（S :91-92・:97-106） | 同上（§4-G） |
| 8 | frontend/src/pages/teams/TeamEditPage.tsx | 同上（S :24・:26・:28-43） | useApiQuery＋useSeededForm（§4-H） |
| 9 | frontend/src/pages/suppliers/SupplierEditPage.tsx | 同上（S :26・:28・:30-46） | useApiQuery＋useSeededForm（§4-I） |
| 10 | frontend/src/components/CommerceSubmitButtonMigration.test.tsx | cleanup の後に写しを消さない | cleanup の後に queryClient.clear()（§4-K） |
| 11 | frontend/src/lib/query/batch3cPages.test.tsx | 無い | 新しく作る。Q1（§4-L 全文） |
| 12 | docs/handoff/line-like-speed/batch3c-card.md | 無い | このカード（設計担当が書いた。実装役は触らない） |
| 13 | docs/handoff/line-like-speed/design.md | §3-4-14-a まで | §3-4-15 にこのカードの場所を書き足し済み（設計担当。実装役は触らない） |
| 14 | .claude-pipeline/active-work.d/release-line-like-speed-batch3c.md | 無い | 作業の札（設計担当。実装役は触らない） |

## 2. 触らない範囲
- backend/・migrations/・.github/workflows/・scripts/・tests/prod-check/・frontend/viewer/ は触らない（design §3-3）。
- frontend/src/lib/api.ts・frontend/src/contexts/AuthContext.tsx・frontend/src/lib/auth/・frontend/src/lib/query/apiQuery.ts・frontend/src/lib/query/useSeededForm.ts・frontend/src/lib/query/QueryAuthSync.tsx・frontend/src/App.tsx・frontend/src/hooks/・frontend/src/mocks/ は触らない。
- frontend/src/components/（PageLayout・Spinner・LoadingBlock・TeamFormFields・SupplierFormFields を含む。試験のファイルは §4-K の行だけ）・CSS・ja.json・en.json は触らない。新しい言葉・色・寸法を足さない。
- 8 画面の中の、書き方（post・patch の path と中身）・表の列・ボタン・モーダル・ドロワー・フォームの欄・請求書を作る画面の見積の読み込み（S InvoiceCreatePage.tsx:140-170 loadQuoteForEdit）と作成（S :180-218）・要フォロー顧客の絞り込みとページ（S FollowUpsPage.tsx:82-95）は変えない。変えるのは §4 に書いた行だけ。
- funnel.ts の getFunnel・getRevenueSummary・getFollowUps・getChannels と、ほかの path を作る関数は変えない（画面が使わなくなっても消さない）。
- QueryClient を作らない（試験の中でも作らない）。staleTime を設定しない。写しをブラウザの保存に書かない。
- ほかの画面は変えない。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) 最新の origin/main で `git diff --stat 5c76e9029 origin/main -- frontend/src` が空か。空でなければ、変わったファイルの名前と行数を報告に書く。§1 #1〜#10 のどれかが変わっていたら停止して報告する。ほかのファイルだけなら続ける。
- (b) `cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json` が `"5.104.4"` の 1 行。違えば停止して報告する。
- (c) §4 の「変更前」の文が、書かれた行にそのままあること。1 か所でも無い・2 か所以上ある時は、直さずに停止して BLOCKED: で `grep -n` の出力を報告する。
- (d) 手順 2 で、変える前の 9 ファイル（§1 #1〜#9）の lint の警告の数を数えておく。変えた後は、その数より増えないこと（0 になってもよい）。増えたら直す。直せない時は停止する。
- (e) Q1・今ある画面の試験のどれかが落ちたら、試験を書き換えて通さない（§4-K の行を除く）。画面の §4 の写し違いを探し、写し違いが無ければ停止して NEEDS_DECISION: で生の出力を返す。Q1 の画面の中の部品（例: 会社と担当の選び欄・チームの欄）が見本の中身で困って落ちた時も停止する。
- (f) TeamFormButtonMigration.test.tsx と FullPageFormButtonMigration.test.tsx は、保存できた後に `/teams/7`・`/suppliers/63` の写しを古い印にする（§4-H・§4-I）。その画面は戻り先へ移って消えるので取り直しは走らない見込み。走った時も、その 2 本の get の見本は `/teams/7`・`/suppliers/63` に答える（S TeamFormButtonMigration.test.tsx の get の見本・S FullPageFormButtonMigration.test.tsx の get の見本）。落ちたら試験を変えずに停止して NEEDS_DECISION: で生の出力を返す。
- (g) InvoicesPage.tsx は api の import を消す（§4-E1）。消す前に `grep -n "api\." <ファイル>` が S :55 の 1 行だけであることを確かめる。ほかにも出たら消さずに残し、報告に書く（tsc と lint が通れば続けてよい）。OwnInventoryPage.tsx（S :75 の post）・InvoiceCreatePage.tsx（S :146・:195）・TeamEditPage.tsx（S :49）・SupplierEditPage.tsx（S :65）は api を残す。

## 4-A. #1 frontend/src/api/funnel.ts
- A1 S :183 の channelsPath の閉じ `}` の次（空行を挟んで）に足す:
```ts

/** 成約・失注の理由の path（画面の写しの名前もここで決まる・ADR-1054） */
export function reasonsPath(type: "won" | "lost", month: string): string {
  return `/analytics/reasons?${new URLSearchParams({ type, month })}`;
}
```
- A2 S :217 `  return api.get<ReasonsResponse>(`/analytics/reasons?type=${type}&month=${month}`);` → `  return api.get<ReasonsResponse>(reasonsPath(type, month));`（:211-216 と :218 は今のまま）
- 作る path の文字列は今と同じ（`/analytics/reasons?type=won&month=YYYY-MM`）。type は won か lost、month は数字とハイフンだけなので、URLSearchParams で文字が変わらない。

## 4-B. #2 frontend/src/pages/dashboard/FunnelReasonsPage.tsx
- B1 S :7 `import { useEffect, useState } from "react";` → `import { useState } from "react";`
- B2 S :10 `import { getReasons, type ReasonsResponse } from "../../api/funnel";` → `import { FUNNEL_MOCK, reasonsPath, type ReasonsResponse } from "../../api/funnel";`
- B3 S :12 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";` とし、その次に 2 行足す:
```ts
import { useApiQuery } from "../../lib/query/apiQuery";
import { MOCK_REASONS_LOST, MOCK_REASONS_WON } from "../../mocks/funnelFixtures";
```
- B4 S :20-21（data と loading の useState の 2 行）を消す。:19 の reasonType・:23-26 の currentMonth は残す。
- B5 S :28-33（useEffect の塊）を次に置き換える:
```ts
  const reasonsQ = useApiQuery<ReasonsResponse>(reasonsPath(reasonType, currentMonth), { enabled: !FUNNEL_MOCK });
  const mockReasons = reasonType === "won" ? MOCK_REASONS_WON : MOCK_REASONS_LOST;
  const data: ReasonsResponse | null = FUNNEL_MOCK ? mockReasons : reasonsQ.data ?? null;
  const loading = !FUNNEL_MOCK && reasonsQ.isPending;
```
- B6 S :36-39 の PageLayout の `subtitleKey="funnel.reasonsPageTitle"` の次の行に足す:
  `      headerLeft={reasonsQ.isFetching && !reasonsQ.isPending ? <Spinner size="sm" /> : undefined}`
- :58 `{loading ? (`・:60 `!data ?`・:41-56 のタブは変えない。
- 理由: 先例は S pages/dashboard/FunnelSection.tsx:456-462 と段 3 の 2 回目の FunnelLeadsPage（batch3b-card.md §4-B）。keepPrevious を付けない理由は V3c-7。

## 4-C. #3 frontend/src/pages/dashboard/FunnelRevenuePage.tsx
- C1 S :7 `import { useEffect, useState } from "react";` を消す（このファイルは useState を他に使わない。消した後に `grep -n "useState\|useEffect" <ファイル>` が 0 行であることを確かめる）。
- C2 S :10 `import { getRevenueSummary, type RevenueSummaryResponse } from "../../api/funnel";` → `import { FUNNEL_MOCK, revenueSummaryPath, type RevenueSummaryResponse } from "../../api/funnel";`
- C3 S :12 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";` とし、その次に 2 行足す:
```ts
import { useApiQuery } from "../../lib/query/apiQuery";
import { MOCK_REVENUE_SUMMARY } from "../../mocks/funnelFixtures";
```
- C4 S :26-27（data と loading の useState の 2 行）を消す。:29-32 の currentMonth は残す。
- C5 S :34-39（useEffect の塊）を次に置き換える:
```ts
  const revenueQ = useApiQuery<RevenueSummaryResponse>(revenueSummaryPath(currentMonth), { enabled: !FUNNEL_MOCK });
  const data: RevenueSummaryResponse | null = FUNNEL_MOCK ? MOCK_REVENUE_SUMMARY : revenueQ.data ?? null;
  const loading = !FUNNEL_MOCK && revenueQ.isPending;
```
- C6 S :61-65 の PageLayout（最後の return の方）の `subtitleKey="funnel.revenuePageTitle"` の次の行に足す:
  `      headerLeft={revenueQ.isFetching && !revenueQ.isPending ? <Spinner size="sm" /> : undefined}`
- :41-47 の `if (loading)`・:49-55 の `if (!data)`・:57 以降は変えない。
- 作る path は今と同じ（getRevenueSummary も同じ revenueSummaryPath を使う・S funnel.ts:196-199）。

## 4-D. #4 frontend/src/pages/dashboard/FollowUpsPage.tsx
- D1 S :7 `import { useEffect, useState } from "react";` → `import { useMemo, useState } from "react";`
- D2 S :15 `import { getFollowUps, type FollowUpItem } from "../../api/funnel";` → `import { FUNNEL_MOCK, followUpsPath, type FollowUpItem, type FollowUpsResponse } from "../../api/funnel";`
- D3 S :17 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";` とし、その次に 2 行足す:
```ts
import { useApiQuery } from "../../lib/query/apiQuery";
import { MOCK_FOLLOW_UPS } from "../../mocks/funnelFixtures";
```
- D4 S :63-64（items と loading の useState の 2 行）を次に置き換える:
```ts
  const followUpsQ = useApiQuery<FollowUpsResponse>(followUpsPath(), { enabled: !FUNNEL_MOCK });
  const items = useMemo<FollowUpRow[]>(
    () => ((FUNNEL_MOCK ? MOCK_FOLLOW_UPS : followUpsQ.data)?.items ?? []).map((i) => ({ ...i, id: i.customer_id })),
    [followUpsQ.data],
  );
  const loading = !FUNNEL_MOCK && followUpsQ.isPending;
```
- D5 S :73-80（useEffect の塊）を消す。:70-71 の useRecordDrawer は変えない。
- D6 S :140-143 の PageLayout の `subtitleKey="funnel.followUpTitle"` の次の行に足す:
  `      headerLeft={followUpsQ.isFetching && !followUpsQ.isPending ? <Spinner size="sm" /> : undefined}`
- :82-95 の filtered・pageItems・counts、:164 `{loading ? (` は変えない。取れなかった時は今と同じく文を出さない。
- 作る path は今と同じ（`/analytics/follow-ups?`。getFollowUps も同じ followUpsPath を使う・S funnel.ts:201-204）。

## 4-E. #5 frontend/src/pages/invoices/InvoicesPage.tsx
- E1 S :9 `import { useEffect, useState } from "react";` → `import { useState } from "react";`。S :12 `import { api } from "../../lib/api";` を `import { useApiQuery } from "../../lib/query/apiQuery";` に置き換える（§3(g)）。
- E2 S :19 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`
- E3 S :47 `  const [invoices, setInvoices] = useState<Invoice[]>([]);` を消す。
- E4 S :48 `  const [statusFilter, setStatusFilter] = useState("");` の次に足す:
```ts
  const invoicesQ = useApiQuery<Invoice[]>(`/invoices${statusFilter ? `?status=${statusFilter}` : ""}`, { keepPrevious: true });
  const invoices = invoicesQ.data ?? [];
```
- E5 S :49-50（error と loading の useState の 2 行）を次の 1 行に置き換える（setError は S :58 の load の中だけで使う）:
  `  const shownError = invoicesQ.error ? (invoicesQ.error instanceof Error ? invoicesQ.error.message : t("common.fetchError")) : "";`
- E6 S :52-65（load・空行・eslint-disable の行・useEffect）を消す（load の呼び出しは他に無い）。
- E7 S :123-126 の PageLayout の `subtitleKey="invoices.subtitle"` の次の行に足す:
  `      headerLeft={invoicesQ.isFetching && !invoicesQ.isPending ? <Spinner size="sm" /> : undefined}`
- E8 S :148 `      {error && <div className="error-message">{error}</div>}` → `      {shownError && <div className="error-message">{shownError}</div>}`
- E9 S :150 `      {loading ? (` → `      {invoicesQ.isPending ? (`
- :155 `data={invoices}`・列（S :67-120）は変えない。作る path は今と同じ（`/invoices` か `/invoices?status=<絞り込み>`）。

## 4-F. #6 frontend/src/pages/inventory/OwnInventoryPage.tsx
- F1 S :7 `import { useCallback, useEffect, useState } from "react";` → `import { useState } from "react";`
- F2 S :9 `import { api } from "../../lib/api";` の次に `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` を足す（api は S :75 の post で使うので残す）。
- F3 S :17 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`
- F4 S :34 `  const [items, setItems] = useState<OwnInventoryRow[]>([]);` を消す。:35 の page は残す。
- F5 S :36-37（loading と error の useState の 2 行）を次に置き換える:
```ts
  const itemsQ = useApiQuery<OwnInventoryRow[]>(`/own-inventory?page=${page}&per_page=${PER_PAGE}`, { keepPrevious: true });
  const items = itemsQ.data ?? [];
  const error = itemsQ.error ? t("ownInventory.loadError") : "";
  const invalidate = useInvalidateApi();
```
- F6 S :42-59（load の useCallback・空行・useEffect）を次に置き換える:
```ts
  const load = () => {
    void invalidate(["own-inventory"]);
  };
```
- F7 S :99 `    <PageLayout navKey="nav.ownInventory" subtitleKey="ownInventory.subtitle">` → 次の 5 行にする:
```tsx
    <PageLayout
      navKey="nav.ownInventory"
      subtitleKey="ownInventory.subtitle"
      headerLeft={itemsQ.isFetching && !itemsQ.isPending ? <Spinner size="sm" /> : undefined}
    >
```
- F8 S :106 `      {loading ? (` → `      {itemsQ.isPending ? (`
- F9 S :209 `              disabled={items.length < PER_PAGE}` → `              disabled={items.length < PER_PAGE || itemsQ.isPlaceholderData}`
- load の呼び出し（S :80 `void load();`）・:100-104 の誤りの文・:188 `data={items}`・:200-201 の前へは変えない。取れなかった時の文は今と同じ（ownInventory.loadError）。

## 4-G. #7 frontend/src/pages/invoice-create/InvoiceCreatePage.tsx
- G1 S :11 `import { useState, useEffect, FormEvent } from "react";` → `import { useState, FormEvent } from "react";`
- G2 S :14 `import { api } from "../../lib/api";` の次に `import { useApiQuery } from "../../lib/query/apiQuery";` を足す（api は S :146・:195 で使うので残す）。
- G3 S :91-92（quotes と quotesLoading の useState の 2 行）を次に置き換える:
```ts
  const quotesQ = useApiQuery<QuoteSummary[]>("/quotes?status=approved", { enabled: mode === "quote" });
  const quotes = quotesQ.data ?? [];
  const quotesLoading = quotesQ.isPending;
```
- G4 S :94 `  const [error, setError] = useState("");` の次に足す:
  `  const shownError = error || (mode === "quote" && quotesQ.error ? (quotesQ.error instanceof Error ? quotesQ.error.message : t("common.fetchError")) : "");`
- G5 S :97-106（useEffect の塊）を消す。:108 以降の addItem は変えない。
- G6 S :234 `      {error && <div className="error-message">{error}</div>}` → `      {shownError && <div className="error-message">{shownError}</div>}`
- G7 S :246 `          onClick={() => { setSourceQuoteCode(null); setMode("quote"); }}` → `          onClick={() => { setSourceQuoteCode(null); setError(""); setMode("quote"); }}`（V3c-5。今の effect の `setError("")` と同じ時に消す）
- :256 `{quotesLoading ? (`・:258 `quotes.length === 0`・:270 `quotes.map` は変えない。回る印は足さない（作る画面）。
- 動き: 見積を選ぶ形でない間は取りに行かない（enabled が false）。その間 quotesLoading は true のままだが、:253 の `mode === "quote"` の側が描かれないので画面に出ない。在庫表から → 見積から と戻した時は、写しがあればすぐ出して裏で取り直す。

## 4-H. #8 frontend/src/pages/teams/TeamEditPage.tsx
- H1 S :10 `import { useEffect, useState, type FormEvent } from "react";` → `import { useState, type FormEvent } from "react";`
- H2 S :15 `import { api } from "../../lib/api";` の次に 2 行足す（api は保存で使うので残す）:
```ts
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { useSeededForm } from "../../lib/query/useSeededForm";
```
- H3 S :18 `const emptyForm: TeamFormState = { name: "", leader_id: "", description: "" };` の次に足す（空行を挟む。中身は S :31-39 の型と setForm の中身をそのまま移したもの）:
```ts

type TeamDetail = { id: number; name: string; leader_id: number | null; description: string | null };

const formFromTeam = (team: TeamDetail): TeamFormState => ({
  name: team.name,
  leader_id: team.leader_id != null ? String(team.leader_id) : "",
  description: team.description ?? "",
});
```
- H4 S :24-26（form・error・loading の useState の 3 行）を次に置き換える:
```ts
  const teamQ = useApiQuery<TeamDetail>(`/teams/${id}`, { enabled: id !== undefined });
  const { form, setForm, ready } = useSeededForm(`team/${id}`, teamQ.data, formFromTeam, emptyForm);
  const [error, setError] = useState("");
  const loading = teamQ.error === null && !ready;
  const shownError = error || (teamQ.error ? (teamQ.error instanceof Error ? teamQ.error.message : t("common.fetchError")) : "");
  const invalidate = useInvalidateApi();
```
- H5 S :28-43（useEffect の塊）を消す。
- H6 S :54 `      navigate("/teams");` の前の行に足す（保存できた後だけ。失敗した時は取り直さない）:
  `      void invalidate(["teams", id ?? ""]);`
- H7 S :62 `      {error && <div className="error-message">{error}</div>}` → `      {shownError && <div className="error-message">{shownError}</div>}`
- :63 `{loading ? (`・:67 の onChange（setForm に関数を渡す。useSeededForm の setForm は関数も受け取る）・:72 の取り消しは変えない。
- 理由: Bot の編集（S BotEditPage.tsx:35・:48-55・:70）と同じ形。`invalidate(["teams", "7"])` は `/teams/7` から始まる写しだけを古い印にする（チームの一覧 `/teams` は words が 1 語なので当たらない。一覧は開いた時に取り直す）。

## 4-I. #9 frontend/src/pages/suppliers/SupplierEditPage.tsx
- I1 S :10 `import { useEffect, useState, type FormEvent } from "react";` → `import { useState, type FormEvent } from "react";`
- I2 S :15 `import { api } from "../../lib/api";` の次に 2 行足す（api は保存で使うので残す）:
```ts
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { useSeededForm } from "../../lib/query/useSeededForm";
```
- I3 S :20 `};`（emptyForm の閉じ）の次に足す（空行を挟む。中身は S :33-42 の型と setForm の中身をそのまま移したもの）:
```ts

type SupplierDetail = {
  id: number; name: string; contact_name: string | null; email: string | null;
  phone: string | null; address: string | null; notes: string | null;
};

const formFromSupplier = (s: SupplierDetail): SupplierFormState => ({
  name: s.name,
  contact_name: s.contact_name ?? "",
  email: s.email ?? "",
  phone: s.phone ?? "",
  address: s.address ?? "",
  notes: s.notes ?? "",
});
```
- I4 S :26-28（form・error・loading の useState の 3 行）を次に置き換える:
```ts
  const supplierQ = useApiQuery<SupplierDetail>(`/suppliers/${id}`, { enabled: id !== undefined });
  const { form, setForm, ready } = useSeededForm(`supplier/${id}`, supplierQ.data, formFromSupplier, emptyForm);
  const [error, setError] = useState("");
  const loading = supplierQ.error === null && !ready;
  const shownError = error || (supplierQ.error ? (supplierQ.error instanceof Error ? supplierQ.error.message : t("common.fetchError")) : "");
  const invalidate = useInvalidateApi();
```
- I5 S :30-46（`/* 既存データ取得 */` の行と useEffect の塊）を消す。:48-50 の handleChange は変えない。
- I6 S :66 `      navigate("/suppliers");` の前の行に足す（保存できた後だけ）:
  `      void invalidate(["suppliers", id ?? ""]);`
- I7 S :74 `      {error && <div className="error-message">{error}</div>}` → `      {shownError && <div className="error-message">{shownError}</div>}`
- :75 `{loading ? (`・:55-63 の payload・:84 の取り消しは変えない。

## 4-K. #10 frontend/src/components/CommerceSubmitButtonMigration.test.tsx（ほかの行は変えない）
- K1 S :9 `import en from '../locales/en.json';` の次に `import { queryClient } from '../lib/query/apiQuery';` を足す。
- K2 S :63 `afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });` → `afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });`
- 理由: 画面が同じ 1 個の写しの置き場を使うので、前の試験の写しが次の試験に残らないようにする（段 3 の 1 回目・2 回目の §4-K と同じ）。この試験は AuthContext を mock していないので、開発の時の仮の利用者（S frontend/src/contexts/AuthContext.tsx:173-197。`import.meta.env.DEV` で /login 以外の時に uid "e2e-test-user-uid"）で写しを取る。人を入れる直しは要らない。

## 4-L. #11 frontend/src/lib/query/batch3cPages.test.tsx（新しく作る・全文）
```tsx
/**
 * ADR-1054 段 3 の 3 回目: 本物の画面の試験（Q1）。
 * Q1 戻った時に写しを先に出す（読み込み中の印を出さない）・一覧と詳しい画面は見出しの横に回る印・裏で取り直す。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import type { ComponentType } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import FollowUpsPage from "../../pages/dashboard/FollowUpsPage";
import FunnelReasonsPage from "../../pages/dashboard/FunnelReasonsPage";
import FunnelRevenuePage from "../../pages/dashboard/FunnelRevenuePage";
import OwnInventoryPage from "../../pages/inventory/OwnInventoryPage";
import InvoiceCreatePage from "../../pages/invoice-create/InvoiceCreatePage";
import InvoicesPage from "../../pages/invoices/InvoicesPage";
import SupplierEditPage from "../../pages/suppliers/SupplierEditPage";
import TeamEditPage from "../../pages/teams/TeamEditPage";
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
vi.mock("../../hooks/usePermissions", () => ({ usePermissions: () => ({ hasPermission: () => true, loading: false }) }));
vi.mock("../../hooks/useSSE", () => ({ useSSE: vi.fn() }));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
  // api.ts が i18n.ts を読み、i18n.ts が initReactI18next を使う（同じ書き方: src/lib/query/batch3bPages.test.tsx）
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

// 中身は画面の型（TeamEditPage・SupplierEditPage の型・backend/app/schemas/own_inventory.py:42-56・
// InvoicesPage.tsx:21-34・InvoiceCreatePage.tsx:30-38・api/funnel.ts:42-93）の欄
const team = { id: 7, name: "Fixture Team", leader_id: null, description: null };
const supplier = { id: 63, name: "Fixture supplier", contact_name: null, email: null, phone: null, address: null, notes: null };
const ownRow = { id: 1, tenant_id: 1, product_id: 77, physical_qty: 2, reserved_qty: 0, available_qty: 2, unit_price: null, condition: "Fixture Cond", status: "in_stock", note_ja: null, note_en: null, antique_ledger_id: null, created_at: "", updated_at: "" };
const invoice = { id: 7, invoice_number: "INV-7", company_id: 4, currency: "USD", total_amount: 10, amount_jpy: null, status: "draft", issued_at: null, due_date: null, paid_at: null, created_at: "" };
const quote = { id: 7, quote_code: "Q-7", company_id: 4, currency: "USD", total_amount: 10, status: "approved", created_at: "" };
const followUps = { items: [{ customer_id: 5, name: "Fixture Customer", segment: "order_stopped", days: 3, last_order_at: null, last_contact_at: null, assignee: "Fixture Assignee" }] };
const revenue = { revenue: { target: 2000000, actual: 1234567, pace: "on_track" }, split: { new: 1, repeat: 1 }, new_customers: { target: 1, actual: 1 }, active_existing_customers: 1, gross_margin: { amount: 1, uncosted_orders: 0 } };
const reasons = { reasons: [{ label: "Fixture Reason", primary_count: 1, secondary_count: 0 }], memos: [] };

const fixtures: Record<string, unknown> = {
  "/teams/7": team,
  "/suppliers/63": supplier,
  "/own-inventory?page=1&per_page=20": [ownRow],
  "/invoices": [invoice],
  "/quotes?status=approved": [quote],
  "/analytics/follow-ups?": followUps,
};
// 売上と理由は月で path が変わるので頭で見分ける。画面の中の部品が別に取る物（会社の選び欄など）は空の一覧で返す
const answer = (path: string) =>
  (path in fixtures
    ? fixtures[path]
    : path.startsWith("/analytics/revenue-summary?")
      ? revenue
      : path.startsWith("/analytics/reasons?")
        ? reasons
        : []) as never;

type Case = {
  name: string; Page: ComponentType; route: string; at: string;
  path: string | RegExp; text: string; value: boolean; spinner: boolean;
};
const cases: Case[] = [
  { name: "supplier edit", Page: SupplierEditPage, route: "/suppliers/:id/edit", at: "/suppliers/63/edit", path: "/suppliers/63", text: "Fixture supplier", value: true, spinner: false },
  { name: "own inventory", Page: OwnInventoryPage, route: "/own-inventory", at: "/own-inventory", path: "/own-inventory?page=1&per_page=20", text: "Fixture Cond", value: false, spinner: true },
  { name: "follow ups", Page: FollowUpsPage, route: "/dashboard/follow-ups", at: "/dashboard/follow-ups", path: "/analytics/follow-ups?", text: "Fixture Customer", value: false, spinner: true },
  { name: "invoice create", Page: InvoiceCreatePage, route: "/invoices/new", at: "/invoices/new", path: "/quotes?status=approved", text: "Q-7", value: false, spinner: false },
  { name: "invoices", Page: InvoicesPage, route: "/invoices", at: "/invoices", path: "/invoices", text: "INV-7", value: false, spinner: true },
  { name: "team edit", Page: TeamEditPage, route: "/teams/:id/edit", at: "/teams/7/edit", path: "/teams/7", text: "Fixture Team", value: true, spinner: false },
  { name: "revenue", Page: FunnelRevenuePage, route: "/dashboard/revenue", at: "/dashboard/revenue", path: /^\/analytics\/revenue-summary\?month=\d{4}-\d{2}$/, text: "¥1,234,567", value: false, spinner: true },
  { name: "reasons", Page: FunnelReasonsPage, route: "/dashboard/reasons", at: "/dashboard/reasons", path: /^\/analytics\/reasons\?type=won&month=\d{4}-\d{2}$/, text: "Fixture Reason", value: false, spinner: true },
];

function Tree({ c }: { c: Pick<Case, "Page" | "route" | "at"> }) {
  const Page = c.Page;
  return (
    <QueryClientProvider client={queryClient}>
      <QueryAuthSync />
      <MemoryRouter initialEntries={[c.at]}>
        <Routes><Route path={c.route} element={<Page />} /></Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// 編集の画面は欄の中の値で、ほかは文字で見分ける
const shown = (c: Case) => (c.value ? screen.queryAllByDisplayValue(c.text) : screen.queryAllByText(c.text));
const found = (c: Case) => (c.value ? screen.findAllByDisplayValue(c.text) : screen.findAllByText(c.text));
const calledPath = (c: Case) => (typeof c.path === "string" ? c.path : expect.stringMatching(c.path));

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

describe("revisit shows the copy first (Q1)", () => {
  it.each(cases)("$name shows the previous content at once on revisit", async (c) => {
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) => answer(path));
    const first = render(<Tree c={c} />);
    await found(c);
    first.unmount();

    spy.mockClear();
    spy.mockImplementation(() => new Promise<never>(() => {}));
    const { container } = render(<Tree c={c} />);
    expect(shown(c).length).toBeGreaterThan(0);
    expect(container.querySelector(".sa-loading-block")).toBeNull();
    if (c.spinner) {
      await waitFor(() => expect(container.querySelector(".page-layout-title-row .sa-spinner")).not.toBeNull());
    }
    await waitFor(() => expect(spy).toHaveBeenCalledWith(calledPath(c)));
  });
});
```
- LoadingBlock の見分けは `.sa-loading-block`、回る印の見分けは `.page-layout-title-row .sa-spinner`（段 3 の 1 回目・2 回目のカード §4-L と同じ）。チームの編集・仕入先の編集・請求書を作る画面は回る印を出さない（V3c-4・V3c-5）。
- 自社在庫の path は §4-F5 が page 1・PER_PAGE 20（S OwnInventoryPage.tsx:29）で作る文字列。請求書一覧の path は絞り込みなしで作る文字列（`/invoices`）。要フォロー顧客の path は followUpsPath() が作る文字列（`/analytics/follow-ups?`。S funnel.ts:173-176）。
- 売上の「¥1,234,567」は売上の実績の欄（S FunnelRevenuePage.tsx:72 の fmtMoney）に出る。理由の「Fixture Reason」は理由の順位の欄（S FunnelReasonsPage.tsx:74）に出る。請求書を作る画面の「Q-7」は承認済みの見積の表（S InvoiceCreatePage.tsx:272）に出る。
- チームの編集と仕入先の編集の値は、欄の中の値（TeamFormFields・SupplierFormFields の名前の欄）に出る。先例は S TeamFormButtonMigration.test.tsx の `findByDisplayValue('Fixture Team')`。

## 4-M. 実装役の手順（1 手順 1 命令。<W> は手順1 で作られた作業場所の絶対パス）
手順1. クラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）どおり、作業場所を作り、push 済みの枝の先頭に合わせる（設計担当が §1 #12〜#14 を push 済み）。
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/line-like-speed-batch3c
  （出力に出た作業場所の絶対パスを <W> として報告に書く。）
  cd <W> && git fetch origin release/line-like-speed-batch3c
  cd <W> && git switch -C release/line-like-speed-batch3c origin/release/line-like-speed-batch3c
  cd <W> && git rev-parse HEAD origin/release/line-like-speed-batch3c
  （2 行が同じことを確かめる。違えば停止して BLOCKED: で報告する。main は取り込まない。reset・rebase・force・merge・pull は使わない）
  cd <W> && ./scripts/dev/executor-preflight.sh > /tmp/b3c-preflight.txt 2>&1
  cd <W> && grep -n "FAIL" /tmp/b3c-preflight.txt | head -20
  cd <W> && grep -n "origin/main は存在" /tmp/b3c-preflight.txt | head -3
  （FAIL の行が次の 3 つのうちのどれかだけなら続ける: `GitHub API に到達不可` の 1 件・`gh auth switch --hostname github.com --user shingo-cc` の失敗の 1 件・その結果の `PREFLIGHT FAIL` の行。理由は段 3 の 1 回目のカード §4-M 手順1 と同じ。続ける時は `[OK]   origin/main は存在` の行があることを 2 つ目の grep で確かめ、無ければ停止する。ほかの FAIL が 1 件でもあれば停止し、BLOCKED: で grep の出力を報告する。）
  cd <W> && git fetch origin main
  cd <W> && git diff --stat 5c76e9029e5889b6dfebe33a94036edd6f696856 origin/main -- frontend/src | tail -5
  （§3(a) の確かめ。）
手順2. 依存を入れ、§3(b) を確かめ、変える前の lint の警告を数える。
  cd <W>/frontend && npm ci > /tmp/b3c-ci.txt 2>&1
  cd <W> && tail -5 /tmp/b3c-ci.txt
  cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json
  cd <W>/frontend && grep -n "api\." src/pages/invoices/InvoicesPage.tsx
  （§3(g) の確かめ。）
  cd <W>/frontend && npx eslint src/api/funnel.ts src/pages/dashboard/FunnelReasonsPage.tsx src/pages/dashboard/FunnelRevenuePage.tsx src/pages/dashboard/FollowUpsPage.tsx src/pages/invoices/InvoicesPage.tsx src/pages/inventory/OwnInventoryPage.tsx src/pages/invoice-create/InvoiceCreatePage.tsx src/pages/teams/TeamEditPage.tsx src/pages/suppliers/SupplierEditPage.tsx > /tmp/b3c-lint-before.txt 2>&1
  cd <W> && tail -5 /tmp/b3c-lint-before.txt
手順3. §4-L の全文で #11 を作り、§4-A〜§4-K のとおり #1〜#10 を直す。各ファイルを直す前に、§4 の「変更前」の文を `grep -n` で確かめる（§3(c)）。終わったら残りが無いことを確かめる。
  cd <W> && grep -n "useEffect\|useCallback\|setLoading\|setInvoices\|setQuotes\|setQuotesLoading\|setData\|getFollowUps\|getRevenueSummary\|getReasons" frontend/src/pages/dashboard/FunnelReasonsPage.tsx frontend/src/pages/dashboard/FunnelRevenuePage.tsx frontend/src/pages/dashboard/FollowUpsPage.tsx frontend/src/pages/invoices/InvoicesPage.tsx frontend/src/pages/inventory/OwnInventoryPage.tsx frontend/src/pages/invoice-create/InvoiceCreatePage.tsx frontend/src/pages/teams/TeamEditPage.tsx frontend/src/pages/suppliers/SupplierEditPage.tsx | head -20
  （0 行であること。出たら §4 の写し違いを直す。）
  cd <W> && grep -n "setItems" frontend/src/pages/dashboard/FollowUpsPage.tsx frontend/src/pages/inventory/OwnInventoryPage.tsx | head -5
  （0 行であること。InvoiceCreatePage.tsx の setItems は明細の行なので見ない。）
手順4. 型を作ってから試験を流す（新しい試験・直した今ある試験・8 画面を描く今ある試験・全部の試験・型・lint）。作る型（frontend/src/api/generated/）は .gitignore で除かれるので commit に入らない。
  cd <W>/frontend && npm run generate:api-types > /tmp/b3c-gen.txt 2>&1
  cd <W> && tail -3 /tmp/b3c-gen.txt
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/lib/query > /tmp/b3c-unit.txt 2>&1
  cd <W> && tail -30 /tmp/b3c-unit.txt
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/components/CommerceSubmitButtonMigration.test.tsx src/components/TeamFormButtonMigration.test.tsx src/components/FullPageFormButtonMigration.test.tsx src/components/CommerceNavigationButtonMigration.test.tsx src/components/AllLegacyButtonDynamicMigration.test.tsx > /tmp/b3c-pages.txt 2>&1
  cd <W> && tail -30 /tmp/b3c-pages.txt
  cd <W>/frontend && npm run test:unit > /tmp/b3c-unit-all.txt 2>&1
  cd <W> && tail -15 /tmp/b3c-unit-all.txt
  cd <W>/frontend && npx tsc --noEmit -p . > /tmp/b3c-tsc.txt 2>&1
  cd <W> && tail -20 /tmp/b3c-tsc.txt
  cd <W>/frontend && npx eslint src/lib/query src/api/funnel.ts src/pages/dashboard/FunnelReasonsPage.tsx src/pages/dashboard/FunnelRevenuePage.tsx src/pages/dashboard/FollowUpsPage.tsx src/pages/invoices/InvoicesPage.tsx src/pages/inventory/OwnInventoryPage.tsx src/pages/invoice-create/InvoiceCreatePage.tsx src/pages/teams/TeamEditPage.tsx src/pages/suppliers/SupplierEditPage.tsx > /tmp/b3c-lint.txt 2>&1
  cd <W> && tail -20 /tmp/b3c-lint.txt
  （lint の警告が手順2 の数より増えていないこと・誤りが 0 であること。§3(d)。）
手順5. 本番と同じ形で組み立てられるか確かめる。
  cd <W>/frontend && npm run build > /tmp/b3c-build.txt 2>&1
  cd <W> && tail -15 /tmp/b3c-build.txt
手順6. 変わったファイルが §1 の #1〜#11 だけか確かめ、画面の書く path と表・フォームの行が変わっていないことを見る。
  cd <W> && git status --short | head -30
  cd <W> && git diff -w --stat origin/release/line-like-speed-batch3c | tail -20
  cd <W> && git diff -w origin/release/line-like-speed-batch3c -- frontend/src/pages frontend/src/api | head -600
手順7. commit する。
  cd <W> && git add frontend/src/api/funnel.ts frontend/src/pages/dashboard/FunnelReasonsPage.tsx frontend/src/pages/dashboard/FunnelRevenuePage.tsx frontend/src/pages/dashboard/FollowUpsPage.tsx frontend/src/pages/invoices/InvoicesPage.tsx frontend/src/pages/inventory/OwnInventoryPage.tsx frontend/src/pages/invoice-create/InvoiceCreatePage.tsx frontend/src/pages/teams/TeamEditPage.tsx frontend/src/pages/suppliers/SupplierEditPage.tsx frontend/src/components/CommerceSubmitButtonMigration.test.tsx frontend/src/lib/query/batch3cPages.test.tsx
  cd <W> && git commit -m "feat: 残りの8画面を写しを先に出して裏で取り直す形に（ADR-1054 段3の3回目）"
手順8. commit が在ることを確かめてから push する（--no-verify は使わない。push の前の検査が × なら直してから push。fast-forward でないと断られたら直さず BLOCKED:）。
  cd <W> && git log -3 --oneline
  cd <W> && git push -u origin release/line-like-speed-batch3c
手順9. 報告を返す。PR は作らない（設計担当が手元で作る）。報告の 1 つの発言は 600 文字以内にして、番号付きの発言に分ける。報告には手順ごとの tail の出力（生のまま）と、§3(a)〜(g) の結果を書く。

## 4. GO と承認・PO の操作
- PO の実装承認: 2026-11-02 PO 選択「1」（残りの 8 画面も同じ形で、本番の測定まで直す）。ADR-1054 は Accepted。このカードの審査合格の後に、設計担当がクラウドの Sonnet へ渡す。
- 触るのは frontend の画面 8 個・部品の path 1 つ・試験と書類だけで、migrations・deploy.yml・本番 scripts を含まない（番号付き GO の要る危ない PR ではない）。main へのマージで本番の画面に出る（deploy.yml が main への push で動く）。マージは PO の委任に基づき設計担当（Claude Opus）が、マージ前の審査役の APPROVE と必須の確認がすべて pass の後に行う。
- PO が操作することはない。

## 5. 受入（○×）
| # | 基準 | 検証方法 |
|---|---|---|
| B1 | Q1（8 画面とも戻った時に LoadingBlock 0 個で前の中身が出る・一覧と詳しい画面は見出しの横に回る印・裏で取り直す）が合格。段 3 の 1 回目の Q2・Q3（K5）と 2 回目の Q1 も合格のまま | /tmp/b3c-unit.txt の最後（batch3cPages.test.tsx の 8 件が passed・batch3bPages.test.tsx・batch3aPages.test.tsx・useSeededForm.test.tsx・apiQuery.test.tsx・stage2Pages.test.tsx も passed）と、PR の CI の unit-run が success |
| B2 | 今ある画面の試験 5 本・全部の試験・型・lint・組み立てが通る | /tmp/b3c-pages.txt・b3c-unit-all.txt・b3c-tsc.txt・b3c-lint.txt・b3c-build.txt の最後と、PR の必須の確認がすべて pass |
| B3 | 変わったのは §1 の 14 ファイルだけ。画面の書く path と中身・表・フォームの欄は変わっていない | gh pr diff --name-only と git diff -w（§4-M 手順6） |
| B4 | QueryClient を作るのは apiQuery.ts の 1 か所だけ・staleTime を設定していない・写しをブラウザの保存に書かない | `git grep -n "new QueryClient" -- frontend/src` が 1 行、`git grep -n "staleTime:" -- frontend/src` が 0 行、`git grep -n -i "persist" -- frontend/src/lib/query frontend/package.json` が 0 行 |
| B5 | マージの後、毎朝の画面の記録を手で 1 回動かし、§0 V3c-1 の 8 行で K1（戻った時の秒）≤0.1 秒、K2（初めて開く秒）≤2 秒、403・5xx が 0 件。ほかの行は K2 の最大と 2 秒を超えた画面の数が段 3 の 2 回目の受入（run 41409815435）から悪化していない | prod-ui-check の実行の要約（設計担当。`gh workflow run prod-ui-check.yml --ref main` の後に要約の表を読む） |
| B6 | 取り直した後の中身が DB と一致（tenant 001）: 請求書・自社在庫・チーム・仕入先の件数が、本番 DB の同じ条件の件数と同じ | 設計担当が本番の読むだけの道（ADR-1024）で tenant 001 の行を数える。画面の件数は prod-ui-check の記録か PO のログイン済みの Chrome で数える。数えられない時は「画面の件数はまだ確かめていない」と記録し、backend を変えていないこと（B3）と Q1 を根拠にする |
| B7 | マージの後、deploy が成功し、本番の画面が開く | deploy.yml の実行の結論 success と時刻。本番 https://app.salesanchor.jp/ が開き、ブラウザの誤りの記録に TanStack 由来の誤りが無い（設計担当） |
