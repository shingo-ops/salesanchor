# 実装カード 便3: 作る小窓を Google の形に・表示切替を 1 つのボタンに（G3・G11）（2026-11-07）

- 設計: `docs/handoff/schedule-gcal-clone/design.md` §2（G3・G11）・§3.9（PO 2026-11-07「1」で便3〜便5 を順に進める承認）
- 土台: origin/main 37fa04f7b。ブランチ `release/schedule-gcal-create-bin3-impl`
- 成功条件: G3 ①〜④・G11（design.md §2）
- 対象 ADR: ADR-144（金型を使う）・ADR-067（トークン）・ADR-027（文言は t()）。ADR の改訂は無い
- 行番号はすべて origin/main 37fa04f7b の値。

## 0. 作業者への決まり

- このカードに書いたこと以外はしない。迷ったら止めて `NEEDS_DECISION:` で返す。
- 色・寸法の直書き禁止。css に足すのは §5 の 2 規則だけ。
- 画面の文字は `t()` だけ。新しい文言キーは `schedule.dateTimeLine` の 1 つだけ（§4）。
- 金型（`frontend/src/components/`）の中身は変えない。使うだけ。

## 1. 触るファイルと触らないファイル

触る:
| ファイル | 中身 |
|---|---|
| `frontend/src/pages/schedule/schedule-utils.ts` | 関数 `formatDraftDateLine` を足す（§2） |
| `frontend/src/constants/icons.tsx` | outline の絵 3 つを足し、`SCHEDULE_POPOVER_ICONS` に 3 つ足す（§3） |
| `frontend/src/locales/ja.json`・`en.json` | `schedule.moreOptions` を消し、`schedule.dateTimeLine` を足す（§4） |
| `frontend/src/pages/schedule.css` | `.schedule-view-switch*`（:57-90）と `.schedule-popover__more`（:516-518）を消し、1 規則を足す（§5） |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx` | 作る小窓（§6）・表示切替（§7） |
| `frontend/src/pages/schedule/SchedulePageImpl.test.tsx` | 試験を直す・足す（§8） |
| `frontend/src/pages/schedule/schedule-utils.test.ts` | `formatDraftDateLine` の試験（§8） |
| `.claude-pipeline/active-work.d/release-schedule-gcal-create-bin3-impl.md` | 台帳 |

触らない（変えたら差し戻し）:
- `frontend/src/components/` の全ファイル（Button・ContextMenu・TextField・Textarea・CalendarView・calendarView.utils）
- 詳しく見るとき（mode が detail）の中身（`SchedulePageImpl.tsx:309-341`）
- 日の一覧の小窓の札 `.schedule-popover__kicker`（`:693` で使う。css `:403` は残す）
- 保存・削除・Meet の処理、`createDraft`、裏側、移行、`.github/`、`scripts/`

## 2. schedule-utils.ts

先頭の import は今は無い。ファイルの 1 行目の前に足す:

```ts
import { formatMeridiem, formatTimeRange as formatEventTimeRange } from "../../components/calendarView.utils";
```

`combineDateTime`（:90-92）の後に足す:

```ts
type Translate = (key: string, opts?: Record<string, unknown>) => string;

/**
 * 作る小窓の日時の 1 行（design §3.9・G3 ②）。例「11月10日(火) 午前10時～午前11時」。
 * 日付が読めないときは空。終わりだけ読めないときは始まりだけ。
 */
