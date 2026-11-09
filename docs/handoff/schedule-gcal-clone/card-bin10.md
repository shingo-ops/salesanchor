# 実装カード 便10: 日・3日間・週から月へ切り替えると画面全体が消える不具合（G36）（2026-11-09）

- 設計: `docs/handoff/schedule-gcal-clone/design.md` §2（G36）・§3.15（審査は §9 の 13 回目）
- PO の承認: PO の選択「1」（2026-11-09・「画面が消える不具合を先に直す。設計と審査をしてから直し、本番に出します」）
- 土台: origin/main a34b0af43。ブランチ `release/schedule-view-switch-crash-impl`
- 対象 ADR: ADR-1065（金型 CalendarView・FullCalendar 6.1.22 固定）
- 行番号はすべて origin/main a34b0af43 の値。

## 0. 作業者への決まり

- このカードに書いたこと以外はしない。迷ったら止めて `NEEDS_DECISION:` で返す。
- 作業は必ず `bash scripts/new-worktree.sh release/schedule-view-switch-crash-impl --claude` で作った作業場所の中で行う。
- 新しい文言キー・トークン・css は足さない。
- 試験はクラウドの作業場所で回す（`cd frontend && npx vitest run src/components/CalendarView.test.tsx src/pages/schedule/ src/features/schedule/`・`npx tsc --noEmit`・`npm run lint`）。

## 1. 触るファイルと触らないファイル

触る:
| ファイル | 中身 |
|---|---|
| `frontend/src/components/CalendarView.tsx` | `views` を常に渡す（§2） |
| `frontend/src/components/CalendarView.test.tsx` | 試験 2 つ（§3） |
| `.claude-pipeline/active-work.d/release-schedule-view-switch-crash-impl.md` | 台帳（new-worktree.sh が作る形のまま・状態を更新） |

触らない（変えたら差し戻し）:
- `frontend/src/components/CalendarView.tsx` の §2 以外の行（`views` の作り方 `:105-108`・表示を合わせる useEffect `:110-120`・`monthProps` `:230-` を含む）
- `frontend/src/components/CalendarView.css`・`calendarView.utils.ts`・`CalendarView.stories.tsx`
- `frontend/src/pages/schedule/`（読み込み中の出し方 `SchedulePageImpl.tsx:990`・`:1547` も変えない）
- 誤りを受け止める部品（ErrorBoundary）の追加（範囲外・PO に別に伝える）
- 移行（migrations）・`.github/workflows/`・リポジトリ直下の `scripts/`・backend・`frontend/scripts/`

## 2. CalendarView.tsx

### 2-1 `daysProps` から `views` を消す（`:192-194`）
前:
```tsx
  // design §4-3 の表: days だけ・month だけの値は分けて渡す
  const daysProps = {
    views,
    slotDuration: '01:00:00',
```
後:
```tsx
  // design §4-3 の表: days だけ・month だけの値は分けて渡す（views は月でも渡す・下の <FullCalendar>）
  const daysProps = {
    slotDuration: '01:00:00',
```

### 2-2 `<FullCalendar>` に `views` を足す（`:283-285`）
前:
```tsx
        firstDay={weekStart}
        nowIndicator
        {...(isMonth ? monthProps : daysProps)}
```
後:
```tsx
        firstDay={weekStart}
        nowIndicator
        // 月でも calendarDays の定義を渡す。月へ切り替えた時に定義が消えて画面全体が落ちるのを防ぐ
        // （props が変わると FullCalendar は設定を丸ごと置き換える・schedule-gcal-clone design §3.15 G36）
        views={views}
        {...(isMonth ? monthProps : daysProps)}
```

## 3. 試験（`frontend/src/components/CalendarView.test.tsx`）

### 3-1 T3 に足す（`describe('T3 props passed to FullCalendar', ...)` の閉じ `:205` の `});` の直前）
```tsx
  it.each([1, 3, 7] as const)(
    'keeps the days view defined while switching days and month (dayCount %i, G36)',
    (dayCount) => {
      const days = (
        <CalendarView mode="days" date="2026-11-02" dayCount={dayCount} events={events} ariaLabel="cal" />
      );
      const month = (
        <CalendarView mode="month" date="2026-11-02" dayCount={dayCount} events={events} ariaLabel="cal" />
      );
      const expected = { type: 'timeGrid', duration: { days: dayCount } };
      const { rerender } = render(days);
      expect(fcProps().views.calendarDays).toEqual(expected);
      rerender(month);
      expect(fcProps().views.calendarDays).toEqual(expected);
      rerender(days);
      expect(fcProps().views.calendarDays).toEqual(expected);
      rerender(month);
      expect(fcProps().views.calendarDays).toEqual(expected);
      expect(fcProps().initialView).toBe('dayGridMonth');
    },
  );
```
（最後の行: `initialView` は `:77` の `viewName` で、月では `dayGridMonth`。）

### 3-2 T5 に足す（`describe('T5 ...', ...)` の閉じ `:231` の `});` の直前）
```tsx
  it('still replaces every option on resetOptions (core and react wrapper) and builds views from optionOverrides.views (G36)', () => {
    const src = readPackageFiles('core', (n) => n === 'index.js');
    expect(src).toContain('props.optionOverrides = optionOverrides');
    expect(src).toContain('parseViewConfigs(optionOverrides.views)');
    const wrapper = readPackageFiles('react/dist', (n) => n === 'index.js');
    expect(wrapper).toContain('this.calendar.resetOptions(Object.assign(Object.assign({}, this.props)');
  });
```
（`readPackageFiles` は `node_modules/@fullcalendar/<pkg>/` を読むので、`'react/dist'` で包みの `dist/index.js` が読める。関数は変えない。3 つの文は 6.1.22 の中身で在ることを確かめ済み: core `index.js:1367`・`:366`、react `dist/index.js:76`。）

既存の試験は全部通ること（T3 の `passes the days settings for a two-day view` は `p.views.calendarDays` を見るので、`views` を `<FullCalendar>` に移してもそのまま通る）。

## 4. 返事

DONE と HEAD の SHA（40 文字）・試験の結果の数（通った／落ちた）・tsc・lint の結果・`git show --stat HEAD`。止めたときは `BLOCKED:` か `NEEDS_DECISION:` と理由。
