# カード 便1: 金型 CalendarView に口を足す（画面は変わらない）

設計: `docs/handoff/schedule-gcal-clone/design.md` §3.2（足す口の表・選んだ範囲の決まり）・§4 便1。ADR: `docs/adr/ADR-1065-calendar-view-component-fullcalendar-v6.md`（この PR で Opus が改訂する。実装役は触らない）。
成功条件の PO 承認: 2026-11-06（「1.」）。便1 は画面を変えない（金型を使う画面は 0 件・recon §4）。成功条件 G1〜G13 は便2 以降で画面に出る。

## 枝と作業場所
- 枝 `release/schedule-calendarview-mouths`（Opus が `origin/main` から作成済み）。作業場所 `~/worktrees/salesanchor/release-schedule-calendarview-mouths` 相当のクローンでこの枝を checkout して作業する。

## 実物で確かめた事実（2026-11-07・Opus）
- Google カレンダー（日本語）の目盛り: 「午前」か「午後」に 1〜12 の時と「時」を付けた形。0 時は午前に 12 を付け、12 時は午後に 12 を付ける（午前 1 時〜11 時、午後 1 時〜11 時はそのままの数）。
- Google の箱の時刻: ちょうどの時は「午後8時～9時」「午後2時～3時」、分があると「午後12:30～1:30」。終わりの「午前/午後」は始まりと同じなら書かない。区切りは全角の「～」。
- `--on-solid` は `frontend/src/tokens.css:544` にある（今の予定の画面が担当者の色の箱の文字に使う色）。
- 今の予定の画面の小窓の基準の型 `AnchorRect`（`frontend/src/pages/schedule/schedule-utils.ts:4`）は `top`・`right`・`bottom`・`left` を持つ。
- `@fullcalendar/interaction` は `frontend/package.json:75` に 6.1.22 で入っている。

## 変えるもの（6 ファイルだけ）

### 1. `frontend/src/components/calendarView.utils.ts`
型を足す（既存の型・関数の中身は変えない。`eventClassNames` だけ引数を 1 つ足す）。

```ts
/** 押した所・箱の四角（AnchorRect と同じ 4 辺＋幅・高さ） */
export interface CalendarViewRect {
  top: number;
  right: number;
  bottom: number;
  left: number;
  width: number;
  height: number;
}
```

`CalendarViewEvent` に足す:
```ts
  /** 担当者の色（DB が正本。呼ぶ側は受けた値をそのまま渡す）。あるときは tone より優先 */
  color?: string;
  /** false で動かせない（FullCalendar の予定ごとの editable）。無いときは金型の設定に従う */
  editable?: boolean;
```

`CalendarViewProps` に足す（すべて省略可。省略時は今と同じ動き）:
```ts
  /** 時刻の書き方。'h24'＝今の「13:00」（既定）／'meridiem'＝「午後1時」 */
  timeStyle?: 'h24' | 'meridiem';
  /** 箱の並び。'inline'＝時刻・題名を 1 行（既定）／'stacked'＝題名の下に時刻 */
  eventLayout?: 'inline' | 'stacked';
  /** 見える時間。'events'＝startHour〜endHour を予定で広げる（既定）／'full'＝0〜24 時 */
  hourRange?: 'events' | 'full';
  /** true で、開いたとき今の時刻の 1 時間前の所を上に出す */
  scrollToNow?: boolean;
  /** 週の始まり。0＝日曜／1＝月曜（既定） */
  weekStart?: 0 | 1;
  /** true で包む枠の高さいっぱいに広げる（月の升目を下まで）。既定は中身の高さ */
  fillHeight?: boolean;
  /** 押す・引っぱるで選んだ範囲。渡したときだけ選べる */
  onSelectRange?: (start: Date, end: Date, allDay: boolean, anchor: CalendarViewRect | null) => void;
  /** 予定をつかんで動かした。渡したときだけ動かせる。失敗したら revert() で元に戻す */
  onEventMove?: (id: string, start: Date, end: Date | null, allDay: boolean, revert: () => void) => void;
  /** 予定の下の端を引いて長さを変えた。渡したときだけ変えられる */
  onEventResize?: (id: string, start: Date, end: Date | null, revert: () => void) => void;
  /** 月の「ほか N 件」。渡したときは onDayClick を呼ばずにこちらを呼ぶ */
  onMoreClick?: (date: Date, rect: CalendarViewRect | null) => void;
```

