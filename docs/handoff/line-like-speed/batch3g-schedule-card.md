# 段 3 の 7 回目の実装カード（予定表 /schedule の 3 本の読み込みを「写しを先に出して裏で取り直す」形に変える）

- 対象: docs/handoff/line-like-speed/design.md の §3-2（部品）・§3-3（触らない範囲）・§3-4 の段 3・§3-4-19（7 回目に分けた訳）・§3-4-20 と §3-4-20-a（前提のシフトの 500 の直しと受入）・§3-4-21・§3-5 の K1・K2・K5・§3-7。ADR-1054（Accepted）。段 3 の 1〜6 回目のカード（docs/handoff/line-like-speed/batch3a-card.md〜batch3f-card.md）の部品と形をそのまま使う。
- 根拠の写し: S=origin/main 57fbceb0494b2b8b22f647986fb2a81c6084ba5f。行番号はすべてこの sha。2026-11-04 に設計担当が S の写し（作業場所 release/line-like-speed-batch3g-schedule の HEAD と同じ。`git rev-parse HEAD origin/main` で確かめた）で行を読んだ。実装の前に最新の origin/main で行を合わせ直す（§3(a)）。
- 読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/04-worktree.md・guards/05-pr.md・guards/10-executor.md・scripts/agent-hooks/cloud/rules.md（段 3 の 1〜6 回目のカードと同じ節。照合も同じ: 全命令は cd <W> で始める・出力は tail/head で上限・新しいファイルは丸ごとの全文・作業場所は new-worktree.sh で作り出力をパイプに通さない・PR は実行役が作らない・出力をファイルに残す命令と tail で読む命令は別の行）。
- 実行役はクラウドの Sonnet。作業場所の作り方はクラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）を正とする。.pr-number・gh-pr-create-safe.sh は使わない。出力には上限を付ける。待つために sleep を使わない。
- 状態: 第 2 版（2026-11-04 設計担当 Claude Opus）。第 1 版（652d969e9）はカード審査（クラウド Claude Opus）で REVISE: §4-A を当てると S :1237 の行で型の検査が落ちる（TS2367）。第 2 版で A9 を足して直し、A2 の行数と V3g-6 の今の文の書き方を直した。
- 受領確認: 実装役は着手の最初の報告に「段 3 の 7 回目のカード 第 2 版を受け取った・S=57fbceb04」と書く。

## 0. 設計からの直し・詳しくした点（V3g。設計の合格線は変えない）
- V3g-1 対象は予定表（/schedule・S frontend/src/pages/schedule/SchedulePageImpl.tsx）の 1 画面。基準の回（prod-ui-check run 41675927498・測った日時 2026-11-04 01:41:02 JST・main 57fbceb）で K1（戻った時の秒）0.30 秒・K2 0.3 秒・API 4 本・403 0・5xx 0。K1 が合格線 0.1 秒を超えている、測る利用者に見る権限がある最後の画面（design §3-4-19-a の 5 行のうち、/schedule 以外の 4 行は 403 の 3 画面と §3-4-21 で扱いを決める /admin/products/:id/edit）。
- V3g-2 今の読み方（S :921-1000 の useEffect）: 開いた時・表示の期間（rangeStart・rangeEnd、S :875-876）を変えた時・保存と削除の後（S :1075・:1086 の reloadTick）に、次の 3 本を Promise.allSettled でまとめて読み、そろうまで LoadingState（S :839-847）を出す。
  - `/calendar/owners`
  - `/calendar/events?start=${rangeStart.toISOString()}&end=${rangeEnd.toISOString()}`
  - `/shifts?date_from=${formatDayKey(rangeStart)}&date_to=${formatDayKey(rangeEnd)}`
  直した後は 3 本を useApiQuery で読む。path の文字は今と同じ（通信は変わらない）。rangeStart・rangeEnd は日の始まりにそろえた値（S schedule-utils.ts:147-157）なので、同じ期間なら同じ写しになる。
