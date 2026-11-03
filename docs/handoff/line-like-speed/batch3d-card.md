# 段 3 の 4 回目の実装カード（権限の要る 8 画面を「写しを先に出して裏で取り直す」形に変える）

- 対象: docs/handoff/line-like-speed/design.md §3-2（部品）・§3-3（触らない範囲）・§3-4 の段 3・§3-5 の K1・K2・K5・§3-7。ADR-1054（Accepted）。段 3 の 1〜3 回目のカード（docs/handoff/line-like-speed/batch3a-card.md・batch3b-card.md・batch3c-card.md）の部品と形をそのまま使う。
- 根拠の写し: S=origin/main 340fff885920db3d18bbb1001afd7f6e2d327fb1。行番号はすべてこの sha。2026-11-03 に設計担当が S の写しで行を読んだ。2026-11-03 時点の origin/main 1f7bcdef9 と S の間で frontend/src の差は 0（設計担当が `git diff --stat` で確かめた）。実装の前に最新の origin/main で行を合わせ直す（§3(a)）。
- 読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/04-worktree.md・guards/05-pr.md・guards/10-executor.md・scripts/agent-hooks/cloud/rules.md（段 3 の 1〜3 回目のカードと同じ節。照合も同じ: 全命令は cd <W> で始める・出力は tail/head で上限・新しいファイルは丸ごとの全文・作業場所は new-worktree.sh で作り出力をパイプに通さない・PR は実行役が作らない・出力をファイルに残す命令と tail で読む命令は別の行）。
- 実行役はクラウドの Sonnet。作業場所の作り方はクラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）を正とする。.pr-number・gh-pr-create-safe.sh は使わない。出力には上限を付ける。待つために sleep を使わない。
- 状態: 第 2 版（2026-11-03 設計担当 Claude Opus）。第 1 版（e3d16a834）のクラウド審査 REVISE の 4 点（Q2 の押せるかの見方・手順3 の grep 2 本・ORD-FIX の行）を直した。
- 受領確認: 実装役は着手の最初の報告に「段 3 の 4 回目のカード 第 2 版を受け取った・S=340fff885」と書く。

## 0. 設計からの直し・詳しくした点（V3d。設計の合格線は変えない）
- V3d-1 対象は、測る利用者（tenant 001 の測定用の利用者）に見る権限が無く、これまでの毎朝の記録で「断りの画面が戻る秒」しか測れていなかった画面のうち、開くたびに中身を消して取り直している 8 画面（design §3-4-17）。PO 選択「1」（権限を足して本番の測定まで直す）。測る利用者への見る権限は 2026-11-03 に足し済み。残りの 8 画面（チャネル・ロール・スタッフ・スタッフの編集・受注・在庫の見え方・状態・商品区分）は段 3 の 5 回目のカードで扱い、このカードの対象ではない。

  | 行（毎朝の記録の画面） | 画面のファイル | 読む path |
  |---|---|---|
  | /crm/archive | pages/archives/ArchivesPage.tsx | /archives |
  | /data・/management-center/data | pages/erp/ERPPage.tsx | /erp/sync-logs |
  | /shifts・/management-center/shifts | pages/shifts/ShiftsPage.tsx | /shifts |
  | /reports・/management-center/reports | pages/staff-reports/StaffReportsPage.tsx | /staff-reports（絞り込みで ?report_type=） |
  | /settings・/management-center/notifications | pages/notifications/NotificationsPage.tsx | /notification-channels・/notification-event-types |
  | /sales | pages/sales/SalesPage.tsx | /financials/orders |
  | /commissions | pages/commissions/CommissionsPage.tsx | /commissions/monthly?year=&month=・/financials/orders（編集の権限がある時） |
  | /commission-settings・/management-center/commission | pages/commission-settings/CommissionSettingsPage.tsx | /tenant-commission-settings・/commissions/monthly?year=&month= |

  画面の道は S frontend/src/App.tsx:219・:243・:259・:260・:264・:273・:282・:295・:397・:400・:415・:422・:423。13 行の基準（権限を足した後の K1・K2）は §5 B5 の表に書く。
- V3d-2 写しの置き場の部品（S frontend/src/lib/query/apiQuery.ts）と、フォームの初めの値を写しから作る部品（S frontend/src/lib/query/useSeededForm.ts）は変えない。使うのは useApiQuery・useInvalidateApi・useSeededForm だけ。QueryClient を足さない・staleTime を設定しない・写しをブラウザの保存に書かない。
- V3d-3 一覧の画面（保管・ERP の記録・シフト・スタッフの報告・通知の宛先・売上・報酬）は段 3 の 1〜3 回目と同じ形にする: 写しがあればすぐ出す・読み込み中の印（LoadingBlock）は写しが無い初回（isPending）だけ・写しを出したまま裏で取り直している間は見出しの横に小さな回る印（金型 components/loading の Spinner・size "sm"・PageLayout の headerLeft）。報酬の設定は設定のフォームの画面なので回る印は出さない（段 3 の 1 回目の Bot の編集と同じ）。
- V3d-4 書いた後の取り直し: 今の `load()` を呼んでいる所は、そのまま `load()` を呼び、`load` の中身を「その画面の読む path の写しを古い印にする（useInvalidateApi）」に変える。古い印になった写しは、画面が開いている間に裏で 1 回取り直される。売上は財務の編集が保存できた後（S SalesPage.tsx:197-200）、報酬は担当の割り当てが保存できた後（S CommissionsPage.tsx:256-258）に同じく古い印にする。
- V3d-5 見た目の変わる所（意図した変化）: 売上の画面で財務の編集を保存した後、今は読み込み中の印で表が消えてから出直す（S SalesPage.tsx:67 の `setLoading(true)`）。直した後は表を出したまま裏で取り直し、見出しの横に回る印を出す。ほかの 7 画面は、書いた後に読み込み中の印を出していない（S の load は setLoading(true) をしない）ので見た目は変わらない。
- V3d-6 スタッフの報告の種類の絞り込みを変えた時は前の行を出したまま取る（keepPrevious）。今も絞り込みを変えた時は読み込み中の印を出さず前の行が残る（S StaffReportsPage.tsx:31・:37 は初回だけ）ので同じ。報酬の画面の年と月を変えた時は keepPrevious を付けない: 今は変えるたびに読み込み中の印を出す（S CommissionsPage.tsx:95）ので、新しい年と月の写しが無い時は同じく読み込み中の印を出す。1 度開いた年と月は写しからすぐ出る。報酬の設定の画面の下の月の集計は keepPrevious を付ける: 今も年と月を変えた時に前の集計を出したまま取る（S CommissionSettingsPage.tsx:129-139 は読み込み中の印を出さない）ので同じ。
- V3d-7 取れなかった時の文は shownError の 1 か所（S の error と、写しの取り直しの誤りを合わせる）。通知の宛先は 2 つの path のうち先に誤った方の文を出す。今は 2 つのどちらかが取れないと両方とも空のまま（S NotificationsPage.tsx:56-62 の Promise.all）だが、直した後は取れた方は出る。報酬の画面の受注の一覧（編集の権限がある時だけ）は、今と同じく取れなかった時に文を出さず空の一覧にする（S CommissionsPage.tsx:125-128）。報酬の設定の画面の月の集計は今と同じく取れなかった時に文を出さず「集計を取れなかった」の文（S :328 の commissions.monthlyError）を出す。
- V3d-8 写しがある状態で裏の取り直しが失敗した時は、前の中身を出したまま誤りの文を出す（段 3 の 1〜3 回目と同じ。TanStack Query は失敗しても data を残す）。報酬の画面だけは今は失敗した時に集計を消して「集計を取れなかった」の文を出す（S CommissionsPage.tsx:105 の `setMonthly(null)`）が、直した後は前の集計と誤りの文が並ぶ。年と月の欄の値と集計の年月は同じ写しの名前（path に年と月が入る）なので、出ている集計が別の月の物になることはない。
- V3d-9 報酬の設定の画面: 設定を読めなかった時は、今は既定の値（S :65-72 の DEFAULT_FORM）を入れたフォームが出て保存できるので、押すと既定の値で本物の設定を上書きしてしまう。直した後は useSeededForm の ready が false の間（設定をまだ読めていない・読めなかった）は保存のボタンを押せなくする（S :259 `disabled={saving}` → `disabled={saving || !ready}`）。この時フォームの欄は既定の値を出したまま動かない（useSeededForm の setForm は写しが無い間は何もしない・S useSeededForm.ts:23-29）。Q2 で確かめる。
- V3d-10 売上の画面と報酬の画面は同じ `/financials/orders` を読むので、同じ写しを使う（同じ API の同じ答えを 2 か所に分けて持たない）。報酬の画面は答えの items だけを使う（今と同じ）。
- V3d-11 今ある画面の試験のうち、StaffReportFormButtonMigration.test.tsx と FormActionButtonMigration.test.tsx は `cleanup();` の後に写しを消していないので、`queryClient.clear();` を足す（段 3 の 1〜3 回目の §4-K と同じ）。8 画面を描く試験はこの 2 本だけ（設計担当が S で `grep -rln` して確かめた）。
- V3d-12 受入（§5 B5）は、13 行すべてで K1 ≤0.1 秒・K2 ≤2 秒・403 と 5xx が 0 件。K5 は段 3 の 1 回目の Q2・Q3（Bot 編集と useSeededForm の試験）と、写しの名前に利用者が入る作りで確かめる（本番で 2 人のログインは使わない）。

