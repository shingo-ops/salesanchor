# 実装カード 便6: 予定の画面の見た目 5 か所（G15〜G19）（2026-11-07）

- 設計: `docs/handoff/schedule-gcal-clone/design.md` §2.1・§3.8（PO 承認 2026-11-07「１，」・5 回目の審査 APPROVE）
- 土台: origin/main 170ff9612（9cf750f29 から金型・tokens.css・予定の画面・ADR-1065 は変わっていない＝`git diff --stat 9cf750f29 170ff9612 -- frontend/src/components/ frontend/src/tokens.css frontend/src/pages/schedule/` が空）。ブランチ `release/schedule-gcal-look-bin6`
- 成功条件: G15・G16・G17・G18・G19（design.md §2.1）
- 対象 ADR: ADR-1065（金型・What 7 を足す）・ADR-067（トークン）・ADR-144（金型を使う）・ADR-027（文言は t()）
- 行番号はすべて origin/main 170ff9612 の値。

## 0. 作業者への決まり

- このカードに書いたこと以外はしない。迷ったら止めて `NEEDS_DECISION:` で返す。
- 作業は必ず `bash scripts/new-worktree.sh release/schedule-gcal-look-bin6 --claude` で作った作業場所の中で行う（作業場所の外の commit は見張りが止める）。
- 色・寸法の直書き禁止。css の値は `var()`・`calc()`・`%`・`transparent`・`0`・`none`・`top` だけ。新しい寸法はトークン（§4）だけ。
- 画面の文字は `t()` だけ。今回は新しい文言キーは無い（曜日は `Intl`、時刻は既存の `calendarView.am/pm/clockHour`）。
- 試験は Mac で回さない。クラウドの作業場所で回す（`cd frontend && npx vitest run src/components/CalendarView.test.tsx`・`npx tsc --noEmit`・`npm run lint`）。

## 1. 触るファイルと触らないファイル

触る:
| ファイル | 中身 |
|---|---|
| `frontend/src/components/calendarView.utils.ts` | 口の型 `appearance` を足す。関数 `formatWeekdayShort`・`formatSlotLabel` を足す（§2） |
| `frontend/src/components/CalendarView.tsx` | `appearance` を受け、包みの class と days の 3 つの設定を変える（§3） |
| `frontend/src/components/CalendarView.css` | 末尾に `appearance="schedule"` の見た目を足す（§5） |
| `frontend/src/tokens.css` | トークン 2 つを足す（§4） |
| `frontend/src/components/CalendarView.test.tsx` | 試験を足す・`:125` を分ける（§6） |
| `frontend/src/components/CalendarView.stories.tsx` | 見本を 1 つ足す（§7） |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx` | `:1392` の `<CalendarView` に `appearance="schedule"` を 1 行足すだけ |
| `docs/adr/ADR-1065-calendar-view-component-fullcalendar-v6.md` | What 7・Why 1 行・設計・根拠の欄（§8） |
| `docs/adr/README.md` | `node scripts/generate-adr-index.js` で作り直す（手で書かない） |
| .claude-pipeline/active-work.d/release-schedule-gcal-look-bin6.md | 台帳（new-worktree.sh が作る形のまま・状態を更新） |

触らない（変えたら差し戻し）:
- `frontend/src/pages/schedule.css`・`frontend/src/pages/schedule/SchedulePageImpl.tsx` の `:1392` 以外（見た目は金型の css だけに書く）
- 既存の css の規則（`CalendarView.css:1-178`）。足すのは末尾だけ
- 月の表示（`monthProps`・`frontend/src/components/CalendarView.tsx:180-202`）
- T4（`--fc-*` を全部置き換える試験）
- 移行（migrations）・`.github/workflows/deploy.yml`・`scripts/`・backend

## 2. calendarView.utils.ts

### 2-1 口の型
`CalendarViewProps` の `className?: string;`（`:87` 付近・`ariaLabel` の次）の前に足す:

```ts
  /** 見た目の型。'plain'（既定）は今の形。'schedule' は予定の画面の形（ADR-1065 What 7・design §3.8） */
  appearance?: 'plain' | 'schedule';
