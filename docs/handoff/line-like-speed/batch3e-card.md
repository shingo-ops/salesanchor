# 段 3 の 5 回目の実装カード（権限の要る 5 画面を「写しを先に出して裏で取り直す」形に変える）

- 対象: docs/handoff/line-like-speed/design.md §3-2（部品）・§3-3（触らない範囲）・§3-4 の段 3・§3-5 の K1・K2・K5・§3-7。ADR-1054（Accepted）。段 3 の 1〜4 回目のカード（docs/handoff/line-like-speed/batch3a-card.md・batch3b-card.md・batch3c-card.md・batch3d-card.md）の部品と形をそのまま使う。
- 根拠の写し: S=origin/main 0f68fbc78c005ebbd7f39ab923ba3ad9eabd212b。行番号はすべてこの sha。2026-11-03 に設計担当が S の写しで行を読んだ。2026-11-03 時点の origin/main bfcaaa29b と S の間の frontend/src の差は 5 ファイル（components/ToggleMigration.test.tsx・locales/en.json・locales/ja.json・pages/schedule/SchedulePageImpl.tsx・pages/schedule/SchedulePageImpl.test.tsx。116 行足し・5 行消し）で、§1 の #1〜#10 は含まない（設計担当が `git diff --stat` で確かめた）。実装の前に最新の origin/main で行を合わせ直す（§3(a)）。
- 読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/04-worktree.md・guards/05-pr.md・guards/10-executor.md・scripts/agent-hooks/cloud/rules.md（段 3 の 1〜4 回目のカードと同じ節。照合も同じ: 全命令は cd <W> で始める・出力は tail/head で上限・新しいファイルは丸ごとの全文・作業場所は new-worktree.sh で作り出力をパイプに通さない・PR は実行役が作らない・出力をファイルに残す命令と tail で読む命令は別の行）。
- 実行役はクラウドの Sonnet。作業場所の作り方はクラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）を正とする。.pr-number・gh-pr-create-safe.sh は使わない。出力には上限を付ける。待つために sleep を使わない。
- 状態: 第 1 版（2026-11-03 設計担当 Claude Opus）。
- 受領確認: 実装役は着手の最初の報告に「段 3 の 5 回目のカード 第 1 版を受け取った・S=0f68fbc78」と書く。

## 0. 設計からの直し・詳しくした点（V3e。設計の合格線は変えない）
- V3e-1 対象は、測る利用者（tenant 001 の測定用の利用者）に権限を足した後も、開くたびに中身を消して取り直している権限の要る画面のうち 5 画面（design §3-4-18）。PO 選択「1」（権限を足して本番の測定まで直す）。残りの 3 画面（在庫の見え方・状態・商品区分）は測る利用者に見る権限が足りておらず、このカードの対象ではない（設計担当が PO に別に聞く）。

  | 行（毎朝の記録の画面） | 画面のファイル | 読む path |
  |---|---|---|
  | /channels・/management-center/channels | pages/channels/ChannelsPage.tsx | /meta/channels（Discord の設定 /admin/discord-config は変えない） |
  | /roles・/management-center/roles | pages/roles/RolesPage.tsx | /roles・/permissions・/roles/<id>/permissions |
  | /staff・/management-center/staff・management-center→staff | pages/staff/StaffPage.tsx | /staff・/roles |
  | /staff/:id/edit | pages/staff/StaffEditPage.tsx | /staff/<id>・/roles |
  | /orders | pages/orders/OrdersPage.tsx と pages/orders/useOrdersState.ts | /orders?<条件>・/orders/group-counts・/companies?per_page=100・/orders/<id>/shipping・/orders/<id>/purchase |

  画面の道は S frontend/src/App.tsx:257・:266・:267・:272・:287・:396・:398・:407。9 行の基準（権限を足した後の K1・K2）は §5 B5 の表に書く。
- V3e-2 写しの置き場の部品（S frontend/src/lib/query/apiQuery.ts）と、フォームの初めの値を写しから作る部品（S frontend/src/lib/query/useSeededForm.ts）は変えない。使うのは useApiQuery・useApiQueries・useInvalidateApi・useApiCache・useSeededForm だけ。QueryClient を足さない・staleTime を設定しない・写しをブラウザの保存に書かない。
- V3e-3 一覧の画面（チャネル・スタッフ・受注）は段 3 の 1〜4 回目と同じ形にする: 写しがあればすぐ出す・読み込み中の印（LoadingBlock）は写しが無い初回（isPending）だけ・写しを出したまま裏で取り直している間は見出しの横に小さな回る印（金型 components/loading の Spinner・size "sm"・PageLayout の headerLeft）。ロールの画面は PageLayout を使っていない（S RolesPage.tsx:307 の `<div className="page roles-page">`）ので回る印は出さない。スタッフの編集は編集のフォームの画面なので回る印は出さない（段 3 の 1 回目の Bot の編集と同じ）。
- V3e-4 同じ path は同じ写しを使う（同じ API の同じ答えを分けて持たない）: `/roles` はロール・スタッフ・スタッフの編集の 3 画面で 1 つの写し。
- V3e-5 書いた後の取り直し: 今の `loadChannels()`・`loadAll()`・`loadOrders()` を呼んでいる所は、そのまま呼び、中身を「その画面の読む path の写しを古い印にする（useInvalidateApi）」に変える。古い印になった写しは、画面が開いている間に裏で 1 回取り直される。
  - ロールの画面の作成・編集・削除の後は、今と同じく `/roles` を 1 回取り直す（useApiCache の fetch で同じ写しに入れる。古い印にする形にしないのは、消したロールの `/roles/<id>/permissions` を取り直すと 404 になるため）。
  - ロールの権限の保存の後は、そのロールの `/roles/<id>/permissions` だけを古い印にして取り直す（今は手元の元の値を保存した値に置き換えるだけ: S RolesPage.tsx:236）。
  - 受注の `invalidate(["orders"])` は `/orders` から始まる写し（一覧・数・各受注の発送と仕入）を古い印にし、画面に出ている物を取り直す。今も書いた後に一覧を取り直すと、発送と仕入を全部取り直している（S useOrdersState.ts:199-247 は orders が変わるたびに動く）ので同じ。