## 1. 触るファイル（変更前→変更後）
| # | ファイル | 変更前 | 変更後 |
|---|---|---|---|
| 1 | frontend/src/pages/archives/ArchivesPage.tsx | useState と useEffect で読む（S :16・:18・:20-26） | useApiQuery（§4-A） |
| 2 | frontend/src/pages/erp/ERPPage.tsx | 同上（S :19・:21・:24-30） | 同上（§4-B） |
| 3 | frontend/src/pages/shifts/ShiftsPage.tsx | 同上（S :20・:24・:26-32） | 同上（§4-C） |
| 4 | frontend/src/pages/staff-reports/StaffReportsPage.tsx | 同上（S :27・:31・:34-40） | 同上（§4-D） |
| 5 | frontend/src/pages/notifications/NotificationsPage.tsx | 同上（S :40-41・:47・:54-67） | 同上（§4-E） |
| 6 | frontend/src/pages/sales/SalesPage.tsx | 同上（S :60-62・:66-81） | 同上（§4-F） |
| 7 | frontend/src/pages/commissions/CommissionsPage.tsx | 同上（S :69-71・:74・:77-82・:92-132） | 同上（§4-G） |
| 8 | frontend/src/pages/commission-settings/CommissionSettingsPage.tsx | 同上（S :76-79・:113-147） | useApiQuery＋useSeededForm（§4-H） |
| 9 | frontend/src/components/StaffReportFormButtonMigration.test.tsx | cleanup の後に写しを消さない | cleanup の後に queryClient.clear()（§4-K） |
| 10 | frontend/src/components/FormActionButtonMigration.test.tsx | 同上 | 同上（§4-K） |
| 11 | frontend/src/lib/query/batch3dPages.test.tsx | 無い | 新しく作る。Q1・Q2（§4-L 全文） |
| 12 | docs/handoff/line-like-speed/batch3d-card.md | 無い | このカード（設計担当が書いた。実装役は触らない） |
| 13 | docs/handoff/line-like-speed/design.md | §3-4-16-a まで | §3-4-17 にこのカードの場所を書き足し済み（設計担当。実装役は触らない） |
| 14 | .claude-pipeline/active-work.d/release-line-like-speed-batch3d.md | 無い | 作業の札（設計担当。実装役は触らない） |

## 2. 触らない範囲
- backend/・migrations/・.github/workflows/・scripts/・tests/prod-check/・frontend/viewer/ は触らない（design §3-3）。
- frontend/src/lib/api.ts・frontend/src/contexts/AuthContext.tsx・frontend/src/lib/auth/・frontend/src/lib/query/apiQuery.ts・frontend/src/lib/query/useSeededForm.ts・frontend/src/lib/query/QueryAuthSync.tsx・frontend/src/App.tsx・frontend/src/hooks/・frontend/src/mocks/ は触らない。
- frontend/src/components/（PageLayout・Spinner・LoadingBlock・OrderFinancialPanel・CommissionPanel を含む。試験のファイルは §4-K の行だけ）・CSS・ja.json・en.json は触らない。新しい言葉・色・寸法を足さない。
- 8 画面の中の、書き方（post・patch・delete の path と中身）・ERP の書き出し（S ERPPage.tsx:32-50 の fetch）・表の列・ボタン・モーダル・フォームの欄・報酬の設定の保存（S CommissionSettingsPage.tsx:149-168 のうち §4-H7 の 2 行を除く）は変えない。変えるのは §4 に書いた行だけ。
- QueryClient を作らない（試験の中でも作らない）。staleTime を設定しない。写しをブラウザの保存に書かない。
- ほかの画面は変えない。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) 最新の origin/main で `git diff --stat 340fff885 origin/main -- frontend/src` が空か。空でなければ、変わったファイルの名前と行数を報告に書く。§1 #1〜#10 のどれかが変わっていたら停止して報告する。ほかのファイルだけなら続ける。
- (b) `cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json` が `"5.104.4"` の 1 行。違えば停止して報告する。
- (c) §4 の「変更前」の文が、書かれた行にそのままあること。1 か所でも無い・2 か所以上ある時は、直さずに停止して BLOCKED: で `grep -n` の出力を報告する。
- (d) 手順 2 で、変える前の 8 ファイル（§1 #1〜#8）の lint の警告の数を数えておく。変えた後は、その数より増えないこと（0 になってもよい）。増えたら直す。直せない時は停止する。
- (e) Q1・Q2・今ある画面の試験のどれかが落ちたら、試験を書き換えて通さない（§4-K の行を除く）。画面の §4 の写し違いを探し、写し違いが無ければ停止して NEEDS_DECISION: で生の出力を返す。
- (f) StaffReportFormButtonMigration.test.tsx は「保存できた後に報告の一覧の get が 1 回増える・断られた時は増えない」を数える。FormActionButtonMigration.test.tsx は通知の宛先とシフトの読みを数える（保存の後に 2 つの path がそれぞれ 1 回増える）。§4-D・§4-E の load は保存できた後だけ呼ばれ、古い印にした写しは画面が開いている間に 1 回だけ取り直されるので、数は今と同じになる見込み。違った時は試験を変えずに停止して NEEDS_DECISION: で生の出力を返す。
- (g) api の import を消すのは ERPPage.tsx（§4-B1）・SalesPage.tsx（§4-F1）・CommissionsPage.tsx（§4-G1）の 3 つ。消す前に `grep -n "api\." <ファイル>` が、ERPPage.tsx は S :25 の 1 行、SalesPage.tsx は S :70 の 1 行、CommissionsPage.tsx は S :78・:98・:121 の 3 行だけであることを確かめる。ほかにも出たら消さずに残し、報告に書く（tsc と lint が通れば続けてよい）。ArchivesPage.tsx（S :29）・ShiftsPage.tsx（S :37・:43）・StaffReportsPage.tsx（S :45）・NotificationsPage.tsx（S :72・:94・:104）・CommissionSettingsPage.tsx（S :156）は api を残す。

