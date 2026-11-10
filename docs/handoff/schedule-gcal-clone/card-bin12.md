# 実装カード 便12: 作る小窓を Google の形に・作っている途中の箱を動かせる（G42〜G50）（2026-11-10）

- 設計: `docs/handoff/schedule-gcal-clone/design.md` §2.5（G42〜G50）・§3.17（審査は §9 の 15 回目・2 回目 APPROVE）
- PO の承認: PO の選択「1」（2026-11-10・「この設計で作り、本番に出してGoogleと並べて確かめる」）。金型 2 つの変更（`TextFieldControl` の種類 `"schedule-title"`・`CalendarView` の口 `trackEventId`/`onEventRect`）と ADR-1065 What 6 の 1 文もこの承認に含む（ADR-144）。
- 土台: origin/main（作業の時点の最新）。ブランチ `release/schedule-gcal-create-drag-impl`
- 対象 ADR: ADR-1065（金型 CalendarView・What 1 型を外に出さない・What 6 口）・ADR-144（金型）・ADR-067（トークン）・ADR-027（i18n）
- 行番号はすべて origin/main 96a63df05 の値。違っていたら中身で場所を探し、見つからなければ止める。

## 0. 作業者への決まり

- このカードに書いたこと以外はしない。迷ったら止めて `NEEDS_DECISION:` で返す。設計 §3.17 とこのカードが食い違ったら止める。
- 作業は必ず `bash scripts/new-worktree.sh release/schedule-gcal-create-drag-impl --claude` で作った作業場所の中で行う。
- 色・寸法は var() だけ（px・色の直書き禁止。例外は既存の定数の書き方に合わせた TS の数 `CREATE_POPOVER_GAP = 8` だけ）。UI の文字は t() だけ。
- 確かめはクラウドの作業場所で回す: `cd frontend && npx vitest run src/components/CalendarView.test.tsx src/pages/schedule/ src/components/TextField`・`npx tsc --noEmit`・`npm run check:all`。ADR を変えたので `node scripts/generate-adr-index.js` をリポジトリ直下で流し、`docs/adr/README.md` の差分も入れる。
- 試験が落ちたら直してよいのは §9 に書いた試験だけ。ほかの試験が落ちたら止めて返す。

## 1. 触るファイルと触らないファイル

触る:
| ファイル | 中身 |
|---|---|
| `frontend/src/pages/schedule/schedule-utils.ts` | 純粋な関数 4 つ（§2） |
| `frontend/src/pages/schedule/schedule-utils.test.ts` | §2 の試験（§9） |
| `frontend/src/components/calendarView.utils.ts` | 口 2 つの型（§3） |
| `frontend/src/components/CalendarView.tsx` | 口 2 つの中身（§3） |
| `frontend/src/components/CalendarView.test.tsx` | §9 |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx` | §4〜§6 |
| `frontend/src/pages/schedule/SchedulePageImpl.test.tsx`・`SchedulePageCache.test.tsx` | §9 |
| `frontend/src/components/TextField.tsx`・`frontend/src/components/FormField.css`・`frontend/src/components/TextField.stories.tsx` | 種類 `"schedule-title"`（§7） |
| `frontend/src/constants/icons.tsx` | 絵 3 つ（§7） |
| `frontend/src/tokens.css` | トークン 5 行（§7） |
| `frontend/src/pages/schedule.css` | 写し 2 行を消す・作る小窓の規則（§7） |
| `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` | キー 2 つ（§8） |
| `docs/adr/ADR-1065-calendar-view-component-fullcalendar-v6.md`・`docs/adr/README.md` | What 6 に 1 文・索引（§8） |
| `.claude-pipeline/active-work.d/release-schedule-gcal-create-drag-impl.md` | 台帳（new-worktree.sh が作る形のまま・状態を更新） |

触らない（変えたら差し戻し）:
- 詳しく見る小窓・直す小窓・「他 N 件」の小窓（`ScheduleDayListPopover`）の見た目と動き。幕（`.schedule-popover-backdrop`）の規則と `--schedule-overlay-scrim`
- `TextFieldControl` の今ある種類（standard・karte・search・schedule・composer・login・product-edit）の規則
- `frontend/src/components/CalendarView.css`・`frontend/src/components/Button.*`
- backend・migrations・`.github/workflows/`・リポジトリ直下の `scripts/`・`frontend/scripts/`

## 2. schedule-utils.ts に純粋な関数を足す（`fitPopover` の次・`normalizeEvent` の前）

`ScheduleDraft` は `SchedulePageImpl.tsx` の中の型なので、ここでは日時の 5 項目だけの型を置く。`ScheduleDraft` はこの形を含むので、そのまま渡せる。

```ts
/** 下書きの日時の 5 項目（ScheduleDraft の一部・design §3.17 作り方 1） */
export interface DraftDates {
  startDate: string;
  startTime: string;
  endDate: string;
  endTime: string;
  allDay: boolean;
}

/** 作る小窓を仮の箱の横に置くときの、箱と小窓のあき(px)。--space-2 と同じ値（design §3.17 作り方 4） */
export const CREATE_POPOVER_GAP = 8;

/**
 * 下書きの日時 → 仮の箱の start・end・allDay（design §3.17 作り方 1・G47）。
 * 終日の end は endDate の次の日 0 時（FullCalendar の終日の end と同じ）。
 * 日時が読めない・end が start 以前のときは null（箱を出さない）。保存（saveEvent）と同じ combineDateTime を使う。
 */