- V3g-3 同じ path は同じ写しを使う（同じ API の同じ答えを分けて持たない）: `/calendar/owners` は予定表の設定の画面（S ScheduleSettingsPage.tsx:42 の useApiQuery）と同じ 1 つの写しになる。予定表の設定の画面が書いた後の取り直し（S ScheduleSettingsPage.tsx:84 の invalidate(["calendar","owners"])）と、シフトの画面が書いた後の取り直し（S pages/shifts/ShiftsPage.tsx:30 の invalidate(["shifts"])）は、頭の言葉で予定表の写しも古い印にするので、予定表を開き直した時に新しい値になる。
- V3g-4 写しの置き場の部品（S frontend/src/lib/query/apiQuery.ts）は変えない。使うのは useApiQuery・useInvalidateApi だけ。QueryClient を足さない・staleTime を設定しない・写しをブラウザの保存に書かない。keepPrevious は使わない（前の期間の予定を新しい期間の枠に出さない。写しが無い期間に移った時は今と同じく LoadingState を出す）。
- V3g-5 読み込み中の印: LoadingState は「見本の状態でなく、3 本のどれかが写しの無い初回（isPending）」の時だけ出す。写しがあれば最初の描画から予定を出し、裏で 3 本を取り直す。見本の状態（?demoState=loading・empty、S :924-940）は今と同じ形にし、3 本を取りに行かない（enabled: false）。
- V3g-6 読めなかった時（今と同じにする所・変える所）:
  - 写しが無い時に 1 本が読めない: 今と同じく、その 1 本の分を空にして文を出さない（S :946-980 の allSettled）。
  - 写しを出したまま裏の取り直しが失敗した: 前の予定を出したまま、今ある言葉 schedule.errorFetch（S ja.json の schedule.errorFetch「予定の取得に失敗しました」）を今の誤りの場所（S :1239-1243 の .schedule-error）に出す（段 3 の 1〜6 回目の「前の中身を出したまま誤りの文を出す」と同じ）。今は取り直しが失敗すると予定が消えて文も出ないので、意図した変化。
  - 答えの形が違って予定を作れない: 今と同じく予定を空にし、誤りの文を出す（S :984-988 の catch）。今は誤りが Error ならその英語の文（err.message）をそのまま出し、そうでなければ schedule.errorFetch を出す。直した後はいつも schedule.errorFetch（日本語の決まった文）を出す（ADR-027 のとおり画面の文を t() にそろえる）。今は持ち主の一覧を前のまま残すが、直した後は持ち主の一覧も空にする（1 つの関数で作るため。形が違う答えは今は来ない）。
- V3g-7 保存・削除の後（書く path と中身は変えない）: 今は 3 本を取り直し、そのあいだ予定表全体が LoadingState に替わる（S :1075・:1086 → S :943 の setLoading(true)）。直した後は予定の写し（頭の言葉 ["calendar","events"]）だけを古い印にして取り直し、LoadingState は出さない（前の予定を出したまま、新しい予定が来たら描き直す）。持ち主（/calendar/owners）とシフト（/shifts）は予定の保存・削除で変わらない（別の表・別の API）ので取り直さない。GET が 2 本減る。保存・削除の失敗の文（common.saveError・common.deleteError）は今と同じ。
- V3g-8 表示する持ち主の初めの値（S :961 の「何も選んでいなければ自分を選ぶ」）: 直した後は、写しがあれば最初の描画から自分を選んだ状態で出す（useState の初めの値を写しから作る。全員の予定が一瞬出てから絞られる形にしない）。写しが無い時は今と同じく、持ち主の答えが来た後に自分を選ぶ。期間を変えた時も、何も選んでいなければ自分を選ぶ（今と同じ）。保存・削除の後に自分を選び直すことはしない（今は読み直しの後に選び直す。全部外して保存した時だけ違う）。
- V3g-9 保存・削除の失敗の文は、今は次の読み込みの始め（S :926・:935・:944 の setError(null)）で消える。直した後は、表示の期間か見本の状態を変えた時と、保存・削除が成功した時に消す（今と同じ時に消える。読み直しが無くなるため消す場所を移す）。
- V3g-10 測り方との関係: 予定表の LoadingState の印（.schedule-loading）は、毎朝の記録の読み込み中の印（S tests/prod-check/settle.ts:13 の LOADING_SELECTOR）に入っていない。K1 は「読み込み中の印が無く、開き終えた時と同じ構造（タグとクラス名）が描かれた最初のコマ」（S tests/prod-check/page-speed.spec.ts:357）で、LoadingState の構造は予定表の格子と違うので、今も直した後も LoadingState のあいだは合わない。tests/prod-check は触らない。
- V3g-11 今ある予定表の試験（S frontend/src/pages/schedule/SchedulePageImpl.test.tsx の 6 件）は既に写しを消している（S :68 の queryClient.clear）ので変えない。設計担当が S で `git grep -ln "SchedulePageImpl\|pages/schedule/SchedulePage" -- "frontend/src/*.test.tsx"` を流し、出たのはこの 1 本だけだった。
- V3g-12 api.ts の GET の送り直し（S frontend/src/lib/api.ts）は変えない。
- V3g-13 受入（§5 G5）は /schedule の K1 ≤0.1 秒・K2 ≤2 秒・403 と 5xx が 0 件。/schedule/settings・/shifts・/management-center/shifts（基準の回で K1 0.01 秒）が 0.1 秒以下のままかも並べて見る。K5 は段 3 の 1 回目の Q2・Q3 と、写しの名前に利用者が入る作りで確かめる（本番で 2 人のログインは使わない）。