`onEventClick` の型を変える（引数が 1 つ増えるだけ。今の呼ぶ側は 0 件）:
```ts
  onEventClick?: (id: string, rect: CalendarViewRect | null) => void;
```

純粋な関数を足す（FullCalendar を import しない）:

```ts
/** 0〜23 時 → 12 時間表記の時と午前・午後。0 時は 午前12、12 時は 午後12（Google と同じ） */
export function toMeridiemHour(hour: number): { hour12: number; pm: boolean } {
  const h = ((hour % 24) + 24) % 24;
  return { hour12: h % 12 === 0 ? 12 : h % 12, pm: h >= 12 };
}

type Translate = (key: string, opts?: Record<string, unknown>) => string;

/** 1 つの時刻の本体（午前・午後なし）。分が 0 なら「8時」、あれば「12:30」 */
export function formatClock(date: Date, t: Translate): string {
  const { hour12 } = toMeridiemHour(date.getHours());
  const minute = date.getMinutes();
  return minute === 0
    ? t('calendarView.clockHour', { hour: hour12 })
    : t('calendarView.clockMinute', { hour: hour12, minute: String(minute).padStart(2, '0') });
}

/** 午前・午後を付けた時刻（目盛りにも使う） */
export function formatMeridiem(date: Date, t: Translate): string {
  const key = toMeridiemHour(date.getHours()).pm ? 'calendarView.pm' : 'calendarView.am';
  return t(key, { time: formatClock(date, t) });
}

/**
 * 箱の時刻「午後12:30～1:30」。終わりが無いときは始まりだけ。
 * omitSameMeridiem が真で、始まりと終わりの午前・午後が同じなら、終わりの午前・午後を書かない。
 */
export function formatTimeRange(
  start: Date,
  end: Date | null,
  t: Translate,
  omitSameMeridiem: boolean,
): string {
  const startText = formatMeridiem(start, t);
  if (!end) return startText;
  const same = toMeridiemHour(start.getHours()).pm === toMeridiemHour(end.getHours()).pm;
  const endText = omitSameMeridiem && same ? formatClock(end, t) : formatMeridiem(end, t);
  return t('calendarView.timeRange', { start: startText, end: endText });
}

/** 今の時刻の 1 時間前（0 時より前にしない）を "HH:00:00" で */
export function scrollTimeForNow(now: Date): string {
  return `${pad2(Math.max(0, now.getHours() - 1))}:00:00`;
}

/** 押しただけ（15 分以下）なら始まりから 1 時間に広げる。終日はそのまま */
export function normalizeSelectedRange(
  start: Date,
  end: Date,
  allDay: boolean,
): { start: Date; end: Date } {
  if (allDay) return { start, end };
  const QUARTER = 15 * 60 * 1000;
  if (end.getTime() - start.getTime() <= QUARTER) {
    return { start, end: new Date(start.getTime() + MS_PER_HOUR) };
  }
  return { start, end };
}

/** 要素の四角を CalendarViewRect に。要素が無ければ null */
export function rectOf(el: Element | null | undefined): CalendarViewRect | null {
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return { top: r.top, right: r.right, bottom: r.bottom, left: r.left, width: r.width, height: r.height };
}

/** 押した 1 点を幅・高さ 0 の四角に。イベントが無ければ null */
export function pointRect(ev: { clientX: number; clientY: number } | null | undefined): CalendarViewRect | null {
  if (!ev) return null;
  return { top: ev.clientY, bottom: ev.clientY, left: ev.clientX, right: ev.clientX, width: 0, height: 0 };
}
```

`eventClassNames` の引数の型に `'color'` を足し、`event.color` があるとき `'comp-calendar__event--owner-color'` を `conflict` の前に足す（無いときの並びは今と同じ）。