export function draftToRange(draft: DraftDates): { start: Date; end: Date; allDay: boolean } | null {
  const start = combineDateTime(draft.startDate, draft.allDay ? "00:00" : draft.startTime);
  const end = draft.allDay
    ? addDays(combineDateTime(draft.endDate, "00:00"), 1)
    : combineDateTime(draft.endDate, draft.endTime);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end.getTime() <= start.getTime()) return null;
  return { start, end, allDay: draft.allDay };
}

/**
 * 箱の日時 → 下書きの日時（design §3.17 作り方 2）。openCreateRange と moveDraft の両方が使う。
 * 終日: endDate は end（無ければ start＋1 日）の 1 日前、時刻は 00:00／23:59。
 * 時刻つき: end が無ければ start＋1 時間（FullCalendar の既定と同じ）。
 */
export function rangeToDraftDates(start: Date, end: Date | null, allDay: boolean): DraftDates {
  if (allDay) {
    const endDay = end ?? addDays(start, 1);
    return {
      startDate: formatDateInput(start),
      startTime: "00:00",
      endDate: formatDateInput(addDays(endDay, -1)),
      endTime: "23:59",
      allDay: true,
    };
  }
  const timedEnd = end ?? new Date(start.getTime() + 60 * 60 * 1000);
  return {
    startDate: formatDateInput(start),
    startTime: formatTimeInput(start),
    endDate: formatDateInput(timedEnd),
    endTime: formatTimeInput(timedEnd),
    allDay: false,
  };
}

/**
 * 作る小窓で始まりの日付・時刻だけを直したとき、長さを保って終わりも同じだけずらす（design §3.17 作り方 1・Google と同じ）。
 * 今の下書きの長さが読めない（どちらかが読めない・0 以下）か、新しい始まりが読めないときは、始まりだけ入れ替える。
 */
export function shiftDraftStart<T extends DraftDates>(draft: T, nextStartDate: string, nextStartTime: string): T {
  const startOnly = { ...draft, startDate: nextStartDate, startTime: nextStartTime };
  if (draft.allDay) {
    const oldStart = combineDateTime(draft.startDate, "00:00");
    const oldEnd = combineDateTime(draft.endDate, "00:00");
    const nextStart = combineDateTime(nextStartDate, "00:00");
    if ([oldStart, oldEnd, nextStart].some((d) => Number.isNaN(d.getTime())) || oldEnd < oldStart) return startOnly;
    const days = Math.round((oldEnd.getTime() - oldStart.getTime()) / (24 * 60 * 60 * 1000));
    return { ...startOnly, endDate: formatDateInput(addDays(nextStart, days)) };
  }
  const oldStart = combineDateTime(draft.startDate, draft.startTime);
  const oldEnd = combineDateTime(draft.endDate, draft.endTime);
  const nextStart = combineDateTime(nextStartDate, nextStartTime);
  if ([oldStart, oldEnd, nextStart].some((d) => Number.isNaN(d.getTime())) || oldEnd <= oldStart) return startOnly;
  const nextEnd = new Date(nextStart.getTime() + (oldEnd.getTime() - oldStart.getTime()));
  return { ...startOnly, endDate: formatDateInput(nextEnd), endTime: formatTimeInput(nextEnd) };
}

/**
 * 作る小窓を仮の箱の横に置く（design §3.17 作り方 4・G43・Google の実測 R12-3）。
 * 横: 箱の右＋gap。入らなければ箱の左−小窓の幅−gap。
 * 縦: 「箱の上の端」と「画面の真ん中に置いた位置」の小さい方を、margin〜(画面の高さ−小窓の高さ−margin) に収める。
 * 箱が無いとき（C キー・作成ボタン）は fitPopover と同じ真ん中。
 */
export function fitCreatePopover(
  anchor: AnchorRect | null,
  size: PopoverSize,
  viewport: PopoverViewport,
  margin: number,
  gap: number,
): { left: number; top: number } {
  if (!anchor) return fitPopover(null, size, viewport, margin);
  const maxLeft = Math.max(margin, viewport.width - size.width - margin);
  const maxTop = Math.max(margin, viewport.height - size.height - margin);
  const rightSide = anchor.right + gap;
  const leftSide = anchor.left - size.width - gap;
  const left = clamp(rightSide + size.width > viewport.width - margin ? leftSide : rightSide, margin, maxLeft);
  const top = clamp(Math.min(anchor.top, (viewport.height - size.height) / 2), margin, maxTop);
  return { left, top };
}
```

`formatDateInput`・`formatTimeInput`・`addDays`・`clamp`・`combineDateTime` は同じファイルの既存の関数。`formatDateInput`・`formatTimeInput` は `export function` の宣言なので、ファイルの後ろにあっても使える。

## 3. 金型 CalendarView に口を 2 つ足す（ADR-1065 What 6）

### 3-1. calendarView.utils.ts（`onMoreClick` の行 `:84` の次）

前:
```ts
  /** 月の「ほか N 件」。渡したときは onDayClick を呼ばずにこちらを呼ぶ */
  onMoreClick?: (date: Date, rect: CalendarViewRect | null) => void;
  ariaLabel: string;
```
後:
```ts
  /** 月の「ほか N 件」。渡したときは onDayClick を呼ばずにこちらを呼ぶ */
  onMoreClick?: (date: Date, rect: CalendarViewRect | null) => void;
  /** 四角を知りたい予定の id。onEventRect と組で渡す */
  trackEventId?: string;
  /**
   * trackEventId の予定の四角（画面の座標）。描いた後・動かした後・長さを変えた後・巻き上げた後・包みの大きさが変わった後に呼ぶ。
   * 見えない（visibility: hidden・幅 0）・描かれていないときは null。つかんでいる間・引いている間は呼ばず、離した後に 1 回呼ぶ。
   */
  onEventRect?: (id: string, rect: CalendarViewRect | null) => void;
  ariaLabel: string;