## 1. 触るファイル（変更前→変更後）
| # | ファイル | 変更前 | 変更後 |
|---|---|---|---|
| 1 | frontend/src/pages/schedule/SchedulePageImpl.tsx | useState と useEffect で 3 本を読む（S :861-864・:870・:921-1000・:1075・:1086・:1239・:1241） | useApiQuery 3 本＋予定を作る関数（§4-A） |
| 2 | frontend/src/pages/schedule/SchedulePageCache.test.tsx | 無い | 新しく作る。R1〜R5（§4-L 全文） |
| 3 | docs/handoff/line-like-speed/batch3g-schedule-card.md | 無い | このカード（設計担当が書いた。実装役は触らない） |
| 4 | docs/handoff/line-like-speed/design.md | §3-4-20 まで | §3-4-20-a（シフトの直しの受入）と §3-4-21（このカードの場所と基準）を書き足し済み（設計担当。実装役は触らない） |
| 5 | .claude-pipeline/active-work.d/release-line-like-speed-batch3g-schedule.md | 無い | 作業の札（設計担当。実装役は触らない・commit しない） |

## 2. 触らない範囲
- backend/・migrations/・.github/workflows/・scripts/・tests/prod-check/・frontend/viewer/ は触らない（design §3-3）。
- frontend/src/lib/api.ts・frontend/src/contexts/・frontend/src/lib/auth/・frontend/src/lib/query/（apiQuery.ts・useSeededForm.ts・QueryAuthSync.tsx・試験を含む全部）・frontend/src/App.tsx・frontend/src/hooks/・frontend/src/mocks/ は触らない。
- frontend/src/pages/schedule/ の SchedulePageImpl.tsx 以外（schedule-utils.ts・schedule-owner.ts・ScheduleSettingsPage.tsx・SchedulePage.tsx・SchedulePageImpl.test.tsx・Schedule.stories.tsx）と frontend/src/pages/shifts/ は触らない。
- frontend/src/components/・CSS（schedule.css を含む）・ja.json・en.json は触らない。新しい言葉・色・寸法を足さない（使う言葉 schedule.errorFetch は今ある）。
- 予定表の中の、書き方（post・patch・delete の path と中身、S :1046-1090）・Google カレンダーの接続（S :855-856・:888-918）・格子と月の表・持ち主の欄・ポップオーバー・見本の状態の分かれ道の見た目は変えない。変えるのは §4 に書いた行だけ。
- QueryClient を作らない（試験の中でも作らない）。staleTime を設定しない。写しをブラウザの保存に書かない。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) 最新の origin/main で `git diff --stat 57fbceb0494b2b8b22f647986fb2a81c6084ba5f origin/main -- frontend/src | tail -12` が空か。§1 #1 か frontend/src/pages/schedule/・frontend/src/lib/query/apiQuery.ts が変わっていたら停止して報告する。ほかのファイルだけなら、変わったファイルの名前と行数を報告に書いて続ける。
- (b) `cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json` が `"5.104.4"` の 1 行。違えば停止して報告する。
- (c) §4 の「変更前」の文が、書かれた行にそのままあること。1 か所でも無い・2 か所以上ある時は、直さずに停止して BLOCKED: で `grep -n` の出力を報告する（2 か所あるとカードに書いた §4-A8 は除く）。
- (d) 手順 2 で、変える前の #1 の lint の警告の数を数えておく。変えた後は、その数より増えないこと（0 になってもよい）。増えたら直す。直せない時は停止する。
- (e) R1〜R5・今ある試験のどれかが落ちたら、試験を書き換えて通さない。画面の §4 の写し違いを探し、写し違いが無ければ停止して NEEDS_DECISION: で生の出力を返す。
- (f) 今ある試験との関係（変わらない見込み。違った時は試験を変えずに停止して NEEDS_DECISION: で生の出力を返す）:
  - SchedulePageImpl.test.tsx は api を差し替え（S :19-44）、/shifts の答えは既定の `[]`（S :41）。3 本とも useApiQuery で同じ答えを読むので、出る予定は今と同じ。
  - 同じ試験の「ほかの人の予定を直す時に共有の切り替えを出さない」（S :146-161）は、持ち主の答えの後に自分（user_id 101）が選ばれ（§4-A6 の useEffect）、試験が「Owner Other」の欄を押して 202 を足す。今と同じ順。
  - 同じ試験の保存の 2 件（S :117-144）は post・patch の中身だけを見るので、保存の後の取り直しの数が変わっても変わらない。
- (g) api の import は残す（書くのと Google カレンダーの接続で使う: S :1062-1088 の patch・post・delete と S :906 の get）。useEffect・useMemo・useRef・useState の import も残す（S :9）。normalizeEvent・normalizeShift・normalizeOwner・formatDayKey と型 ApiCalendarEvent・ApiShift・ApiCalendarOwnersResponse・CalendarOwner・ScheduleItem の import は §4-A2・A4 で使うので残す。

