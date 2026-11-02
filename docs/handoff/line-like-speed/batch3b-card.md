# 段 3 の 2 回目の実装カード（遅い順の 10 画面を「写しを先に出して裏で取り直す」形に変える）

- 対象: docs/handoff/line-like-speed/design.md §3-2（部品）・§3-3（触らない範囲）・§3-4 の段 3・§3-5 の K1・K2・K5・§3-7。ADR-1054（Accepted）。段 3 の 1 回目のカード（docs/handoff/line-like-speed/batch3a-card.md）の部品と形をそのまま使う。
- 根拠の写し: S=origin/main 3bfc5d555661bf81701890c43cd0f57314f56875。行番号はすべてこの sha。2026-11-02 に設計担当が S の写しで行を読んだ。実装の前に最新の origin/main で行を合わせ直す（§3(a)）。
- 読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/04-worktree.md・guards/05-pr.md・guards/10-executor.md・scripts/agent-hooks/cloud/rules.md（段 3 の 1 回目のカードと同じ節。照合も同じ: 全命令は cd <W> で始める・出力は tail/head で上限・新しいファイルは丸ごとの全文・作業場所は new-worktree.sh で作り出力をパイプに通さない・PR は実行役が作らない・出力をファイルに残す命令と tail で読む命令は別の行）。
- 実行役はクラウドの Sonnet。作業場所の作り方はクラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）を正とする。.pr-number・gh-pr-create-safe.sh は使わない。出力には上限を付ける。待つために sleep を使わない。
- 状態: 第 2 版（2026-11-02 設計担当 Claude Opus）。第 1 版のクラウド審査は REVISE で、①§4-L の担当者の見本に emails・discord・contact_channels が無く画面が落ちる ②§4-F4 の quotes が描画ごとに変わり lint の警告が 1 件増える ③手順3 の確かめで setLoadingAdvice の行も出る、の 3 つを直した。審査役は 3 つを写しで当て、tsc 0・lint の警告 0・Q1 10 件合格を確かめた。
- 受領確認: 実装役は着手の最初の報告に「段 3 の 2 回目のカード 第 2 版を受け取った・S=3bfc5d555」と書く。

## 0. 設計からの直し・詳しくした点（V3b。設計の合格線は変えない）
- V3b-1 対象は、段 3 の 1 回目の受入の回（prod-ui-check run 41389073263）で戻った時の秒（K1）が遅い順の 10 行（9 画面。/teams と /management-center/teams は同じ画面）。PO 選択「1」（遅い順に 10 画面ずつ、本番の測定まで進める）。

  | 行 | 画面のファイル | K1 の基準（秒） |
  |---|---|---|
  | /dashboard/leads | pages/dashboard/FunnelLeadsPage.tsx・api/funnel.ts | 0.20 |
  | /management-center/units | pages/units/UnitsPage.tsx | 0.19 |
  | /management-center/status-master | pages/status-master/StatusMasterPage.tsx | 0.19 |
  | /crm/contacts | pages/contacts/ContactsPage.tsx | 0.19 |
  | /schedule/settings | pages/schedule/ScheduleSettingsPage.tsx | 0.19 |
  | /quotes | pages/quotes/QuotesPage.tsx | 0.19 |
  | /goals/settings | pages/goal-setting/GoalSettingPage.tsx | 0.18 |
  | /management-center/teams | pages/teams/TeamsPage.tsx | 0.18 |
  | /quotes/:id | pages/quote-detail/QuoteDetailPage.tsx | 0.18 |
  | /teams | pages/teams/TeamsPage.tsx | 0.17 |

- V3b-2 写しの置き場の部品（S frontend/src/lib/query/apiQuery.ts）と、フォームの初めの値を写しから作る部品（S frontend/src/lib/query/useSeededForm.ts）は変えない。使うのは useApiQuery（keepPrevious つき）・useInvalidateApi・useSeededForm だけ。QueryClient を足さない・staleTime を設定しない・写しをブラウザの保存に書かない。
- V3b-3 一覧と詳しい画面（単位・状態マスタ・担当者一覧・見積一覧・見積の詳しい画面・チーム・リード流入）は段 3 の 1 回目と同じ形にする: 写しがあればすぐ出す・読み込み中の印（LoadingBlock）は写しが無い初回（isPending）だけ・写しを出したまま裏で取り直している間は見出しの横に小さな回る印（金型 components/loading の Spinner・size "sm"・PageLayout の headerLeft）・取れなかった時の文は shownError の 1 か所。条件（ページ・検索・絞り込み）を変えた時は前の行を出したまま取る（keepPrevious）。前の行を出している間は「次へ」を押せなくする（isPlaceholderData）。
- V3b-4 書いた後の読み直し（今の `load()`・`loadTeams()`・`loadContacts()`）は、写しを古い印にして取り直す（useInvalidateApi）。呼び出す場所は変えない。
- V3b-5 担当者一覧の「会社の選択肢」は、担当者の編集（段 3 の 1 回目 V3a-7）と同じ path（`/companies?per_page=100`）なので同じ写しを使う。取れなかった時は今と同じく文を出さない。
- V3b-6 目標の設定は、「自分」（`/me/permissions`・usePermissions と同じ写し）と「チーム」（`/teams`・チームの画面と同じ写し）を写しから出す。読み込み中の印は今と同じく、どちらかの写しが無い初回だけ。選んだチームは、選んだチームが一覧に無い時（初回を含む）だけ一覧の先頭にする（今は初回だけ先頭にする。チームが消された後に古い番号を持ち続けない分だけ良くなる）。目標の値（`/goals?...` の 2 つの effect・S :563・:587）は今のまま effect で取る。回る印は出さない（見出しの横の印は一覧と詳しい画面だけ）。
  - 記録しておく弱い所: 人が変わった時、目標の値の欄は次の取り直しが届くまで前の値を出し得る。今の作りは人が変わっても取り直さない（S :547-560 は 1 回だけ）ので、今より悪くならない。目標の値は人ごとに server が絞って返す（K5 の守りは写しの名前と server の両方）。
- V3b-7 予定の設定（カレンダーの色・表示・共有）は、フォームと同じ形なので useSeededForm で写しから作る。保存は今と同じ（api.patch）。保存できた後に写しを古い印にする（次に開いた時に保存前の古い中身を出さない）。権限が無い時は取りに行かない（今と同じ）。回る印は出さない。
- V3b-8 リード流入の「チャネル別の表」の path は、funnel.ts に channelsPath を足して 1 か所で作る（getChannels もそれを使う）。表示の切り替え（VITE_FUNNEL_DASHBOARD が mock の時は見本の表）は今と同じ。取れなかった時は今と同じく文を出さない。
- V3b-9 今ある画面の試験のうち、TeamFormButtonMigration.test.tsx だけ `cleanup();` の後に写しを消していないので、`queryClient.clear();` を足す（段 3 の 1 回目の §4-K と同じ）。ほかの 5 本（AllLegacyButtonDynamicMigration・CommerceNavigationButtonMigration・MasterSearchButtonMigration・PageFormButtonMigration・ToggleMigration）は変えない（前の 4 本は S で消し済み、ToggleMigration は画面を描かない）。
- V3b-10 受入（§5 B5）は、10 行すべてで K1 ≤0.1 秒・K2 ≤2 秒・403 と 5xx が 0 件。K5 は段 3 の 1 回目の Q2・Q3（Bot 編集と useSeededForm の試験）と、写しの名前に利用者が入る作りで確かめる（本番で 2 人のログインは使わない）。