```

### 3-2. CalendarView.tsx

(1) 受け取る（`:66` の `onMoreClick,` の次）に `trackEventId,`・`onEventRect,` を足す。

(2) `wrapperRef`（`:74`）の次に、覚えておく物と測る関数を足す。最新の `trackEventId`・`onEventRect` は ref で読む（FullCalendar に渡す関数を作り直さないため）。

```tsx
  // trackEventId の予定の要素と、つかんでいる間かどうか（design schedule-gcal-clone §3.17 作り方 4）
  const trackedElRef = useRef<HTMLElement | null>(null);
  const draggingRef = useRef(false);
  const trackRef = useRef({ trackEventId, onEventRect });
  trackRef.current = { trackEventId, onEventRect };

  const emitTrackedRect = useCallback(() => {
    const { trackEventId: id, onEventRect: emit } = trackRef.current;
    if (!id || !emit || draggingRef.current) return;
    const el = trackedElRef.current;
    if (!el || !el.isConnected) {
      emit(id, null);
      return;
    }
    const rect = rectOf(el);
    const hidden = getComputedStyle(el).visibility === 'hidden' || !rect || rect.width === 0;
    emit(id, hidden ? null : rect);
  }, []);
```
`useCallback` を react の import に足す（`:9-31` の import の中の react の行）。

(3) harness の style の変化を見る。覚えた要素が変わるたびに付け直す。`trackedElRef` は ref なので、付け直しのきっかけに state `trackedEl` を 1 つ持つ（`setTrackedEl` は mount・unmount の時だけ呼ぶ）。

```tsx
  const [trackedEl, setTrackedEl] = useState<HTMLElement | null>(null);

  useEffect(() => {
    if (!trackedEl || typeof MutationObserver === 'undefined') return;
    const target =
      trackedEl.closest<HTMLElement>('.fc-timegrid-event-harness, .fc-daygrid-event-harness') ?? trackedEl;
    const observer = new MutationObserver(() => emitTrackedRect());
    observer.observe(target, { attributes: true, attributeFilter: ['style'] });
    return () => observer.disconnect();
  }, [trackedEl, emitTrackedRect]);
```
`useState` を react の import に足す（無ければ）。

(4) 時間割の巻き上げで測り直す（`wrapperRef` の中の scroll を capture で受ける）:
```tsx
  useEffect(() => {
    const el = wrapperRef.current;
    if (!el) return;
    const onScroll = () => emitTrackedRect();
    el.addEventListener('scroll', onScroll, true);
    return () => el.removeEventListener('scroll', onScroll, true);
  }, [emitTrackedRect]);
```

(5) 今の ResizeObserver（`:123-131`）の中で、`updateSize()` の次に `emitTrackedRect();` を足す（依存の配列は `[emitTrackedRect]` にする）。

(6) FullCalendar の口（`:294-314`）:

前:
```tsx
        eventDidMount={(arg) => {
          const color = (arg.event.extendedProps.source as CalendarViewEvent).color;
          if (color) arg.el.style.setProperty('--comp-calendar-owner-color', color);
        }}
```
後:
```tsx
        eventDidMount={(arg) => {
          const color = (arg.event.extendedProps.source as CalendarViewEvent).color;
          if (color) arg.el.style.setProperty('--comp-calendar-owner-color', color);
          if (trackRef.current.trackEventId && arg.event.id === trackRef.current.trackEventId) {
            trackedElRef.current = arg.el;
            setTrackedEl(arg.el);
            requestAnimationFrame(() => emitTrackedRect());
          }
        }}
        eventWillUnmount={(arg) => {
          // 別の日へ動かすと、新しい要素の mount の後に古い要素の unmount が来ることがある。同じ要素のときだけ忘れる
          if (trackedElRef.current === arg.el) {
            trackedElRef.current = null;
            setTrackedEl(null);
            requestAnimationFrame(() => emitTrackedRect());
          }
        }}
        eventDragStart={() => { draggingRef.current = true; }}
        eventDragStop={() => { draggingRef.current = false; }}
        eventResizeStart={() => { draggingRef.current = true; }}
        eventResizeStop={() => { draggingRef.current = false; }}
```

前:
```tsx
        eventDrop={(arg) => {
          onEventMove?.(arg.event.id, arg.event.start as Date, arg.event.end, arg.event.allDay, arg.revert);
        }}
        eventResize={(arg) => {
          onEventResize?.(arg.event.id, arg.event.start as Date, arg.event.end, arg.revert);
        }}
```
後:
```tsx
        eventDrop={(arg) => {
          draggingRef.current = false;
          onEventMove?.(arg.event.id, arg.event.start as Date, arg.event.end, arg.event.allDay, arg.revert);
          requestAnimationFrame(() => emitTrackedRect());
        }}
        eventResize={(arg) => {
          draggingRef.current = false;
          onEventResize?.(arg.event.id, arg.event.start as Date, arg.event.end, arg.revert);
          requestAnimationFrame(() => emitTrackedRect());
        }}