## 4-A. #1 frontend/src/pages/schedule/SchedulePageImpl.tsx
- A1 S :24 `import { useApiQuery } from "../../lib/query/apiQuery";` → `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";`
- A2 S :847 `}`（LoadingState の終わり。§3(c) では :839-847 の LoadingState の塊の直後の `}` を見る）の次に、次の 36 行を足す（塊の 1 行目は空行）（:848 の空行と :849 の `export default function SchedulePage()` はそのまま）:
```ts

/** 持ち主の一覧から自分の印（user_id、無ければ staff_id）を返す。自分がいなければ null */
function selfOwnerKey(owners: CalendarOwner[]): number | null {
  const self = owners.find((owner) => owner.isSelf);
  return self ? self.userId ?? self.staffId : null;
}

/**
 * ADR-1054 段 3 の 7 回目: 3 本の写しから、持ち主と予定（カレンダーの予定とシフト）を作る。
 * 1 本が読めない時はその分を空にする（今の Promise.allSettled と同じ）。
 * 答えの形が違って作れない時は failed を立てる（今の catch と同じ）。
 */
function buildSchedule(
  ownersData: ApiCalendarOwnersResponse | undefined,
  eventsData: { events: ApiCalendarEvent[] } | undefined,
  shiftsData: ApiShift[] | undefined,
  t: (key: string) => string,
): { owners: CalendarOwner[]; events: ScheduleItem[]; failed: boolean } {
  try {
    const owners = ownersData ? ownersData.owners.map(normalizeOwner) : [];
    const selfUserId = owners.find((owner) => owner.isSelf)?.userId ?? null;
    const events: ScheduleItem[] = eventsData
      ? eventsData.events.map(normalizeEvent).map((item) => {
          const ownerUserId = item.ownerUserId ?? selfUserId;
          const owner = ownerUserId != null ? owners.find((entry) => entry.userId === ownerUserId) ?? null : null;
          return { ...item, ownerUserId, ownerName: item.ownerName ?? owner?.name ?? null };
        })
      : [];
    if (shiftsData) {
      events.push(...shiftsData.map((shift) => normalizeShift(shift, t)));
    }
    return { owners, events, failed: false };
  } catch {
    return { owners: [], events: [], failed: true };
  }
}
```
  （予定に持ち主を埋める所は S :966-978 と同じ。シフトは S :979-981 と同じ。）
- A3 S :861-864 の 4 行（events・owners・visibleOwnerIds・loading の useState）を消す（:865 の error の useState から残す）。
- A4 S :870 `  const [reloadTick, setReloadTick] = useState(0);` を消す（:871 の setNowTick は残す）。
- A5 S :876 `  const rangeEnd = useMemo(() => toRangeEnd(view, anchorDate), [view, anchorDate]);` の次に、次の 27 行を足す（:877 の currentMonth はそのまま）:
```ts
  // ADR-1054 段 3 の 7 回目: 3 本を写しの置き場で読む（path の文字は今と同じ）。見本の状態では取りに行かない。
  const live = demoState !== "loading" && demoState !== "empty";
  const ownersQ = useApiQuery<ApiCalendarOwnersResponse>("/calendar/owners", { enabled: live });
  const eventsQ = useApiQuery<{ events: ApiCalendarEvent[] }>(
    `/calendar/events?start=${rangeStart.toISOString()}&end=${rangeEnd.toISOString()}`,
    { enabled: live },
  );
  const shiftsQ = useApiQuery<ApiShift[]>(
    `/shifts?date_from=${formatDayKey(rangeStart)}&date_to=${formatDayKey(rangeEnd)}`,
    { enabled: live },
  );
  const invalidate = useInvalidateApi();
  const built = useMemo(
    () => (live ? buildSchedule(ownersQ.data, eventsQ.data, shiftsQ.data, t) : { owners: [], events: [], failed: false }),
    [live, ownersQ.data, eventsQ.data, shiftsQ.data, t],
  );
  const { owners, events } = built;
  // 写しが無い初回だけ読み込み中の印を出す（今と同じく 3 本がそろうまで）
  const loading = live && (ownersQ.isPending || eventsQ.isPending || shiftsQ.isPending);
  // 写しを出したまま裏の取り直しが失敗した時だけ、取れなかった文を出す（写しが無い時の失敗は今と同じく出さない）
  const staleFailed = [ownersQ, eventsQ, shiftsQ].some((q) => q.isError && q.data !== undefined);
  const shownError = error ?? (built.failed || staleFailed ? t("schedule.errorFetch") : null);
  const selfKey = selfOwnerKey(owners);
  // 写しがあれば最初の描画から自分を選ぶ（全員の予定が一瞬出てから絞られる形にしない）
  const [visibleOwnerIds, setVisibleOwnerIds] = useState<number[]>(() => (selfKey != null ? [selfKey] : []));
  // 期間・見本の状態を変えた時に前の保存・削除の失敗の文を消す（今は読み込みの始めに消していた）
  useEffect(() => { setError(null); }, [demoState, rangeStart, rangeEnd]);
```
- A6 S :921-1000（読み込みの useEffect の 80 行）を、次の 5 行に置き換える（:920 の空行と :1001 の空行はそのまま）:
```ts
  // 自分の印が分かった時と期間を変えた時に、何も選んでいなければ自分を選ぶ（今の読み込みの後と同じ）
  useEffect(() => {
    if (selfKey == null) return;
    setVisibleOwnerIds((current) => (current.length > 0 ? current : [selfKey]));
  }, [selfKey, rangeStart, rangeEnd]);
```
- A7 S :1075 と S :1086 の `      setReloadTick((value) => value + 1);`（同じ文が 2 か所）を、それぞれ次の 2 行に置き換える（:1074・:1085 の setPopover(null) はそのまま）:
```ts
      setError(null);
      void invalidate(["calendar", "events"]);
```
- A8 S :1239 `                {error && (` → `                {shownError && (`。S :1241 `                    {error}` → `                    {shownError}`。（§3(c) の 2 か所の例外ではない。どちらもファイルに 1 か所だけ。）
- A9 S :1237 `            {(loading || demoState === "loading") && demoState !== "empty" ? <LoadingState /> : (` → `            {loading || demoState === "loading" ? <LoadingState /> : (`（行頭の空白 12 個はそのまま）。訳: §4-A5 の loading は live（見本の empty でない）を含むので、TypeScript が後ろの `demoState !== "empty"` を「いつも true」と見て型の検査が落ちる（カード審査で TS2367 を確認）。empty の時は loading が false で demoState も "loading" でないので、動きは今と同じ。S :1046-1090 の保存・削除の残り・:1119 の visibleEvents・:1126-1132 の toggleOwner・:1134-1140 の canChangeVisibility・canEditSelected は変えない。
- A1〜A9 を当てた後、S の行番号はずれる。上から順に当てず、§3(c) の「変更前」の文で場所を探して当てる。