```

### 2-2 関数（`formatMeridiem`（`:194`）の後に足す）

```ts
/** 曜日の短い名前（ja「日」・en「Sun」）。日付の帯の上の段（design §3.8・G15） */
export function formatWeekdayShort(date: Date, language: string): string {
  return new Intl.DateTimeFormat(language, { weekday: 'short' }).format(date);
}

/**
 * 時刻の目盛りの文字。0 時 0 分だけ空にする（Google と同じ・G18）。
 * meridiem は formatMeridiem、h24 は FullCalendar が作った文字（text）をそのまま使う。
 */
export function formatSlotLabel(
  date: Date,
  text: string,
  t: Translate,
  timeStyle: 'h24' | 'meridiem',
): string {
  if (date.getHours() === 0 && date.getMinutes() === 0) return '';
  return timeStyle === 'meridiem' ? formatMeridiem(date, t) : text;
}
```

## 3. CalendarView.tsx

- 分解（`:45-68`）に `appearance = 'plain',` を足す（`className,` の前）。
- import（calendarView.utils から）に `formatSlotLabel`・`formatWeekdayShort` を足す。
- `const isSchedule = appearance === 'schedule';` を `wrapperClass` の前に足す。
- `wrapperClass`（`:154-161`）の `` `comp-calendar--${mode}`, `` の次に `isSchedule ? 'comp-calendar--schedule' : null,` を足す。
- `daysProps`（`:164-179`）を次の形にする（他の行は変えない）:

変更前:
```tsx
    slotEventOverlap: false,
    ...
    ...(timeStyle === 'meridiem'
      ? { slotLabelContent: (arg: { date: Date }) => formatMeridiem(arg.date, t) }
      : {}),
```
変更後:
```tsx
    slotEventOverlap: isSchedule,
    ...
    ...(isSchedule
      ? {
          slotLabelContent: (arg: { date: Date; text: string }) =>
            formatSlotLabel(arg.date, arg.text, t, timeStyle),
          dayHeaderContent: (arg: { date: Date; isToday: boolean }) => (
            <span className="comp-calendar__day-head">
              <span className="comp-calendar__dayname">
                {formatWeekdayShort(arg.date, i18n.language ?? 'en')}
              </span>
              <span
                className={
                  arg.isToday
                    ? 'comp-calendar__daynum comp-calendar__daynum--today'
                    : 'comp-calendar__daynum'
                }
              >
                {arg.date.getDate()}
              </span>
            </span>
          ),
        }
      : timeStyle === 'meridiem'
        ? { slotLabelContent: (arg: { date: Date }) => formatMeridiem(arg.date, t) }
        : {}),
```
- `formatMeridiem` の import は残す（`'plain'` の枝で使う）。
- 引数の形の根拠: `slotLabelContent` は `{level, time, date, view, text}`（FullCalendar timegrid 6.1.22）、`dayHeaderContent` は `{date, view, text, isToday, ...}`（core 6.1.22 internal-common.js:6227）。

## 4. tokens.css

`--schedule-gridline-w: 1px;`（`:422`）の並びの後（`:424` の次）に足す:

```css
  --schedule-now-line-w: 2px;     /* 今の時刻の線の太さ（G16） */
  --schedule-now-dot-size: 12px;  /* 今の時刻の丸の直径（G16） */
```
色ではないので暗い表示（`:640` 以降）には足さない。

## 5. CalendarView.css（末尾に足す）

```css
/* ---- 予定の画面の見た目（appearance="schedule"・時間割だけ・ADR-1065 What 7・design §3.8） ---- */
.comp-calendar--schedule.comp-calendar--days {
  --fc-today-bg-color: transparent;
}

.comp-calendar--schedule.comp-calendar--days .fc-col-header-cell {
  font-weight: var(--font-weight-normal);
}

.comp-calendar--schedule.comp-calendar--days .comp-calendar__day-head {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) 0;
}

.comp-calendar--schedule.comp-calendar--days .comp-calendar__dayname {
  font-size: var(--font-2xs);
  font-weight: var(--font-weight-medium);
  color: var(--schedule-hour-label);
}

.comp-calendar--schedule.comp-calendar--days .fc-day-today .comp-calendar__dayname {
  color: var(--schedule-today);
}