```
（FullCalendar 6.1.22 は `eventDragStop` の後に `eventDrop` を呼ぶ順のため、`eventDrop` の中でも偽に戻しておく。順は interaction の `index.js:1286`（DragStart）・`:1371`（DragStop）・`:1595`（ResizeStart）・`:1663`（ResizeStop）で設計時に確かめた。）

FullCalendar の型や名前を金型の外へ出さない（口の型は `CalendarViewRect` と string だけ）。

## 4. 予定の画面: 仮の箱を下書きから出す（G45〜G49・SSOT）

`frontend/src/pages/schedule/SchedulePageImpl.tsx`:

(1) import（`:34-67` の `./schedule-utils` の中）に `draftToRange`・`rangeToDraftDates`・`shiftDraftStart`・`fitCreatePopover`・`CREATE_POPOVER_GAP` を足す。

(2) 宣言 `:952`:
前: `const [pendingRange, setPendingRange] = useState<{ start: Date; end: Date; allDay: boolean } | null>(null);`
後:
```tsx
  // 時間割を押して作ったときだけ真。箱の日時は draft から出す（design §3.17 作り方 1・SSOT）
  const [pendingVisible, setPendingVisible] = useState(false);
  // 予定の画面の時間割の箱。作る小窓の「外を押したら閉じる」の内側の判定に使う（作り方 3）
  const calendarAreaRef = useRef<HTMLDivElement | null>(null);
```

(3) `:1223` `setPendingRange(null)` → `setPendingVisible(false)`。`:1249` も同じ。`:1590` も同じ。

(4) openCreateRange（`:1227-1245`）:
前:
```tsx
    // 終日の終わりは FullCalendar では「次の日 0:00」。小窓の終わりの日は 1 日戻す
    const lastDay = allDay ? addDays(end, -1) : end;
    setDraft({
      title: "",
      category: "meeting",
      startDate: formatDateInput(start),
      startTime: allDay ? "00:00" : formatTimeInput(start),
      endDate: formatDateInput(lastDay),
      endTime: allDay ? "23:59" : formatTimeInput(end),
      allDay,
      visibleToStaff: true,
      description: "",
      location: "",
      addMeet: false,
    });
    setPendingRange({ start, end, allDay });
```
後:
```tsx
    // 終日の終わりは FullCalendar では「次の日 0:00」。小窓の終わりの日は 1 日戻す（rangeToDraftDates）
    setDraft({
      title: "",
      category: "meeting",
      ...rangeToDraftDates(start, end, allDay),
      visibleToStaff: true,
      description: "",
      location: "",
      addMeet: false,
    });
    setPendingVisible(true);
```
`addDays` がこのファイルでほかに使われていなければ、import から消す（tsc・eslint が教える）。

(5) `moveDraft` を `itemById`（`:1258`）の前に足す:
```tsx
  // 仮の箱を動かした・長さを変えた → 下書きの日時だけ直す。裏側へは何も送らない（作り方 2・G48）
  const moveDraft = (start: Date, end: Date | null, allDay: boolean) => {
    setDraft((current) => ({ ...current, ...rangeToDraftDates(start, end, allDay) }));
  };
```

(6) `calendarEvents`（`:1260-1284`）を `useMemo` で包み、仮の箱を下書きから出す:
```tsx
  const pendingBox = pendingVisible ? draftToRange(draft) : null;
  const calendarEvents: CalendarViewEvent[] = useMemo(() => [
    ...(pendingBox
      ? [{
          id: "pending",
          title: draft.title.trim() || t("schedule.noTitle"),
          start: pendingBox.start,
          end: pendingBox.end,
          allDay: pendingBox.allDay,
          color: currentOwnerUserId != null
            ? getOwnerMeta(ownerByUserId, currentOwnerUserId, currentOwnerUserId).color
            : undefined,
          editable: true,
        }]
      : []),
    ...visibleEvents.map((item) => ({ /* 今の :1274-1282 のまま */ })),
    ...toHolidayEvents(holidaysQ.data?.holidays),
  ], [
    pendingBox?.start.getTime(), pendingBox?.end.getTime(), pendingBox?.allDay,
    draft.title, visibleEvents, holidaysQ.data, ownerByUserId, currentOwnerUserId, t,
    // canMoveItem は canEditItem（currentOwnerUserId・canManageOwners）から決まる
    canManageOwners,
  ]);
```
- `pendingBox` は毎回作り直されるので、依存には `getTime()` の数と `allDay` を入れる（eslint の `react-hooks/exhaustive-deps` が `pendingBox` を求めたら、`// eslint-disable-next-line react-hooks/exhaustive-deps -- pendingBox は start・end の時刻と allDay で追う（design §3.17）` を 1 行付ける）。中で使う値（`visibleEvents`・`holidaysQ.data`・`ownerByUserId`・`currentOwnerUserId`・`canManageOwners`・`t`・`draft.title`）は 1 つも削らない。
- `useMemo` は、このファイルの今ある hooks の並びの中で、早い return より前に置かれていることを確かめる（`:1258` は hooks の後ろの位置。早い return があればその前へ移す。分からなければ止める）。

(7) `CalendarView` の口（`:1563-1592`）:
前:
```tsx
                  <div className="schedule-calendar">
```
後:
```tsx
                  <div className="schedule-calendar" ref={calendarAreaRef}>
```
前:
```tsx
                      onDayClick={(date) => {
                        setAnchorDate(date);
                        setView("day");
                      }}
                      onSelectRange={handleSelectRange}
                      onEventMove={patchMoved}
                      onEventResize={(id, start, end, revert) => patchMoved(id, start, end, itemById(id)?.allDay ?? false, revert)}
```
後:
```tsx
                      onDayClick={(date) => {
                        setAnchorDate(date);
                        setView("day");
                        // 日の数字は時間割の中なので「外を押す」で閉じない。日表示へ移るときに作る小窓を閉じる（作り方 3）
                        setPopover((current) => (current?.mode === "create" ? null : current));
                      }}
                      onSelectRange={handleSelectRange}
                      onEventMove={(id, start, end, allDay, revert) => {
                        if (id === "pending") {
                          moveDraft(start, end, allDay);
                          return;
                        }
                        void patchMoved(id, start, end, allDay, revert);
                      }}
                      onEventResize={(id, start, end, revert) => {
                        if (id === "pending") {
                          // onEventResize は終日かどうかを渡さない。仮の箱は下書きから取る（作り方 2）
                          moveDraft(start, end, draft.allDay);
                          return;
                        }
                        void patchMoved(id, start, end, itemById(id)?.allDay ?? false, revert);
                      }}
                      trackEventId="pending"
                      onEventRect={handlePendingRect}
```
`setPopover` が関数の形を受けない作りなら（`useState` なので受ける）そのまま。