## 4-L. #2 frontend/src/pages/schedule/SchedulePageCache.test.tsx（新しく作る・全文）
```tsx
/**
 * ADR-1054 段 3 の 7 回目: 予定表の写し。
 * R1 戻った時に前の予定をすぐ出す（読み込み中の印を出さない）・裏で 3 本を取り直す。
 * R2 予定を保存した後は予定の写しだけを取り直す（読み込み中の印を出さない・持ち主とシフトは取り直さない）。
 * R3 写しを出したまま裏の取り直しが失敗したら、前の予定を出したまま取れなかった文を出す。写しが無い時の失敗は今と同じく文を出さない。
 * R4 見本の状態（demoState=empty）では 3 本を取りに行かない。
 * R5 前に見た週へ戻った時はすぐ出す。写しの無い週へ移った時は今と同じく読み込み中の印を出す。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { queryClient } from "../../lib/query/apiQuery";
import SchedulePage from "./SchedulePageImpl";

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: { uid: "user-a" } }),
}));

// mode: ok = 答える・hang = 3 本は返事を返さない・fail = 3 本は失敗する（権限など 3 本以外はいつも答える）
const answers = vi.hoisted(() => ({ mode: "ok" as "ok" | "hang" | "fail" }));

function todayAt(hour: number) {
  const d = new Date();
  d.setHours(hour, 0, 0, 0);
  return d.toISOString();
}

// 中身は SchedulePageImpl.test.tsx の答えと同じ形（schedule-owner.ts の ApiCalendarOwnersResponse・schedule-utils.ts の ApiCalendarEvent）
const OWNERS = {
  can_manage_others: false,
  current_staff_id: 7,
  current_user_id: 101,
  owners: [
    { staff_id: 7, user_id: 101, staff_code: "A01", name: "Owner Self", primary_email: null, color: null, is_visible: true, share_mode: "self", is_self: true },
  ],
};
const eventsAnswer = () => ({
  events: [{
    id: 1, user_id: 101, calendar_type: "shared", category: "meeting", title: "Cached Event",
    description: null, location: null, start_datetime: todayAt(10), end_datetime: todayAt(11),
    is_all_day: false, google_event_id: null, source: "app", sync_status: "synced",
    created_by_user_id: 101, created_at: null, updated_at: null, owner_name: null, created_by_name: null,
  }],
});
const isScheduleRead = (path: string) =>
  path === "/calendar/owners" || path.startsWith("/calendar/events?") || path.startsWith("/shifts?");

vi.mock("../../lib/api", () => ({
  api: {
    get: vi.fn(async (path: string) => {
      if (path === "/me/permissions") return { permissions: [], is_tenant_admin: false };
      if (isScheduleRead(path) && answers.mode === "hang") return new Promise<never>(() => {});
      if (isScheduleRead(path) && answers.mode === "fail") throw new Error("read failed");
      if (path === "/calendar/owners") return OWNERS;
      if (path.startsWith("/calendar/events?")) return eventsAnswer();
      if (path.startsWith("/shifts?")) return [];
      throw new Error(`Unexpected GET ${path}`);
    }),
    post: vi.fn(async () => ({})),
    patch: vi.fn(async () => ({})),
    put: vi.fn(async () => ({})),
    delete: vi.fn(async () => ({})),
  },
}));

import { api } from "../../lib/api";
const mockGet = vi.mocked(api.get);
const readsOf = (head: string) => mockGet.mock.calls.filter(([path]) => String(path).startsWith(head)).length;
const view = (url = "/schedule") => render(<MemoryRouter initialEntries={[url]}><SchedulePage /></MemoryRouter>);
const loadingMark = () => document.querySelector(".schedule-loading");

beforeEach(async () => {
  await i18n.changeLanguage("ja");
  answers.mode = "ok";
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  queryClient.clear();
});

describe("schedule revisit shows the copy first (R1)", () => {
  it("shows the previous events at once on revisit and refetches the three reads", async () => {
    const first = view();
    await screen.findByText("Cached Event");
    first.unmount();
    mockGet.mockClear();
    answers.mode = "hang";
    view();
    expect(screen.queryAllByText("Cached Event").length).toBeGreaterThan(0);
    expect(loadingMark()).toBeNull();
    await waitFor(() => expect(readsOf("/calendar/owners")).toBe(1));
    expect(readsOf("/calendar/events?")).toBe(1);
    expect(readsOf("/shifts?")).toBe(1);
  });
});

describe("schedule save refetches only the events (R2)", () => {
  it("refetches only the events after saving, without the loading mark", async () => {
    view();
    await screen.findByText("Cached Event");
    await waitFor(() => expect(readsOf("/shifts?")).toBe(1));
    mockGet.mockClear();
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("schedule.create") }));
    fireEvent.change(screen.getByPlaceholderText(i18n.t("schedule.eventTitle")), { target: { value: "New Event" } });
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    await waitFor(() => expect(readsOf("/calendar/events?")).toBe(1));
    expect(loadingMark()).toBeNull();
    expect(screen.queryAllByText("Cached Event").length).toBeGreaterThan(0);
    expect(readsOf("/calendar/owners")).toBe(0);
    expect(readsOf("/shifts?")).toBe(0);
  });
});

describe("schedule read failure (R3)", () => {
  it("keeps the previous events and shows the fetch error when the refetch fails", async () => {
    const first = view();
    await screen.findByText("Cached Event");
    first.unmount();
    answers.mode = "fail";
    view();
    expect(screen.queryAllByText("Cached Event").length).toBeGreaterThan(0);
    expect(await screen.findByText(i18n.t("schedule.errorFetch"))).toBeTruthy();
    expect(screen.queryAllByText("Cached Event").length).toBeGreaterThan(0);
  });

  it("shows the grid without the error text when the first read fails (as today)", async () => {
    answers.mode = "fail";
    const { container } = view();
    await waitFor(() => expect(container.querySelector(".schedule-main__surface")).not.toBeNull());
    expect(loadingMark()).toBeNull();
    expect(screen.queryByText(i18n.t("schedule.errorFetch"))).toBeNull();
  });
});

describe("schedule demo state (R4)", () => {
  it("does not read the three paths in the empty demo state", async () => {
    const { container } = view("/schedule?demoState=empty");
    await waitFor(() => expect(container.querySelector(".schedule-main__surface")).not.toBeNull());
    expect(readsOf("/calendar/owners") + readsOf("/calendar/events?") + readsOf("/shifts?")).toBe(0);
  });
});

describe("schedule period change (R5)", () => {
  it("shows the earlier week at once when going back, and the loading mark for an unread week", async () => {
    view();
    await screen.findByText("Cached Event");
    answers.mode = "hang";
    fireEvent.click(screen.getByRole("button", { name: i18n.t("schedule.nextPeriod") }));
    await waitFor(() => expect(loadingMark()).not.toBeNull());
    fireEvent.click(screen.getByRole("button", { name: i18n.t("schedule.prevPeriod") }));
    expect(loadingMark()).toBeNull();
    expect(screen.queryAllByText("Cached Event").length).toBeGreaterThan(0);
  });
});
```