### 2. `frontend/src/components/CalendarView.tsx`
- `import interactionPlugin from '@fullcalendar/interaction';` を足し、`PLUGINS = [timeGridPlugin, dayGridPlugin, interactionPlugin]`。
- 新しい props を受ける（既定値: `timeStyle = 'h24'`・`eventLayout = 'inline'`・`hourRange = 'events'`・`scrollToNow = false`・`weekStart = 1`・`fillHeight = false`）。
- `range`: `hourRange === 'full'` なら `{ slotMinTime: '00:00:00', slotMaxTime: '24:00:00' }`、そうでなければ今の `computeHourRange`。
- `fcEvents` の各予定に、`ev.editable !== undefined` のとき `editable: ev.editable` を足す（無いときは今と同じ形）。**`backgroundColor`・`borderColor`・`color` は FullCalendar に渡さない**（渡すと FullCalendar が要素に色を直接書き、見積もりの地と重なりの赤枠より強くなる・core `internal-common.js:7199-7201`・審査 Q2）。
- 担当者の色は `<FullCalendar>` の `eventDidMount` で置く:
  ```ts
  eventDidMount={(arg) => {
    const color = (arg.event.extendedProps.source as CalendarViewEvent).color;
    if (color) arg.el.style.setProperty('--comp-calendar-owner-color', color);
  }}
  ```
  （色の値は DB から来たデータ。css に色を書くのではなく、変数に入れるだけ。css 側の 3 がこの変数を使う）
- `const omitSameMeridiem = i18n.language?.startsWith('ja') ?? false;`
- `renderContent`:
  - `renderEventContent` があれば今のまま。
  - 時刻の文字: `timeStyle === 'meridiem'` かつ終日でないとき `formatTimeRange(event.start, event.end, t, omitSameMeridiem)`、それ以外は今の `arg.timeText`。`renderContent` の引数の型に `event.start: Date | null`・`event.end: Date | null`・`event.allDay: boolean` を足す。`start` が null のときは `arg.timeText`。
  - `eventLayout === 'stacked'` のときは `<span className="comp-calendar__content comp-calendar__content--stacked"><span className="comp-calendar__title">題名</span>{時刻があれば <span className="comp-calendar__time">時刻</span>}</span>`。`'inline'` は今のまま（時刻→題名）。
- `daysProps` に足す:
  - `timeStyle === 'meridiem'` のとき `slotLabelContent: (arg: { date: Date }) => formatMeridiem(arg.date, t)`（`slotLabelFormat` は今のまま残す）。
  - `snapDuration: '00:15:00'`。
  - `scrollToNow` が真のとき `scrollTime: initialScrollTime`（`const initialScrollTime = useMemo(() => scrollTimeForNow(new Date()), [])`）。
- `monthProps.moreLinkClick` を次にする（戻り値はどちらでも `arg.view.type`・design §3.2・審査 2 回目 Q1）:
  ```ts
  moreLinkClick: (arg: { date: Date; jsEvent: { target: EventTarget | null }; view: { type: string } }) => {
    if (onMoreClick) {
      onMoreClick(arg.date, rectOf(arg.jsEvent.target as Element | null));
    } else {
      onDayClick?.(arg.date);
    }
    return arg.view.type;
  },
  ```
- `<FullCalendar>` の props:
  - `firstDay={weekStart}`
  - `eventClick={(arg) => { onEventClick?.(arg.event.id, rectOf(arg.el)); }}`
  - `selectable={Boolean(onSelectRange)}`・`selectMirror={false}`
  - `select={(arg) => { const r = normalizeSelectedRange(arg.start, arg.end, arg.allDay); onSelectRange?.(r.start, r.end, arg.allDay, pointRect(arg.jsEvent)); arg.view.calendar.unselect(); }}`（選んだ色付けは残さない。仮の箱は便2 で画面が出す・design §3.7）
  - `editable={Boolean(onEventMove || onEventResize)}`・`eventStartEditable={Boolean(onEventMove)}`・`eventDurationEditable={Boolean(onEventResize)}`
  - `eventDrop={(arg) => { onEventMove?.(arg.event.id, arg.event.start as Date, arg.event.end, arg.event.allDay, arg.revert); }}`
  - `eventResize={(arg) => { onEventResize?.(arg.event.id, arg.event.start as Date, arg.event.end, arg.revert); }}`
  - `eventClassNames` は今のまま（utils 側で色の class が増える）。
  - `height={fillHeight ? '100%' : 'auto'}`
- 包む `div` の class に `fillHeight` のとき `comp-calendar--fill` を足す。
- FullCalendar の型名（`DateSelectArg` など）を import して使ってよいが、`export` しない（ADR-1065 What 3）。