(8) `handlePendingRect` を `moveDraft` の次に足す。四角が前と同じなら state を変えない。`null` の間は前の四角のまま:
```tsx
  // 仮の箱の四角を作る小窓の置き場所に使う（作り方 4）。null の間は前の四角（無ければ押した点）のまま
  const handlePendingRect = useCallback((id: string, rect: AnchorRect | null) => {
    if (id !== "pending" || !rect) return;
    setPopover((current) => {
      if (!current || current.mode !== "create") return current;
      const prev = current.anchor;
      if (prev && prev.top === rect.top && prev.left === rect.left && prev.right === rect.right && prev.bottom === rect.bottom) {
        return current;
      }
      return { ...current, anchor: rect };
    });
  }, []);
```
`CalendarViewRect` と `AnchorRect` は同じ 6 項目（`calendarView.utils.ts:20`・`schedule-utils.ts:6`）。型が合わなければ止める。

(9) `SchedulePopover` を呼ぶ所（`:1618-1640`）に `placement={pendingVisible ? "box" : "point"}` と `calendarAreaRef={calendarAreaRef}` を足す。

## 5. 予定の画面: 作る小窓の幕を外し、外を押したら閉じる（G44）

`SchedulePopover`（`:224-`）:

(1) 受け取る物に足す:
```tsx
  /** 作る小窓を仮の箱の横に置くか（"box"）、押した点の横に置くか（"point"）（design §3.17 作り方 4） */
  placement: "box" | "point";
  /** 予定の画面の時間割の箱。作る小窓は、ここと小窓の外を押したら閉じる（作り方 3） */
  calendarAreaRef: RefObject<HTMLDivElement | null>;
```
`RefObject` を `import type { CSSProperties, ReactNode } from "react";`（`:10`）に足す。

(2) 置き場所: `usePopoverPlacement(anchor)`（`:259`）を `usePopoverPlacement(anchor, creating && placement === "box")` にし、`usePopoverPlacement`（`:157-191`）に 2 つ目の引数 `besideBox: boolean` を足す。`place` の中:
```tsx
    const size = { width: rect.width, height: rect.height };
    const viewport = { width: window.innerWidth, height: window.innerHeight };
    const next = besideBox
      ? fitCreatePopover(anchor, size, viewport, POPOVER_MARGIN, CREATE_POPOVER_GAP)
      : fitPopover(anchor, size, viewport, POPOVER_MARGIN);
```
`useCallback` の依存を `[anchor, besideBox]` にする。ほかの呼び出し（`ScheduleDayListPopover` など）は 2 つ目に `false` を渡す（`grep -n "usePopoverPlacement(" SchedulePageImpl.tsx` で全部探す）。

(3) 幕（`:289`）:
前: `      <div className="schedule-popover-backdrop" onClick={onClose} />`
後: `      {!creating && <div className="schedule-popover-backdrop" onClick={onClose} />}`
「他 N 件」の幕（`:739`）は変えない。

(4) 外を押したら閉じる（作る小窓だけ）。`titleRef` の effect（`:269-271`）の次に:
```tsx
  // 作る小窓は幕が無い。時間割と小窓の外を押したら閉じる（design §3.17 作り方 3・G44）。押した先の部品が止めても届くよう capture で見る
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  useEffect(() => {
    if (!creating) return;
    const onPointerDown = (event: PointerEvent) => {
      const path = event.composedPath();
      const popoverEl = popoverRef.current;
      const calendarEl = calendarAreaRef.current;
      if (popoverEl && path.includes(popoverEl)) return;
      if (calendarEl && path.includes(calendarEl)) return;
      onCloseRef.current();
    };
    document.addEventListener("pointerdown", onPointerDown, true);
    return () => document.removeEventListener("pointerdown", onPointerDown, true);
  }, [creating, popoverRef, calendarAreaRef]);
```

## 6. 予定の画面: 作る小窓の中身（G42・G45・G47・G50）

作る小窓（`creating` が真）のときだけ形を変える。詳しく見る（`mode === "detail"`）・直す（`mode === "edit"`）は今の JSX のまま残す（同じ JSX を条件で分けてよいが、直す小窓の DOM・文言・順番は変えない）。

(1) 小窓の class（`:290`）:
前: `<div ref={popoverRef} className="schedule-popover" ...>`
後: `` <div ref={popoverRef} className={`schedule-popover${creating ? " schedule-popover--create" : ""}`} ...> ``

(2) 題名（`:366-376`）を作るときだけ次の形に:
```tsx
            <div className="schedule-create-row schedule-create-row--title">
              <span className="schedule-create-row__icon" aria-hidden="true" />
              <TextFieldControl
                variant="schedule-title"
                value={draft.title}
                onChange={(event) => onDraftChange({ ...draft, title: event.target.value })}
                placeholder={t("schedule.addTitle")}
                aria-label={t("schedule.eventTitle")}
                ref={titleRef}
              />
            </div>
```
直す小窓は今の `<label className="schedule-field">…variant="schedule"…placeholder={t("schedule.eventTitle")}` のまま。