## 1. 触るファイル（変更前→変更後）
| # | ファイル | 変更前 | 変更後 |
|---|---|---|---|
| 1 | frontend/src/api/funnel.ts | getChannels が path を中で作る（S :199-204） | channelsPath を足し、getChannels がそれを使う（§4-A） |
| 2 | frontend/src/pages/dashboard/FunnelLeadsPage.tsx | useState と useEffect で読む（S :33-35・:42-58） | useApiQuery（§4-B） |
| 3 | frontend/src/pages/units/UnitsPage.tsx | 同上（S :62・:64・:67・:102-116） | 同上（§4-C） |
| 4 | frontend/src/pages/status-master/StatusMasterPage.tsx | 同上（S :83・:85・:88・:134-148） | 同上（§4-D） |
| 5 | frontend/src/pages/contacts/ContactsPage.tsx | 同上（S :113-114・:125・:131-157） | 同上（§4-E） |
| 6 | frontend/src/pages/quotes/QuotesPage.tsx | 同上（S :49・:53-54・:56-69） | 同上（§4-F） |
| 7 | frontend/src/pages/quote-detail/QuoteDetailPage.tsx | 同上（S :60-62・:66-78） | 同上（§4-G） |
| 8 | frontend/src/pages/teams/TeamsPage.tsx | 同上（S :59・:68・:74-83・:94-95） | 同上（§4-H） |
| 9 | frontend/src/pages/goal-setting/GoalSettingPage.tsx | 同上（S :514-515・:536・:547-560） | 同上（§4-I） |
| 10 | frontend/src/pages/schedule/ScheduleSettingsPage.tsx | 同上（S :38-39・:51-81） | useApiQuery＋useSeededForm（§4-J） |
| 11 | frontend/src/components/TeamFormButtonMigration.test.tsx | cleanup の後に写しを消さない | cleanup の後に queryClient.clear()（§4-K） |
| 12 | frontend/src/lib/query/batch3bPages.test.tsx | 無い | 新しく作る。Q1（§4-L 全文） |
| 13 | docs/handoff/line-like-speed/batch3b-card.md | 無い | このカード（設計担当が書いた。実装役は触らない） |
| 14 | docs/handoff/line-like-speed/design.md | §3-4-13-a まで | §3-4-14 にこのカードの場所を書き足し済み（設計担当。実装役は触らない） |
| 15 | .claude-pipeline/active-work.d/release-line-like-speed-batch3b.md | 無い | 作業の札（設計担当。実装役は触らない） |

## 2. 触らない範囲
- backend/・migrations/・.github/workflows/・scripts/・tests/prod-check/・frontend/viewer/ は触らない（design §3-3）。
- frontend/src/lib/api.ts・frontend/src/contexts/AuthContext.tsx・frontend/src/lib/auth/・frontend/src/lib/query/apiQuery.ts・frontend/src/lib/query/useSeededForm.ts・frontend/src/lib/query/QueryAuthSync.tsx・frontend/src/App.tsx・frontend/src/hooks/usePermissions.ts・frontend/src/mocks/ は触らない。
- frontend/src/components/（PageLayout・Spinner・LoadingBlock を含む。試験のファイルは §4-K の行だけ）・CSS・ja.json・en.json は触らない。新しい言葉・色・寸法を足さない。
- 9 画面の中の、書き方（post・patch・delete の path と中身）・書き出し・表の列・ボタン・モーダル・ドロワー・フォームの欄・目標の値の取り方（S GoalSettingPage.tsx:563-608）・チームの人の取り方（S TeamsPage.tsx:85-92 loadMembers）は変えない。変えるのは §4 に書いた行だけ。
- QueryClient を作らない（試験の中でも作らない）。staleTime を設定しない。写しをブラウザの保存に書かない。
- ほかの画面は変えない（次の画面は次のカード）。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) 最新の origin/main で `git diff --stat 3bfc5d555 origin/main -- frontend/src` が空か。空でなければ、変わったファイルの名前と行数を報告に書く。§1 #1〜#11 のどれかが変わっていたら停止して報告する。ほかのファイルだけなら続ける。
- (b) `cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json` が `"5.104.4"` の 1 行。違えば停止して報告する。
- (c) §4 の「変更前」の文が、書かれた行にそのままあること。1 か所でも無い・2 か所以上ある時は、直さずに停止して BLOCKED: で `grep -n` の出力を報告する。
- (d) 手順 2 で、変える前の 10 ファイル（§1 #1〜#10）の lint の警告の数を数えておく。変えた後は、その数より増えないこと（0 になってもよい）。増えたら直す。直せない時は停止する。
- (e) Q1・今ある画面の試験のどれかが落ちたら、試験を書き換えて通さない（§4-K の行を除く）。画面の §4 の写し違いを探し、写し違いが無ければ停止して NEEDS_DECISION: で生の出力を返す。Q1 の画面の中の部品が見本の中身で困って落ちた時（例: 欄の値が null で `.map` する所）も停止する。
- (f) TeamFormButtonMigration.test.tsx の「保存を 2 回待たせた時に /teams を 2 回読む」（S :129 `before + 2`）は、取り直しを 2 回頼むと TanStack が 1 本目を止めて 2 本目を取る（既定の cancelRefetch）ので、api.get が 2 回呼ばれる見込み（段 3 の 1 回目の §3(f) の LeadFormButtonMigration と同じ形で通った）。落ちたら試験を変えずに停止して NEEDS_DECISION: で生の出力を返す。
- (g) QuotesPage.tsx と FunnelLeadsPage.tsx は api の import を消す（§4-F1・§4-B1）。消す前に `grep -n "api\." <ファイル>` が S :59 / :47 の 1 行だけであることを確かめる。ほかにも出たら消さずに残し、報告に書く（tsc と lint が通れば続けてよい）。