- V3e-6 見た目の変わる所（意図した変化）:
  - 受注: 書いた後（作成・編集・削除・支払済の切り替え）、今は読み込み中の印で表が消えてから出直す（S useOrdersState.ts:159 の `setLoading(true)`）。直した後は表を出したまま裏で取り直し、見出しの横に回る印を出す。絞り込み・検索・並べ替えを変えた時は keepPrevious を付けない: 今も変えるたびに読み込み中の印を出す（S :159）ので、新しい条件の写しが無い時は同じく読み込み中の印を出す。1 度開いた条件は写しからすぐ出る。
  - 受注: 支払済の切り替えの後に、今は一覧だけ取り直す（S :327）が、直した後は数（/orders/group-counts）も 1 回取り直す（同じ頭の写しのため）。GET が 1 回増える。
  - 受注: 数の取り直しが失敗した時、今は数を消して 0 を出す（S :178 の `setGroupCounts(null)`）。直した後は前の数を出したまま（TanStack Query は失敗しても data を残す）。初めから取れない時は今と同じく 0 を出す。
  - ロール: 別のロールを選んで、そのロールの権限をまだ読めていない間、今は前のロールのチェックが残って押せる（S :141-150 は読み終わるまで前の値を置いたまま）。直した後は、そのロールの写しが無い間はチェックを全部外した形で押せなくする（useSeededForm の ready が false の間。新しい `canTogglePerms`）。1 度読んだロールは写しからすぐ出る。Q2 で確かめる。
  - ロール: 選んでいるロールを消した時、今は残りの先頭のロールを選ぶ（S :298）。直した後は、選んだロールが一覧に無ければ先頭のロールを出す（selectedRoleId を一覧から求める）ので同じ。
  - スタッフの編集: 読めなかった時、今は空のフォームが出て保存できるので、押すと空の値で本物のスタッフを上書きしてしまう（S :95-119 の catch は setForm しない・:154 は loading だけを見る）。直した後は、スタッフを読めていない間（useSeededForm の ready が false）はフォームを出さず、誤りの文だけを出す。Q2 で確かめる。
  - スタッフの編集: 2 回目に開いた時は前に読んだ値がすぐ出て、取り直した値が来たら（人がまだ直していなければ）作り直す（useSeededForm）。
- V3e-7 権限の判定（ロールの `canEditPerms`。S :183）は変えない。ロールの編集・削除のボタン（S :367-374）と保存のボタン（S :378）はそのまま canEditPerms を見る。押せなくするのはチェックの 3 種（S :404・:413・:425）と、その 3 つのトグルの関数（S :187・:196・:208）だけ。
- V3e-8 取れなかった時の文は 1 か所にまとめる: チャネルは今の `loadError`（S :403-405）の位置、ロール・スタッフ・スタッフの編集・受注は今の error の位置（shownError）。2 つ以上の path を読む画面は先に誤った方の文を出す。受注の会社の一覧は今と同じく取れなかった時に文を出さず空の一覧にする（S :188-190）。受注の発送と仕入は今と同じく取れなかった時（404 を含む）は null にする（S :209-211・:234-236）。
- V3e-9 写しがある状態で裏の取り直しが失敗した時は、前の中身を出したまま誤りの文を出す（段 3 の 1〜4 回目と同じ）。
- V3e-10 今ある画面の試験のうち、5 画面を描く試験は 4 本（設計担当が S で `grep -rln "StaffPage\|StaffEditPage\|ChannelsPage\|RolesPage\|OrdersPage" frontend/src --include="*.test.tsx"` で確かめた）。OrderLeadButtonMigration.test.tsx は既に写しを消している（S :9・:45）ので変えない。ほかの 3 本は `cleanup();` の後に写しを消していないので、`queryClient.clear();` を足す（§4-K）。
- V3e-11 api.ts の GET の送り直し（S frontend/src/lib/api.ts）は変えない。
- V3e-12 受入（§5 B5）は、9 行すべてで K1 ≤0.1 秒・K2 ≤2 秒・403 と 5xx が 0 件。K5 は段 3 の 1 回目の Q2・Q3（Bot 編集と useSeededForm の試験）と、写しの名前に利用者が入る作りで確かめる（本番で 2 人のログインは使わない）。

## 1. 触るファイル（変更前→変更後）
| # | ファイル | 変更前 | 変更後 |
|---|---|---|---|
| 1 | frontend/src/pages/channels/ChannelsPage.tsx | useState と useEffect で読む（S :93-95・:171-186） | useApiQuery（§4-A） |
| 2 | frontend/src/pages/roles/RolesPage.tsx | 同上（S :106-108・:112-116・:125-150） | useApiQuery＋useSeededForm（§4-B） |
| 3 | frontend/src/pages/staff/StaffPage.tsx | 同上（S :114-115・:124・:128-143） | useApiQuery（§4-C） |
| 4 | frontend/src/pages/staff/StaffEditPage.tsx | 同上（S :90-93・:95-119） | useApiQuery＋useSeededForm（§4-D） |
| 5 | frontend/src/pages/orders/useOrdersState.ts | 同上（S :101-103・:119・:124・:128・:157-247） | useApiQuery＋useApiQueries（§4-E） |
| 6 | frontend/src/pages/orders/OrdersPage.tsx | setShippings・setPurchases を使う（S :41・:43・:150・:161） | writeShipping・writePurchase と回る印（§4-F） |
| 7 | frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx | cleanup の後に写しを消さない | cleanup の後に queryClient.clear()（§4-K） |
| 8 | frontend/src/components/RoleKnowledgeButtonMigration.test.tsx | 同上 | 同上（§4-K） |
| 9 | frontend/src/components/StaffFormButtonMigration.test.tsx | 同上 | 同上（§4-K） |
| 10 | frontend/src/lib/query/batch3ePages.test.tsx | 無い | 新しく作る。Q1・Q2（§4-L 全文） |
| 11 | docs/handoff/line-like-speed/batch3e-card.md | 無い | このカード（設計担当が書いた。実装役は触らない） |
| 12 | docs/handoff/line-like-speed/design.md | §3-4-17-a まで | §3-4-18 にこのカードの場所を書き足し済み（設計担当。実装役は触らない） |
| 13 | .claude-pipeline/active-work.d/release-line-like-speed-batch3e.md | 無い | 作業の札（設計担当。実装役は触らない） |