(3) 日時（`:378-451`）: 作るときの閉じた 1 行は
```tsx
              <div className="schedule-create-row">
                <ClockIcon size={20} aria-hidden="true" className="schedule-create-row__icon" />
                <Button variant="ghost" size="md" fullWidth layoutClassName="schedule-popover__line" onClick={() => setDateOpen(true)}>
                  <span className="schedule-popover__line-text">{formatDraftDateLine(draft, t, i18n.language)}</span>
                </Button>
              </div>
```
（絵は Button の外・1 列目。`ClockIcon` などの絵の部品が `className` を受けなければ、`<span className="schedule-create-row__icon"><ClockIcon size={20} aria-hidden="true" /></span>` で包む。以下同じ。）
開いた日時の欄（終日の切り替え・始まり・終わり）は今の中身のまま、`<div className="schedule-create-row">` の 2 列目（1 列目は `ClockIcon`）に入れる。**作るときだけ**、始まりの日付・時刻の `onChange`（`:400`・`:410`）を次にする（終わりの欄・直す小窓は今のまま）:
```tsx
onChange={(event) => onDraftChange(creating ? shiftDraftStart(draft, event.target.value, draft.startTime) : { ...draft, startDate: event.target.value })}
onChange={(event) => onDraftChange(creating ? shiftDraftStart(draft, draft.startDate, event.target.value) : { ...draft, startTime: event.target.value })}
```

(4) 種類（`:452-473`）: 作るときは見出しの span を出さず、`<div className="schedule-create-row">` に `CategoryIcon`（`SCHEDULE_POPOVER_ICONS.category`）と `SelectControl`（`aria-label={t("schedule.category")}` を足す）を並べる。直す小窓は今のまま。

(5) Meet（`:476-485`）・社員にも見せる（`:487-496`）: 作るときは `<div className="schedule-create-row">` の 1 列目に `MeetIcon`（`.meet`）・`ShareIcon`（`.share`）、2 列目に今の `schedule-field schedule-field--inline`（文字＋切り替え）をそのまま置く。出す条件（`meetAvailable && !item?.meetUrl`・`canChangeVisibility`）は変えない。`joinMeetLink`（`:475`）は作るときは null（item が無い）なので触らない。

(6) 場所・説明（`:498-533`）: 作るときの閉じた 1 行は (3) と同じ形（1 列目に `LocationIcon`・`DescriptionIcon`、2 列目に `size="md"` の Button と文字）。開いた欄は 2 列目に今の中身。

(7) 下（`:537-559`）: 作るときだけ
```tsx
            <>
              {!(dateOpen && locationOpen && descriptionOpen) && (
                <Button
                  variant="ghost"
                  onClick={() => {
                    setDateOpen(true);
                    setLocationOpen(true);
                    setDescriptionOpen(true);
                  }}
                >
                  {t("schedule.moreOptions")}
                </Button>
              )}
              <Button variant="primary" onClick={onSave} disabled={!draft.title.trim()}>
                {t("common.save")}
              </Button>
            </>
```
（「キャンセル」は出さない。× と Esc は今のまま。）直す小窓（`mode === "edit"`）は今の「保存」「キャンセル」のまま。詳しく見るも今のまま。
`locationOpen`・`descriptionOpen` を真にしても、場所・説明に文字が入っていれば今も開いている（`showLocation`・`showDescription`）。「全部開いたら出さない」は `showDate && showLocation && showDescription` で判定する（上の式の代わりにこちらを使う）。

(8) 絵の取り出し（`:251-256` の並び）に足す:
```tsx
  const CategoryIcon = SCHEDULE_POPOVER_ICONS.category;
  const MeetIcon = SCHEDULE_POPOVER_ICONS.meet;
  const ShareIcon = SCHEDULE_POPOVER_ICONS.share;
```

## 7. 金型・トークン・見た目

### 7-1. icons.tsx

outline の import（`:54-90`）に `VideoCameraIcon as VideoCameraOutlineIcon,` を足す（`CalendarIcon`・`UsersIcon as UsersOutlineIcon` は既に在る・`:62`・`:58`）。hi() の並び（`:137-155` 付近）に:
```ts
const CalendarOutline     = hi(CalendarIcon);
const VideoCameraOutline  = hi(VideoCameraOutlineIcon);
```
（`CalendarBlank = hi(CalendarIcon)`（`:142`）が既に在るので、`CalendarOutline` は作らず `CalendarBlank` を使ってもよい。どちらかに決め、同じ物を 2 つ作らない。）
`SCHEDULE_POPOVER_ICONS`（`:369-376`）の `description` の次に:
```ts
  category:    CalendarBlank,          // CalendarIcon outline — 種類の行（便12）
  meet:        VideoCameraOutline,     // VideoCameraIcon outline — Google Meet の行（便12）
  share:       UsersOutline,           // UsersIcon outline — 社員にも見せるの行（便12）
```

### 7-2. tokens.css（`:410` `--schedule-popover-max-h` の次の行）
```css
  --schedule-create-popover-width:  37.5rem;  /* 作る小窓の幅（600px・Google の実測 598px・G42） */
  --schedule-create-popover-radius: 1.75rem;  /* 作る小窓の角の丸み（28px・G42） */
  --schedule-create-popover-bg:     var(--bg-subtle); /* 作る小窓の地（G42） */
  --schedule-create-icon-col:       2.75rem;  /* 作る小窓の絵の列の幅（絵 20px＋あき 24px・G42） */
  --schedule-create-title-size:     1.375rem; /* 作る小窓の題名の文字（22px・G42） */
```
ダークの段には足さない（色は `--bg-subtle` を指すだけ）。

### 7-3. schedule.css

(1) `:7-8` の 2 行（`--schedule-popover-width: 20rem;`・`--schedule-popover-max-h: 34rem;`）を消す（tokens.css `:409-410` の 1 か所にする・値は同じ）。ほかの写しの行（`:9-` の `--schedule-month-cell-min-h` など）は今回は触らない。