## 4-M. 実装役の手順（1 手順 1 命令。<W> は手順1 で作られた作業場所の絶対パス）
手順1. クラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）どおり、作業場所を作り、push 済みの枝の先頭に合わせる（設計担当が §1 #3・#4 を push 済み）。
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/line-like-speed-batch3g-schedule
  （出力に出た作業場所の絶対パスを <W> として報告に書く。）
  cd <W> && git fetch origin release/line-like-speed-batch3g-schedule
  cd <W> && git switch -C release/line-like-speed-batch3g-schedule origin/release/line-like-speed-batch3g-schedule
  cd <W> && git rev-parse HEAD origin/release/line-like-speed-batch3g-schedule
  （2 行が同じことを確かめる。違えば停止して BLOCKED: で報告する。main は取り込まない。reset・rebase・force・merge・pull は使わない）
  cd <W> && ./scripts/dev/executor-preflight.sh > /tmp/b3g-preflight.txt 2>&1
  cd <W> && grep -n "FAIL" /tmp/b3g-preflight.txt | head -20
  cd <W> && grep -n "origin/main は存在" /tmp/b3g-preflight.txt | head -3
  （FAIL の行が次の 3 つのうちのどれかだけなら続ける: `GitHub API に到達不可` の 1 件・`gh auth switch --hostname github.com --user shingo-cc` の失敗の 1 件・その結果の `PREFLIGHT FAIL` の行。理由は段 3 の 1 回目のカード §4-M 手順1 と同じ。続ける時は `[OK]   origin/main は存在` の行があることを 2 つ目の grep で確かめ、無ければ停止する。ほかの FAIL が 1 件でもあれば停止し、BLOCKED: で grep の出力を報告する。）
  cd <W> && git fetch origin main
  cd <W> && git diff --stat 57fbceb0494b2b8b22f647986fb2a81c6084ba5f origin/main -- frontend/src | tail -12
  （§3(a) の確かめ。）