.comp-calendar--schedule.comp-calendar--days .comp-calendar__daynum {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--schedule-mini-size);
  height: var(--schedule-mini-size);
  border-radius: var(--radius-full);
  font-size: var(--schedule-day-num-size);
  color: var(--text-primary);
}

.comp-calendar--schedule.comp-calendar--days .comp-calendar__daynum--today {
  background: var(--schedule-today);
  color: var(--on-solid);
}

.comp-calendar--schedule.comp-calendar--days .fc-timegrid-now-indicator-line {
  border-top-width: var(--schedule-now-line-w);
}

.comp-calendar--schedule.comp-calendar--days .fc-timegrid-now-indicator-line::before {
  content: '';
  position: absolute;
  left: 0;
  top: calc((var(--schedule-now-dot-size) + var(--schedule-now-line-w)) / -2);
  width: var(--schedule-now-dot-size);
  height: var(--schedule-now-dot-size);
  border-radius: var(--radius-full);
  background: var(--schedule-now-line);
  transform: translateX(-50%);
}

.comp-calendar--schedule.comp-calendar--days .fc-timegrid-now-indicator-arrow {
  display: none;
}

.comp-calendar--schedule.comp-calendar--days .fc-timegrid-col-events {
  margin-right: var(--space-3);
}

.comp-calendar--schedule.comp-calendar--days .comp-calendar__event:not(.comp-calendar__event--line-dashed) {
  --fc-event-border-color: var(--fc-event-bg-color);
}

.comp-calendar--schedule.comp-calendar--days .fc-timegrid-event {
  font-size: var(--font-xs);
  line-height: var(--line-height-tight);
}

.comp-calendar--schedule.comp-calendar--days .fc-timegrid-event .fc-event-main {
  padding: var(--space-1) var(--space-2) 0;
}

.comp-calendar--schedule.comp-calendar--days .fc-timegrid-slot-label {
  vertical-align: top;
  font-size: var(--font-2xs);
  line-height: var(--line-height-tight);
}