## 4-A. #1 frontend/src/api/funnel.ts
- A1 S :176 の followUpsPath の閉じ `}` の次（空行を挟んで）に足す:
```ts

/** チャネル別のリード流入の path（画面の写しの名前もここで決まる・ADR-1054） */
export function channelsPath(month: string, scope?: "mine"): string {
  const params = new URLSearchParams({ month });
  if (scope) params.set("scope", scope);
  return `/analytics/channels?${params}`;
}
```
- A2 S :199-204 の getChannels の中身（S :200-203 の 4 行）を次の 2 行にする（:199 の関数の名前・引数・返す型と :204 の閉じは今のまま）:
```ts
  if (MOCK_MODE) return Promise.resolve(MOCK_CHANNELS);
  return api.get<ChannelsResponse>(channelsPath(month, scope));
```
- 作る path の文字列は今と同じ（`/analytics/channels?month=YYYY-MM`）。

## 4-B. #2 frontend/src/pages/dashboard/FunnelLeadsPage.tsx
- B1 S :7 `import { useEffect, useState } from "react";` → `import { useMemo } from "react";`
- B2 S :11 `import { api } from "../../lib/api";` を消す（§3(g)）。
- B3 S :12 `import { getChannels, type ChannelRow } from "../../api/funnel";` → `import { channelsPath, FUNNEL_MOCK, type ChannelRow, type ChannelsResponse } from "../../api/funnel";`
- B4 S :13 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";` とし、その次に 2 行足す:
```ts
import { useApiQuery } from "../../lib/query/apiQuery";
import { MOCK_CHANNELS } from "../../mocks/funnelFixtures";
```
- B5 S :33-35（rows・summary・loading の useState の 3 行）を消す。:37-40 の currentMonth は残す。
- B6 S :42-58（useEffect の塊）を次に置き換える:
```ts
  const channelsQ = useApiQuery<ChannelsResponse>(channelsPath(currentMonth), { enabled: !FUNNEL_MOCK });
  // このページは管理視点固定なので、対象外も team スコープで揃える。
  const summaryQ = useApiQuery<LeadSummaryResponse>("/analytics/summary?period=1m&tab=team");
  const rows = useMemo<ChannelRowWithId[]>(
    () => ((FUNNEL_MOCK ? MOCK_CHANNELS : channelsQ.data)?.rows ?? []).map((r, i) => ({ ...r, id: i + 1 })),
    [channelsQ.data],
  );
  const summary = summaryQ.data ?? null;
  const loading = (!FUNNEL_MOCK && channelsQ.isPending) || summaryQ.isPending;
  const refreshing = (channelsQ.isFetching || summaryQ.isFetching) && !loading;
```
- B7 S :103-105 の PageLayout の `subtitleKey="funnel.leadsPageTitle"` の次の行に足す:
  `      headerLeft={refreshing ? <Spinner size="sm" /> : undefined}`
- :107 `{loading ? (`・:133 の summary・:144 `data={rows}` は変えない。取れなかった時は今と同じく文を出さない（今の Promise.allSettled と同じ）。
- 理由: 先例は S pages/dashboard/FunnelSection.tsx:456-463（同じ funnel の写しを `enabled: !FUNNEL_MOCK` で取り、mock の時は見本を出す）。

## 4-C. #3 frontend/src/pages/units/UnitsPage.tsx
- C1 S :7 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`
- C2 S :8 `import { useEffect, useRef, useState, FormEvent } from "react";` → `import { useRef, useState, FormEvent } from "react";`
- C3 S :11 `import { api } from "../../lib/api";` の次に `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` を足す（api は書き方と書き出しで使うので残す）。
- C4 S :62 `const [units, setUnits] = useState<Unit[]>([]);` を消す。:63 の error は残す。
- C5 S :64 `const [loading, setLoading] = useState(true);` を消す。:65 の page・:66 の PER_PAGE は残す。S :67 `const [hasNext, setHasNext] = useState(false);` を消す。
- C6 S :69 `const [search, setSearch] = useState("");` の次に足す:
```ts
  const unitsParams = new URLSearchParams({ page: String(page), per_page: String(PER_PAGE) });
  if (search.trim()) unitsParams.set("search", search.trim());
  const unitsQ = useApiQuery<Unit[]>(`/units?${unitsParams.toString()}`, { keepPrevious: true });
  const units = unitsQ.data ?? [];
  const hasNext = units.length === PER_PAGE && !unitsQ.isPlaceholderData;
  const invalidate = useInvalidateApi();
  const shownError = error || (unitsQ.error ? (unitsQ.error instanceof Error ? unitsQ.error.message : t("common.fetchError")) : "");
```
- C7 S :102-116（load・eslint-disable の行・useEffect）を次に置き換える:
```ts
  const load = () => {
    void invalidate(["units"]);
  };