## 4-A. #1 frontend/src/pages/archives/ArchivesPage.tsx
- A1 S :1 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`
- A2 S :2 `import { useEffect, useState } from "react";` → `import { useState } from "react";`
- A3 S :4 `import { api } from "../../lib/api";` の次に `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` を足す。
- A4 S :16 `  const [archives, setArchives] = useState<Archive[]>([]);` を次の 2 行に置き換える:
```ts
  const archivesQ = useApiQuery<Archive[]>("/archives");
  const archives = archivesQ.data ?? [];
```
- A5 S :18 `  const [loading, setLoading] = useState(true);` を次の 2 行に置き換える（:17 の error は残す）:
```ts
  const shownError = error || (archivesQ.error ? (archivesQ.error instanceof Error ? archivesQ.error.message : t("common.fetchError")) : "");
  const invalidate = useInvalidateApi();
```
- A6 S :20-26（load・eslint-disable の行・useEffect）を次に置き換える:
```ts
  const load = () => {
    void invalidate(["archives"]);
  };
```
- A7 S :34 `    <PageLayout navKey="nav.archive" subtitleKey="archives.subtitle">` → 次の 5 行にする:
```tsx
    <PageLayout
      navKey="nav.archive"
      subtitleKey="archives.subtitle"
      headerLeft={archivesQ.isFetching && !archivesQ.isPending ? <Spinner size="sm" /> : undefined}
    >