(2) `.schedule-popover__line-text`（`:481-485`）の次に、作る小窓だけの規則:
```css
/* 作る小窓（design §3.17 作り方 5・G42）。詳しく見る・直す小窓は上の規則のまま */
.schedule-popover.schedule-popover--create {
  width: min(var(--schedule-create-popover-width), calc(100vw - var(--space-6)));
  padding: var(--space-4) var(--space-6) var(--space-6);
  border: none;
  border-radius: var(--schedule-create-popover-radius);
  background: var(--schedule-create-popover-bg);
}

.schedule-popover--create .schedule-popover__body--form {
  gap: 0;
}

.schedule-create-row {
  display: grid;
  grid-template-columns: var(--schedule-create-icon-col) minmax(0, 1fr);
  align-items: center;
  min-height: var(--space-10);
}

.schedule-create-row__icon {
  grid-column: 1;
  color: var(--text-secondary);
}

.schedule-create-row > :not(.schedule-create-row__icon) {
  grid-column: 2;
}
```
- 題名の行・日時の行に 1 列目の絵が無い（題名は空の span）ときも、中身は 2 列目に入る。
- `--space-10` が tokens.css に無ければ止める（`grep -n "\-\-space-10" frontend/src/tokens.css`）。
- 値はすべて var()。`npm run check:all` の見張り（色・数値の直書き）で緑を確かめる。

### 7-4. 金型 TextFieldControl に種類 `"schedule-title"`（ADR-144・PO 承認済み）

`frontend/src/components/TextField.tsx:35`:
前: `export type TextFieldVariant = "standard" | "karte" | "search" | "schedule" | "composer" | "login" | "product-edit";`
後: `export type TextFieldVariant = "standard" | "karte" | "search" | "schedule" | "schedule-title" | "composer" | "login" | "product-edit";`

`frontend/src/components/FormField.css` の `.comp-input--schedule`（`:382-390`）の次に:
```css
/* schedule-title: 予定の作る小窓の題名（下線だけ・Google の実測 22px・schedule-gcal-clone design §3.17 G42） */
.comp-field__input.comp-input--schedule-title {
  min-height: var(--space-10);
  padding: 0;
  border: none;
  border-bottom: 1px solid var(--border);
  border-radius: 0;
  background-color: transparent;
  font-size: var(--schedule-create-title-size);
  line-height: normal;
}

.comp-field__input.comp-input--schedule-title:focus,
.comp-field__input.comp-input--schedule-title:focus-visible {
  border-bottom: 2px solid var(--accent);
  box-shadow: none;
  outline: none;
}
```
- `1px`・`2px` の線の太さを直書きと見張りが止めたら、FormField.css の今の書き方（`grep -n "border.*px" frontend/src/components/FormField.css`）に合わせ、それでも止まるなら止めて返す。
- 金型の今の focus の規則（`.comp-field__input:focus` など）が `outline` や `box-shadow` を付けていて、上の規則で消すことが見張りに止められたら、止めて返す（勝手に別の書き方にしない）。

`frontend/src/components/TextField.stories.tsx` の `ControlVariants`（`:111-121`）の `variant="schedule"` の例の次に:
```tsx
      <TextFieldControl variant="schedule-title" placeholder="Add title" aria-label="Schedule title" />
```
`name` の文字（`:112`）に `schedule-title` を足す。

## 8. 文言・ADR

### 8-1. ja.json・en.json の `schedule`（`:3211-` の中・`"eventTitle"`（`:3310`）の次の行）
ja:
```json
    "addTitle": "タイトルを追加",
    "moreOptions": "その他のオプション",
```
en:
```json
    "addTitle": "Add title",
    "moreOptions": "More options",
```
（`addTitle` は別の段（`:2606`・`:3987`）にも在るが、段が違うので重ならない。`schedule` の段の中に同じキーが無いことを足す前に確かめる。）

### 8-2. ADR-1065 What 6（`docs/adr/ADR-1065-calendar-view-component-fullcalendar-v6.md:20`）
前:
```
6. 送るボタン・見出しは FullCalendar の物を使わず、呼ぶ側が金型 Button で置く。選択・動かす・長さを変える・他 N 件の小窓は、呼ぶ側が口を渡したときだけ使う。
```
後:
```
6. 送るボタン・見出しは FullCalendar の物を使わず、呼ぶ側が金型 Button で置く。選択・動かす・長さを変える・他 N 件の小窓は、呼ぶ側が口を渡したときだけ使う。予定の四角を知りたいときは、呼ぶ側が対象の id と口（onEventRect）を渡す。金型はその予定の四角だけを返す（2026-11-10 便12・schedule-gcal-clone design §3.17）。
```
表の「設計・根拠」の行（`:10`）の終わりに `。2026-11-10 改訂（What 6 の四角の口）: [schedule-gcal-clone design.md §3.17](../handoff/schedule-gcal-clone/design.md)、[card-bin12.md](../handoff/schedule-gcal-clone/card-bin12.md)` を足す。
リポジトリ直下で `node scripts/generate-adr-index.js` を流し、`docs/adr/README.md` の差分も commit に入れる。

## 9. 試験