.comp-calendar--schedule.comp-calendar--days .fc-timegrid-slot-label-cushion {
  display: inline-block;
  font-weight: var(--font-weight-medium);
  transform: translateY(-50%);
}
```
- 線の要素は FullCalendar が `position: absolute` で置いている（`::before` の `absolute` はその中で効く）。丸の上下の中心＝線の太さの中央になるよう `top` を calc で合わせた。
- 重なりの赤枠（`:165-168`）は `border-color` を直接書くので、上の `--fc-event-border-color` の置き換えより強く残る。見積もりの点線は `:not(...)` で除いた。
- 書いた後、`cd frontend && npm run check:css-colors && npm run check:css-values` がどちらも 0 件。

想定分岐:
- `transform: translateY(-50%)` が `inline` の要素に効かないため `display: inline-block` を付けた。目盛りの文字が右に寄らなくなったら止めて `NEEDS_DECISION:`（文字の右寄せは `.fc-timegrid-slot-label` の `text-align` のまま）。
- lint が `::before` の `content: ''` を止めたら、止めた規則名を書いて `NEEDS_DECISION:`。

## 6. 試験（CalendarView.test.tsx）

- import に `formatSlotLabel`・`formatWeekdayShort` を足す。
- `:125` の `expect(p.slotEventOverlap).toBe(false);` はそのまま（既定）。新しい `describe('T8 appearance schedule', ...)` に次を足す:
  1. `appearance="schedule"` かつ `mode="days"` で `fcProps().slotEventOverlap === true`。
  2. `appearance="schedule"` かつ `mode="month"` で `fcProps().slotEventOverlap === undefined`（月には渡さない）・`dayHeaderContent === undefined`。
  3. 包み（`container.querySelector('.comp-calendar')`）に `comp-calendar--schedule` が付く。既定（`appearance` なし）では付かない。
  4. `fcProps().slotLabelContent({ date: new Date(2026, 10, 8, 0, 0), text: '00:00' })` が `''`。`new Date(2026, 10, 8, 9, 0)` で `timeStyle="meridiem"` なら `'calendarView.am'`（この試験の `t` の差し替えはキーをそのまま返すため）、`timeStyle="h24"` なら渡した `text`（`'09:00'`）。
  5. `fcProps().dayHeaderContent({ date: new Date(2026, 10, 8), isToday: true })` を `render` すると `.comp-calendar__daynum--today` が 1 つ・数字は `8`。`isToday: false` では 0 個。
- `describe('T9 formatWeekdayShort / formatSlotLabel', ...)`（`T7` の `tJa` の作り方を同じく使う）:
  - `formatWeekdayShort(new Date(2026, 10, 8), 'ja')` が `'日'`、`'en'` で `'Sun'`。
  - `formatSlotLabel(new Date(2026, 10, 8, 0, 0), '00:00', tJa, 'meridiem')` と `'h24'` の両方が `''`。
  - `formatSlotLabel(new Date(2026, 10, 8, 9, 0), '09:00', tJa, 'meridiem')` が `'午前9時'`。`'h24'` で `'09:00'`。
- 日付は必ず `new Date(年, 月-1, 日, 時, 分)` で作る（文字から作らない・5 回目の審査 R5）。
- T4 は変えない。

## 7. 見本帳（CalendarView.stories.tsx）

`OwnerColor` の後に足す:

```tsx
export const ScheduleAppearance: Story = {
  args: {
    mode: 'days',
    dayCount: 7,
    appearance: 'schedule',
    timeStyle: 'meridiem',
    eventLayout: 'stacked',
    hourRange: 'full',
    events: [
      { id: 'a1', title: 'Meeting A', start: at(0, 10), end: at(0, 11), tone: 'meeting' },
      { id: 'a2', title: 'Meeting B', start: at(0, 10, 30), end: at(0, 11, 30), tone: 'personal' },
      { id: 'a3', title: 'Estimate', start: at(1, 13), end: at(1, 14), tone: 'billing', line: 'dashed' },
    ],
  },
};
```
（`at` は同じファイル `:17` 付近の既存の関数。他の args は `meta.args` の既定を使う。型が合わなければ既存の `Week` の args の形に合わせる）

## 8. ADR-1065

- What の 6 の後に足す:
  `7. 見た目の型 `appearance` を口で選べる。`'plain'`（標準）は今の形。`'schedule'`（Sales Anchor の予定の画面）は時間割のときだけ、日付の帯を 2 段・今の線を丸つき・予定の枠を地と同じ色・時刻の文字を線の高さに合わせ、重なりは後の予定を先の予定の上に重ねて置く（PO 2026-11-07 G15〜G19 承認）。`
- Why の最後に足す:
  `- 重なり横並びは 'plain' の形として残す。予定の画面は PO が Google と同じ重ね方を選んだ（G19）。`
- 「設計・根拠」の欄の末尾に足す: `。2026-11-07 改訂（What 7）: [schedule-gcal-clone design.md §3.8](../handoff/schedule-gcal-clone/design.md)、[card-bin6.md](../handoff/schedule-gcal-clone/card-bin6.md)`
- `node scripts/generate-adr-index.js` を回し、`docs/adr/README.md` の差分を同じ commit に入れる。

## 9. PR

- `gh auth status` で `shingo-cc` を確かめてから `gh pr create --base main --head release/schedule-gcal-look-bin6`（Draft にしない・移行や deploy は無い）。
- 本文はリポジトリの PR のひな形から作る。必ず入れる:
  - 「デザイントークン変更時」のチェック項目を全部 `[x]`（`frontend/scripts/check-new-tokens.js` が見る）。足したトークン 2 つと理由（G16）を書く。
  - `### 標準ワークフロー確認`: recon・設計 = `docs/handoff/schedule-gcal-clone/`、対象 ADR: ADR-1065、触るファイル（§1 の表）、削除するファイル: なし、PO 承認: 2026-11-07「１，」、Opus 審査記録: design.md §9 の 5 回目。
- PR を作ったら URL を返して終わる。CI の完了は待たない。マージしない。

## 10. 返す物

- `DONE: <PR の URL>` と、§5 の直書き検査 2 つ・§6 の試験・`tsc`・lint の実行結果（生の最後の 20 行）。
- 止めたときは `BLOCKED:` か `NEEDS_DECISION:` と理由。