### 3. `frontend/src/components/CalendarView.css`
（審査 1 回目 Q1・Q2 を 2026-11-07 に直した版）
足すのは次の 4 つだけ（値は var() だけ・px や # を書かない）。
置く場所: 1 と 2 はファイルの末尾。3 と 4 は **`.comp-calendar__event--tone-holiday` の規則の直後、`/* 見積もり: 点線の枠…` の規則より前**（同じ強さの規則は後ろが勝つため。見積もりの面の色の地と重なりの赤枠を、担当者の色より後ろに置いて勝たせる・ADR-1065 What 5・審査 Q2）。
```css
/* 1 */
.comp-calendar--fill {
  height: 100%;
}

/* 2 */
.comp-calendar .comp-calendar__content--stacked {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* 3 担当者の色の箱: 地と枠は予定ごとの色（eventDidMount が要素に --comp-calendar-owner-color を置く）、文字は塗りの上の色 */
.comp-calendar .comp-calendar__event--owner-color {
  --fc-event-bg-color: var(--comp-calendar-owner-color);
  --fc-event-border-color: var(--comp-calendar-owner-color);
  --fc-event-text-color: var(--on-solid);
}

/* 4 担当者の色の見積もり: 地は面の色（下の見積もりの規則）なので、文字は本文の色 */
.comp-calendar .comp-calendar__event--owner-color.comp-calendar__event--line-dashed {
  --fc-event-text-color: var(--text-primary);
}
```
（4 は 2 つの class を持つので強さが上。置く場所は 3 の直後でよい。`--text-primary` は `frontend/src/index.css:24`）

### 4. `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`
`calendarView` の中に同じキーを足す（既存の `more`・`allDay` は変えない）:

| キー | ja | en |
|---|---|---|
| `am` | `午前{{time}}` | `{{time}} AM` |
| `pm` | `午後{{time}}` | `{{time}} PM` |
| `clockHour` | `{{hour}}時` | `{{hour}}` |
| `clockMinute` | `{{hour}}:{{minute}}` | `{{hour}}:{{minute}}` |
| `timeRange` | `{{start}}～{{end}}` | `{{start}} – {{end}}` |

