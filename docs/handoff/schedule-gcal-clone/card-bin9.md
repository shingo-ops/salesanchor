# 実装カード 便9: 月表示・詳しくの小窓と一覧の時刻を Google の形に（G31〜G35）（2026-11-09）

- 設計: `docs/handoff/schedule-gcal-clone/design.md` §2（G31〜G35）・§3.14（審査は §9 の 12 回目 APPROVE）
- PO の承認: G31〜G35 は PO の選択「1」（2026-11-09・「5か所の直しを承認して、作るところまで進める」）
- 土台: origin/main 04c7147a5。ブランチ `release/schedule-gcal-bin9-impl`
- 対象 ADR: ADR-1065（金型 CalendarView・決まり 3 と 7）・ADR-144（金型を使う）・ADR-067（トークン）・ADR-027（文言は t()）
- 行番号はすべて origin/main 04c7147a5 の値。

## 0. 作業者への決まり

- このカードに書いたこと以外はしない。迷ったら止めて `NEEDS_DECISION:` で返す。
- 作業は必ず `bash scripts/new-worktree.sh release/schedule-gcal-bin9-impl --claude` で作った作業場所の中で行う。
- FullCalendar の型名（`DayCellContentArg` など）を金型の外に出さない。金型の中でも型は自分で書いた形（下のコード）だけを使う。
- 新しい文言キーは足さない。新しいトークンは §4 の 1 つだけ。
- 色・寸法の直書き禁止。css の値は `var()` と言葉の値（`transparent`・`center`・`hidden` など）と `0` だけ。
- 試験はクラウドの作業場所で回す（`cd frontend && npx vitest run src/pages/schedule/ src/features/schedule/ src/components/CalendarView.test.tsx`・`npx tsc --noEmit`・`npm run lint`・`node scripts/check-css-hardcoded-values.js`・`node scripts/check-css-hardcoded-colors.js`・`npm run check:dark-parity`）。リポジトリ直下で `node scripts/generate-adr-index.js`。

## 1. 触るファイルと触らないファイル

触る:
| ファイル | 中身 |
|---|---|
| `frontend/src/components/CalendarView.tsx` | 月の日付の中身・月の予定の 1 行（§2） |
| `frontend/src/components/CalendarView.css` | 月の段を足す（§3） |
| `frontend/src/tokens.css` | トークン 1 つ（§4） |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx` | 詳しくの小窓の時刻・一覧の時刻・import（§5） |
| `frontend/src/pages/schedule/schedule-utils.ts` | 使わなくなった `formatTimeRange` を消す（§6） |
| `frontend/src/pages/schedule.css` | `.schedule-popover__date,` の 1 行を消す（§6） |
| `docs/adr/ADR-1065-calendar-view-component-fullcalendar-v6.md`・`docs/adr/README.md` | 決まり 7 に 1 文・索引の作り直し（§7） |
| `frontend/src/components/CalendarView.test.tsx`・`frontend/src/pages/schedule/SchedulePageImpl.test.tsx` | 試験（§8） |
| `.claude-pipeline/active-work.d/release-schedule-gcal-bin9-impl.md` | 台帳（new-worktree.sh が作る形のまま・状態を更新） |

触らない（変えたら差し戻し）:
- `frontend/src/components/calendarView.utils.ts`・`frontend/src/components/CalendarView.stories.tsx`・ほかの `frontend/src/components/` のファイル
- `frontend/src/components/CalendarView.css` の今の規則（足すだけ。`:37` の `--fc-today-bg-color` と `:98-102` の枠の規則も変えない）
- 作る小窓・上の帯・終日の行の文字・時刻の刻み（B 組・PO に聞く）
- `frontend/src/pages/schedule/SchedulePageImpl.tsx` の `formatDayLabel` を使う所（`:146-150`・`:744`・`:816`）と import の `formatDayLabel`
- 移行（migrations）・`.github/workflows/`・リポジトリ直下の `scripts/`・backend・`frontend/scripts/`

## 2. CalendarView.tsx

### 2-1 月の予定の 1 行（G33）（`:146-148`）
前:
```tsx
  }): ReactNode => {
    const source = arg.event.extendedProps.source as CalendarViewEvent;
    if (renderEventContent) return renderEventContent(source, arg.timeText);
```
後:
```tsx
  }): ReactNode => {
    const source = arg.event.extendedProps.source as CalendarViewEvent;
    if (renderEventContent) return renderEventContent(source, arg.timeText);
    // 月の升目・予定の画面の見た目・時刻のある予定は「点＋時刻＋題名」の 1 行（Google と同じ・design §3.14 G33）。
    // 点の形か帯の形かは FullCalendar が決め、帯の形の時は css で点を隠す。
    if (isMonth && appearance === 'schedule' && !arg.event.allDay && arg.event.start) {
      return (
        <>
          <span className="fc-daygrid-event-dot" />
          <span className="comp-calendar__time">{formatMeridiem(arg.event.start, t)}</span>
          <span className="comp-calendar__title">{arg.event.title}</span>
        </>
      );
    }
```
（`isSchedule` は `:169` で後から作られるので、ここでは `appearance === 'schedule'` を直接書く。）

### 2-2 月の日付（G31）（`:219-241` の `monthProps`）
`monthProps` の最後（`:238-240` の `navLinkDayClick` の `},` の後・`:241` の `};` の前）に足す:
```tsx
    ...(isSchedule
      ? {
          // 日付は升目の上の真ん中・1 日だけ「M月1日」・今日は丸（design §3.14 G31）
          dayCellContent: (arg: { date: Date; isToday: boolean }) => (
            <span
              className={
                arg.isToday
                  ? 'comp-calendar__monthnum comp-calendar__monthnum--today'
                  : 'comp-calendar__monthnum'
              }
            >
              {arg.date.getDate() === 1
                ? new Intl.DateTimeFormat(i18n.language ?? 'en', {
                    month: 'short',
                    day: 'numeric',
                  }).format(arg.date)
                : arg.date.getDate()}
            </span>
          ),
        }
      : {}),