```
- C8 S :206-208 の PageLayout の `subtitleKey="unitMaster.title"` の次の行に足す:
  `      headerLeft={unitsQ.isFetching && !unitsQ.isPending ? <Spinner size="sm" /> : undefined}`
- C9 S :229 `      {error && <div className="error-message">{error}</div>}` → `      {shownError && <div className="error-message">{shownError}</div>}`
- C10 S :367 `      {loading ? (` → `      {unitsQ.isPending ? (`
- C11 S :379 `      {!loading && units.length > 0 && (` → `      {!unitsQ.isPending && units.length > 0 && (`
- load の呼び出し（S :132・:153・:164）・:371 `data={units}`・:396・:409・:413 の hasNext・:80 付近の書き出しは変えない。

## 4-D. #4 frontend/src/pages/status-master/StatusMasterPage.tsx
- D1 S :7 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`
- D2 S :8 `import { useEffect, useRef, useState, FormEvent } from "react";` → `import { useRef, useState, FormEvent } from "react";`
- D3 S :11 `import { api } from "../../lib/api";` の次に `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` を足す（api は残す）。
- D4 S :83 `const [items, setItems] = useState<StatusEntry[]>([]);` を消す。:84 の error は残す。
- D5 S :85 `const [loading, setLoading] = useState(true);` を消す。:86 の page・:87 の PER_PAGE は残す。S :88 `const [hasNext, setHasNext] = useState(false);` を消す。
- D6 S :107 `const [search, setSearch] = useState("");` の次に足す:
```ts
  const itemsParams = new URLSearchParams({ page: String(page), per_page: String(PER_PAGE) });
  if (search.trim()) itemsParams.set("search", search.trim());
  const itemsQ = useApiQuery<StatusEntry[]>(`/status-master?${itemsParams.toString()}`, { keepPrevious: true });
  const items = itemsQ.data ?? [];
  const hasNext = items.length === PER_PAGE && !itemsQ.isPlaceholderData;
  const invalidate = useInvalidateApi();
  const shownError = error || (itemsQ.error ? (itemsQ.error instanceof Error ? itemsQ.error.message : t("common.fetchError")) : "");
```
- D7 S :134-148（load・eslint-disable の行・useEffect）を次に置き換える:
```ts
  const load = () => {
    void invalidate(["status-master"]);
  };
```
- D8 S :317-319 の PageLayout の `subtitleKey="statusMaster.title"` の次の行に足す:
  `      headerLeft={itemsQ.isFetching && !itemsQ.isPending ? <Spinner size="sm" /> : undefined}`
- D9 S :340 `      {error && <div className="error-message">{error}</div>}` → `      {shownError && <div className="error-message">{shownError}</div>}`
- D10 S :420 `      {loading ? (` → `      {itemsQ.isPending ? (`
- D11 S :432 `      {!loading && items.length > 0 && (` → `      {!itemsQ.isPending && items.length > 0 && (`
- load の呼び出し（S :157・:171・:182）・:425 `data={items}`・:449・:462・:466 の hasNext は変えない。

## 4-E. #5 frontend/src/pages/contacts/ContactsPage.tsx
- E1 S :13 `import { useEffect, useState, FormEvent } from "react";` → `import { useMemo, useState, FormEvent } from "react";`
- E2 S :17 `import { api } from "../../lib/api";` の次に `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` を足す（api は残す）。
- E3 S :36 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`
- E4 S :113-114（contacts と companies の useState の 2 行）を消す。:115 の companyFilter・:116 の search は残す。
- E5 S :116 `  const [search, setSearch] = useState("");` の次に足す:
```ts
  const contactParts: string[] = [];
  if (search) contactParts.push(`search=${encodeURIComponent(search)}`);
  if (companyFilter) contactParts.push(`company_id=${encodeURIComponent(companyFilter)}`);
  contactParts.push("per_page=100");
  const contactsQ = useApiQuery<Contact[]>(`/contacts?${contactParts.join("&")}`, { keepPrevious: true });
  // 会社の選択肢は担当者の編集と同じ写し（取れなくても静かに無視・今と同じ）
  const companiesQ = useApiQuery<ContactCompany[]>("/companies?per_page=100");
  const contacts = contactsQ.data ?? [];
  const companies = useMemo<ContactCompany[]>(
    () => (companiesQ.data ?? []).map((c) => ({ id: c.id, company_code: c.company_code, name: c.name })),
    [companiesQ.data],
  );
  const invalidate = useInvalidateApi();
```
- E6 S :124 `  const [error, setError] = useState("");` の次に足す:
  `  const shownError = error || (contactsQ.error ? (contactsQ.error instanceof Error ? contactsQ.error.message : t("common.fetchError")) : "");`
- E7 S :125 `  const [loading, setLoading] = useState(true);` を消す。
- E8 S :131-157（loadContacts・loadCompanies・eslint-disable の行・useEffect 2 行）を次に置き換える:
```ts
  const loadContacts = async () => {
    await invalidate(["contacts"]);
  };
```
- E9 S :271-275 の PageLayout の `subtitleKey="contacts.subtitle"` の次の行に足す:
  `      headerLeft={contactsQ.isFetching && !contactsQ.isPending ? <Spinner size="sm" /> : undefined}`
- E10 S :297 `      {error && <div className="error-banner">{error}</div>}` → `      {shownError && <div className="error-banner">{shownError}</div>}`
- E11 S :387 `      {loading ? (` → `      {contactsQ.isPending ? (`
- loadContacts の呼び出し（S :191・:214・:225・:239 の `await loadContacts();`）・companyName（S :159-）・:420 `data={contacts}` は変えない。
- 型の注意: S の ContactCompany が id・company_code・name 以外の欄を持つ時は、E5 の map の行はそのまま使い、tsc の結果を報告に書く（今の S :149 の map と同じ形なので通る見込み）。

## 4-F. #6 frontend/src/pages/quotes/QuotesPage.tsx
- F1 S :9 `import { useEffect, useMemo, useState } from "react";` → `import { useMemo, useState } from "react";`。S :12 `import { api } from "../../lib/api";` を `import { useApiQuery } from "../../lib/query/apiQuery";` に置き換える（§3(g)）。
- F2 S :21 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`
- F3 S :49 `  const [quotes, setQuotes] = useState<Quote[]>([]);` を消す。
- F4 S :50 `  const [statusFilter, setStatusFilter] = useState("");` の次に足す:
```ts
  const quotesQ = useApiQuery<Quote[]>(`/quotes${statusFilter ? `?status=${statusFilter}` : ""}`, { keepPrevious: true });
  const quotes = useMemo(() => quotesQ.data ?? [], [quotesQ.data]);
```
- F5 S :53-54（error と loading の useState の 2 行）を次の 1 行に置き換える（setError は S :62 の load の中だけで使う）:
  `  const shownError = quotesQ.error ? (quotesQ.error instanceof Error ? quotesQ.error.message : t("common.fetchError")) : "";`
- F6 S :56-69（load・空行・eslint-disable の行・useEffect）を消す（load の呼び出しは他に無い）。
- F7 S :88-90 の PageLayout の `subtitleKey="quotes.subtitle"` の次の行に足す:
  `      headerLeft={quotesQ.isFetching && !quotesQ.isPending ? <Spinner size="sm" /> : undefined}`
- F8 S :143 `      {error && <div className="error-message">{error}</div>}` → `      {shownError && <div className="error-message">{shownError}</div>}`
- F9 S :145 `      {loading ? (` → `      {quotesQ.isPending ? (`
- :82-85 の sortedQuotes・:175 `data={sortedQuotes}` は変えない。

## 4-G. #7 frontend/src/pages/quote-detail/QuoteDetailPage.tsx
- G1 S :9 `import { useEffect, useState } from "react";` → `import { useState } from "react";`
- G2 S :12 `import { api } from "../../lib/api";` の次に `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` を足す（api は書き方と為替で使うので残す）。
- G3 S :18 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`
- G4 S :60-62（quote・error・loading の useState の 3 行）を次に置き換える:
```ts
  const quoteQ = useApiQuery<QuoteDetail>(`/quotes/${id}`, { enabled: id !== undefined });
  const quote = quoteQ.data ?? null;
  const [error, setError] = useState("");
  const shownError = error || (quoteQ.error ? (quoteQ.error instanceof Error ? quoteQ.error.message : t("common.fetchError")) : "");
  const invalidate = useInvalidateApi();
```
- G5 S :66-78（load・空行・eslint-disable の行・useEffect）を次に置き換える:
```ts
  const load = () => {
    void invalidate(["quotes", id ?? ""]);
  };
```
- G6 S :120 `  if (loading) return <div className="page"><LoadingBlock /></div>;` → `  if (quoteQ.isPending) return <div className="page"><LoadingBlock /></div>;`
- G7 S :121 の `{error || t("common.fetchError")}` → `{shownError || t("common.fetchError")}`
- G8 S :127-129 の PageLayout の `subtitleKey="quotes.detailSubtitle"` の次の行に足す:
  `      headerLeft={quoteQ.isFetching && !quoteQ.isPending ? <Spinner size="sm" /> : undefined}`
- G9 S :156 `      {error && <div className="error-message">{error}</div>}` → `      {shownError && <div className="error-message">{shownError}</div>}`
- doAction（S :83 の `load();`）・convertToInvoice・handleFetchFxRate（S :102-113）は変えない。
- 理由: 段 3 の 1 回目の請求書の詳しい画面（batch3a-card.md §4-I）と同じ形。`invalidate(["quotes", "7"])` は `/quotes/7` の写しだけを古い印にする（見積一覧の `["api", uid, "quotes", {…}]` は words が `quotes` の 1 語なので、2 語目 "7" が合わず当たらない）。

## 4-H. #8 frontend/src/pages/teams/TeamsPage.tsx
- H1 S :10 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`
- H2 S :11 `import { useEffect, useState, FormEvent } from "react";` → `import { useState, FormEvent } from "react";`
- H3 S :14 `import { api } from "../../lib/api";` の次に `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` を足す（api は残す）。
- H4 S :59 `  const [teams, setTeams] = useState<Team[]>([]);` を次に置き換える:
```ts
  const teamsQ = useApiQuery<Team[]>("/teams");
  const teams = teamsQ.data ?? [];
  const invalidate = useInvalidateApi();
```
- H5 S :67 `  const [error, setError] = useState("");` の次に足す:
  `  const shownError = error || (teamsQ.error ? (teamsQ.error instanceof Error ? teamsQ.error.message : t("common.fetchError")) : "");`
- H6 S :68 `  const [loading, setLoading] = useState(true);` を消す。
- H7 S :74-83（loadTeams）を次に置き換える:
```ts
  const loadTeams = () => {
    void invalidate(["teams"]);
  };
```
- H8 S :94-95（eslint-disable の行と useEffect）を消す。:85-92 の loadMembers は変えない。
- H9 S :175-177 の PageLayout の `subtitleKey="teams.subtitle"` の次の行に足す:
  `      headerLeft={teamsQ.isFetching && !teamsQ.isPending ? <Spinner size="sm" /> : undefined}`
- H10 S :179 `      {error && <div className="error-message">{error}</div>}` → `      {shownError && <div className="error-message">{shownError}</div>}`
- H11 S :273 `      {loading ? (` → `      {teamsQ.isPending ? (`
- loadTeams の呼び出し（S :109・:127・:139・:157・:168）・:263 `data={members}`・:296 `data={teams}` は変えない。
- 注意: `invalidate(["teams"])` は words が `teams` で始まる写しをすべて古い印にする（`/teams/7/members` も含む）。開いている写しだけが取り直されるので、人の一覧を開いていない時は取りに行かない。

## 4-I. #9 frontend/src/pages/goal-setting/GoalSettingPage.tsx
- I1 S :15 `import { useEffect, useRef, useState } from "react";` → `import { useEffect, useMemo, useRef, useState } from "react";`
- I2 S :17 `import { api } from "../../lib/api";` の次に `import { useApiQuery } from "../../lib/query/apiQuery";` を足す（api は目標の値の取り方と保存で使うので残す）。
- I3 S :514-515（teams と currentUser の useState の 2 行）を次に置き換える:
```ts
  const meQ = useApiQuery<MyPermissionsResponse>("/me/permissions");
  const teamsQ = useApiQuery<Team[]>("/teams");
  const teams = useMemo(() => teamsQ.data ?? [], [teamsQ.data]);
  const currentUser = useMemo<CurrentUser | null>(
    () => (meQ.data ? { id: meQ.data.user_id, isTenantAdmin: meQ.data.is_tenant_admin } : null),
    [meQ.data],
  );
```
- I4 S :516 `  const [selectedTeamId, setSelectedTeamId] = useState<number | null>(null);` の次に足す（選んだチームが一覧に無い時だけ先頭にする・V3b-6）:
```ts
  if (teams.length > 0 && !teams.some((tm) => tm.id === selectedTeamId)) setSelectedTeamId(teams[0].id);
```
- I5 S :536 `  const [loading, setLoading] = useState(true);` を消す。:535 の error は残す（保存の失敗 S :636 で使う）。
- I6 S :547-560（`useEffect(() => {` から `}, []);` まで・Promise.all の塊）を次に置き換える:
```ts
  const loading = meQ.isPending || teamsQ.isPending;
  const loadError = meQ.error ?? teamsQ.error;
  const shownError = error || (loadError ? (loadError instanceof Error ? loadError.message : t("common.fetchError")) : "");
```
- I7 S :655 `      {error && <div className="error-message">{error}</div>}` → `      {shownError && <div className="error-message">{shownError}</div>}`
- :563・:587 の 2 つの effect（目標の値）・:642 selectedTeam・:645 `if (loading) {` は変えない。
- 理由: currentUser は写しの中身が変わらない時は同じ物（TanStack の structural sharing と useMemo）なので、S :563 の effect は写しが届いた時と中身が変わった時だけ動く。I4 は React の公式の「描画の途中で state を直す」形（react.dev の useState「Storing information from previous renders」）。条件が成り立つのは一覧が変わった時だけで、直した後は成り立たないので繰り返さない。

## 4-J. #10 frontend/src/pages/schedule/ScheduleSettingsPage.tsx
- J1 S :1 `import { useEffect, useMemo, useState } from "react";` → `import { useMemo, useState } from "react";`
- J2 S :10 `import { api } from "../../lib/api";` の次に 2 行足す（api は保存で使うので残す）:
```ts
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { useSeededForm } from "../../lib/query/useSeededForm";
```
- J3 S :16 `import { LoadingBlock } from "../../components/loading";` の次に空行を挟んで足す（人が変わった時もフォームの空の値を同じ物にする）:
```ts

const EMPTY_OWNERS: CalendarOwner[] = [];
```
- J4 S :38-39（owners と loading の useState の 2 行）を次に置き換える:
```ts
  const ownersQ = useApiQuery<ApiCalendarOwnersResponse>("/calendar/owners", {
    enabled: !permsLoading && hasPermission("staff.view"),
  });
  const { form: owners, setForm: setOwners, ready } = useSeededForm(
    "calendar/owners",
    ownersQ.data,
    (d) => d.owners.map(normalizeOwner),
    EMPTY_OWNERS,
  );
  const loading = !ready && !ownersQ.isError;
  const invalidate = useInvalidateApi();
```
- J5 S :42 `  const [error, setError] = useState<string | null>(null);` の次に足す:
  `  const shownError = error ?? (ownersQ.error ? (ownersQ.error instanceof Error ? ownersQ.error.message : t("common.fetchError")) : null);`
- J6 S :51-81（useEffect の塊）を消す。:83-87 の updateOwner は変えない（setOwners は関数も受け取る）。
- J7 S :101 `      setSavedStaffId(owner.staffId);` の次の行に足す（保存できた後だけ。失敗した時は取り直さない）:
  `      void invalidate(["calendar", "owners"]);`
- J8 S :126 `        {error && <div className="error-message">{error}</div>}` → `        {shownError && <div className="error-message">{shownError}</div>}`
- :109-121（権限の読み込み中と権限が無い時）・:127 `{loading ? (` は変えない。
- 動き: 権限が無い時は取りに行かず、:113 の権限の文を出す（今と同じ）。人がまだ何も直していない時だけ、取り直した写しでフォームを作り直す。直した後は作り直さない（打ちかけを消さない）。保存した後の取り直しは、次に開いた時に新しい中身を出すため（直した後の今のフォームは作り直されない）。

## 4-K. #11 frontend/src/components/TeamFormButtonMigration.test.tsx（ほかの行は変えない）
- K1 S :9 `import en from '../locales/en.json';` の次に `import { queryClient } from '../lib/query/apiQuery';` を足す。
- K2 S :73 の行頭 `  cleanup(); expect(fetch)` → `  cleanup(); queryClient.clear(); expect(fetch)`（同じ行の後ろは変えない）。
- 理由: 画面が同じ 1 個の写しの置き場を使うので、前の試験の写しが次の試験に残らないようにする（段 3 の 1 回目の §4-K と同じ）。この試験は AuthContext を `user: mock.user`（uid 'fixture-user'）で mock 済み（S :13）なので、人を入れる直しは要らない。

## 4-L. #12 frontend/src/lib/query/batch3bPages.test.tsx（新しく作る・全文）
```tsx
/**
 * ADR-1054 段 3 の 2 回目: 本物の画面の試験（Q1）。
 * Q1 戻った時に写しを先に出す（読み込み中の印を出さない）・一覧と詳しい画面は見出しの横に回る印・裏で取り直す。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import type { ComponentType } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ContactsPage from "../../pages/contacts/ContactsPage";
import FunnelLeadsPage from "../../pages/dashboard/FunnelLeadsPage";
import GoalSettingPage from "../../pages/goal-setting/GoalSettingPage";
import QuoteDetailPage from "../../pages/quote-detail/QuoteDetailPage";
import QuotesPage from "../../pages/quotes/QuotesPage";
import ScheduleSettingsPage from "../../pages/schedule/ScheduleSettingsPage";
import StatusMasterPage from "../../pages/status-master/StatusMasterPage";
import TeamsPage from "../../pages/teams/TeamsPage";
import UnitsPage from "../../pages/units/UnitsPage";
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
  // api.ts が i18n.ts を読み、i18n.ts が initReactI18next を使う（同じ書き方: src/lib/query/batch3aPages.test.tsx）
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

// 中身は画面の型（UnitsPage.tsx:25-33・StatusMasterPage.tsx:26-39・ContactsPage.tsx:38-・QuotesPage.tsx:23-・
// QuoteDetailPage.tsx:26-53・TeamsPage.tsx:29-38・schedule-owner.ts:3-19）の欄から画面が使う物だけ。
// チームは TeamFormButtonMigration.test.tsx:14 の写し
const unit = { id: 1, code: "FX", canonical: "Fixture Unit", kubun: null, is_active: true, created_at: "", updated_at: "" };
const status = { id: 1, status_id: "FX", canonical: "Fixture Status", search_pattern: "", exclude_pattern: "", priority: 1, enabled: true, note: "", match_type: "contains", effect: "OUTPUT", created_at: "", updated_at: "" };
const contact = { id: 52, tenant_id: 1, company_id: 41, contact_code: "C52", lead_id: null, surname: "Fixture contact", given_name: null, display_name: null, job_title: null, department: null, is_primary_contact: false, primary_email: null, primary_phone: null, status: "active", notes: null, emails: [], discord: null, contact_channels: [], created_at: "", updated_at: "" };
const quote = { id: 7, quote_code: "Q-7", company_id: 4, contact_id: null, currency: "USD", subtotal: 10, total_amount: 10, status: "approved", validity_date: null, created_at: "" };
const quoteDetail = { ...quote, shipping_fee: 0, tax_amount: 0, notes: null, items: [] };
const team = { id: 7, name: "Fixture Team", leader_id: null, description: null, is_active: true, member_count: 0, created_at: "", updated_at: "" };
const owners = { can_manage_others: true, current_staff_id: 1, current_user_id: 1, owners: [{ staff_id: 1, user_id: 1, staff_code: "S1", name: "Fixture Owner", primary_email: null, color: "", is_visible: true, share_mode: "self", is_self: true }] };

const fixtures: Record<string, unknown> = {
  "/units?page=1&per_page=100": [unit],
  "/status-master?page=1&per_page=100": [status],
  "/contacts?per_page=100": [contact],
  "/companies?per_page=100": [],
  "/quotes": [quote],
  "/quotes/7": quoteDetail,
  "/teams": [team],
  "/me/permissions": { user_id: 1, is_tenant_admin: true, permissions: [] },
  "/calendar/owners": owners,
  "/analytics/summary?period=1m&tab=team": { leads: { excluded: 37 } },
};
// チャネル別の表は月で path が変わるので頭で見分ける。画面の中の部品が別に取る物（目標の値など）は空の一覧で返す
const answer = (path: string) =>
  (path in fixtures ? fixtures[path] : path.startsWith("/analytics/channels?") ? { rows: [] } : []) as never;

type Case = { name: string; Page: ComponentType; route: string; at: string; path: string; text: string | RegExp; spinner: boolean };
const cases: Case[] = [
  { name: "funnel leads", Page: FunnelLeadsPage, route: "/dashboard/leads", at: "/dashboard/leads", path: "/analytics/summary?period=1m&tab=team", text: "37", spinner: true },
  { name: "units", Page: UnitsPage, route: "/management-center/units", at: "/management-center/units", path: "/units?page=1&per_page=100", text: "Fixture Unit", spinner: true },
  { name: "status master", Page: StatusMasterPage, route: "/management-center/status-master", at: "/management-center/status-master", path: "/status-master?page=1&per_page=100", text: "Fixture Status", spinner: true },
  { name: "contacts", Page: ContactsPage, route: "/crm/contacts", at: "/crm/contacts", path: "/contacts?per_page=100", text: "Fixture contact", spinner: true },
  { name: "schedule settings", Page: ScheduleSettingsPage, route: "/schedule/settings", at: "/schedule/settings", path: "/calendar/owners", text: "Fixture Owner", spinner: false },
  { name: "quotes", Page: QuotesPage, route: "/quotes", at: "/quotes", path: "/quotes", text: "Q-7", spinner: true },
  { name: "goal settings", Page: GoalSettingPage, route: "/goals/settings", at: "/goals/settings", path: "/teams", text: "Fixture Team", spinner: false },
  { name: "teams", Page: TeamsPage, route: "/teams", at: "/teams", path: "/teams", text: "Fixture Team", spinner: true },
  { name: "quote detail", Page: QuoteDetailPage, route: "/quotes/:id", at: "/quotes/7", path: "/quotes/7", text: /Q-7/, spinner: true },
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

const shown = (c: Case) => screen.queryAllByText(c.text);
const found = (c: Case) => screen.findAllByText(c.text);

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
    await waitFor(() => expect(spy).toHaveBeenCalledWith(c.path));
  });

  it("funnel leads fetches the channel table through the one path builder", async () => {
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) => answer(path));
    render(<Tree c={cases[0]} />);
    await found(cases[0]);
    expect(spy).toHaveBeenCalledWith(expect.stringMatching(/^\/analytics\/channels\?month=\d{4}-\d{2}$/));
  });
});
```
- LoadingBlock の見分けは `.sa-loading-block`、回る印の見分けは `.page-layout-title-row .sa-spinner`（段 3 の 1 回目のカード §4-L と同じ）。目標の設定と予定の設定は回る印を出さない（V3b-6・V3b-7）。
- Q1 は 9 画面（10 行のうち /teams と /management-center/teams は同じ画面）。単位と状態マスタの path は §4-C6・§4-D6 が page 1・PER_PAGE 100（S UnitsPage.tsx:66・StatusMasterPage.tsx:87）・検索なしで作る文字列。担当者の path は §4-E5 が検索なし・会社の絞り込みなし（MemoryRouter の URL に company_id が無い）で作る文字列。
- 目標の設定の「Fixture Team」はチームの選び肢（S GoalSettingPage.tsx:725-728。`teams.length > 0` の時だけ出る・S :712）に出る。
- 予定の設定の「Fixture Owner」は自分の行の名前（S ScheduleSettingsPage.tsx の OwnerBadge）に出る。見本の color "" は normalizeOwner が既定の色にする（S schedule-owner.ts:43）。

## 4-M. 実装役の手順（1 手順 1 命令。<W> は手順1 で作られた作業場所の絶対パス）
手順1. クラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）どおり、作業場所を作り、push 済みの枝の先頭に合わせる（設計担当が §1 #13〜#15 を push 済み）。
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/line-like-speed-batch3b
  （出力に出た作業場所の絶対パスを <W> として報告に書く。）
  cd <W> && git fetch origin release/line-like-speed-batch3b
  cd <W> && git switch -C release/line-like-speed-batch3b origin/release/line-like-speed-batch3b
  cd <W> && git rev-parse HEAD origin/release/line-like-speed-batch3b
  （2 行が同じことを確かめる。違えば停止して BLOCKED: で報告する。main は取り込まない。reset・rebase・force・merge・pull は使わない）
  cd <W> && ./scripts/dev/executor-preflight.sh > /tmp/b3b-preflight.txt 2>&1
  cd <W> && grep -n "FAIL" /tmp/b3b-preflight.txt | head -20
  cd <W> && grep -n "origin/main は存在" /tmp/b3b-preflight.txt | head -3
  （FAIL の行が次の 3 つのうちのどれかだけなら続ける: `GitHub API に到達不可` の 1 件・`gh auth switch --hostname github.com --user shingo-cc` の失敗の 1 件・その結果の `PREFLIGHT FAIL` の行。理由は段 3 の 1 回目のカード §4-M 手順1 と同じ。続ける時は `[OK]   origin/main は存在` の行があることを 2 つ目の grep で確かめ、無ければ停止する。ほかの FAIL が 1 件でもあれば停止し、BLOCKED: で grep の出力を報告する。）
  cd <W> && git fetch origin main
  cd <W> && git diff --stat 3bfc5d555661bf81701890c43cd0f57314f56875 origin/main -- frontend/src | tail -5
  （§3(a) の確かめ。）
手順2. 依存を入れ、§3(b) を確かめ、変える前の lint の警告を数える。
  cd <W>/frontend && npm ci > /tmp/b3b-ci.txt 2>&1
  cd <W> && tail -5 /tmp/b3b-ci.txt
  cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json
  cd <W>/frontend && grep -n "api\." src/pages/quotes/QuotesPage.tsx src/pages/dashboard/FunnelLeadsPage.tsx
  （§3(g) の確かめ。）
  cd <W>/frontend && npx eslint src/api/funnel.ts src/pages/dashboard/FunnelLeadsPage.tsx src/pages/units/UnitsPage.tsx src/pages/status-master/StatusMasterPage.tsx src/pages/contacts/ContactsPage.tsx src/pages/quotes/QuotesPage.tsx src/pages/quote-detail/QuoteDetailPage.tsx src/pages/teams/TeamsPage.tsx src/pages/goal-setting/GoalSettingPage.tsx src/pages/schedule/ScheduleSettingsPage.tsx > /tmp/b3b-lint-before.txt 2>&1
  cd <W> && tail -5 /tmp/b3b-lint-before.txt
手順3. §4-L の全文で #12 を作り、§4-A〜§4-K のとおり #1〜#11 を直す。各ファイルを直す前に、§4 の「変更前」の文を `grep -n` で確かめる（§3(c)）。終わったら残りが無いことを確かめる。
  cd <W> && grep -n "useEffect\|setLoading\|setUnits\|setItems\|setHasNext\|setContacts\|setCompanies\|setQuotes\|setQuote\b\|setTeams\|setCurrentUser\|getChannels\|setRows\|setSummary" frontend/src/pages/dashboard/FunnelLeadsPage.tsx frontend/src/pages/units/UnitsPage.tsx frontend/src/pages/status-master/StatusMasterPage.tsx frontend/src/pages/contacts/ContactsPage.tsx frontend/src/pages/quotes/QuotesPage.tsx frontend/src/pages/quote-detail/QuoteDetailPage.tsx frontend/src/pages/teams/TeamsPage.tsx frontend/src/pages/goal-setting/GoalSettingPage.tsx frontend/src/pages/schedule/ScheduleSettingsPage.tsx | head -20
  （出てよいのは GoalSettingPage.tsx の useEffect の行だけ: import の 1 行・GoalAdvisorPanel の 2 つ（S :265・:272）・目標の値の 2 つ（S :563・:587）と、相談の読み込み中の印 setLoadingAdvice の 3 行（S :260・:288・:312。触らない）。ほかが出たら §4 の写し違いを直す。）
手順4. 型を作ってから試験を流す（新しい試験・直した今ある試験・9 画面を描く今ある試験・全部の試験・型・lint）。作る型（frontend/src/api/generated/）は .gitignore で除かれるので commit に入らない。
  cd <W>/frontend && npm run generate:api-types > /tmp/b3b-gen.txt 2>&1
  cd <W> && tail -3 /tmp/b3b-gen.txt
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/lib/query > /tmp/b3b-unit.txt 2>&1
  cd <W> && tail -30 /tmp/b3b-unit.txt
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/components/TeamFormButtonMigration.test.tsx src/components/AllLegacyButtonDynamicMigration.test.tsx src/components/CommerceNavigationButtonMigration.test.tsx src/components/MasterSearchButtonMigration.test.tsx src/components/PageFormButtonMigration.test.tsx src/components/ToggleMigration.test.tsx > /tmp/b3b-pages.txt 2>&1
  cd <W> && tail -30 /tmp/b3b-pages.txt
  cd <W>/frontend && npm run test:unit > /tmp/b3b-unit-all.txt 2>&1
  cd <W> && tail -15 /tmp/b3b-unit-all.txt
  cd <W>/frontend && npx tsc --noEmit -p . > /tmp/b3b-tsc.txt 2>&1
  cd <W> && tail -20 /tmp/b3b-tsc.txt
  cd <W>/frontend && npx eslint src/lib/query src/api/funnel.ts src/pages/dashboard/FunnelLeadsPage.tsx src/pages/units/UnitsPage.tsx src/pages/status-master/StatusMasterPage.tsx src/pages/contacts/ContactsPage.tsx src/pages/quotes/QuotesPage.tsx src/pages/quote-detail/QuoteDetailPage.tsx src/pages/teams/TeamsPage.tsx src/pages/goal-setting/GoalSettingPage.tsx src/pages/schedule/ScheduleSettingsPage.tsx > /tmp/b3b-lint.txt 2>&1
  cd <W> && tail -20 /tmp/b3b-lint.txt
  （lint の警告が手順2 の数より増えていないこと・誤りが 0 であること。§3(d)。）
手順5. 本番と同じ形で組み立てられるか確かめる。
  cd <W>/frontend && npm run build > /tmp/b3b-build.txt 2>&1
  cd <W> && tail -15 /tmp/b3b-build.txt
手順6. 変わったファイルが §1 の #1〜#12 だけか確かめ、画面の書く path と表・フォームの行が変わっていないことを見る。
  cd <W> && git status --short | head -30
  cd <W> && git diff -w --stat origin/release/line-like-speed-batch3b | tail -20
  cd <W> && git diff -w origin/release/line-like-speed-batch3b -- frontend/src/pages frontend/src/api | head -600
手順7. commit する。
  cd <W> && git add frontend/src/api/funnel.ts frontend/src/pages/dashboard/FunnelLeadsPage.tsx frontend/src/pages/units/UnitsPage.tsx frontend/src/pages/status-master/StatusMasterPage.tsx frontend/src/pages/contacts/ContactsPage.tsx frontend/src/pages/quotes/QuotesPage.tsx frontend/src/pages/quote-detail/QuoteDetailPage.tsx frontend/src/pages/teams/TeamsPage.tsx frontend/src/pages/goal-setting/GoalSettingPage.tsx frontend/src/pages/schedule/ScheduleSettingsPage.tsx frontend/src/components/TeamFormButtonMigration.test.tsx frontend/src/lib/query/batch3bPages.test.tsx
  cd <W> && git commit -m "feat: 遅い順の次の10画面を写しを先に出して裏で取り直す形に（ADR-1054 段3の2回目）"
手順8. commit が在ることを確かめてから push する（--no-verify は使わない。push の前の検査が × なら直してから push。fast-forward でないと断られたら直さず BLOCKED:）。
  cd <W> && git log -3 --oneline
  cd <W> && git push -u origin release/line-like-speed-batch3b
手順9. 報告を返す。PR は作らない（設計担当が手元で作る）。報告の 1 つの発言は 600 文字以内にして、番号付きの発言に分ける。報告には手順ごとの tail の出力（生のまま）と、§3(a)〜(g) の結果を書く。

## 4. GO と承認・PO の操作
- PO の実装承認: 2026-11-02 PO 選択「1」（残りの遅い画面を遅い順に 10 画面ずつ、本番の測定まで直す）。ADR-1054 は Accepted。このカードの審査合格の後に、設計担当がクラウドの Sonnet へ渡す。
- 触るのは frontend の画面 9 個・部品の path 1 つ・試験と書類だけで、migrations・deploy.yml・本番 scripts を含まない（番号付き GO の要る危ない PR ではない）。main へのマージで本番の画面に出る（deploy.yml が main への push で動く）。マージは PO の委任に基づき設計担当（Claude Opus）が、マージ前の審査役の APPROVE と必須の確認がすべて pass の後に行う。
- PO が操作することはない。

## 5. 受入（○×）
| # | 基準 | 検証方法 |
|---|---|---|
| B1 | Q1（9 画面とも戻った時に LoadingBlock 0 個で前の中身が出る・一覧と詳しい画面は見出しの横に回る印・裏で取り直す）とリード流入の表の path の試験が合格。段 3 の 1 回目の Q2・Q3（K5）も合格のまま | /tmp/b3b-unit.txt の最後（batch3bPages.test.tsx の 10 件が passed・batch3aPages.test.tsx・useSeededForm.test.tsx・apiQuery.test.tsx・stage2Pages.test.tsx も passed）と、PR の CI の unit-run が success |
| B2 | 今ある画面の試験 6 本・全部の試験・型・lint・組み立てが通る | /tmp/b3b-pages.txt・b3b-unit-all.txt・b3b-tsc.txt・b3b-lint.txt・b3b-build.txt の最後と、PR の必須の確認がすべて pass |
| B3 | 変わったのは §1 の 15 ファイルだけ。画面の書く path と中身・表・フォームの欄は変わっていない | gh pr diff --name-only と git diff -w（§4-M 手順6） |
| B4 | QueryClient を作るのは apiQuery.ts の 1 か所だけ・staleTime を設定していない・写しをブラウザの保存に書かない | `git grep -n "new QueryClient" -- frontend/src` が 1 行、`git grep -n "staleTime:" -- frontend/src` が 0 行、`git grep -n -i "persist" -- frontend/src/lib/query frontend/package.json` が 0 行 |
| B5 | マージの後、毎朝の画面の記録を手で 1 回動かし、§0 V3b-1 の 10 行で K1（戻った時の秒）≤0.1 秒、K2（初めて開く秒）≤2 秒、403・5xx が 0 件。ほかの行は K2 の最大と 2 秒を超えた画面の数が段 3 の 1 回目の受入（run 41389073263）から悪化していない | prod-ui-check の実行の要約（設計担当。`gh workflow run prod-ui-check.yml --ref main` の後に要約の表を読む） |
| B6 | 取り直した後の中身が DB と一致（tenant 001）: 単位・状態マスタ・担当者・チームの件数が、本番 DB の同じ条件の件数と同じ | 設計担当が本番の読むだけの道（ADR-1024）で tenant 001 の行を数える。画面の件数は prod-ui-check の記録か PO のログイン済みの Chrome で数える。数えられない時は「画面の件数はまだ確かめていない」と記録し、backend を変えていないこと（B3）と Q1 を根拠にする |
| B7 | マージの後、deploy が成功し、本番の画面が開く | deploy.yml の実行の結論 success と時刻。本番 https://app.salesanchor.jp/ が開き、ブラウザの誤りの記録に TanStack 由来の誤りが無い（設計担当） |