## 2. 触らない範囲
- backend/・migrations/・.github/workflows/・scripts/・tests/prod-check/・frontend/viewer/ は触らない（design §3-3）。
- frontend/src/lib/api.ts・frontend/src/contexts/・frontend/src/lib/auth/・frontend/src/lib/query/apiQuery.ts・frontend/src/lib/query/useSeededForm.ts・frontend/src/lib/query/QueryAuthSync.tsx・frontend/src/App.tsx・frontend/src/hooks/・frontend/src/mocks/ は触らない。
- frontend/src/components/（PageLayout・Spinner・LoadingBlock・ShippingDetailPanel・PurchaseDetailPanel・CompanyContactSelector・CheckboxControl を含む。試験のファイルは §4-K の行だけ）・CSS・ja.json・en.json は触らない。新しい言葉・色・寸法を足さない。
- frontend/src/pages/orders/ の OrdersTable.tsx・OrdersFormModal.tsx・OrdersFilterBar.tsx・orders.types.ts は触らない。
- 5 画面の中の、書き方（post・put・patch・delete の path と中身）・チャネルの Discord の設定（S ChannelsPage.tsx:120-131・:189-260）・Meta の接続（S :262-300）・表の列・ボタン・モーダル・フォームの欄・受注の検索の待ち（S useOrdersState.ts:130-140）・スタッフの編集の保存（S StaffEditPage.tsx:123-149）は変えない。変えるのは §4 に書いた行だけ。
- QueryClient を作らない（試験の中でも作らない）。staleTime を設定しない。写しをブラウザの保存に書かない。
- ほかの画面は変えない。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) 最新の origin/main で `git diff --stat 0f68fbc78 origin/main -- frontend/src` が、この版を書いた時の 5 ファイル（冒頭の「根拠の写し」）だけか。§1 #1〜#9 のどれかが変わっていたら停止して報告する。ほかのファイルだけなら、変わったファイルの名前と行数を報告に書いて続ける。
- (b) `cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json` が `"5.104.4"` の 1 行。違えば停止して報告する。
- (c) §4 の「変更前」の文が、書かれた行にそのままあること。1 か所でも無い・2 か所以上ある時は、直さずに停止して BLOCKED: で `grep -n` の出力を報告する。
- (d) 手順 2 で、変える前の 6 ファイル（§1 #1〜#6）の lint の警告の数を数えておく。変えた後は、その数より増えないこと（0 になってもよい）。増えたら直す。直せない時は停止する。
- (e) Q1・Q2・今ある画面の試験のどれかが落ちたら、試験を書き換えて通さない（§4-K の行を除く）。画面の §4 の写し違いを探し、写し違いが無ければ停止して NEEDS_DECISION: で生の出力を返す。
- (f) 今ある試験の数え方との関係（変わらない見込み。違った時は試験を変えずに停止して NEEDS_DECISION: で生の出力を返す）:
  - OrderLeadButtonMigration.test.tsx は作成の後に `/orders?` と `/orders/group-counts` の get が 1 回ずつ増えることを数える（S :61-62）。§4-E の `invalidate(["orders"])` は画面に出ている 2 つを 1 回ずつ取り直す。
  - StaffFormButtonMigration.test.tsx は保存の後に `/staff` の get が 1 回増えることを数え（S :152・:157）、`/staff/me` の数も数える。§4-C の loadAll は `/staff` と `/roles` を 1 回ずつ取り直す。`/staff/me` は写しを使わない（S frontend/src/contexts/UiPrefsContext.tsx の api.get）ので数は変わらない。
  - RoleKnowledgeButtonMigration.test.tsx は afterEach で fetch が呼ばれていないことを確かめる（S :35）。§4-B は api.get だけで読むので変わらない。
- (g) api の import はどのファイルでも残す（書くのに使う: ChannelsPage.tsx の post・delete、RolesPage.tsx の put・patch・post・delete と §4-B の cache.fetch の中の get、StaffPage.tsx の post・patch・delete、StaffEditPage.tsx の patch、useOrdersState.ts の patch・post・delete）。消すのは useOrdersState.ts の ApiError だけ（S :210・:235 の 2 か所だけで使い、§4-E で両方消える）。ChannelsPage.tsx の ApiError は §4-A の誤りの文で使うので残す。

## 4-A. #1 frontend/src/pages/channels/ChannelsPage.tsx
- A1 S :21 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`
- A2 S :25 `import { ApiError, api } from "../../lib/api";` の次に `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` を足す。S :22 の useEffect・useRef は残す（S :121・:189・:197 で使う）。
- A3 S :93-95（channels・loading・loadError の useState の 3 行）を次の 3 行に置き換える（:96 の connecting は残す）:
```ts
  const channelsQ = useApiQuery<ChannelsResponse>("/meta/channels");
  const channels = channelsQ.data?.channels || [];
  const loadError = channelsQ.error ? (channelsQ.error instanceof ApiError ? channelsQ.error.message : (channelsQ.error instanceof Error ? channelsQ.error.message : t("channels.loadErrorFallback"))) : "";
```
- A4 S :171-186（loadChannels・空行・eslint-disable の行・useEffect）を次の 2 行に置き換える（:170 の説明の行と :187 の空行は残す）:
```ts
  const invalidate = useInvalidateApi();
  const loadChannels = () => invalidate(["meta", "channels"]);