### 5. `frontend/src/components/CalendarView.test.tsx`
今の試験は消さず・変えずに足す。変えてよいのは次の 3 か所だけ:
- 1 行目に足す（実装の 2 回目で、commit 前の検査 `eslint --max-warnings=0` が T7 の日本語の期待値を `local/no-japanese-literal` の警告として止めたため。前例 `frontend/src/components/DataTable.test.tsx:1`・`frontend/src/pages/inbox/discordSendError.test.ts:1`）: `/* eslint-disable local/no-japanese-literal -- テスト: 午前・午後の時刻が Google と同じ日本語で出ることを検証する（ADR-027・precedent: DataTable.test.tsx） */`
- T3 の `expect(onEventClick).toHaveBeenCalledWith('e1');`（`frontend/src/components/CalendarView.test.tsx:192`）→ `expect(onEventClick).toHaveBeenCalledWith('e1', null);`（`el` を渡していないので四角は null・審査 Q1）。
- T4: 数える包みに `readPackageFiles('interaction', (n) => n === 'index.js' || n.startsWith('internal'))` を足す。interaction の `--fc-*` が増えて漏れが出たら、css に足さずに BLOCKED: で止める。
- T6 `toMeridiemHour`: 0→{12,false}、9→{9,false}、12→{12,true}、13→{1,true}、23→{11,true}。
- T7 `formatTimeRange`（`t` は試験の中で `import ja from '../locales/ja.json'` の `calendarView` の文を引き、`{{名前}}` を値で置き換える小さな関数を作る。文を試験に書き写さない）: 20:00〜21:00 → `午後8時～9時`、12:30〜13:30 → `午後12:30～1:30`、11:30〜12:30 → `午前11:30～午後12:30`、end null → `午後8時`、omitSameMeridiem 偽で 20:00〜21:00 → `午後8時～午後9時`。
- T8 `normalizeSelectedRange`: 10:00〜10:15（押しただけ）→ 10:00〜11:00、10:00〜12:00 → そのまま、終日はそのまま。
- T9 `scrollTimeForNow`: 12:34 → `11:00:00`、0:10 → `00:00:00`。
- T10 FullCalendar に渡す値（今の mock の `captured.props` を使う）:
  - 口を渡さないとき `selectable`・`editable` が false、`firstDay` が 1、`height` が `'auto'`（今の T3 と同じ）。
  - `onSelectRange` を渡すと `selectable` が true。`select({ start: 10:00, end: 10:15, allDay: false, jsEvent: { clientX: 5, clientY: 7 }, view: { calendar: { unselect } } })` で、onSelectRange が (10:00, 11:00, false, {top:7,bottom:7,left:5,right:5,width:0,height:0}) で呼ばれ、unselect が 1 回呼ばれる。`jsEvent: null` なら anchor が null。
  - `onEventMove` を渡すと `editable`・`eventStartEditable` が true、`eventDurationEditable` が false。`eventDrop` で onEventMove が id・start・end・allDay・revert で呼ばれる。
  - `onEventResize` を渡すと `eventDurationEditable` が true。`eventResize` で呼ばれる。
  - `onMoreClick` を渡すと `moreLinkClick` が onMoreClick を呼び、onDayClick は呼ばず、戻り値は `arg.view.type`。呼び方: `moreLinkClick({ date: 11/5 0:00, jsEvent: { target: el }, view: { type: 'dayGridMonth' } })`（el は `getBoundingClientRect` が `{ top: 1, right: 4, bottom: 3, left: 2, width: 2, height: 2 }` を返す小さな物）→ onMoreClick が (11/5 0:00, {top:1,right:4,bottom:3,left:2,width:2,height:2}) で呼ばれ、戻り値は `'dayGridMonth'`。`jsEvent: { target: null }` なら四角は null（審査 2 回目の推奨）。
  - `eventClick({ event: { id: 'e1' }, el })` で onEventClick が ('e1', 四角) で呼ばれる（el は `getBoundingClientRect` を持つ小さな物で作る）。
  - `weekStart={0}` で `firstDay` が 0。`fillHeight` で `height` が `'100%'`。`hourRange="full"` で `slotMinTime` `00:00:00`・`slotMaxTime` `24:00:00`。`scrollToNow` で `scrollTime` が `HH:00:00` の形。`timeStyle="meridiem"` で `slotLabelContent` が関数。
  - `color: '#123456'`・`editable: false` の予定で、`events[0]` に `editable: false` が付き、`backgroundColor`・`borderColor` は付かない。`eventClassNames` に `comp-calendar__event--owner-color` が入る。`eventDidMount({ event: { extendedProps: { source: その予定 } }, el: document.createElement('div') })` の後、その el の `style.getPropertyValue('--comp-calendar-owner-color')` が `#123456`。color の無い予定では空。
  - 試験の中に色を書くのは予定のデータとしての値だけ（css には書かない）。

### 6. `frontend/src/components/CalendarView.stories.tsx`
今の stories は変えずに 2 つ足す（ADR-073）:
- `GoogleLike`: `mode="days"`・`dayCount={7}`・`timeStyle="meridiem"`・`eventLayout="stacked"`・`hourRange="full"`・`scrollToNow`・`weekStart={0}`、予定は `baseEvents()` に 30 分の予定を 1 つ足したもの。`onSelectRange`・`onEventMove`・`onEventResize`・`onEventClick` を渡す（中身は何もしない関数。他の stories で `fn()` を使っていればそれに合わせる）。
- `OwnerColor`: 予定 2 つに `color` を付ける。値は `frontend/src/pages/schedule/schedule-owner.ts:34` の `DEFAULT_OWNER_COLOR` を import して使う（stories に色の値を書かない）。

## 触らない範囲
- 上の 6 ファイル以外（`docs/adr/` は Opus が直すので触らない）。予定の画面（`frontend/src/pages/schedule/`）・tokens.css・裏側・`package.json` は触らない。

## 確かめ
- Mac では試験を流さない。push して GitHub の CI（frontend の試験・lint・型・UI governance）が緑になることで確かめる。
- 想定の分かれ道:
  - FullCalendar 6.1.22 の型で `select`・`eventDrop`・`eventResize`・`moreLinkClick` の引数の名前が上と違う → 型に合わせず BLOCKED: で止めて実物の型を報告する。
  - `slotLabelContent` に文字を返すと型が通らない → `{ html: ... }` にはせず BLOCKED:。
  - lint や UI governance が新しい css・文字を止めた → 迂回せず BLOCKED:。

## commit と PR
- commit 文: `feat(calendar-view): add selection, drag, meridiem time and layout options`。末尾 `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
- PR は実装役は作らない（Opus が作る）。