手順2. 依存を入れ、§3(b) を確かめ、変える前の lint の警告を数える。
  cd <W>/frontend && npm ci > /tmp/b3g-ci.txt 2>&1
  cd <W> && tail -5 /tmp/b3g-ci.txt
  cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json
  cd <W>/frontend && npx eslint src/pages/schedule/SchedulePageImpl.tsx > /tmp/b3g-lint-before.txt 2>&1
  cd <W> && tail -5 /tmp/b3g-lint-before.txt
手順3. §4-L の全文で #2 を作り、§4-A のとおり #1 を直す。直す前に、§4-A の「変更前」の文を `grep -n` で確かめる（§3(c)）。終わったら残りが無いことを確かめる。
  cd <W> && grep -nw "setEvents\|setOwners\|setLoading\|reloadTick\|setReloadTick\|cancelled\|allSettled" frontend/src/pages/schedule/SchedulePageImpl.tsx | head -20
  （0 行であること。出たら §4-A の写し違いを直す。）
  cd <W> && grep -c "api\.get" frontend/src/pages/schedule/SchedulePageImpl.tsx
  （1 であること。残るのは S :906 の Google カレンダーの接続の 1 か所。違えば `grep -n "api\.get"` の出力を報告に書いて停止する。）
  cd <W> && grep -n "useApiQuery<" frontend/src/pages/schedule/SchedulePageImpl.tsx | head -8
  （4 行であること: /google-calendar/status（S :855）と §4-A5 の 3 本。）
手順4. 型を作ってから試験を流す（新しい試験・今ある予定表の試験・全部の試験・型・lint）。作る型（frontend/src/api/generated/）は .gitignore で除かれるので commit に入らない。
  cd <W>/frontend && npm run generate:api-types > /tmp/b3g-gen.txt 2>&1
  cd <W> && tail -3 /tmp/b3g-gen.txt
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/pages/schedule > /tmp/b3g-schedule.txt 2>&1
  cd <W> && tail -30 /tmp/b3g-schedule.txt
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/lib/query > /tmp/b3g-unit.txt 2>&1
  cd <W> && tail -20 /tmp/b3g-unit.txt
  cd <W>/frontend && npm run test:unit > /tmp/b3g-unit-all.txt 2>&1
  cd <W> && tail -15 /tmp/b3g-unit-all.txt
  cd <W>/frontend && npx tsc --noEmit -p . > /tmp/b3g-tsc.txt 2>&1
  cd <W> && tail -20 /tmp/b3g-tsc.txt
  cd <W>/frontend && npx eslint src/pages/schedule/SchedulePageImpl.tsx src/pages/schedule/SchedulePageCache.test.tsx > /tmp/b3g-lint.txt 2>&1
  cd <W> && tail -20 /tmp/b3g-lint.txt
  （lint の警告が手順2 の数より増えていないこと・誤りが 0 であること。§3(d)。）
手順5. 本番と同じ形で組み立てられるか確かめる。
  cd <W>/frontend && npm run build > /tmp/b3g-build.txt 2>&1
  cd <W> && tail -15 /tmp/b3g-build.txt
手順6. 変わったファイルが §1 の #1・#2 だけか確かめ、書く path が変わっていないことを見る。
  cd <W> && git status --short | head -20
  cd <W> && git diff -w --stat origin/release/line-like-speed-batch3g-schedule | tail -8
  cd <W> && git diff -w origin/release/line-like-speed-batch3g-schedule -- frontend/src/pages/schedule/SchedulePageImpl.tsx | head -300
手順7. commit する。
  cd <W> && git add frontend/src/pages/schedule/SchedulePageImpl.tsx frontend/src/pages/schedule/SchedulePageCache.test.tsx
  cd <W> && git commit -m "feat: 予定表を写しを先に出して裏で取り直す形に（ADR-1054 段3の7回目）"