```
- A5 S :337 `      subtitleKey="channels.subtitle"` の次の行に足す:
  `      headerLeft={channelsQ.isFetching && !channelsQ.isPending ? <Spinner size="sm" /> : undefined}`
- A6 S :421 `      {loading ? (` → `      {channelsQ.isPending ? (`
- :296 の `await loadChannels();`（接続を外した後）・:403-412 の誤りの文と送り直しのボタン（:410 `onClick={loadChannels}`）・:388・:437・:559 の `<Button loading=`・:8 の説明の行は変えない。`invalidate(["meta", "channels"])` は `/meta/channels` だけに当たる（Meta の接続の書く path は写しを使っていない）。

## 4-B. #2 frontend/src/pages/roles/RolesPage.tsx
- B1 S :16 `import { useEffect, useMemo, useState, FormEvent } from "react";` → `import { useMemo, useState, FormEvent } from "react";`
- B2 S :19 `import { api } from "../../lib/api";` の次に 2 行足す:
```ts
import { useApiCache, useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { useSeededForm } from "../../lib/query/useSeededForm";
```
- B3 S :101 `export default function RolesPage() {` の前に次の 5 行を足す（:100 の空行の後。最後の空行を含む）:
```ts
const NO_ROLES: Role[] = [];
const NO_PERMISSIONS: Permission[] = [];
const EMPTY_IDS: Set<number> = new Set();
const toIds = (perms: Permission[]): Set<number> => new Set(perms.map((p) => p.id));

```
  （空の一覧を毎回作り直さないため。S :153-162 の grouped の useMemo が permissions を見ている。）
- B4 S :106-108（roles・permissions・loading の useState の 3 行）を次の 4 行に置き換える（:109 の error は残す）:
```ts
  const rolesQ = useApiQuery<Role[]>("/roles");
  const permsQ = useApiQuery<Permission[]>("/permissions");
  const roles = rolesQ.data ?? NO_ROLES;
  const permissions = permsQ.data ?? NO_PERMISSIONS;
```
- B5 S :112 `  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);` を次の 3 行に置き換える（:111 の説明の行は残す）:
```ts
  const [pickedRoleId, setPickedRoleId] = useState<number | null>(null);
  // 選んだロールが一覧に無い（まだ選んでいない・消した）時は先頭のロール
  const selectedRoleId = roles.some((r) => r.id === pickedRoleId) ? pickedRoleId : (roles[0]?.id ?? null);
```
- B6 S :113-116（元の権限の説明の行と useState・編集中の説明の行と useState の 4 行）を次に置き換える（:117 の savingPerms は残す）:
```ts
  // そのロールの権限（元の状態は写し・編集中はフォーム。写しが無い間は全部外して押せない）
  const rolePermsQ = useApiQuery<Permission[]>(`/roles/${selectedRoleId}/permissions`, { enabled: selectedRoleId !== null });
  const originalPermIds = useMemo(() => (rolePermsQ.data ? toIds(rolePermsQ.data) : EMPTY_IDS), [rolePermsQ.data]);
  const { form: editedPermIds, setForm: setEditedPermIds, ready: permsReady } = useSeededForm(
    `roles/${selectedRoleId}/permissions`, rolePermsQ.data, toIds, EMPTY_IDS,
  );
  const readError = rolesQ.error ?? permsQ.error ?? rolePermsQ.error;
  const shownError = error || (readError ? (readError instanceof Error ? readError.message : t("common.fetchError")) : "");
  const invalidate = useInvalidateApi();
  const cache = useApiCache();
```
- B7 S :125-151（初回ロードの説明の行と useEffect・空行・選択ロール変更時の説明の行と useEffect・空行）を消す（:152 の grouped の説明の行から残す）。
- B8 S :183 `  const canEditPerms = hasPermission("roles.update") && !isSystemRole;` の次の行に足す:
  `  const canTogglePerms = canEditPerms && permsReady;`
- B9 S :187・:196・:208 の `    if (!canEditPerms) return;`（3 か所）→ `    if (!canTogglePerms) return;`
- B10 S :404・:413・:425 の `disabled={!canEditPerms}`（3 か所。字下げは各行のまま）→ `disabled={!canTogglePerms}`。S :367 と :378 の canEditPerms は変えない（V3e-7）。
- B11 S :236 `      setOriginalPermIds(new Set(editedPermIds));` → `      await invalidate(["roles", String(selectedRoleId), "permissions"]);`
- B12 S :250 `    setSelectedRoleId(id);` → `    setPickedRoleId(id);`
- B13 S :283-284 の 2 行
```ts
      const latest = await api.get<Role[]>("/roles");
      setRoles(latest);
```
  を次の 1 行に置き換える:
```ts
      await cache.fetch("/roles", () => api.get<Role[]>("/roles"));
```
- B14 S :296-298 の 3 行（latest の取得・setRoles・消したロールを選んでいた時の setSelectedRoleId）を次の 1 行に置き換える:
```ts
      await cache.fetch("/roles", () => api.get<Role[]>("/roles"));
```
- B15 S :304 `  if (loading) return <div className="page"><LoadingBlock /></div>;` → `  if (rolesQ.isPending || permsQ.isPending) return <div className="page"><LoadingBlock /></div>;`
- B16 S :308 `      {error && <div className="error-message">{error}</div>}` → `      {shownError && <div className="error-message">{shownError}</div>}`
- :245 の cancelEdits（`setEditedPermIds(new Set(originalPermIds))`）・:166-170 の dirty・:229-242 の保存の put・:249 の未保存の確かめ・:331 の選んだロールの印（selectedRoleId）は変えない。
- 動き: 保存できた後、そのロールの写しを古い印にして取り直し、取り直しが終わるまで保存中の印（savingPerms）が続く。取り直した写しで元の状態（originalPermIds）が保存した値になり、編集中の値は人が直した後なので作り直さない（useSeededForm）。中身が同じなので dirty は false になる（今と同じ）。

## 4-C. #3 frontend/src/pages/staff/StaffPage.tsx
- C1 S :11 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`。S :12 `import { useEffect, useState, FormEvent } from "react";` → `import { useState, FormEvent } from "react";`
- C2 S :17 `import { api } from "../../lib/api";` の次に `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` を足す。
- C3 S :114-115（staff・roles の useState の 2 行）を次の 4 行に置き換える:
```ts
  const staffQ = useApiQuery<Staff[]>("/staff");
  const rolesQ = useApiQuery<StaffRole[]>("/roles");
  const staff = staffQ.data ?? [];
  const roles = rolesQ.data ?? [];
```
- C4 S :124 `  const [loading, setLoading] = useState(true);` を次の 4 行に置き換える（:123 の error・:125 の submitting は残す）:
```ts
  const readError = staffQ.error ?? rolesQ.error;
  const shownError = error || (readError ? (readError instanceof Error ? readError.message : t("common.fetchError")) : "");
  const refetching = (staffQ.isFetching && !staffQ.isPending) || (rolesQ.isFetching && !rolesQ.isPending);
  const invalidate = useInvalidateApi();
```
- C5 S :128-143（loadAll・eslint-disable の行・useEffect）を次に置き換える（:144 の空行は残す）:
```ts
  const loadAll = () => {
    void invalidate(["staff"]);
    void invalidate(["roles"]);
  };
```
- C6 S :217 `      subtitleKey="staff.subtitle"` の次の行に足す:
  `      headerLeft={refetching ? <Spinner size="sm" /> : undefined}`
- C7 S :219 `      {error && <div className="error-message">{error}</div>}` → `      {shownError && <div className="error-message">{shownError}</div>}`
- C8 S :327 `      {loading ? (` → `      {staffQ.isPending || rolesQ.isPending ? (`
- :174・:196・:208 の `loadAll();`・:300 の `<Button loading={submitting}`・表の列（:334 の名前の列を含む）・作成のモーダル・編集のドロワーは変えない。
- `invalidate(["roles"])` は `/roles` から始まる写し（ロールの画面の `/roles/<id>/permissions` を含む）を古い印にするが、取り直すのは画面に出ている物だけ。

## 4-D. #4 frontend/src/pages/staff/StaffEditPage.tsx
- D1 S :11 `import { useEffect, useState, type FormEvent } from "react";` → `import { useState, type FormEvent } from "react";`
- D2 S :17 `import { api } from "../../lib/api";` の次に 2 行足す:
```ts
import { useApiQuery } from "../../lib/query/apiQuery";
import { useSeededForm } from "../../lib/query/useSeededForm";
```
- D3 S :83 `};`（emptyForm の閉じ）の次に足す（空行を挟む。中身は S :102-114 の setForm に渡している形と同じ）:
```ts

const toForm = (staff: Staff): FormState => ({
  surname_jp: staff.surname_jp,
  given_name_jp: staff.given_name_jp,
  surname_kana: staff.surname_kana ?? "",
  given_name_kana: staff.given_name_kana ?? "",
  surname_en: staff.surname_en ?? "",
  given_name_en: staff.given_name_en ?? "",
  primary_email: staff.primary_email,
  discord_user_id: staff.discord_user_id ?? "",
  role_id: String(staff.role_id),
  status: staff.status,
  ui_preferences: staff.ui_preferences || { ...emptyPrefs },
});
```
- D4 S :90-93（form・roles・error・loading の useState の 4 行）を次に置き換える:
```ts
  const staffQ = useApiQuery<Staff>(`/staff/${id}`, { enabled: !!id });
  const rolesQ = useApiQuery<Role[]>("/roles");
  const roles = rolesQ.data ?? [];
  const { form, setForm, ready } = useSeededForm(`staff/${id}`, staffQ.data, toForm, emptyForm);
  const [error, setError] = useState("");
  const readError = staffQ.error ?? rolesQ.error;
  const shownError = error || (readError ? (readError instanceof Error ? readError.message : t("common.fetchError")) : "");
```
- D5 S :95-120（useEffect と次の空行）を消す（:121 の toNull から残す）。
- D6 S :153 `      {error && <div className="error-message">{error}</div>}` → `      {shownError && <div className="error-message">{shownError}</div>}`
- D7 S :154-156 の 3 行
```tsx
      {loading ? (
        <LoadingBlock />
      ) : (
```
  を次の 3 行に置き換える:
```tsx
      {staffQ.isPending || rolesQ.isPending ? (
        <LoadingBlock />
      ) : !ready ? null : (
```
- :123-149 の handleSubmit（setForm・setError・api.patch・navigate）・:157 以降のフォームの欄は変えない。id が無い時は今と同じく読み込み中の印のまま（enabled が false の間 isPending）。
- ロールだけ読めなかった時は、今は空のフォームが出る（S の Promise.all がまとめて失敗する）。直した後はスタッフの値が入ったフォームと誤りの文が出て、ロールの選択肢は空になる（role_id はスタッフの値のまま送られる）。

## 4-E. #5 frontend/src/pages/orders/useOrdersState.ts
- E1 S :8 `import { api, ApiError } from "../../lib/api";` → `import { api } from "../../lib/api";` とし、その次の行に `import { useApiCache, useApiQueries, useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` を足す（§3(g)）。S :6 の import は変えない（useEffect・useRef は S :131-140 の検索の待ちで、useMemo は S :142-155 で使う）。
- E2 S :101-103（orders・groupCounts・companies の useState の 3 行）を消す（:104 の statusFilter は残す）。
- E3 S :119 `  const [loading, setLoading] = useState(true);` を消す（:118 の error は残す）。
- E4 S :124 `  const [shippings, setShippings] = useState<Record<number, ShippingDetailDto | null>>({});` を消す（:123 の shippingTarget は残す）。
- E5 S :128 `  const [purchases, setPurchases] = useState<Record<number, PurchaseDetailDto | null>>({});` を消す（:127 の purchaseTarget は残す）。
- E6 S :157-247（loadOrders・loadGroupCounts・loadCompanies・3 つの useEffect・発送と仕入の 2 つの useEffect）を次に置き換える（:248 の空行は残す）:
```ts
  const ordersQ = useApiQuery<OrderListItem[]>(`/orders${queryString ? `?${queryString}` : ""}`);
  const orders = ordersQ.data ?? [];
  const groupCountsQ = useApiQuery<GroupCountsResponse>(
    `/orders/group-counts${groupCountsQueryString ? `?${groupCountsQueryString}` : ""}`,
    { keepPrevious: true },
  );
  const groupCounts = groupCountsQ.data ?? null;
  const companiesQ = useApiQuery<CompanyMini[]>("/companies?per_page=100");
  const companies = useMemo<CompanyMini[]>(
    () => (companiesQ.data ?? []).map((c) => ({ id: c.id, company_code: c.company_code, name: c.name })),
    [companiesQ.data],
  );
  const loading = ordersQ.isPending;
  const refetching =
    (ordersQ.isFetching && !ordersQ.isPending) ||
    (groupCountsQ.isFetching && !groupCountsQ.isPending) ||
    (companiesQ.isFetching && !companiesQ.isPending);
  const shownError = error || (ordersQ.error ? (ordersQ.error instanceof Error ? ordersQ.error.message : t("common.fetchError")) : "");
  const invalidate = useInvalidateApi();
  const cache = useApiCache();

  const loadOrders = () => {
    void invalidate(["orders"]);
  };

  // ADR-021 Sprint 3・4: 発送と仕入を 1 件ずつ写しで取る（取れない・404 は null）
  const shippingQs = useApiQueries<ShippingDetailDto>(orders.map((o) => `/orders/${o.id}/shipping`));
  const purchaseQs = useApiQueries<PurchaseDetailDto>(orders.map((o) => `/orders/${o.id}/purchase`));
  const shippings: Record<number, ShippingDetailDto | null> = Object.fromEntries(
    orders.map((o, i) => [o.id, shippingQs[i]?.data ?? null]),
  );
  const purchases: Record<number, PurchaseDetailDto | null> = Object.fromEntries(
    orders.map((o, i) => [o.id, purchaseQs[i]?.data ?? null]),
  );
  const writeShipping = (saved: ShippingDetailDto) => cache.write(`/orders/${saved.order_id}/shipping`, saved);
  const writePurchase = (saved: PurchaseDetailDto) => cache.write(`/orders/${saved.order_id}/purchase`, saved);
```
- E7 S :283 `      loadGroupCounts();`（handleSubmit の中）と S :310 `      loadGroupCounts();`（performDelete の中）を消す。:282・:309 の `loadOrders();` は残す（数も同じ頭の写しなので一緒に取り直す）。:327 の setPaidOrder の `loadOrders();` も残す。
- E8 返す物（S :335-357）のうち次の 4 行を変える:
  - S :347 `    error, loading,` → `    error: shownError, loading, refetching,`
  - S :350 `    shippings, setShippings,` → `    shippings, writeShipping,`
  - S :352 `    purchases, setPurchases,` → `    purchases, writePurchase,`
  - S :354 `    loadOrders, loadGroupCounts,` → `    loadOrders,`
- :255-287 の handleSubmit・:289-301 の handleEdit・:303-314 の performDelete・:316-320 の companyDisplay・:322-331 の setPaidOrder・:333 の toggleSortOrder は、E7 の 2 行のほかは変えない。setError は handleSubmit・performDelete・setPaidOrder で使うので error の useState は残す。
- useOrdersState を使うのは OrdersPage.tsx と、OrdersTable.tsx の fmtCurrency・orderPhase の import だけ（設計担当が S で `grep -rn "useOrdersState" frontend/src` で確かめた）。返す物から消す setShippings・setPurchases・loadGroupCounts を使うのは OrdersPage.tsx の :41・:43・:150・:161 だけ（§4-F で直す）。
- ShippingDetailDto と PurchaseDetailDto は order_id を持つ（S frontend/src/components/ShippingDetailPanel.tsx・PurchaseDetailPanel.tsx の型。今の S OrdersPage.tsx:150・:161 も saved.order_id を使う）。

## 4-F. #6 frontend/src/pages/orders/OrdersPage.tsx
- F1 S :21 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`
- F2 S :38 `    selectorError, error, loading,` → `    selectorError, error, loading, refetching,`
- F3 S :41 `    shippings, setShippings,` → `    shippings, writeShipping,`
- F4 S :43 `    purchases, setPurchases,` → `    purchases, writePurchase,`
- F5 S :64 `    <PageLayout navKey="nav.orders" subtitleKey="orders.subtitle" noScroll>` → `    <PageLayout navKey="nav.orders" subtitleKey="orders.subtitle" headerLeft={refetching ? <Spinner size="sm" /> : undefined} noScroll>`
- F6 S :150 `            setShippings((prev) => ({ ...prev, [saved.order_id]: saved }));` → `            writeShipping(saved);`
- F7 S :161 `            setPurchases((prev) => ({ ...prev, [saved.order_id]: saved }));` → `            writePurchase(saved);`
- :109 の誤りの文・:111-124 の読み込み中の印と表・:128-142 のフォーム・:166-180 の確かめのモーダルは変えない（error は E8 で shownError を返す）。

## 4-K. #7〜#9 今ある試験の写しを消す（ほかの行は変えない）
- K1 frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx: S :7 `import en from '../locales/en.json';` の次に `import { queryClient } from '../lib/query/apiQuery';` を足す。S :29 `afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });` → `afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });`
- K2 frontend/src/components/RoleKnowledgeButtonMigration.test.tsx: S :7 `import en from '../locales/en.json';` の次に `import { queryClient } from '../lib/query/apiQuery';` を足す。S :35 `afterEach(() => { cleanup(); expect(fetch).not.toHaveBeenCalled(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });` → `afterEach(() => { cleanup(); queryClient.clear(); expect(fetch).not.toHaveBeenCalled(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });`。S :94 `    cleanup(); roleColor = existingColor; await renderRoles();` → `    cleanup(); queryClient.clear(); roleColor = existingColor; await renderRoles();`（試験の途中で描き直す所。前の写しが残ると新しい色のロールが出ないため）
- K3 frontend/src/components/StaffFormButtonMigration.test.tsx: S :10 `import en from '../locales/en.json';` の次に `import { queryClient } from '../lib/query/apiQuery';` を足す。S :133-134 の afterEach の中の `  cleanup();` の次の行に `  queryClient.clear();` を足す。
- 理由: 画面が同じ 1 個の写しの置き場を使うので、前の試験の写しが次の試験に残らないようにする（段 3 の 1〜4 回目の §4-K と同じ）。
- 実装役は K1〜K3 の前に `grep -n "afterEach\|^import en\|cleanup(); roleColor" <ファイル>` で行を確かめる（§3(c)）。

## 4-L. #10 frontend/src/lib/query/batch3ePages.test.tsx（新しく作る・全文）
```tsx
/**
 * ADR-1054 段 3 の 5 回目: 本物の画面の試験。
 * Q1 戻った時に写しを先に出す（読み込み中の印を出さない）・一覧の画面は見出しの横に回る印・裏で取り直す。
 * Q2 ロールの権限を読めていない間はチェックを押せない。スタッフを読めなかった時はフォームを出さない（空の値で上書きしない）。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import type { ComponentType } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ChannelsPage from "../../pages/channels/ChannelsPage";
import OrdersPage from "../../pages/orders/OrdersPage";
import RolesPage from "../../pages/roles/RolesPage";
import StaffEditPage from "../../pages/staff/StaffEditPage";
import StaffPage from "../../pages/staff/StaffPage";
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
  // api.ts が i18n.ts を読み、i18n.ts が initReactI18next を使う（同じ書き方: src/lib/query/batch3dPages.test.tsx）
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

// 中身は画面の型（ChannelsPage.tsx:33-49・RolesPage.tsx:33-52・StaffPage.tsx:43-63・StaffEditPage.tsx:32-50・
// orders.types.ts:5-24・:32-35）の欄
const channel = {
  page_id: "p1", page_name: "Fixture Page", instagram_business_account_id: null, instagram_username: null,
  is_active: true, connected_at: null, page_token_expires_at: null, connected_by_staff_id: null,
  connected_by_staff_name: null, granted_scopes: null, requires_reauth: false,
};
const role = { id: 1, name: "Fixture Role", color: null, priority: 500, is_system: false, description: null, created_at: "", updated_at: "" };
const permission = { id: 10, key: "customers.view", resource: "customers", action: "view", description: "Fixture Permission", category: "customers" };
const staff = {
  id: 7, tenant_id: 1, user_id: null, staff_code: "ST-FIX", surname_jp: "Fixture", given_name_jp: "Person",
  surname_kana: null, given_name_kana: null, surname_en: "Fixture", given_name_en: "Person",
  primary_email: "fixture@example.invalid", discord_user_id: null, role_id: 1, role_name: "Fixture Role",
  status: "active", emails: [], ui_preferences: null, created_at: "", updated_at: "",
};
const order = {
  id: 1, company_id: 1, contact_id: null, invoice_id: null, order_number: "ORD-FIX", total_amount: null,
  currency: "JPY", status: "awaiting_payment", paid_at: null, notes: null,
  created_at: "2026-11-01T00:00:00Z", updated_at: "2026-11-01T00:00:00Z",
  company_name: "Fixture Company", contact_display_name: null, shipping_city: null, shipping_country_code: null,
};

const fixtures: Record<string, unknown> = {
  "/meta/channels": { channels: [channel] },
  "/admin/discord-config": { guild_id: null, connected_at: null, connected_by_staff_name: null },
  "/roles": [role],
  "/permissions": [permission],
  "/roles/1/permissions": [permission],
  "/staff": [staff],
  "/staff/7": staff,
  "/orders?sort_by=updated_at&sort_order=desc": [order],
  "/orders/group-counts": { counts: {}, total: 1 },
  "/companies?per_page=100": [],
};
// ほかの path（受注の発送と仕入など）は取れない扱い（画面は null にする）
const answer = (path: string) => {
  if (!(path in fixtures)) throw new Error(`Unexpected GET ${path}`);
  return fixtures[path] as never;
};

type Case = {
  name: string; Page: ComponentType; route: string; at: string;
  path: string; text: string; value: boolean; spinner: boolean;
};
const cases: Case[] = [
  { name: "channels", Page: ChannelsPage, route: "/channels", at: "/channels", path: "/meta/channels", text: "Fixture Page", value: false, spinner: true },
  { name: "roles", Page: RolesPage, route: "/roles", at: "/roles", path: "/roles", text: "Fixture Role", value: false, spinner: false },
  { name: "staff", Page: StaffPage, route: "/staff", at: "/staff", path: "/staff", text: "Fixture Person", value: false, spinner: true },
  { name: "staff edit", Page: StaffEditPage, route: "/staff/:id/edit", at: "/staff/7/edit", path: "/staff/7", text: "Fixture", value: true, spinner: false },
  { name: "orders", Page: OrdersPage, route: "/orders", at: "/orders", path: "/orders?sort_by=updated_at&sort_order=desc", text: "ORD-FIX", value: false, spinner: true },
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
});

describe("edits wait until the record is read (Q2)", () => {
  const permissionBox = () =>
    screen.getByText("Fixture Permission").closest("label")!.querySelector("input") as HTMLInputElement;

  it("keeps the role permission boxes disabled until that role's permissions are read", async () => {
    let release: (value: unknown) => void = () => {};
    const held = new Promise((resolve) => { release = resolve; });
    vi.spyOn(api, "get").mockImplementation(async (path: string) =>
      (path === "/roles/1/permissions" ? held : answer(path)) as never,
    );
    render(<Tree c={{ Page: RolesPage, route: "/roles", at: "/roles" }} />);
    await screen.findByText("Fixture Permission");
    expect(permissionBox().disabled).toBe(true);

    release([permission]);
    await waitFor(() => expect(permissionBox().disabled).toBe(false));
    expect(permissionBox().checked).toBe(true);
  });

  it("does not show the staff form when the staff could not be read", async () => {
    vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === "/staff/7") throw new Error("Fixture read failure");
      return answer(path);
    });
    const { container } = render(<Tree c={{ Page: StaffEditPage, route: "/staff/:id/edit", at: "/staff/7/edit" }} />);
    await screen.findByText("Fixture read failure");
    expect(container.querySelector("form")).toBeNull();
  });
});
```
- LoadingBlock の見分けは `.sa-loading-block`、回る印の見分けは `.page-layout-title-row .sa-spinner`（段 3 の 1〜4 回目のカード §4-L と同じ）。ロールとスタッフの編集は回る印を出さない（V3e-3）。
- 「Fixture Page」はチャネルの表のページ名（S ChannelsPage.tsx:471）、「Fixture Role」はロールの左の一覧（S RolesPage.tsx:331 の付近）、「Fixture Person」はスタッフの表の名前の列（S StaffPage.tsx:334 の `${s.surname_jp} ${s.given_name_jp}`）、「Fixture」はスタッフの編集の姓の欄（S StaffEditPage.tsx:159）、「ORD-FIX」は受注の表の受注番号の列（S frontend/src/pages/orders/OrdersTable.tsx:73 の列の定義）に出る。
- 「Fixture Permission」はロールの権限のチェックの説明（S RolesPage.tsx:429。チェックは同じ label の中の input: S :422-427、CheckboxControl は disabled と checked を input にそのまま渡す: S frontend/src/components/CheckboxControl.tsx:5・:39）。S の試験には jest-dom が入っていないため、押せるかどうかは `input.disabled` を直に見る（段 3 の 4 回目の Q2 と同じ）。
- スタッフの画面は UiPrefsProvider の外で描くので、useUiPrefs は既定の値を返し `/staff/me` を取りに行かない（S frontend/src/contexts/UiPrefsContext.tsx:154-165）。
- 受注の画面の発送と仕入（`/orders/1/shipping`・`/orders/1/purchase`）は fixtures に無いので取れない扱いになり、画面は null にする（今の 404 と同じ）。会社の一覧は空。チャネルの画面は権限があるので Discord の設定も読む（fixtures にある）。

## 4-M. 実装役の手順（1 手順 1 命令。<W> は手順1 で作られた作業場所の絶対パス）
手順1. クラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）どおり、作業場所を作り、push 済みの枝の先頭に合わせる（設計担当が §1 #11〜#13 を push 済み）。
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/line-like-speed-batch3e
  （出力に出た作業場所の絶対パスを <W> として報告に書く。）
  cd <W> && git fetch origin release/line-like-speed-batch3e
  cd <W> && git switch -C release/line-like-speed-batch3e origin/release/line-like-speed-batch3e
  cd <W> && git rev-parse HEAD origin/release/line-like-speed-batch3e
  （2 行が同じことを確かめる。違えば停止して BLOCKED: で報告する。main は取り込まない。reset・rebase・force・merge・pull は使わない）
  cd <W> && ./scripts/dev/executor-preflight.sh > /tmp/b3e-preflight.txt 2>&1
  cd <W> && grep -n "FAIL" /tmp/b3e-preflight.txt | head -20
  cd <W> && grep -n "origin/main は存在" /tmp/b3e-preflight.txt | head -3
  （FAIL の行が次の 3 つのうちのどれかだけなら続ける: `GitHub API に到達不可` の 1 件・`gh auth switch --hostname github.com --user shingo-cc` の失敗の 1 件・その結果の `PREFLIGHT FAIL` の行。理由は段 3 の 1 回目のカード §4-M 手順1 と同じ。続ける時は `[OK]   origin/main は存在` の行があることを 2 つ目の grep で確かめ、無ければ停止する。ほかの FAIL が 1 件でもあれば停止し、BLOCKED: で grep の出力を報告する。）
  cd <W> && git fetch origin main
  cd <W> && git diff --stat 0f68fbc78c005ebbd7f39ab923ba3ad9eabd212b origin/main -- frontend/src | tail -12
  （§3(a) の確かめ。）
手順2. 依存を入れ、§3(b)・§3(g) を確かめ、変える前の lint の警告を数える。
  cd <W>/frontend && npm ci > /tmp/b3e-ci.txt 2>&1
  cd <W> && tail -5 /tmp/b3e-ci.txt
  cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json
  cd <W>/frontend && grep -n "ApiError" src/pages/orders/useOrdersState.ts
  （§3(g) の確かめ。S :8・:210・:235 の 3 行であること。）
  cd <W>/frontend && npx eslint src/pages/channels/ChannelsPage.tsx src/pages/roles/RolesPage.tsx src/pages/staff/StaffPage.tsx src/pages/staff/StaffEditPage.tsx src/pages/orders/useOrdersState.ts src/pages/orders/OrdersPage.tsx > /tmp/b3e-lint-before.txt 2>&1
  cd <W> && tail -5 /tmp/b3e-lint-before.txt
手順3. §4-L の全文で #10 を作り、§4-A〜§4-K のとおり #1〜#9 を直す。各ファイルを直す前に、§4 の「変更前」の文を `grep -n` で確かめる（§3(c)）。終わったら残りが無いことを確かめる。
  cd <W> && grep -nw "setChannels\|setLoadError\|setRoles\|setPermissions\|setSelectedRoleId\|setOriginalPermIds\|setStaff\|setLoading\|setShippings\|setPurchases" frontend/src/pages/channels/ChannelsPage.tsx frontend/src/pages/roles/RolesPage.tsx frontend/src/pages/staff/StaffPage.tsx frontend/src/pages/staff/StaffEditPage.tsx frontend/src/pages/orders/OrdersPage.tsx | head -20
  （0 行であること。出たら §4 の写し違いを直す。）
  cd <W> && grep -nw "setOrders\|setGroupCounts\|setCompanies\|setShippings\|setPurchases\|setLoading\|loadGroupCounts\|loadCompanies\|ApiError" frontend/src/pages/orders/useOrdersState.ts | head -20
  （0 行であること。）
  cd <W> && grep -nw "useEffect" frontend/src/pages/roles/RolesPage.tsx frontend/src/pages/staff/StaffPage.tsx frontend/src/pages/staff/StaffEditPage.tsx | head -10
  （0 行であること。ChannelsPage.tsx と useOrdersState.ts は useEffect を残す: §4-A2・§4-E1。）
  cd <W> && grep -c "api\." frontend/src/pages/channels/ChannelsPage.tsx frontend/src/pages/roles/RolesPage.tsx frontend/src/pages/staff/StaffPage.tsx frontend/src/pages/staff/StaffEditPage.tsx frontend/src/pages/orders/useOrdersState.ts
  （どのファイルも 1 以上であること。§3(g)。）
手順4. 型を作ってから試験を流す（新しい試験・直した今ある試験・全部の試験・型・lint）。作る型（frontend/src/api/generated/）は .gitignore で除かれるので commit に入らない。
  cd <W>/frontend && npm run generate:api-types > /tmp/b3e-gen.txt 2>&1
  cd <W> && tail -3 /tmp/b3e-gen.txt
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/lib/query > /tmp/b3e-unit.txt 2>&1
  cd <W> && tail -30 /tmp/b3e-unit.txt
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/components/PurchaseAdminEditorButtonMigration.test.tsx src/components/RoleKnowledgeButtonMigration.test.tsx src/components/StaffFormButtonMigration.test.tsx src/components/OrderLeadButtonMigration.test.tsx > /tmp/b3e-pages.txt 2>&1
  cd <W> && tail -30 /tmp/b3e-pages.txt
  cd <W>/frontend && npm run test:unit > /tmp/b3e-unit-all.txt 2>&1
  cd <W> && tail -15 /tmp/b3e-unit-all.txt
  cd <W>/frontend && npx tsc --noEmit -p . > /tmp/b3e-tsc.txt 2>&1
  cd <W> && tail -20 /tmp/b3e-tsc.txt
  cd <W>/frontend && npx eslint src/lib/query src/pages/channels/ChannelsPage.tsx src/pages/roles/RolesPage.tsx src/pages/staff/StaffPage.tsx src/pages/staff/StaffEditPage.tsx src/pages/orders/useOrdersState.ts src/pages/orders/OrdersPage.tsx > /tmp/b3e-lint.txt 2>&1
  cd <W> && tail -20 /tmp/b3e-lint.txt
  （lint の警告が手順2 の数より増えていないこと・誤りが 0 であること。§3(d)。）
手順5. 本番と同じ形で組み立てられるか確かめる。
  cd <W>/frontend && npm run build > /tmp/b3e-build.txt 2>&1
  cd <W> && tail -15 /tmp/b3e-build.txt
手順6. 変わったファイルが §1 の #1〜#10 だけか確かめ、画面の書く path と表・フォームの行が変わっていないことを見る。
  cd <W> && git status --short | head -30
  cd <W> && git diff -w --stat origin/release/line-like-speed-batch3e | tail -20
  cd <W> && git diff -w origin/release/line-like-speed-batch3e -- frontend/src/pages | head -700
手順7. commit する。
  cd <W> && git add frontend/src/pages/channels/ChannelsPage.tsx frontend/src/pages/roles/RolesPage.tsx frontend/src/pages/staff/StaffPage.tsx frontend/src/pages/staff/StaffEditPage.tsx frontend/src/pages/orders/useOrdersState.ts frontend/src/pages/orders/OrdersPage.tsx frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx frontend/src/components/RoleKnowledgeButtonMigration.test.tsx frontend/src/components/StaffFormButtonMigration.test.tsx frontend/src/lib/query/batch3ePages.test.tsx
  cd <W> && git commit -m "feat: 権限の要る5画面を写しを先に出して裏で取り直す形に（ADR-1054 段3の5回目）"
手順8. commit が在ることを確かめてから push する（--no-verify は使わない。push の前の検査が × なら直してから push。fast-forward でないと断られたら直さず BLOCKED:）。
  cd <W> && git log -3 --oneline
  cd <W> && git push -u origin release/line-like-speed-batch3e
手順9. 報告を返す。PR は作らない（設計担当が手元で作る）。報告の 1 つの発言は 600 文字以内にして、番号付きの発言に分ける。報告には手順ごとの tail の出力（生のまま）と、§3(a)〜(g) の結果を書く。

## 4. GO と承認・PO の操作
- PO の実装承認: 2026-11-03 PO 選択「1」（権限の要る画面も測れるように権限を足し、同じ形で本番の測定まで直す）・「操作していいから足して」・「つぎを進める」。ADR-1054 は Accepted。このカードの審査合格の後に、設計担当がクラウドの Sonnet へ渡す。
- 触るのは frontend の画面 5 個（6 ファイル）・試験と書類だけで、migrations・deploy.yml・本番 scripts を含まない（番号付き GO の要る危ない PR ではない）。main へのマージで本番の画面に出る（deploy.yml が main への push で動く）。マージは PO の委任に基づき設計担当（Claude Opus）が、マージ前の審査役の APPROVE と必須の確認がすべて pass の後に行う。
- PO が操作することはない。

## 5. 受入（○×）
| # | 基準 | 検証方法 |
|---|---|---|
| B1 | Q1（5 画面とも戻った時に LoadingBlock 0 個で前の中身が出る・一覧の画面は見出しの横に回る印・裏で取り直す）と Q2（ロールの権限を読めていない間はチェックを押せず、読めたら押せる・スタッフを読めなかった時はフォームを出さない）が合格。段 3 の 1 回目の Q2・Q3（K5）と 2〜4 回目の Q1 も合格のまま | /tmp/b3e-unit.txt の最後（batch3ePages.test.tsx の 7 件が passed・batch3dPages.test.tsx・batch3cPages.test.tsx・batch3bPages.test.tsx・batch3aPages.test.tsx・useSeededForm.test.tsx・apiQuery.test.tsx・stage2Pages.test.tsx も passed）と、PR の CI の unit-run が success |
| B2 | 今ある画面の試験 4 本・全部の試験・型・lint・組み立てが通る | /tmp/b3e-pages.txt・b3e-unit-all.txt・b3e-tsc.txt・b3e-lint.txt・b3e-build.txt の最後と、PR の必須の確認がすべて pass |
| B3 | 変わったのは §1 の 13 ファイルだけ。画面の書く path と中身・表・フォームの欄は変わっていない | gh pr diff --name-only と git diff -w（§4-M 手順6） |
| B4 | QueryClient を作るのは apiQuery.ts の 1 か所だけ・staleTime を設定していない・写しをブラウザの保存に書かない | `git grep -n "new QueryClient" -- frontend/src` が 1 行、`git grep -n "staleTime:" -- frontend/src` が 0 行、`git grep -n -i "persist" -- frontend/src/lib/query frontend/package.json` が 0 行 |
| B5 | マージの後、毎朝の画面の記録を手で 1 回動かし、下の 9 行で K1（戻った時の秒）≤0.1 秒、K2（初めて開く秒）≤2 秒、403・5xx が 0 件。ほかの行は K2 の最大と 2 秒を超えた画面の数が、基準の回（prod-ui-check run 41591179240）から悪化していない | prod-ui-check の実行の要約（設計担当。`gh workflow run prod-ui-check.yml --ref main` の後に要約の表を読む）。基準の値は下の表と design §3-4-18 |
| B6 | 取り直した後の中身が DB と一致（tenant 001）: チャネル・ロール・スタッフ・受注の件数が、本番 DB の同じ条件の件数と同じ | 設計担当が本番の読むだけの道（ADR-1024）で tenant 001 の行を数える。画面の件数は prod-ui-check の記録か PO のログイン済みの Chrome で数える。数えられない時は「画面の件数はまだ確かめていない」と記録し、backend を変えていないこと（B3）と Q1 を根拠にする |
| B7 | マージの後、deploy が成功し、本番の画面が開く | deploy.yml の実行の結論 success と時刻。本番 https://app.salesanchor.jp/ が開き、ブラウザの誤りの記録に TanStack 由来の誤りが無い（設計担当） |

B5 の基準（prod-ui-check run 41591179240・測った日時 2026-11-03 15:42:42 JST・main b492b3f。権限を足した後で、9 行とも 403 0 件・5xx 0 件）:

| 行 | K1（秒） |
|---|---|
| /channels | 0.24 |
| /management-center/channels | 0.20 |
| /roles | 0.33 |
| /management-center/roles | 0.36 |
| /staff | 0.23 |
| /management-center/staff | 0.24 |
| management-center→staff | 0.22 |
| /staff/:id/edit | 0.19 |
| /orders | 0.19 |