```

## 3. CalendarView.css

`:288`（`.fc-timegrid-now-indicator-container` の規則の `}`）の後に空行を 1 つ置いて足す:
```css

/* ---- 予定の画面の見た目・月の升目（ADR-1065 What 7・design §3.14 G31〜G33） ---- */
.comp-calendar--schedule.comp-calendar--month {
  --fc-today-bg-color: transparent;
}

.comp-calendar--schedule.comp-calendar--month .fc-col-header-cell {
  font-size: var(--font-2xs);
  font-weight: var(--font-weight-medium);
  color: var(--schedule-hour-label);
}

.comp-calendar--schedule.comp-calendar--month .fc-daygrid-day-top {
  justify-content: center;
}

.comp-calendar--schedule.comp-calendar--month .comp-calendar__monthnum {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: var(--schedule-month-daynum-size);
  height: var(--schedule-month-daynum-size);
  padding: 0 var(--space-1);
  border-radius: var(--radius-full);
  font-size: var(--font-xs);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.comp-calendar--schedule.comp-calendar--month .comp-calendar__monthnum--today {
  background: var(--schedule-today);
  color: var(--on-solid);
}

.comp-calendar--schedule.comp-calendar--month .fc-daygrid-dot-event.comp-calendar__event {
  border-width: 0;
  background: transparent;
  color: var(--text-primary);
}

.comp-calendar--schedule.comp-calendar--month .fc-daygrid-block-event .fc-daygrid-event-dot {
  display: none;
}

.comp-calendar--schedule.comp-calendar--month .comp-calendar__title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
```
（`min-width: 0` は、横並びの中で題名が縮んで「…」になるために要る。設計の `overflow`・`text-overflow` を効かせるための 1 行。）

## 4. tokens.css

`:412` の `--schedule-month-dot-size: 8px;      /* 月ビュー・一覧の担当者色の丸 */` の次の行に足す:
```css
  --schedule-month-daynum-size: 24px;  /* 月ビューの日付の丸（今日の丸・Google の実測 24px） */
```
ダーク側（`[data-theme="dark"]` など）には足さない（寸法なので同じ値。`npm run check:dark-parity` が通ることを確かめる）。

## 5. SchedulePageImpl.tsx

### 5-1 import（`:43-64` の `./schedule-utils` の読み込み）
`:56` の `  formatTimeRange,` の 1 行を消す。
`./schedule-utils` の読み込みの文の次の行に足す:
```ts
import { formatTimeRange as formatEventTimeRange } from "../../components/calendarView.utils";
```
（同じ所から既に読み込んでいる行があれば、その行の `{ }` の中に `formatTimeRange as formatEventTimeRange` を足す形にする。どちらにするかは eslint の `import/no-duplicates` が通る方。）

### 5-2 詳しくの小窓の時刻（G34）（`:273-274`）
前:
```tsx
  const dateLabel = item ? formatDayLabel(item.start) : "";
  const timeLabel = item ? formatTimeRange(item.start, item.end, item.allDay, "ja-JP", t("schedule.allDay")) : "";
```
後:
```tsx
  const timeLabel = item ? formatSearchResultLine(item, t, i18n.language) : "";
```

### 5-3 詳しくの小窓の日付の行を消す（`:340`）
`            <p className="schedule-popover__date">{dateLabel}</p>` の 1 行を消す。`:339` の `schedule-popover__time` の行は残す。

### 5-4 一覧の時刻（G35）（`:831`）
前:
```tsx
                      {item.allDay ? t("schedule.allDay") : formatTimeRange(item.start, item.end, false)}
```
後:
```tsx
                      {item.allDay ? t("schedule.allDay") : formatEventTimeRange(item.start, item.end, t, false)}
```

## 6. 使わなくなった物を消す

- 消す前に `grep -rn "formatTimeRange" frontend/src --include='*.ts' --include='*.tsx'` を流し、`frontend/src/pages/` の中で schedule-utils の `formatTimeRange` を使う所が 0 であることを確かめる（`frontend/src/components/` の中と `formatTimeRange as formatEventTimeRange` は別の関数なので残る）。0 でなければ `NEEDS_DECISION:`。
- `frontend/src/pages/schedule/schedule-utils.ts:164-168`（`export function formatTimeRange(...)` の関数 5 行）と、その後の空行 1 行を消す。
- `frontend/src/pages/schedule.css:409` の `.schedule-popover__date,` の 1 行を消す（`:408` の `.schedule-popover__time,` と `:410-411` は残す）。

## 7. ADR-1065 の決まり 7

`docs/adr/ADR-1065-calendar-view-component-fullcalendar-v6.md:22` の行の終わり（`（PO 2026-11-07 G15〜G19 承認）。`の後）に、同じ行のまま 1 文を足す:
```
月の升目のときは、日付を升目の上の真ん中に・今日を丸で・曜日を時間割と同じ文字で・時刻のある 1 日の予定を点＋時刻＋題名の 1 行で出す（PO 承認 G31〜G35）。
```
その後リポジトリ直下で `node scripts/generate-adr-index.js` を流し、`docs/adr/README.md` に差が出たら一緒に commit する（差が無ければそのまま）。

## 8. 試験

`frontend/src/components/CalendarView.test.tsx` の `describe('T11 appearance schedule', ...)` の中に足す（今の書き方 `fcProps()` を使う）:
- (a) `mode="month"`・`appearance="schedule"` で `fcProps().dayCellContent` が関数。`render(fcProps().dayCellContent({ date: new Date(2026, 10, 8), isToday: true }))` の中に `.comp-calendar__monthnum--today` が 1 つ・文字が `8`。`isToday: false` では `--today` が 0。`date: new Date(2026, 10, 1)` の文字が `new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric' }).format(new Date(2026, 10, 1))` と同じ。
- (b) `appearance` を渡さない `mode="month"` では `fcProps().dayCellContent` が `undefined`。
- (c) `mode="month"`・`appearance="schedule"`・`eventLayout="stacked"`・`timeStyle="meridiem"` で、`render(<>{fcProps().eventContent({ timeText: '8p', event: { title: 'e1', start: new Date(2026, 10, 2, 20), end: new Date(2026, 10, 2, 21), allDay: false, extendedProps: { source: events[0] } } })}</>)` の中に `.fc-daygrid-event-dot` が 1 つ、`.comp-calendar__time` の文字が `calendarView.pm`（試験の t は鍵をそのまま返す）、`.comp-calendar__title` の文字が `e1`、`.comp-calendar__content--stacked` が 0。
- (d) 同じ形で `allDay: true` のときは `.fc-daygrid-event-dot` が 0。`mode="days"`・`appearance="schedule"` のときも `.fc-daygrid-event-dot` が 0（時間割は今のまま）。

`frontend/src/pages/schedule/SchedulePageImpl.test.tsx` に `describe("SchedulePage time lines (G34-G35)", ...)` を足す（今の `apiEvent({})`・`view()`・`answers.events` を使う。読み込みに `formatDateInput`・`formatDraftDateLine`・`formatTimeInput` を `./schedule-utils` から、`formatTimeRange` を `../../components/calendarView.utils` から足す）:
- (e) `answers.events = [apiEvent({})]` で `view()`、`Own Event` を押して詳しくの小窓を開く。`document.querySelector(".schedule-popover__time")` の文字が、`const s = new Date(todayAt(10)); const e = new Date(todayAt(11));` から作った `formatDraftDateLine({ startDate: formatDateInput(s), startTime: formatTimeInput(s), endDate: formatDateInput(e), endTime: formatTimeInput(e), allDay: false }, i18n.t.bind(i18n) as never, i18n.language)` と同じ。`document.querySelectorAll(".schedule-popover__date").length` が 0。
- (f) 同じ予定で `view()` の後、一覧の表示へ切り替える（`fireEvent.keyDown(document.body, { key: "a" })` か、今の試験と同じ切り替え方）。`.schedule-list__time` の文字が `formatTimeRange(s, e, i18n.t.bind(i18n) as never, false)` と同じで、`/\d{2}:\d{2} - \d{2}:\d{2}/` に当たらない。

既存の試験は全部通ること（T11 の `passes nothing to month mode` は `slotEventOverlap` と `dayHeaderContent` だけを見ているので、そのまま通る）。

## 9. 返事

DONE と HEAD の SHA（40 文字）・試験の結果の数（通った／落ちた）・tsc・lint・css 検査 2 つ・dark-parity の結果・ADR 索引の作り直しで差が出たか・§6 の grep の結果の行数・`git show --stat HEAD`。止めたときは `BLOCKED:` か `NEEDS_DECISION:` と理由。