手順8. commit が在ることを確かめてから push する（--no-verify は使わない。push の前の検査が × なら直してから push。fast-forward でないと断られたら直さず BLOCKED:）。
  cd <W> && git log -3 --oneline
  cd <W> && git push -u origin release/line-like-speed-batch3g-schedule
手順9. 報告を返す。PR は作らない（設計担当が手元で作る）。報告の 1 つの発言は 600 文字以内にして、番号付きの発言に分ける。報告には手順ごとの tail の出力（生のまま）と、§3(a)〜(g) の結果を書く。

## 4. GO と承認・PO の操作
- PO の実装承認: 2026-11-03 PO「つぎを進める」（段 3 の残りの遅い画面を直す流れ）。予定表は 6 回目のカード（batch3f-card.md V3f-2）で 7 回目に分けると決め、前提のシフトの 500 の直し（PR #5092）が 2026-11-04 に受入済み（design §3-4-20-a）。ADR-1054 は Accepted。このカードの審査合格の後に、設計担当がクラウドの Sonnet へ渡す。
- 触るのは frontend の画面 1 個と試験と書類だけで、migrations・deploy.yml・本番 scripts を含まない（番号付き GO の要る危ない PR ではない）。main へのマージで本番の画面に出る（deploy.yml が main への push で動く）。マージは PO の委任に基づき設計担当（Claude Opus）が、マージ前の審査役の APPROVE と確認がすべて pass の後に行う。
- PO が操作することはない。

## 5. 受入（○×）
| # | 基準 | 検証方法 |
|---|---|---|
| G1 | R1〜R5（SchedulePageCache.test.tsx の 6 件）が合格。今ある予定表の試験（SchedulePageImpl.test.tsx の 6 件）と段 3 の 1〜6 回目の試験（src/lib/query の全部）も合格のまま | /tmp/b3g-schedule.txt・/tmp/b3g-unit.txt の最後と、PR の CI の unit-run が success |
| G2 | 全部の試験・型・lint・組み立てが通る | /tmp/b3g-unit-all.txt・b3g-tsc.txt・b3g-lint.txt・b3g-build.txt の最後と、PR の確認がすべて pass |
| G3 | 変わったのは §1 の #1〜#4 だけ（#5 は commit しない）。書く path と中身（post・patch・delete）は変わっていない | gh pr diff --name-only と git diff -w（§4-M 手順6） |
| G4 | QueryClient を作るのは apiQuery.ts の 1 か所だけ・staleTime を設定していない・写しをブラウザの保存に書かない・予定表の画面に 3 本を api.get で直に読む所が無い | `git grep -n "new QueryClient" -- frontend/src` が 1 行、`git grep -n "staleTime:" -- frontend/src` が 0 行、`git grep -n -i "persist" -- frontend/src/lib/query frontend/package.json` が 0 行、`git grep -n "api.get" -- frontend/src/pages/schedule/SchedulePageImpl.tsx` が 1 行（/google-calendar/connect/start） |
| G5 | マージの後、毎朝の画面の記録を手で 1 回動かし、/schedule で K1（戻った時の秒）≤0.1 秒、K2（初めて開く秒）≤2 秒、403・5xx が 0 件。/schedule/settings・/shifts・/management-center/shifts は K1 0.1 秒以下のまま。ほかの行は K2 の最大と 2 秒を超えた画面の数が、基準の回から悪化していない | prod-ui-check の実行の要約（設計担当。deploy.yml の終わりを待ってから `gh workflow run prod-ui-check.yml --ref main` を流し、要約の表を読む）。基準は下の表と design §3-4-21 |
| G6 | 取り直した後の中身が DB と一致（tenant 001）: 予定表に出る今週の予定の数が、本番 DB の tenant 001 の今週の予定とシフトの数と同じ | 設計担当が本番の読むだけの道（ADR-1024）で tenant 001 の今週の calendar_events とシフトの行を数える。画面は PO のログイン済みの Chrome（設計担当が操作）で読む。読めない時は「画面の値はまだ確かめていない」と記録し、backend を変えていないこと（G3）と R1 を根拠にする |
| G7 | マージの後、deploy が成功し、本番の予定表が開く | deploy.yml の実行の結論 success と時刻。本番 https://app.salesanchor.jp/schedule が開き、ブラウザの誤りの記録に TanStack 由来の誤りが無い（設計担当） |

G5 の基準（prod-ui-check run 41675927498・測った日時 2026-11-04 01:41:02 JST・main 57fbceb。4 行とも 403 0 件・5xx 0 件）:

| 行 | K2（秒） | API の数 | K1（秒） |
|---|---|---|---|
| /schedule | 0.3 | 4 | 0.30 |
| /schedule/settings | 0.3 | 2 | 0.01 |
| /shifts | 0.3 | 2 | 0.01 |
| /management-center/shifts | 0.2 | 2 | 0.01 |