```
- A8 S :35 `      {error && <div className="error-message">{error}</div>}` → `      {shownError && <div className="error-message">{shownError}</div>}`
- A9 S :36 `      {loading ? <LoadingBlock /> : (() => {` → `      {archivesQ.isPending ? <LoadingBlock /> : (() => {`
- :29 の restore（`load();` を呼ぶ）・:37-75 の列と表は変えない。

## 4-B. #2 frontend/src/pages/erp/ERPPage.tsx
- B1 S :1 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`。S :2 `import { useEffect, useState } from "react";` → `import { useState } from "react";`。S :4 `import { api } from "../../lib/api";` を `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` に置き換える（§3(g)。:5 の getAccessToken は残す）。
- B2 S :19 `  const [logs, setLogs] = useState<SyncLog[]>([]);` を次の 2 行に置き換える:
```ts
  const logsQ = useApiQuery<SyncLog[]>("/erp/sync-logs");
  const logs = logsQ.data ?? [];
```
- B3 S :21 `  const [loading, setLoading] = useState(true);` を次の 2 行に置き換える（:20 の error・:22 の exporting は残す）:
```ts
  const shownError = error || (logsQ.error ? (logsQ.error instanceof Error ? logsQ.error.message : t("common.fetchError")) : "");
  const invalidate = useInvalidateApi();
```
- B4 S :24-30（load・eslint-disable の行・useEffect）を次に置き換える:
```ts
  const load = () => {
    void invalidate(["erp", "sync-logs"]);
  };
```
- B5 S :55 `      subtitleKey="erp.subtitle"` の次の行に足す:
  `      headerLeft={logsQ.isFetching && !logsQ.isPending ? <Spinner size="sm" /> : undefined}`
- B6 S :57 `      {error && <div className="error-message">{error}</div>}` → `      {shownError && <div className="error-message">{shownError}</div>}`
- B7 S :68 `      {loading ? <LoadingBlock /> : (() => {` → `      {logsQ.isPending ? <LoadingBlock /> : (() => {`
- :32-50 の書き出し（:47 の `load();` を含む）・列は変えない。

## 4-C. #3 frontend/src/pages/shifts/ShiftsPage.tsx
- C1 S :1 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`。S :2 `import { useEffect, useState, FormEvent } from "react";` → `import { useState, FormEvent } from "react";`
- C2 S :4 `import { api } from "../../lib/api";` の次に `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` を足す。
- C3 S :20 `  const [shifts, setShifts] = useState<Shift[]>([]);` を次の 2 行に置き換える:
```ts
  const shiftsQ = useApiQuery<Shift[]>("/shifts");
  const shifts = shiftsQ.data ?? [];
```
- C4 S :24 `  const [loading, setLoading] = useState(true);` を次の 2 行に置き換える（:23 の error は残す）:
```ts
  const shownError = error || (shiftsQ.error ? (shiftsQ.error instanceof Error ? shiftsQ.error.message : t("common.fetchError")) : "");
  const invalidate = useInvalidateApi();
```
- C5 S :26-32（load・eslint-disable の行・useEffect）を次に置き換える:
```ts
  const load = () => {
    void invalidate(["shifts"]);
  };
```
- C6 S :50 `      subtitleKey="shifts.subtitle"` の次の行に足す:
  `      headerLeft={shiftsQ.isFetching && !shiftsQ.isPending ? <Spinner size="sm" /> : undefined}`
- C7 S :52 `      {error && <div className="error-message">{error}</div>}` → `      {shownError && <div className="error-message">{shownError}</div>}`
- C8 S :87 `      {loading ? <LoadingBlock /> : (() => {` → `      {shiftsQ.isPending ? <LoadingBlock /> : (() => {`
- :34-45 の登録と削除（`load();` を呼ぶ）・:58-86 のモーダル・列は変えない。
- `invalidate(["shifts"])` は `/shifts` から始まる写しを古い印にする。予定の画面（/schedule）の `/shifts?date_from=&date_to=` も同じ頭なので当たるが、その画面が写しを使っていない（S pages/schedule の api.get）なら何も起きない。使っていても、シフトを足した・消した後に予定を取り直すのは正しい動き。

## 4-D. #4 frontend/src/pages/staff-reports/StaffReportsPage.tsx
- D1 S :1 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`。S :2 `import { useEffect, useState, FormEvent } from "react";` → `import { useState, FormEvent } from "react";`
- D2 S :4 `import { api } from "../../lib/api";` の次に `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` を足す。
- D3 S :27 `  const [reports, setReports] = useState<StaffReport[]>([]);` を消す。
- D4 S :31 `  const [loading, setLoading] = useState(true);` を消す。
- D5 S :32 `  const [typeFilter, setTypeFilter] = useState("");` の次に足す:
```ts
  const reportsQ = useApiQuery<StaffReport[]>(`/staff-reports${typeFilter ? `?report_type=${typeFilter}` : ""}`, { keepPrevious: true });
  const reports = reportsQ.data ?? [];
  const shownError = error || (reportsQ.error ? (reportsQ.error instanceof Error ? reportsQ.error.message : t("common.fetchError")) : "");
  const invalidate = useInvalidateApi();
```
- D6 S :34-40（load・eslint-disable の行・useEffect）を次に置き換える:
```ts
  const load = () => {
    void invalidate(["staff-reports"]);
  };
```
- D7 S :56 `      subtitleKey="reports.subtitle"` の次の行に足す:
  `      headerLeft={reportsQ.isFetching && !reportsQ.isPending ? <Spinner size="sm" /> : undefined}`
- D8 S :75 `      {error && <div className="error-message">{error}</div>}` → `      {shownError && <div className="error-message">{shownError}</div>}`
- D9 S :102 `      {loading ? <LoadingBlock /> : (` → `      {reportsQ.isPending ? <LoadingBlock /> : (`
- :42-51 の登録（:49 の `load();` を含む）・:58-74 の絞り込み・:103-276 の表は変えない。作る path は今と同じ（`/staff-reports` か `/staff-reports?report_type=<種類>`。種類は daily・weekly・monthly のどれか）。

## 4-E. #5 frontend/src/pages/notifications/NotificationsPage.tsx
- E1 S :1 `import { useEffect, useState, FormEvent } from "react";` → `import { useState, FormEvent } from "react";`
- E2 S :3 `import { api } from "../../lib/api";` の次に `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` を足す。
- E3 S :16 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`
- E4 S :40-41（channels と eventTypes の useState の 2 行）を次の 4 行に置き換える:
```ts
  const channelsQ = useApiQuery<Channel[]>("/notification-channels");
  const eventTypesQ = useApiQuery<EventTypeOption[]>("/notification-event-types");
  const channels = channelsQ.data ?? [];
  const eventTypes = eventTypesQ.data ?? [];
```
- E5 S :47 `  const [loading, setLoading] = useState(true);` を次の 4 行に置き換える（:46 の error は残す）:
```ts
  const readError = channelsQ.error ?? eventTypesQ.error;
  const shownError = error || (readError ? (readError instanceof Error ? readError.message : t("common.fetchError")) : "");
  const refetching = (channelsQ.isFetching && !channelsQ.isPending) || (eventTypesQ.isFetching && !eventTypesQ.isPending);
  const invalidate = useInvalidateApi();
```
- E6 S :54-67（load・eslint-disable の行・useEffect）を次に置き換える:
```ts
  const load = () => {
    void invalidate(["notification-channels"]);
    void invalidate(["notification-event-types"]);
  };
```
- E7 S :111 `      subtitleKey="settings.subtitle"` の次の行に足す:
  `      headerLeft={refetching ? <Spinner size="sm" /> : undefined}`
- E8 S :113 `      {error && <div className="error-message">{error}</div>}` → `      {shownError && <div className="error-message">{shownError}</div>}`
- E9 S :174 `      {loading ? <LoadingBlock /> : (() => {` → `      {channelsQ.isPending || eventTypesQ.isPending ? <LoadingBlock /> : (() => {`
- :69-106 の登録・編集・削除（:77・:99・:104 の `load();`）・:119-173 のモーダル・列は変えない。種類の一覧も保存の後に取り直すのは今と同じ（S の load は 2 つとも取り直す）。

## 4-F. #6 frontend/src/pages/sales/SalesPage.tsx
- F1 S :12 `import { useCallback, useEffect, useState } from "react";` → `import { useState } from "react";`。S :14 `import { api } from "../../lib/api";` を `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` に置き換える（§3(g)）。
- F2 S :22 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`
- F3 S :60-62（data・loading・error の useState の 3 行）を次の 4 行に置き換える（:63-64 の editing は残す）:
```ts
  const salesQ = useApiQuery<SalesListDto>("/financials/orders");
  const data = salesQ.data ?? null;
  const shownError = salesQ.error ? (salesQ.error instanceof Error ? salesQ.error.message : t("common.fetchError")) : "";
  const invalidate = useInvalidateApi();
```
- F4 S :66-81（load の useCallback・空行・useEffect）を次に置き換える（:82 の空行は残す）:
```ts
  const load = () => invalidate(["financials", "orders"]);
```
- F5 S :84 `    <PageLayout navKey="nav.sales" subtitleKey="sales.subtitle">` → 次の 5 行にする:
```tsx
    <PageLayout
      navKey="nav.sales"
      subtitleKey="sales.subtitle"
      headerLeft={salesQ.isFetching && !salesQ.isPending ? <Spinner size="sm" /> : undefined}
    >
```
- F6 S :85 `      {error && <div className="error-message">{error}</div>}` → `      {shownError && <div className="error-message">{shownError}</div>}`
- F7 S :87 `      {loading ? (` → `      {salesQ.isPending ? (`
- :92 `{data && (`・:259 `data={data?.items ?? []}`・:197-200 の onSaved（`void load();`）は変えない。setError は S :68・:73 の load の中だけで使うので、error の useState ごと消してよい（V3d-7）。

## 4-G. #7 frontend/src/pages/commissions/CommissionsPage.tsx
- G1 S :13 `import { useCallback, useEffect, useState } from "react";` → `import { useState } from "react";`。S :15 `import { api } from "../../lib/api";` を `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` に置き換える（§3(g)）。
- G2 S :24 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`
- G3 S :69-71（monthly・loading・error の useState の 3 行）を次の 4 行に置き換える:
```ts
  const monthlyQ = useApiQuery<MonthlySummaryDto>(`/commissions/monthly?year=${year}&month=${month}`);
  const monthly = monthlyQ.data ?? null;
  const shownError = monthlyQ.error ? (monthlyQ.error instanceof Error ? monthlyQ.error.message : t("common.fetchError")) : "";
  const invalidate = useInvalidateApi();
```
- G4 S :74 `  const [orders, setOrders] = useState<CommissionOrderItem[]>([]);` を次の 2 行に置き換える（:73 の説明の行・:75 の assigning は残す）:
```ts
  const ordersQ = useApiQuery<{ items: CommissionOrderItem[] }>("/financials/orders", { enabled: canEdit });
  const orders = ordersQ.data?.items ?? [];
```
- G5 S :77-82（reloadMonthly の useCallback）を次の 1 行に置き換える:
```ts
  const reloadMonthly = () => invalidate(["commissions"]);
```
- G6 S :91-132（:90 の `};` の次の空行・月の集計の useEffect・空行・受注の一覧の説明の行と useEffect）を消す（:133 の空行は残す）。
- G7 S :135 `    <PageLayout navKey="nav.commissions" subtitleKey="commissions.listSubtitle">` → 次の 5 行にする:
```tsx
    <PageLayout
      navKey="nav.commissions"
      subtitleKey="commissions.listSubtitle"
      headerLeft={(monthlyQ.isFetching && !monthlyQ.isPending) || (ordersQ.isFetching && !ordersQ.isPending) ? <Spinner size="sm" /> : undefined}
    >
```
- G8 S :136 `      {error && <div className="error-message">{error}</div>}` → `      {shownError && <div className="error-message">{shownError}</div>}`
- G9 S :167 `        {loading ? (` → `        {monthlyQ.isPending ? (`
- :140-165 の年と月の欄・:169-216 の集計・:218-249 の受注の一覧・:256-258 の onSaved（`void reloadMonthly();`）は変えない。
- `invalidate(["commissions"])` は `/commissions/...` の写し（どの年と月も）を古い印にし、開いている年と月だけ裏で取り直す。今の reloadMonthly は開いている年と月だけ取り直すので、画面の動きは同じ。受注の一覧は今も担当の割り当ての後に取り直していない（S :116-132 は canEdit が変わった時だけ）ので古い印にしない。
- 受注の一覧は編集の権限がある時だけ取る（enabled: canEdit。今と同じ）。権限が無い間 ordersQ は isPending のままだが、:218 の `canEdit &&` の側が描かれないので画面に出ない。

## 4-H. #8 frontend/src/pages/commission-settings/CommissionSettingsPage.tsx
- H1 S :12 `import { FormEvent, useEffect, useState } from "react";` → `import { FormEvent, useState } from "react";`
- H2 S :14 `import { api } from "../../lib/api";` の次に 2 行足す（api は保存で使うので残す）:
```ts
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { useSeededForm } from "../../lib/query/useSeededForm";
```
- H3 S :76-79（settings・form・monthly・loading の useState の 4 行）を消す。:80-82 の saving・error・info は残す。
- H4 S :91 `  const [month, setMonth] = useState(nowJst.getMonth() + 1);` の次に足す:
```ts
  const monthlyQ = useApiQuery<MonthlySummaryDto>(`/commissions/monthly?year=${year}&month=${month}`, { keepPrevious: true });
  const monthly = monthlyQ.data ?? null;
```
- H5 S :111 `  };`（dtoToForm の閉じ）の次に足す（空行を挟む）:
```ts

  const settingsQ = useApiQuery<CommissionSettingsDto>("/tenant-commission-settings");
  const settings = settingsQ.data ?? null;
  const { form, setForm, ready } = useSeededForm("commission-settings", settingsQ.data, dtoToForm, DEFAULT_FORM);
  const shownError = error || (settingsQ.error ? (settingsQ.error instanceof Error ? settingsQ.error.message : t("common.fetchError")) : "");
  const invalidate = useInvalidateApi();
```
- H6 S :112-147（空行・loadSettings・空行・loadMonthly・空行・2 つの useEffect）を消す（:148 の空行は残す）。
- H7 S :160-161 の 2 行
```ts
      setSettings(updated);
      setForm(dtoToForm(updated));
```
  を次の 2 行に置き換える:
```ts
      setForm(dtoToForm(updated));
      void invalidate(["tenant-commission-settings"]);
```
- H8 S :179 `      {loading ? (` → `      {settingsQ.isPending ? (`
- H9 S :183 `          {error && <div className="error-message">{error}</div>}` → `          {shownError && <div className="error-message">{shownError}</div>}`
- H10 S :259 `                disabled={saving}` → `                disabled={saving || !ready}`（V3d-9）
- :170-172 の updateRole（setForm に関数を渡す。useSeededForm の setForm は関数も受け取る）・:265-269 の最終更新（settings を使う）・:274-330 の月の集計は変えない。回る印は足さない（V3d-3）。
- 動き: 保存できた後、フォームは保存の答えで作り直し（今と同じ）、写しを古い印にして取り直す。取り直した写しでフォームを作り直すのは人がまだ直していない時だけ（useSeededForm）。保存の直後のフォームは setForm で作り直した後なので「直した」扱いになり、取り直しでは作り直さないが、中身は保存の答えと同じ。最終更新の時刻は取り直した写しから出る。

## 4-K. #9・#10 今ある試験の写しを消す（ほかの行は変えない）
- K1 frontend/src/components/StaffReportFormButtonMigration.test.tsx: S :7 `import en from '../locales/en.json';` の次に `import { queryClient } from '../lib/query/apiQuery';` を足す。S :82-87 の afterEach の中の `cleanup();` の次の行に `  queryClient.clear();` を足す（字下げは前の行に合わせる）。
- K2 frontend/src/components/FormActionButtonMigration.test.tsx: S :9 `import en from '../locales/en.json';` の次に `import { queryClient } from '../lib/query/apiQuery';` を足す。S :85 `afterEach(() => { cleanup(); expect(fetch).not.toHaveBeenCalled(); expect(mock.delete).not.toHaveBeenCalled(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });` → `afterEach(() => { cleanup(); queryClient.clear(); expect(fetch).not.toHaveBeenCalled(); expect(mock.delete).not.toHaveBeenCalled(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });`
- 理由: 画面が同じ 1 個の写しの置き場を使うので、前の試験の写しが次の試験に残らないようにする（段 3 の 1〜3 回目の §4-K と同じ）。2 本とも AuthContext を mock していないので、開発の時の仮の利用者（S frontend/src/contexts/AuthContext.tsx:173-197。`import.meta.env.DEV` で /login 以外の時に uid "e2e-test-user-uid"）で写しを取る。人を入れる直しは要らない。
- 実装役は K1・K2 の前に `grep -n "afterEach\|^import en" <ファイル>` で行を確かめる（§3(c)）。

## 4-L. #11 frontend/src/lib/query/batch3dPages.test.tsx（新しく作る・全文）
```tsx
/**
 * ADR-1054 段 3 の 4 回目: 本物の画面の試験。
 * Q1 戻った時に写しを先に出す（読み込み中の印を出さない）・一覧の画面は見出しの横に回る印・裏で取り直す。
 * Q2 報酬の設定を読めなかった時は保存のボタンを押せない（既定の値で本物の設定を上書きしない）。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import type { ComponentType } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ArchivesPage from "../../pages/archives/ArchivesPage";
import CommissionSettingsPage from "../../pages/commission-settings/CommissionSettingsPage";
import CommissionsPage from "../../pages/commissions/CommissionsPage";
import ERPPage from "../../pages/erp/ERPPage";
import NotificationsPage from "../../pages/notifications/NotificationsPage";
import SalesPage from "../../pages/sales/SalesPage";
import ShiftsPage from "../../pages/shifts/ShiftsPage";
import StaffReportsPage from "../../pages/staff-reports/StaffReportsPage";
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
  // api.ts が i18n.ts を読み、i18n.ts が initReactI18next を使う（同じ書き方: src/lib/query/batch3cPages.test.tsx）
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

// 中身は画面の型（ArchivesPage.tsx:11・ERPPage.tsx:14・ShiftsPage.tsx:15・StaffReportsPage.tsx:14-18・
// NotificationsPage.tsx:18-19・SalesPage.tsx:24-45・CommissionsPage.tsx:44-61・CommissionSettingsPage.tsx:29-35）の欄
const archive = { id: 1, source_table: "Fixture Table", source_id: 9, archived_by: null, archived_at: "2026-11-01T00:00:00Z", restored_at: null };
const syncLog = { id: 1, sync_type: "Fixture Sync", direction: "export", record_count: 1, status: "success", error_message: null, started_at: "2026-11-01T00:00:00Z", completed_at: null };
const shift = { id: 1, user_id: 5, shift_date: "2026-11-01", start_time: "09:00", end_time: "18:00", shift_type: "Fixture Shift", notes: null, created_at: "" };
const report = { id: 1, report_code: "SR-FIX", report_type: "daily", user_id: 5, period: "2026-11", review: null, goals: null, challenges: null, reviewer_comment: null, reviewed_at: null, submitted_at: null, created_at: "" };
const channel = { id: 1, channel_name: "Fixture Channel", webhook_url: "https://example.invalid/hook", event_types: "", is_active: true, created_at: "" };
const sales = {
  items: [{ order_id: 1, order_number: "ORD-FIX", company_name: null, contact_display_name: null, currency: "JPY", created_at: "2026-11-01T00:00:00Z", revenue_amount: null, cost_total: null, gross_profit: null, gross_profit_rate: null }],
  count: 1, revenue_total: 0, cost_total: 0, gross_profit_total: 0, gross_profit_rate: null,
};
const monthly = { year: 2026, month: 11, by_staff: [{ staff_id: 5, staff_name: "Fixture Staff", total: 100 }], by_role: [], total: 100 };
const settings = {
  id: 1, tenant_id: 1, created_at: "", updated_at: "2026-11-01T00:00:00Z",
  commission_rates: {
    sales: { type: "rate", value: 0.37 }, order: { type: "rate", value: 0.1 }, ship: { type: "fixed", value: 200 },
    purchase: { type: "fixed", value: 100 }, trouble: { type: "fixed", value: 500 },
  },
};

const fixtures: Record<string, unknown> = {
  "/archives": [archive],
  "/erp/sync-logs": [syncLog],
  "/shifts": [shift],
  "/staff-reports": [report],
  "/notification-channels": [channel],
  "/notification-event-types": [],
  "/financials/orders": sales,
  "/tenant-commission-settings": settings,
};
// 報酬の月の集計は年と月で path が変わるので頭で見分ける
const answer = (path: string) =>
  (path in fixtures ? fixtures[path] : path.startsWith("/commissions/monthly?") ? monthly : []) as never;

type Case = {
  name: string; Page: ComponentType; route: string; at: string;
  path: string | RegExp; text: string; value: boolean; spinner: boolean;
};
const cases: Case[] = [
  { name: "archives", Page: ArchivesPage, route: "/crm/archive", at: "/crm/archive", path: "/archives", text: "Fixture Table", value: false, spinner: true },
  { name: "erp", Page: ERPPage, route: "/data", at: "/data", path: "/erp/sync-logs", text: "Fixture Sync", value: false, spinner: true },
  { name: "shifts", Page: ShiftsPage, route: "/shifts", at: "/shifts", path: "/shifts", text: "Fixture Shift", value: false, spinner: true },
  { name: "staff reports", Page: StaffReportsPage, route: "/reports", at: "/reports", path: "/staff-reports", text: "SR-FIX", value: false, spinner: true },
  { name: "notifications", Page: NotificationsPage, route: "/management-center/notifications", at: "/management-center/notifications", path: "/notification-channels", text: "Fixture Channel", value: false, spinner: true },
  { name: "sales", Page: SalesPage, route: "/sales", at: "/sales", path: "/financials/orders", text: "ORD-FIX", value: false, spinner: true },
  { name: "commissions", Page: CommissionsPage, route: "/commissions", at: "/commissions", path: /^\/commissions\/monthly\?year=\d{4}&month=\d{1,2}$/, text: "Fixture Staff", value: false, spinner: true },
  { name: "commission settings", Page: CommissionSettingsPage, route: "/commission-settings", at: "/commission-settings", path: "/tenant-commission-settings", text: "0.37", value: true, spinner: false },
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

// 設定の画面は欄の中の値で、ほかは文字で見分ける
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

describe("commission settings save is blocked until the settings are read (Q2)", () => {
  it("disables save when the settings could not be read", async () => {
    vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === "/tenant-commission-settings") throw new Error("Fixture read failure");
      return answer(path);
    });
    render(<Tree c={{ Page: CommissionSettingsPage, route: "/commission-settings", at: "/commission-settings" }} />);
    await screen.findByText("Fixture read failure");
    expect((screen.getByTestId("settings-save") as HTMLButtonElement).disabled).toBe(true);
  });

  it("enables save once the settings are read", async () => {
    vi.spyOn(api, "get").mockImplementation(async (path: string) => answer(path));
    render(<Tree c={{ Page: CommissionSettingsPage, route: "/commission-settings", at: "/commission-settings" }} />);
    await screen.findAllByDisplayValue("0.37");
    expect((screen.getByTestId("settings-save") as HTMLButtonElement).disabled).toBe(false);
  });
});
```
- LoadingBlock の見分けは `.sa-loading-block`、回る印の見分けは `.page-layout-title-row .sa-spinner`（段 3 の 1〜3 回目のカード §4-L と同じ）。報酬の設定は回る印を出さない（V3d-3）。
- 「Fixture Table」は保管の表の種類の列（S ArchivesPage.tsx:39-41）、「Fixture Sync」は ERP の表の種類の列（S ERPPage.tsx:71-74）、「Fixture Shift」はシフトの表の種類の列（S ShiftsPage.tsx:107-109）、「SR-FIX」はスタッフの報告の表のコードの列（S StaffReportsPage.tsx:108）、「Fixture Channel」は通知の宛先の表の名前の列（S NotificationsPage.tsx:177-179）、「ORD-FIX」は売上の表の受注番号の列（S SalesPage.tsx:116-120 の列の定義）、「Fixture Staff」は報酬の担当ごとの表（S CommissionsPage.tsx:178）に出る。報酬の画面は受注の一覧にも「ORD-FIX」が出るが、この試験は見ない。
- 「0.37」は報酬の設定の営業の値の欄（testid `settings-value-sales`・S CommissionSettingsPage.tsx:231）の値。S の試験には jest-dom が入っていないため、押せるかどうかは `button.disabled` を直に見る（S の既存の書き方: frontend/src/components/TeamFormButtonMigration.test.tsx:114）。
- 通知の宛先の event_types を空の文字にしたのは、S :24-31 の parseEventTypes が空の一覧を返し、種類の言葉の表を引かないため。webhook_url の `example.invalid` は送られない（試験は fetch を止めている）。

## 4-M. 実装役の手順（1 手順 1 命令。<W> は手順1 で作られた作業場所の絶対パス）
手順1. クラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）どおり、作業場所を作り、push 済みの枝の先頭に合わせる（設計担当が §1 #12〜#14 を push 済み）。
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/line-like-speed-batch3d
  （出力に出た作業場所の絶対パスを <W> として報告に書く。）
  cd <W> && git fetch origin release/line-like-speed-batch3d
  cd <W> && git switch -C release/line-like-speed-batch3d origin/release/line-like-speed-batch3d
  cd <W> && git rev-parse HEAD origin/release/line-like-speed-batch3d
  （2 行が同じことを確かめる。違えば停止して BLOCKED: で報告する。main は取り込まない。reset・rebase・force・merge・pull は使わない）
  cd <W> && ./scripts/dev/executor-preflight.sh > /tmp/b3d-preflight.txt 2>&1
  cd <W> && grep -n "FAIL" /tmp/b3d-preflight.txt | head -20
  cd <W> && grep -n "origin/main は存在" /tmp/b3d-preflight.txt | head -3
  （FAIL の行が次の 3 つのうちのどれかだけなら続ける: `GitHub API に到達不可` の 1 件・`gh auth switch --hostname github.com --user shingo-cc` の失敗の 1 件・その結果の `PREFLIGHT FAIL` の行。理由は段 3 の 1 回目のカード §4-M 手順1 と同じ。続ける時は `[OK]   origin/main は存在` の行があることを 2 つ目の grep で確かめ、無ければ停止する。ほかの FAIL が 1 件でもあれば停止し、BLOCKED: で grep の出力を報告する。）
  cd <W> && git fetch origin main
  cd <W> && git diff --stat 340fff885920db3d18bbb1001afd7f6e2d327fb1 origin/main -- frontend/src | tail -5
  （§3(a) の確かめ。）
手順2. 依存を入れ、§3(b)・§3(g) を確かめ、変える前の lint の警告を数える。
  cd <W>/frontend && npm ci > /tmp/b3d-ci.txt 2>&1
  cd <W> && tail -5 /tmp/b3d-ci.txt
  cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json
  cd <W>/frontend && grep -n "api\." src/pages/erp/ERPPage.tsx src/pages/sales/SalesPage.tsx src/pages/commissions/CommissionsPage.tsx
  （§3(g) の確かめ。5 行であること。）
  cd <W>/frontend && npx eslint src/pages/archives/ArchivesPage.tsx src/pages/erp/ERPPage.tsx src/pages/shifts/ShiftsPage.tsx src/pages/staff-reports/StaffReportsPage.tsx src/pages/notifications/NotificationsPage.tsx src/pages/sales/SalesPage.tsx src/pages/commissions/CommissionsPage.tsx src/pages/commission-settings/CommissionSettingsPage.tsx > /tmp/b3d-lint-before.txt 2>&1
  cd <W> && tail -5 /tmp/b3d-lint-before.txt
手順3. §4-L の全文で #11 を作り、§4-A〜§4-K のとおり #1〜#10 を直す。各ファイルを直す前に、§4 の「変更前」の文を `grep -n` で確かめる（§3(c)）。終わったら残りが無いことを確かめる。
  cd <W> && grep -nw "useEffect\|useCallback\|setLoading\|setArchives\|setLogs\|setShifts\|setReports\|setChannels\|setEventTypes\|setData\|setMonthly\|setOrders\|setSettings\|loadSettings\|loadMonthly" frontend/src/pages/archives/ArchivesPage.tsx frontend/src/pages/erp/ERPPage.tsx frontend/src/pages/shifts/ShiftsPage.tsx frontend/src/pages/staff-reports/StaffReportsPage.tsx frontend/src/pages/notifications/NotificationsPage.tsx frontend/src/pages/sales/SalesPage.tsx frontend/src/pages/commissions/CommissionsPage.tsx frontend/src/pages/commission-settings/CommissionSettingsPage.tsx | head -20
  （0 行であること。`-w` は語として当たる行だけ出すため、G5 で残す `reloadMonthly` は出ない。出たら §4 の写し違いを直す。）
  cd <W> && grep -n "loading" frontend/src/pages/archives/ArchivesPage.tsx frontend/src/pages/erp/ERPPage.tsx frontend/src/pages/shifts/ShiftsPage.tsx frontend/src/pages/staff-reports/StaffReportsPage.tsx frontend/src/pages/notifications/NotificationsPage.tsx frontend/src/pages/sales/SalesPage.tsx frontend/src/pages/commissions/CommissionsPage.tsx frontend/src/pages/commission-settings/CommissionSettingsPage.tsx | head -20
  （出るのは `components/loading` の import の行 8 行と、今からあるボタンの `<Button loading=` の行 2 行（ERPPage.tsx の書き出しのボタン・CommissionSettingsPage.tsx の保存のボタン。どちらも変えない）の、合わせて 10 行だけであること。）
手順4. 型を作ってから試験を流す（新しい試験・直した今ある試験・全部の試験・型・lint）。作る型（frontend/src/api/generated/）は .gitignore で除かれるので commit に入らない。
  cd <W>/frontend && npm run generate:api-types > /tmp/b3d-gen.txt 2>&1
  cd <W> && tail -3 /tmp/b3d-gen.txt
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/lib/query > /tmp/b3d-unit.txt 2>&1
  cd <W> && tail -30 /tmp/b3d-unit.txt
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/components/StaffReportFormButtonMigration.test.tsx src/components/FormActionButtonMigration.test.tsx > /tmp/b3d-pages.txt 2>&1
  cd <W> && tail -30 /tmp/b3d-pages.txt
  cd <W>/frontend && npm run test:unit > /tmp/b3d-unit-all.txt 2>&1
  cd <W> && tail -15 /tmp/b3d-unit-all.txt
  cd <W>/frontend && npx tsc --noEmit -p . > /tmp/b3d-tsc.txt 2>&1
  cd <W> && tail -20 /tmp/b3d-tsc.txt
  cd <W>/frontend && npx eslint src/lib/query src/pages/archives/ArchivesPage.tsx src/pages/erp/ERPPage.tsx src/pages/shifts/ShiftsPage.tsx src/pages/staff-reports/StaffReportsPage.tsx src/pages/notifications/NotificationsPage.tsx src/pages/sales/SalesPage.tsx src/pages/commissions/CommissionsPage.tsx src/pages/commission-settings/CommissionSettingsPage.tsx > /tmp/b3d-lint.txt 2>&1
  cd <W> && tail -20 /tmp/b3d-lint.txt
  （lint の警告が手順2 の数より増えていないこと・誤りが 0 であること。§3(d)。）
手順5. 本番と同じ形で組み立てられるか確かめる。
  cd <W>/frontend && npm run build > /tmp/b3d-build.txt 2>&1
  cd <W> && tail -15 /tmp/b3d-build.txt
手順6. 変わったファイルが §1 の #1〜#11 だけか確かめ、画面の書く path と表・フォームの行が変わっていないことを見る。
  cd <W> && git status --short | head -30
  cd <W> && git diff -w --stat origin/release/line-like-speed-batch3d | tail -20
  cd <W> && git diff -w origin/release/line-like-speed-batch3d -- frontend/src/pages | head -700
手順7. commit する。
  cd <W> && git add frontend/src/pages/archives/ArchivesPage.tsx frontend/src/pages/erp/ERPPage.tsx frontend/src/pages/shifts/ShiftsPage.tsx frontend/src/pages/staff-reports/StaffReportsPage.tsx frontend/src/pages/notifications/NotificationsPage.tsx frontend/src/pages/sales/SalesPage.tsx frontend/src/pages/commissions/CommissionsPage.tsx frontend/src/pages/commission-settings/CommissionSettingsPage.tsx frontend/src/components/StaffReportFormButtonMigration.test.tsx frontend/src/components/FormActionButtonMigration.test.tsx frontend/src/lib/query/batch3dPages.test.tsx
  cd <W> && git commit -m "feat: 権限の要る8画面を写しを先に出して裏で取り直す形に（ADR-1054 段3の4回目）"
手順8. commit が在ることを確かめてから push する（--no-verify は使わない。push の前の検査が × なら直してから push。fast-forward でないと断られたら直さず BLOCKED:）。
  cd <W> && git log -3 --oneline
  cd <W> && git push -u origin release/line-like-speed-batch3d
手順9. 報告を返す。PR は作らない（設計担当が手元で作る）。報告の 1 つの発言は 600 文字以内にして、番号付きの発言に分ける。報告には手順ごとの tail の出力（生のまま）と、§3(a)〜(g) の結果を書く。

## 4. GO と承認・PO の操作
- PO の実装承認: 2026-11-03 PO 選択「1」（権限の要る画面も測れるように権限を足し、同じ形で本番の測定まで直す）・「操作していいから足して」。ADR-1054 は Accepted。このカードの審査合格の後に、設計担当がクラウドの Sonnet へ渡す。
- 触るのは frontend の画面 8 個・試験と書類だけで、migrations・deploy.yml・本番 scripts を含まない（番号付き GO の要る危ない PR ではない）。main へのマージで本番の画面に出る（deploy.yml が main への push で動く）。マージは PO の委任に基づき設計担当（Claude Opus）が、マージ前の審査役の APPROVE と必須の確認がすべて pass の後に行う。
- PO が操作することはない。

## 5. 受入（○×）
| # | 基準 | 検証方法 |
|---|---|---|
| B1 | Q1（8 画面とも戻った時に LoadingBlock 0 個で前の中身が出る・一覧の画面は見出しの横に回る印・裏で取り直す）と Q2（設定を読めない間は保存を押せない・読めたら押せる）が合格。段 3 の 1 回目の Q2・Q3（K5）と 2・3 回目の Q1 も合格のまま | /tmp/b3d-unit.txt の最後（batch3dPages.test.tsx の 10 件が passed・batch3cPages.test.tsx・batch3bPages.test.tsx・batch3aPages.test.tsx・useSeededForm.test.tsx・apiQuery.test.tsx・stage2Pages.test.tsx も passed）と、PR の CI の unit-run が success |
| B2 | 今ある画面の試験 2 本・全部の試験・型・lint・組み立てが通る | /tmp/b3d-pages.txt・b3d-unit-all.txt・b3d-tsc.txt・b3d-lint.txt・b3d-build.txt の最後と、PR の必須の確認がすべて pass |
| B3 | 変わったのは §1 の 14 ファイルだけ。画面の書く path と中身・表・フォームの欄は変わっていない | gh pr diff --name-only と git diff -w（§4-M 手順6） |
| B4 | QueryClient を作るのは apiQuery.ts の 1 か所だけ・staleTime を設定していない・写しをブラウザの保存に書かない | `git grep -n "new QueryClient" -- frontend/src` が 1 行、`git grep -n "staleTime:" -- frontend/src` が 0 行、`git grep -n -i "persist" -- frontend/src/lib/query frontend/package.json` が 0 行 |
| B5 | マージの後、毎朝の画面の記録を手で 1 回動かし、§0 V3d-1 の 13 行で K1（戻った時の秒）≤0.1 秒、K2（初めて開く秒）≤2 秒、403・5xx が 0 件。ほかの行は K2 の最大と 2 秒を超えた画面の数が、権限を足した後の基準の回（prod-ui-check run 41579361752）から悪化していない | prod-ui-check の実行の要約（設計担当。`gh workflow run prod-ui-check.yml --ref main` の後に要約の表を読む）。基準の 13 行の値は design §3-4-17 に書く |
| B6 | 取り直した後の中身が DB と一致（tenant 001）: 保管・シフト・スタッフの報告・通知の宛先の件数が、本番 DB の同じ条件の件数と同じ | 設計担当が本番の読むだけの道（ADR-1024）で tenant 001 の行を数える。画面の件数は prod-ui-check の記録か PO のログイン済みの Chrome で数える。数えられない時は「画面の件数はまだ確かめていない」と記録し、backend を変えていないこと（B3）と Q1 を根拠にする |
| B7 | マージの後、deploy が成功し、本番の画面が開く | deploy.yml の実行の結論 success と時刻。本番 https://app.salesanchor.jp/ が開き、ブラウザの誤りの記録に TanStack 由来の誤りが無い（設計担当） |