export function formatDraftDateLine(
  value: { startDate: string; startTime: string; endDate: string; endTime: string; allDay: boolean },
  t: Translate,
  language: string,
): string {
  const day = (date: Date) =>
    new Intl.DateTimeFormat(language, { month: "long", day: "numeric", weekday: "short" }).format(date);
  const start = parseDateTime(value.startDate, value.allDay ? "00:00" : value.startTime);
  if (Number.isNaN(start.getTime())) return "";
  const end = parseDateTime(value.endDate, value.allDay ? "00:00" : value.endTime);
  const endValid = !Number.isNaN(end.getTime());
  if (value.allDay) {
    if (!endValid || value.endDate === value.startDate) {
      return t("schedule.dateTimeLine", { date: day(start), time: t("schedule.allDay") });
    }
    return t("calendarView.timeRange", { start: day(start), end: day(end) });
  }
  if (!endValid) return t("schedule.dateTimeLine", { date: day(start), time: formatMeridiem(start, t) });
  if (value.endDate === value.startDate) {
    return t("schedule.dateTimeLine", { date: day(start), time: formatEventTimeRange(start, end, t, false) });
  }
  return t("calendarView.timeRange", {
    start: t("schedule.dateTimeLine", { date: day(start), time: formatMeridiem(start, t) }),
    end: t("schedule.dateTimeLine", { date: day(end), time: formatMeridiem(end, t) }),
  });
}
```

想定分岐: 循環 import や lint の import 順の規則で止まったら、止めた規則名を書いて `NEEDS_DECISION:`。

## 3. icons.tsx

- outline の import（:56-86）の最後（`CheckCircleIcon as CheckCircleOutlineIcon,` の後）に足す:
  `ClockIcon as ClockOutlineIcon,` `MapPinIcon as MapPinOutlineIcon,` `Bars3BottomLeftIcon as Bars3BottomLeftOutlineIcon,`
- `const TrashOutline = hi(TrashOutlineIcon);`（:150）の後に足す:
  ```ts
  const ClockOutline        = hi(ClockOutlineIcon);
  const MapPinOutline       = hi(MapPinOutlineIcon);
  const Bars3BottomLeftOutline = hi(Bars3BottomLeftOutlineIcon);
  ```
- `SCHEDULE_POPOVER_ICONS`（:360-364）に足す:
  ```ts
  clock:       ClockOutline,           // ClockIcon outline — 日時の 1 行
  location:    MapPinOutline,          // MapPinIcon outline — 場所の 1 行
  description: Bars3BottomLeftOutline, // Bars3BottomLeftIcon outline — 説明の 1 行
  ```
想定分岐: 同じ名前の import が既にあって重なったら、既存の名前を使い、足さない。

## 4. 文言

- `frontend/src/locales/ja.json:3340` の `"moreOptions": "詳しく入れる",` を `"dateTimeLine": "{{date}} {{time}}",` に置き換える。
- `frontend/src/locales/en.json:3340` の `"moreOptions": "More options",` を `"dateTimeLine": "{{date}} {{time}}",` に置き換える。
- `schedule.addEvent` は小窓の札で使わなくなるが、消さない（今回の範囲の外。他の文言キーは触らない）。
- `moreOptions` は他で使っていない（`grep -rn moreOptions frontend/src` で locales 以外は `SchedulePageImpl.tsx:486` だけ）。

## 5. schedule.css

- `:57-90`（`.schedule-view-switch` から `.schedule-view-switch__button:focus { … }` まで）を消す。
- `:516-518`（`.schedule-popover__more { margin-right: auto; }`）を消し、同じ場所に足す:
  ```css
  /* 作る小窓の 1 行のボタン（日時・場所・説明）は左に寄せる（design §3.9） */
  .schedule-popover .schedule-popover__line {
    justify-content: flex-start;
  }

  /* 金型 Button は折り返さない（Button.css の white-space: nowrap）。長い文は小窓の幅で「…」にする */
  .schedule-popover__line-text {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  ```

## 6. SchedulePageImpl.tsx 作る小窓（SchedulePopover :213-515）

6-0. 位置決めの関数 `usePopoverPlacement`（:146-182）:
- 小窓は最初の描画で `visibility: hidden` にして測ってから見せる（:176-178）。隠れている間は `autoFocus` が効かない（審査 1 回目 H1・Chromium で再現）。そこで「見えたか」を返す。
- `:142-145` のコメントの「（「詳しく入れる」など）」を「（場所・説明の欄を開いたときなど）」に変える。
- `:181` `return { ref, style };` → `return { ref, style, placed: pos !== null };`
- `:687` の `const { ref, style } = usePopoverPlacement(anchor);` は変えない（`placed` を使わない）。

6-1. import:
- `:9` は今のまま（`useState` は既にある）。
- `:13` の後に `import { ContextMenu } from "../../components/ContextMenu";` を足す（§7 で使う）。
- `:29-58` の schedule-utils の import に `formatDraftDateLine,` を足す（`formatDayLabel,` の後）。

6-2. 関数の頭（:239-245）:
- `:239` `const { t } = useTranslation();` → `const { t, i18n } = useTranslation();`
- `:242` の後に足す:
  ```tsx
  const ClockIcon = SCHEDULE_POPOVER_ICONS.clock;
  const LocationIcon = SCHEDULE_POPOVER_ICONS.location;
  const DescriptionIcon = SCHEDULE_POPOVER_ICONS.description;
  const creating = mode === "create";
  ```
- `:244` `const { ref: popoverRef, style: position } = usePopoverPlacement(anchor);` → `const { ref: popoverRef, style: position, placed } = usePopoverPlacement(anchor);`
- `:245` `const [expanded, setExpanded] = useState(mode !== "create");` を消し、次に置き換える:
  ```tsx
  // 作るときは日時・場所・説明を 1 行で閉じて出し、押すと開く（design §3.9・G3 ②③）
  const [dateOpen, setDateOpen] = useState(false);
  const [locationOpen, setLocationOpen] = useState(false);
  const [descriptionOpen, setDescriptionOpen] = useState(false);
  const showDate = !creating || dateOpen;
  const showLocation = !creating || locationOpen || draft.location !== "";
  const showDescription = !creating || descriptionOpen || draft.description !== "";
  // 作るときは、小窓が見えてから題名の欄に文字が入るようにする（隠れている間の autoFocus は効かない・G3 ①）
  const titleRef = useRef<HTMLInputElement | null>(null);
  useEffect(() => {
    if (creating && placed) titleRef.current?.focus();
  }, [creating, placed]);
  ```
  （`useRef`・`useEffect` は `:9` で既に import 済み。`draft.location`・`draft.description` は文字の型で、`createDraft`（:109-）が `""` を入れる。違ったら `NEEDS_DECISION:`）

6-3. 上の帯（:267-279 の `schedule-popover__header-meta` の中）: 札 2 つを作るとき以外だけ出す。
```tsx
<div className="schedule-popover__header-meta">
  {!creating && (
    <span className="schedule-popover__kicker">
      {mode === "edit" ? t("schedule.editEvent") : t("schedule.eventDetail")}
    </span>
  )}
  {!creating && meta && (
    <span … 今のまま … >
      {t(meta.labelKey)}
    </span>
  )}
</div>
```
（`:266` の外の div と `:280-306` の右のボタンは変えない）

6-4. 入力の並び（:338-479 の `schedule-popover__body--form` の中）を次の順にする。各部品の中身は「今の何行目のまま」と書いた所はそのまま移す。
1. 題名（:339-346）:
   ```tsx
   <label className="schedule-field">
     {!creating && <span className="schedule-field__label">{t("schedule.eventTitle")}</span>}
     <TextFieldControl
       variant="schedule"
       value={draft.title}
       onChange={(event) => onDraftChange({ ...draft, title: event.target.value })}
       placeholder={t("schedule.eventTitle")}
       aria-label={t("schedule.eventTitle")}
       ref={titleRef}
     />
   </label>
   ```
   （題名には `autoFocus` を付けない。focus は 6-2 の `useEffect` が入れる）
2. 日時:
   ```tsx
   {showDate ? (
     <>
       {/* 終日の切り替え（:371-383 のまま） */}
       {/* 始まりの組（:409-430 のまま） */}
       {/* 終わりの組（:432-453 のまま） */}
     </>
   ) : (
     <Button
       variant="ghost"
       size="sm"
       fullWidth
       layoutClassName="schedule-popover__line"
       onClick={() => setDateOpen(true)}
     >
       <ClockIcon size={18} aria-hidden="true" />
       <span className="schedule-popover__line-text">{formatDraftDateLine(draft, t, i18n.language)}</span>
     </Button>
   )}
   ```
3. 種類（:348-369 のまま）
4. `{joinMeetLink}` と Meet の切り替え（:385-395 のまま）
5. 共有の切り替え（:397-406 のまま）
6. 場所:
   ```tsx
   {showLocation ? (
     <label className="schedule-field">
       <span className="schedule-field__label">{t("schedule.eventLocation")}</span>
       <TextFieldControl
         variant="schedule"
         value={draft.location}
         onChange={(event) => onDraftChange({ ...draft, location: event.target.value })}
         placeholder={t("schedule.locationPlaceholder")}
         autoFocus={locationOpen}
       />
     </label>
   ) : (
     <Button variant="ghost" size="sm" fullWidth layoutClassName="schedule-popover__line" onClick={() => setLocationOpen(true)}>
       <LocationIcon size={18} aria-hidden="true" />
       <span className="schedule-popover__line-text">{t("schedule.locationPlaceholder")}</span>
     </Button>
   )}
   ```
   （`autoFocus={locationOpen}`: 1 行を押して開いたときだけ欄に文字が入る。小窓はもう見えているので効く。最初から値があって開いている形では題名から focus を奪わない）
7. 説明: 6 と同じ形。欄は今の `TextareaControl`（:466-474、`rows={4}`）に `autoFocus={descriptionOpen}` を足す。閉じた形は `DescriptionIcon` と `<span className="schedule-popover__line-text">{t("schedule.descriptionPlaceholder")}</span>`、押すと `setDescriptionOpen(true)`。
- `{expanded && ( … )}`（:455-477）は 6・7 に置き換わるので消す。

6-5. 下の帯（:482-489）: `{mode === "create" && !expanded && ( <span className="schedule-popover__more"> … </span> )}` を消す。保存・取消（:490-511）は変えない。

想定分岐:
- `autoFocus` を lint（jsx-a11y/no-autofocus など）が止めたら、止めた規則名を書いて `NEEDS_DECISION:`（規則を切らない）。
- `Button` が子に絵と文字を並べられない（型で止まる）なら `NEEDS_DECISION:`。
- 金型 Button は折り返さない（`white-space: nowrap`）。長い文は §5 の `.schedule-popover__line-text` で末尾が「…」になる。2 行にはならない。
- 金型 Button の中で `<span>` が「…」にならない（はみ出す）ときは、Button.css を変えずに `NEEDS_DECISION:`。

## 7. SchedulePageImpl.tsx 表示切替（:1229-1345）

7-1. 状態: `:892` `const [shortcutsOpen, …]` の後に足す:
```tsx
// 表示切替の一覧（金型 ContextMenu・design §3.9・G11）。開いている間は文字の近道を効かせない
const [viewMenu, setViewMenu] = useState<{ x: number; y: number } | null>(null);
```

7-2. 近道（:1236-1243）:
```tsx
const windowOpen = popover !== null || dayList !== null || viewMenu !== null;
// 3. Esc は入力欄の中でも小窓を閉じる
if (event.key === "Escape") {
  if (windowOpen) {
    setPopover(null);
    setDayList(null);
    setViewMenu(null);
  }
  return;
}
```
（金型 ContextMenu は Esc を document で受けて止めるので、一覧が開いているときの Esc は金型が閉じる。上の `setViewMenu(null)` は念のため）

7-3. ボタン（:1332-1345 の `<div className="schedule-view-switch" …> … </div>` を置き換える）:
```tsx
<Button
  variant="secondary"
  size="md"
  aria-haspopup="menu"
  aria-expanded={viewMenu !== null}
  onMouseDown={(event) => {
    // 金型 ContextMenu は document の mousedown で「外を押した」と見て閉じる（ContextMenu.tsx:141）。
    // 開いているときにこのボタンを押すと、閉じた直後の click で開き直してしまう（審査 1 回目 M1・Chromium で再現）。
    // 開いているときだけ、ボタンの mousedown を document に届けない。閉じるのは下の onClick が行う
    if (viewMenu !== null) event.stopPropagation();
  }}
  onClick={(event) => {
    const rect = event.currentTarget.getBoundingClientRect();
    setViewMenu((open) => (open ? null : { x: rect.left, y: rect.bottom }));
  }}
>
  {t(`schedule.${view}View`)}
  <NAV_ICONS.chevronDown size={16} aria-hidden="true" />
</Button>
<ContextMenu
  open={viewMenu !== null}
  onClose={() => setViewMenu(null)}
  anchor={viewMenu}
  ariaLabel={t("schedule.viewSelect")}
  items={(["day", "week", "month", "list"] as const).map((nextView) => ({
    key: nextView,
    label: t(`schedule.${nextView}View`),
    onSelect: () => setView(nextView),
  }))}
/>
```
想定分岐:
- `NAV_ICONS.chevronDown` を JSX で直接書けず型で止まったら、`const ChevronDownIcon = NAV_ICONS.chevronDown;` を関数の中に置いて使う。
- `Button` が `onMouseDown` を受けない（型で止まる）なら `NEEDS_DECISION:`（金型は変えない）。

## 8. 試験

試験の 2 ファイルとも、答えの日本語を直接書く。commit 前の検査（lint-staged・`eslint --max-warnings=0`・規則 `local/no-japanese-literal`）で止まらないよう、両ファイルの 1 行目に次の 1 行を足す（先例 `frontend/src/components/CalendarView.test.tsx:1`・審査 1 回目 M2）:
```ts
/* eslint-disable local/no-japanese-literal -- テスト: 作る小窓の日時の 1 行が Google と同じ日本語で出ることを検証する（ADR-027・precedent: CalendarView.test.tsx） */
```

`frontend/src/pages/schedule/schedule-utils.test.ts`（`const t = i18n.getFixedT("ja");` の形は `:27` と同じ）:
`describe("formatDraftDateLine", …)` に次の 7 つ。`d = { startDate: "2026-11-10", startTime: "10:00", endDate: "2026-11-10", endTime: "11:00", allDay: false }` を元に変える:
| 入力 | 答え |
|---|---|
| d | `11月10日(火) 午前10時～午前11時` |
| startTime "12:30"・endTime "13:30" | `11月10日(火) 午後12:30～午後1:30` |
| allDay true | `11月10日(火) 終日` |
| allDay true・endDate "2026-11-12" | `11月10日(火)～11月12日(木)` |
| startTime "23:00"・endDate "2026-11-11"・endTime "01:00" | `11月10日(火) 午後11時～11月11日(水) 午前1時` |
| startTime "" | `` （空） |
| endTime "" | `11月10日(火) 午前10時` |
言語は `"ja"` を渡す。

`frontend/src/pages/schedule/SchedulePageImpl.test.tsx`:
- `:246-247` の `pressed` を次にする（表示切替のボタンの文字が今の表示の名前か）。ボタンが無いときは試験を落とす（「無いから false」で効かない試験が通ってしまうのを防ぐ・審査 1 回目の指摘）:
  ```tsx
  const viewSwitch = () => {
    const el = document.querySelector('button[aria-haspopup="menu"]');
    if (!el) throw new Error("view switch button is missing");
    return el;
  };
  const pressed = (name: string) => viewSwitch().textContent === name;
  ```
  （この画面で `aria-haspopup` を持つボタンは表示切替の 1 つだけ。37fa04f7b の `frontend/src/pages/schedule/` に `aria-haspopup` は 0 件）
- 「効かない」試験 2 つ（:384-390「popover が開いている」・:392-399「近道の一覧が開いている」）は、`expect(pressed(i18n.t("schedule.monthView"))).toBe(false);` の後に `expect(pressed(i18n.t("schedule.weekView"))).toBe(true);` を足す（今の表示が週のまま残っていることを見る）。
- T1（:539-550）: `selectRange` の後に日時の 1 行を押してから欄を読む。1 行の文も見る:
  ```tsx
  const line = await screen.findByRole("button", { name: new RegExp(lineText) });
  fireEvent.click(line);
  ```
  `it.each` の表に 4 つ目の値として `"午前10時～午前11時"`・`"午前4時～午前5時"`・`"午後3時～午後4時"` を足す（`lineText`）。
- T3（:565-574）: `selectRange` の後に `fireEvent.click(await screen.findByRole("button", { name: /午前7時～午前8時/ }));` を足してから欄を読む。
- T4（:576-585）: `selectRange` の後に `fireEvent.click(await screen.findByRole("button", { name: /11月10日\(火\)～11月12日\(木\)/ }));` を足してから切り替えと日付を読む。
- 足す（`describe("SchedulePage on CalendarView")` の中）。名前は既存の T1〜T9 と重ならないよう C1〜C4 にする:
  - C1: 範囲を選ぶと題名の欄に文字が入る: `await waitFor(() => expect(document.activeElement).toBe(screen.getByPlaceholderText(i18n.t("schedule.eventTitle"))))`。札「予定を追加」は出ない（`queryByText(i18n.t("schedule.addEvent"))` が null）。
    - 注意: 試験の環境（jsdom）は `visibility: hidden` を見ないので、この試験だけでは H1（隠れている間の autoFocus）を見つけられない。H1 は本番の Chrome で G3 ① として確かめる（Opus が行う）。
  - C2: 作る小窓では `queryByPlaceholderText(i18n.t("schedule.locationPlaceholder"))` が null で、ボタン「場所を追加」がある。押すと欄が出て、その欄に文字が入る（activeElement）。説明も同じ（`descriptionPlaceholder`）。
  - C3: 表示切替のボタン（文字「週」）を押すと `role="menu"` が出て `menuitem` が 4 つ。「月」を押すと `calendarProps.current?.mode` が `"month"` になり、menu が消える。
  - C4: 表示切替を開いたまま `d` を押しても表示は変わらない（`calendarProps.current?.mode` が `"week"` のまま・ボタンの文字は「週」のまま）。続けて Esc で menu を閉じ、もう一度 `d` を押すと `"day"` になる（近道そのものは生きていることを見る）。
- 文字は `i18n.t(...)` で取る（ja が既定の試験の作り）。日本語を直接書いた正規表現は、`it.each` の答えと T3・T4 だけ（答えの文そのものを見るため）。

想定分岐:
- 近道の試験（:297-397）で `pressed` の変更だけで通らない所があったら、どの試験がなぜ落ちたかを書いて `NEEDS_DECISION:`。
- Meet の試験（K12・:400 以降）が日時の 1 行で落ちたら、同じく `NEEDS_DECISION:`（Meet の切り替えは閉じた形でも出るので、落ちない見込み）。

## 9. 回すもの（クラウドの作業場所で）

```
cd frontend
npm ci
npx vitest run src/pages/schedule
npm run check:all
npx tsc --noEmit
npm run lint
npm run build
```
直書き検査: `git diff origin/main -- frontend/src/pages/schedule.css | grep '^+' | grep -E '#[0-9a-fA-F]{3,8}|[0-9]+px'` が空。

## 10. PR

- `gh auth status` で `shingo-cc` を確かめてから `gh pr create --base main --head release/schedule-gcal-create-bin3-impl`（Draft にしない・移行や deploy は無い）。
- 本文はリポジトリの PR のひな形から作る。`### 標準ワークフロー確認`: recon・設計 = `docs/handoff/schedule-gcal-clone/`、対象 ADR: ADR-144・ADR-067・ADR-027（改訂なし）、触るファイル（§1 の表）、削除するファイル: なし、PO 承認: 2026-11-07「1」、Opus 審査記録: design.md §9。
- PR を作ったら URL を返して終わる。CI の完了は待たない。マージしない。

## 11. 返す物

- `DONE: <PR の URL>` と、§9 の実行結果（生の最後の 20 行）。
- 止めたときは `BLOCKED:` か `NEEDS_DECISION:` と理由。