### 9-1. 新しく足す
- `schedule-utils.test.ts`（import の並び `:5-18` に足す）:
  - `draftToRange`: 時刻つき 10:00〜11:00 → start 10:00・end 11:00／終日 1 日（11-10〜11-10）→ end が 11-11 0:00／終日 2 日（11-10〜11-11）→ end が 11-12 0:00／startDate が空 → null／end が start と同じ → null
  - `rangeToDraftDates`: 終日 1 日（11-10 0:00〜11-11 0:00）→ endDate 11-10・時刻 00:00/23:59／終日 2 日／時刻つき 10:00〜11:30／時刻つき end なし → 1 時間後／終日 end なし → endDate＝startDate
  - 往復: `draftToRange(rangeToDraftDates(s, e, a))` が `{ s, e, a }`（終日 1 日・終日 2 日・時刻つき）
  - `shiftDraftStart`: 10:00〜11:00 の始まりを 15:00 → 15:00〜16:00／日付を 1 日進める → 終わりの日付も 1 日進む／終日 2 日の始まりを 3 日進める → 終わりも 3 日進む／新しい始まりが空 → 終わりは今のまま
  - `fitCreatePopover`: 右に入る（left＝anchor.right＋8）／右に入らない（left＝anchor.left−幅−8）／縦は anchor.top と (vh−h)/2 の小さい方／下にはみ出す → vh−h−margin／anchor なし → 真ん中（`fitPopover(null,…)` と同じ）
- `CalendarView.test.tsx`（`fcProps()` で口を呼ぶ・`requestAnimationFrame` は `vi.useFakeTimers()` か `vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => { cb(0); return 0; })` で即時に）:
  - `trackEventId="p"` と `onEventRect` を渡し、`eventDidMount({ event: { id: "p", extendedProps: { source: {} } }, el })` を呼ぶと `onEventRect("p", 四角)` が呼ばれる。`id: "x"` では呼ばれない
  - 同じ要素のまま `eventDrop`（start だけ変えた arg）を呼ぶと、`onEventRect` がもう一度呼ばれる（要素を作り直さない動かし方）
  - 新しい要素 B で `eventDidMount` の後、古い要素 A で `eventWillUnmount` を呼んでも、続く `eventResize` の後の `onEventRect` は B の四角（`getBoundingClientRect` を要素ごとに違う値にして見分ける）
  - `eventDragStart` の後は `onEventRect` を呼ばない（ResizeObserver の代わりに `eventDrop` を呼ばずに巻き上げの scroll を wrapper に送って確かめる）、`eventDrop` の後に 1 回呼ぶ
- `SchedulePageImpl.test.tsx`（`describe("SchedulePage on CalendarView")` の中・`selectRange`・`pendingOf` を使う）:
  - 作る小窓に `.schedule-popover-backdrop` が 0 個。予定を押した詳しく見る小窓では 1 個
  - 仮の箱が `editable: true`。題名に「試し」と入れると箱の title が「試し」、空なら `schedule.noTitle`
  - 作る小窓で日時の 1 行を開き、始まりの時刻を 15:00 にすると、箱の start が 15:00・end が 16:00（10:00〜11:00 から）
  - `calendarProps.current.onEventMove("pending", 水 14:00, 水 15:00, false, revert)` → 日時の 1 行が水曜 14 時〜15 時の文、`api.patch`・`api.post` が 0 回、`revert` も 0 回。続けて題名を入れて保存 → `api.post` の `start_datetime`・`end_datetime` が水 14:00・15:00 の ISO
  - `onEventResize("pending", 10:00, 11:30, revert)` → 終わりの時刻が 11:30
  - 終日 2 日の箱（月表示で `selectRange` 2 日）に `onEventResize("pending", …)` → 下書きの allDay が真のまま（箱の allDay が真）
  - 終日の箱に `onEventMove("pending", 1 週後, 1 週後＋2 日, true, revert)` → 箱の start・end が 1 週後
  - `document.body` に `pointerdown` を送ると小窓が閉じ、仮の箱が消える。時間割の箱（`.schedule-calendar`）と小窓の中の `pointerdown` では閉じない
  - 下のボタンが「その他のオプション」「保存」の順で、`common.cancel` のボタンが無い。「その他のオプション」を押すと日時の欄（`schedule.time` の欄）・場所・説明の欄が開き、「その他のオプション」が消える
  - `onEventRect("pending", 四角)` を呼ぶと、小窓の left が `四角.right + 8`（K1 と同じく `getBoundingClientRect` を差し替えて測る）

### 9-2. 今ある試験で直してよいもの（これ以外は直さない）
- 作る小窓の題名を `ByPlaceholderText(i18n.t("schedule.eventTitle"))` で探している所（`SchedulePageImpl.test.tsx:163,267,354,360,385,393,419,442,445,503,516,544,592,600,641`・`SchedulePageCache.test.tsx:125`）: 同じ種類の `ByLabelText(i18n.t("schedule.eventTitle"))` に替える（題名の欄の aria-label は変えないため）。直す小窓を探している所（`:190` など）で `ByLabelText` が 2 つ以上当たって落ちたら止めて返す。
- `:645` `expect(pending?.editable).toBe(false)` → `toBe(true)`（G45・設計どおりの変更）。
- 作る小窓で `common.cancel` のボタンを押して閉じている試験があれば、× のボタン（`common.close`）で閉じる形に替える。
- 上のどれでも無い試験が落ちたら直さず止めて返す。

## 10. 終わりの確かめと返し方

- `npx vitest run src/components/CalendarView.test.tsx src/pages/schedule/ src/components/TextField`・`npx tsc --noEmit`・`npm run check:all` が全部緑。`node scripts/generate-adr-index.js --check` が緑。
- `git diff origin/main --stat` の一覧が §1 の触るファイルだけ。
- commit（1 つでよい）→ `git push -u origin release/schedule-gcal-create-drag-impl`。PR は作らない（Opus が作る）。
- 返すもの: `DONE` と HEAD の sha、上の確かめの生出力のファイルの場所、§9-2 で直した試験の行の一覧。止めたときは `NEEDS_DECISION:` か `BLOCKED:` と、止めた所・理由・生出力。
