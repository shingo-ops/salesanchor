# 実装カード 便2: 予定の画面を金型 CalendarView に載せ替える（2026-11-07）

- 設計: `docs/handoff/schedule-gcal-clone/design.md`（PO 承認済み・3 回目の審査 APPROVE）§3.1〜3.3・§3.6・§3.7・§4 便2・§6・§8
- 土台: origin/main befd39e9f。ブランチ `release/schedule-on-calendarview-b`
- 成功条件: G2・G4・G5・G6・G8・G9・G10・G13（design.md §2）
- 対象 ADR: ADR-1065（金型）・ADR-067（トークン）・ADR-144（金型を使う）・ADR-1057（Google へ送る決まり）・ADR-027（文言は t()）
- 行番号はすべて origin/main 757d7d795 の値（befd39e9f でも予定の画面・裏側のファイルは同じ。文言の行だけ befd39e9f の値）。

## 0. 作業者への決まり

- このカードに書いたこと以外はしない。迷ったら止めて `NEEDS_DECISION:` で返す。
- 色・寸法の直書き禁止（`#hex`・`px` の新規直書きは不可。試験の中の色も `rgb(…)` の形で書く・guard-hex-increase は試験も数える）。
- 画面の文字は `t()` だけ。ja/en の両方に同じキー。
- 試験は Mac で回さない。クラウドの作業場所で回す。

## 1. 触るファイルと触らないファイル

触る:
| ファイル | 中身 |
|---|---|
| `frontend/src/pages/schedule/SchedulePageImpl.tsx` | 自前の時間割を消し、`CalendarView` を置く（§2） |
| `frontend/src/pages/schedule/schedule-utils.ts` | `layoutDay`・`DayLayoutItem` を消す。`eventNumericId`・`toCalendarEnd` を足す（§3） |
| `frontend/src/pages/schedule/schedule-utils.test.ts` | 消した関数の試験を消し、足した関数の試験を足す |
| `frontend/src/pages/schedule/SchedulePageImpl.test.tsx` | `CalendarView` を差し替えて試験を書き直す（§6） |
| `frontend/src/pages/schedule/SchedulePageCache.test.tsx` | 同じ差し替えを足す（中身の確かめは変えない） |
| `frontend/src/pages/schedule.css` | 使われなくなった class を消す。`.schedule-calendar` を足す（§4） |
| `frontend/src/tokens.css` | `--schedule-row-height` を `48px` → `96px`（:403 の 1 か所だけ。§5） |
| `backend/app/services/calendar_service.py` | `_to_google_event_body` の終日の枝だけ（:648-650。§7） |
| `backend/tests/test_calendar_service.py` | 試験を足す（§7） |

触らない（変えたら差し戻し）:
- `frontend/src/components/CalendarView.tsx`・`CalendarView.css`・`calendarView.utils.ts`・`CalendarView.test.tsx`・見本帳（金型は便1 で完成。口が足りないと思ったら止める）
- `SchedulePopover`（:212-514）・`ScheduleSidebar`（:516-664）・`ScheduleDayListPopover`（:921-975）・`ScheduleListView`（:978-1046）・`ScheduleShortcutsModal`（:1049-）の中身。近道の処理（:1389-1432）
- `backend/app/routers/calendar.py`・移行（migrations）・`deploy.yml`・`scripts/`
- 祝日・作る小窓の形・表示切替・検索（便3〜5）

## 2. 画面（SchedulePageImpl.tsx）

### 2-1 消すもの
- `ScheduleWeekGrid`（:666-828）と `ScheduleMonthGrid`（:830-918）の関数を丸ごと。
- `DEFAULT_ROW_HEIGHT`（:97）。`gridScrollRef`（:1146）と、それを使う送りの effect（:1217-1222）。
- `layoutDay` の import（:50）。`formatTimeRange` の import（:46）は小窓（:247）・一覧で使うので残す。
- 1 分ごとの `setNowTick`（:1147・:1230-1235）と `currentTime`（:1365）。`currentTime` は自前の時刻線（:765-769）と :1573 にしか使われていない（grep 済み）。今の時刻の線は金型の `nowIndicator` が出す。
- 消した後、`grep -n "ScheduleWeekGrid\|ScheduleMonthGrid\|gridScrollRef\|DEFAULT_ROW_HEIGHT\|layoutDay" frontend/src` が 0 件。

### 2-2 足す状態と関数（`SchedulePage` の中）

```tsx
// 押す・引っぱるで選んだ範囲の仮の箱（design §3.7）。DB にも Google にも送らない
const [pendingRange, setPendingRange] = useState<{ start: Date; end: Date; allDay: boolean } | null>(null);

// 1 件の予定を直せるか（今の canEditSelected の中身を 1 件を受け取る形へ切り出す・中身は変えない）
const canEditItem = (item: ScheduleItem) =>
  item.ownerUserId === currentOwnerUserId || canManageOwners;

// 動かせるか（design §3.6）
const canMoveItem = (item: ScheduleItem) =>
  canEditItem(item) && item.source !== "shift" && !(item.source === "google" && item.allDay);
```

`canEditSelected`（:1385-1387）は次に変える（意味は同じ）:
```tsx
const canEditSelected = Boolean(popover?.item && canEditItem(popover.item));
```

仮の箱を消すのは次の 1 か所にまとめる（閉じる・保存・削除・Esc・詳細を開く、のどの道で小窓が閉じても拾える。近道の処理 :1389-1432 には触らない）:
```tsx
useEffect(() => {
  if (popover?.mode !== "create") setPendingRange(null);
}, [popover]);
```
- `openDetail`（:1262）は小窓を `mode: "detail"` にするので、この 1 か所で消える。`closePopover`・`saveEvent`・`deleteEvent`・Esc の処理は変えない。

### 2-3 選んだ範囲から作る小窓を開く

`openCreate`（:1237-1260）は変えない（月の 1 日押し・近道 c・左の作るボタンが使う）。新しく足す:

```tsx
const openCreateRange = (start: Date, end: Date, allDay: boolean, anchor: AnchorRect | null) => {
  setDayList(null);
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
  setPopover({ mode: "create", anchor, item: null });
};
```

`onSelectRange` に渡す関数（design §3.2「選んだ範囲の決まり」）:
```tsx
const handleSelectRange = (start: Date, end: Date, allDay: boolean, anchor: AnchorRect | null) => {
  setPendingRange(null); // 前の仮の箱を消す（月の 1 日押しの道は仮の箱を出さない）
  const oneDay = allDay && addDays(start, 1).getTime() === end.getTime();
  if (view === "month" && oneDay) {
    openCreate(start, anchor); // 今の月の升目と同じ: その日の 7 時から 1 時間（§6 ③）
    return;
  }
  openCreateRange(start, end, allDay, anchor);
};
```
- 月で複数日を引っぱった・週/日の終日の行で選んだ → 終日の予定として開く。
- 週/日の時間の枠 → 金型が押しただけなら 1 時間に広げて返す（`normalizeSelectedRange`）ので、そのまま開く。

### 2-4 金型へ渡す予定の並び

```tsx
const calendarEvents: CalendarViewEvent[] = [
  ...(pendingRange
    ? [{
        id: "pending",
        title: t("schedule.noTitle"), // 既にある「（タイトルなし）」（ja.json:3358・en.json:3358）。新しいキーは作らない
        start: pendingRange.start,
        end: pendingRange.end,
        allDay: pendingRange.allDay,
        color: currentOwnerUserId != null ? getOwnerMeta(ownerByUserId, currentOwnerUserId, currentOwnerUserId).color : undefined,
        editable: false,
      }]
    : []),
  ...visibleEvents.map((item) => ({
    id: item.id,               // "event-12" / "shift-3" のまま
    title: item.title || t("schedule.noTitle"),
    start: item.start,
    end: item.end,
    allDay: item.allDay,
    color: getOwnerMeta(ownerByUserId, item.ownerUserId, currentOwnerUserId).color,
    editable: canMoveItem(item),
  })),
];
```
- `getOwnerMeta` の戻り値に `color` が無い形なら止める（今は :727・:789 で `.color` を使っている）。
- 種類の札（カテゴリの点）は箱に出さない（G4）。

### 2-5 動かす・長さを変える（design §3.3）

```tsx
const itemById = (id: string) => visibleEvents.find((item) => item.id === id) ?? null;

const patchMoved = async (id: string, start: Date, end: Date | null, allDay: boolean, revert: () => void) => {
  const item = itemById(id);
  const numericId = eventNumericId(id);
  if (!item || numericId === null || !canMoveItem(item)) { revert(); return; }
  const startDay = formatDateInput(start);
  const startTime = allDay ? "00:00" : formatTimeInput(start);
  const endValue = toCalendarEnd(start, end, allDay, item);
  try {
    await api.patch(`/calendar/events/${numericId}`, {
      title: item.title,
      start_datetime: combineDateTime(startDay, startTime).toISOString(),
      end_datetime: endValue.toISOString(),
      is_all_day: allDay,
      description: item.description || undefined,
      location: item.location || undefined,
    });
    setError(null);
    void invalidate(["calendar", "events"]);
  } catch (err) {
    revert();
    setError(err instanceof Error ? err.message : t("common.saveError"));
  }
};
```
- `onEventMove={patchMoved}`。`onEventResize={(id, start, end, revert) => patchMoved(id, start, end, itemById(id)?.allDay ?? false, revert)}`。
- `category`・`calendar_type` は送らない（`UpdateEventBody` `backend/app/routers/calendar.py:118-126` に `category` が無い）。

### 2-6 今の直しの道の id（見つけた不具合・同じ関数で直す）

- 事実: 予定の id は `event-${event.id}`（`schedule-utils.ts:211`）。今の保存は `api.patch(\`/calendar/events/${popover.item.id}\`)`（:1308）、削除は `api.delete(\`/calendar/events/${popover.item.id}\`)`（:1327）で、`event-12` の形のまま送っている。受け口は `event_id: int`（`backend/app/routers/calendar.py:385-387,477-479`）。
- 直し: :1308 と :1327 の `popover.item.id` を `eventNumericId(popover.item.id)` に変える。`null`（シフト）のときは送らず `setError(t("common.saveError"))`（削除は `common.deleteError`）。
- 試験: §6 の T7。

### 2-7 描画の差し替え（:1542-1578）

```tsx
{view === "list" ? (
  <ScheduleListView … />   // 今のまま
) : (
  <div className="schedule-calendar">
    <CalendarView
      mode={view === "month" ? "month" : "days"}
      date={view === "month" ? anchorDate : viewDays[0]}
      dayCount={view === "day" ? 1 : 7}
      events={calendarEvents}
      weekStart={0}
      timeStyle="meridiem"
      eventLayout="stacked"
      hourRange="full"
      scrollToNow
      fillHeight
      monthMaxEvents={3}
      onEventClick={(id, rect) => {
        const item = itemById(id);
        if (item) openDetail(item, rect);   // "pending" は何もしない
      }}
      onDayClick={(date) => { setAnchorDate(date); setView("day"); }}
      onSelectRange={handleSelectRange}
      onEventMove={patchMoved}
      onEventResize={(id, start, end, revert) => patchMoved(id, start, end, itemById(id)?.allDay ?? false, revert)}
      onMoreClick={(date, rect) => { setPopover(null); setPendingRange(null); setDayList({ date, anchor: rect }); }}
      ariaLabel={t("schedule.title")}
    />
  </div>
)}
```
- `viewDays[0]` は週なら日曜（`getWeekDays` `schedule-utils.ts:134-138`）、日なら当日。金型の days は `date` の日から始まるので日曜を渡す。
- `dayList` の型（:1144）の `anchor` を `AnchorRect | null` にする（金型の rect は null があり得る）。`ScheduleDayListPopover` の `anchor` は既に `AnchorRect | null`（:931）なので変えない。型だけの変更で中身は変えない。
- `monthMaxEvents={3}`: 今の月の升目も 3 件出して残りを「他 N 件」にしている（:878 `slice(0, 3)`・:899-909）。
- `schedule.title` は既にある（ja.json:3204「スケジュール」）。
- `onDayClick`: 月の升目の日付の数字を押すと、その日の日の表示へ移る（Google と同じ。金型の `navLinks`）。今の画面は日付の数字に別の動きが無く、升目のどこを押しても作る小窓（:874）なので、升目の余白を押したときの動き（§2-3 の 1 日押し）は変わらない。

## 3. schedule-utils.ts

消す: `DayLayoutItem`（:66-72）・`LayoutCandidate`（:248-252）・`layoutDay`（:254-282）。他から使われていないことを grep で確かめてから。

足す:
```ts
/** "event-12" → 12。シフト・仮の箱など予定でない id は null */
export function eventNumericId(id: string): number | null {
  const m = /^event-(\d+)$/.exec(id);
  return m ? Number(m[1]) : null;
}

/**
 * 動かした後の終わり（送る値）。
 * - 終日: FullCalendar の終わりは「次の日 0:00」なので 1 日戻し、その日の 23:59（design §3.3 の 3）
 * - 終わりが null: 元の長さを保つ（終日は同じ 1 日）
 * - 終日 → 時刻つきへ動かして終わりが null: 1 時間（元の 23 時間 59 分を引き継がない）
 */
export function toCalendarEnd(start: Date, end: Date | null, allDay: boolean, item: Pick<ScheduleItem, "start" | "end" | "allDay">): Date {
  if (allDay) {
    const last = end ? addDays(end, -1) : start;
    const lastDay = last.getTime() < start.getTime() ? start : last;
    return combineDateTime(formatDateInput(lastDay), "23:59");
  }
  if (end) return end;
  if (item.allDay) return new Date(start.getTime() + 60 * 60 * 1000);
  return new Date(start.getTime() + (item.end.getTime() - item.start.getTime()));
}
```

## 4. schedule.css

- 消す: 使われなくなった class の規則だけ。候補は :333-580（`.schedule-grid*`・`.schedule-day-head*`・`.schedule-day-column*`・`.schedule-time-label`・`.schedule-slot*`・`.schedule-event*`）と :581-608,610-645,693-705 の月の升目（`.schedule-month`・`__head`・`__grid`・`__cell*`・`__date`・`__events`・`__more*`）、それに画面の幅で切り替える部分（@media）の中の `.schedule-grid__*`（:1462・:1473-1481）。:707 の `.schedule-popover-backdrop` は消さない。
- 残す: `ScheduleDayListPopover`（:955-967）と一覧が使う `.schedule-month__event`・`__dot`・`__time`・`__title` など、消した後も tsx に出てくる class。
- 消す前に、各 class 名を `grep -rn "<class名>" frontend/src --include="*.tsx" --include="*.ts"` で確かめ、0 件のものだけ消す。消した class の一覧を PR 本文に書く。
- 足す（色・寸法の直書きなし）:
```css
/* 金型の時間割・月の升目を、画面の残りの高さいっぱいに置く（G10・G13） */
.schedule-calendar {
  flex: 1;
  min-height: 0;
}
```

## 5. 1 時間の高さ（G6）

- 測った事実（2026-11-07・Opus・同じ Chrome の窓 1620×1448・倍率 2）: Google カレンダーの週の表示で9 時と 10 時の目盛りの文字の上端が 520.5 と 616.5 → **96**。Sales Anchor の今の画面の 1 時間の枠（`.schedule-slot`）の高さ → **48**。
- `frontend/src/tokens.css:403` の `--schedule-row-height: 48px;` を `96px;` に変える。コメントは「1時間の高さ（Google カレンダーの実測に合わせた値）」。
- この token の使い道は `components/CalendarView.css:48` と、消す `schedule.css:491-493,522`・消す関数の中の `SchedulePageImpl.tsx:756,764,769,779` だけ（grep 済み・審査で確認）。金型を呼ぶ画面は予定の画面だけなので、他の画面は変わらない。
- まだ確かめていないこと: Google の高さが窓の高さで変わるか（窓の大きさを変えられず測れなかった）。G6 は窓 1448 で判定する。

## 6. 試験（SchedulePageImpl.test.tsx・SchedulePageCache.test.tsx）

両方のファイルの先頭に、金型の差し替えを足す（FullCalendar は jsdom で描かない・`CalendarView.test.tsx` も FullCalendar を差し替えている）:
```tsx
const calendarProps = vi.hoisted(() => ({ current: null as null | Record<string, any> }));
vi.mock("../../components/CalendarView", () => ({
  CalendarView: (props: Record<string, any>) => {
    calendarProps.current = props;
    return (
      <div data-testid="calendar-view">
        {props.events.map((ev: { id: string; title: string }) => (
          <button key={ev.id} type="button" onClick={(e) => props.onEventClick?.(ev.id, e.currentTarget.getBoundingClientRect())}>
            {ev.title}
          </button>
        ))}
      </div>
    );
  },
}));
```
- 今の試験の「予定の題名を押す」（"Own Event" など）はこの差し替えでそのまま通るはず。通らないものは止めて報告（直し方を勝手に決めない）。小窓の位置の試験（K1）が `getBoundingClientRect` の作り物に頼っている所は、押す要素がボタンに変わっても同じ値を返すように作り物の付け先だけ合わせる。
- :501-530「slot click」の試験は消し、次に置き換える。

| # | 試験 | 期待 |
|---|---|---|
| T1 | `calendarProps.current.onSelectRange(10:00, 11:00, false, null)` を `act` で呼ぶ | 小窓の時刻の欄が 10:00 / 11:00。4 時・15 時も同じ（今の 3 件を引き継ぐ） |
| T2 | T1 の後の `calendarProps.current.events[0]` | id "pending"・題名「（タイトルなし）」・`editable: false`。小窓を閉じると無くなる |
| T3 | 月の表示で `onSelectRange(11/10 0:00, 11/11 0:00, true, null)` | 07:00 / 08:00（今の月の升目と同じ） |
| T4 | 月の表示で `onSelectRange(11/10, 11/13, true, null)` | 終日の欄がオン・開始 11/10・終了 11/12 |
| T5 | events の `editable` | 自分の予定 true・他人（管理者でない）false・シフト false・取り込んだ終日 false |
| T6 | `onEventMove("event-1", 新しい開始, 新しい終了, false, revert)` | `api.patch` が `/calendar/events/1` に title・start・end・is_all_day・description・location を付けて 1 回。`category` は無い。失敗させると `revert` が 1 回呼ばれ、失敗の文が出る |
| T7 | 予定を開いて直して保存・削除 | `api.patch` / `api.delete` の宛先が `/calendar/events/1`（`event-1` ではない） |
| T8 | 終日の予定を `onEventMove(id, 11/10, 11/12 0:00, true, revert)` | 送る終わりが 11/11 23:59 の値（`combineDateTime("2026-11-11","23:59").toISOString()`） |
| T9 | 週の表示で渡す `date` と `dayCount`・`weekStart` | 日曜・7・0。日の表示は当日・1 |

schedule-utils.test.ts: `eventNumericId`（"event-12"→12、"shift-3"→null、"pending"→null）と `toCalendarEnd`（終日 1 日・終日 3 日・終わり null の時刻つき・終日の予定を時刻つきへ動かして終わり null → 1 時間）。`layoutDay` の試験は今のファイルに無いので、消すものは無い。

## 7. 裏側: 終日が Google で 1 日前にずれる直し（design §3.3 の 4）

`backend/app/services/calendar_service.py:648-650` を次の手順に変える（定数は足さない。`_JST` :505 と `_parse_dt` :34 を使う）:
1. 値に `T` が無い（日付だけ）ときは、そのまま `{"date": 値}` にする（今の試験 `test_all_day_event` :93-105 が通ること）。
2. `T` があるときは `_parse_dt` で読み、時差が無ければ `replace(tzinfo=_JST)`、その後 `astimezone(_JST).date()`。
3. 始まり = 始まりの日。終わり = 終わりの日 + 1 日（Google の終わりは次の日）。終わり ≤ 始まりなら 始まり + 1 日。
4. 時刻つきの枝（:651-653）・説明・場所は変えない。
5. 始まりと終わりで形が違う（片方だけ日付だけ）ときも、それぞれを 1・2 の決まりで日付にしてから 3 を当てる。

試験（`backend/tests/test_calendar_service.py`）:
- `TestToGoogleEventBody` に 6 件:
  1. `2026-06-30T15:00:00.000Z` / `2026-07-01T14:59:00.000Z` → `2026-07-01` / `2026-07-02`
  2. 3 日間 `2026-06-30T15:00:00.000Z` / `2026-07-03T14:59:00.000Z` → `2026-07-01` / `2026-07-04`
  3. `+09:00` の形 `2026-07-01T00:00:00+09:00` / `2026-07-01T23:59:00+09:00` → `2026-07-01` / `2026-07-02`
  4. 時差なし `2026-07-01T00:00:00` / `2026-07-01T23:59:00` → 同上
  5. 行って戻る: 1 の結果を `_google_times`（:508）に通すと 7/1 00:00〜7/1 23:59（日本時間）・終日
  6. 終わりが始まりより前 → 終わり = 始まり + 1 日
- `TestCreateEvent`（:231）・`TestUpdateEvent`（:362）に各 1 件: 終日を `...Z` の形で送ったとき、Google へ渡す本文の `start.date` が日本時間の日付になる（今の作り物の付け方に合わせる）。

## 8. 確かめるコマンド（クラウドで実行し、生の出力をファイルに残す）

```
cd frontend
npm run test:unit -- src/pages/schedule
npm run test:unit -- src/components/CalendarView
npx tsc --noEmit
npm run check:all
npm run check:new-tokens
npm run check:dark-parity
npm run build
cd ../backend
pytest tests/test_calendar_service.py -q
grep -rn "ScheduleWeekGrid\|ScheduleMonthGrid\|gridScrollRef\|DEFAULT_ROW_HEIGHT\|layoutDay" ../frontend/src   # 0 件
```
全部が通ってから commit。1 つでも落ちたら直せる範囲（このカードの中）で直し、範囲外なら止める。

## 9. 受入れ（本番反映後に Opus が画面で確かめる）

| # | 基準 | 検証方法 |
|---|---|---|
| G2 | 枠を押すと「（タイトルなし）」の仮の箱が出て、閉じると消える | 週の 10 時を押して見る・閉じる |
| G4 | 箱に題名と「午後12:30〜1:30」の形の時刻。札なし | 30 分・1 時間の予定を見る |
| G5 | 目盛りが「午前9時」の形 | 画面で見る |
| G6 | 9 時〜10 時の線の間が 91〜101（96 の ±5%） | 同じ窓で測る |
| G8 | 引っぱって作る・自分の予定を動かす・下の端で長さを変える → 再読み込みしても残る | 3 操作して再読み込み（試しの予定を作って最後に消す） |
| G9 | 他人の予定・シフト・取り込んだ終日はつかめない | つかもうとする |
| G10 | 月の升目が画面の下まで・3 日の予定が 1 本の帯 | 窓 1448 で見る |
| G13 | 週・日を開くと今の時刻の 1 時間前から見える | 開いて見る |
| §6 ①〜⑨ | 詳しくの小窓・他 N 件・月で作る・近道 12 個・一覧・他のカレンダー切替・左の小さな月・前へ次へ今日・シフトの見た目 | 1 つずつ |
| 直しの道 | 予定を開いて直して保存できる（今は宛先が `event-12` の形で失敗する） | 試しの予定で |
| 終日 | 終日の予定を作ると Google カレンダーでも同じ日に出る | 試しの予定で並べて見る |

## 10. 維持の仕組み（design §8 で便2 に決めると書いた件）

- 時間割を自前で書いた画面を UI の見張り（ADR-144）で止める仕組みは、**今回は足さない**。理由: 載せ替えで時間割を持つ画面は金型 1 か所だけになり（§2-1 の grep 0 件で確かめる）、新しく自前の時間割を書く画面の予定も無い。足すかどうかは、次に時間割を使う画面を作るときに決める。
- 守り手: `SchedulePageImpl.test.tsx` の T1〜T9 と `CalendarView.test.tsx`（CI で毎回）。

## 11. 想定される分かれ道（出たら止める）

- 今の試験の一部が差し替えで通らず、直し方が 1 つに決まらない。
- `getOwnerMeta` が色を返さない予定がある（その時の色の決め方はカードに無い）。
- 金型の口・型が足りない（金型は触らない決まり）。
- `schedule.css` の class が tsx 以外（他の css・storybook）から使われている。

## 12. 審査の記録

- 1 回目（2026-11-07・クラウドの Opus・HEAD 1538745c）: REVISE。直さないと実装で迷う 1 件（Esc の扱いが §1 と §2-2 で食い違い）と、行のずれ（CSS の消す範囲・他 N 件・token の使い道）、直した方がよい 4 件（layoutDay の試験は無い・日別小窓の型は既に null あり・月の 1 日押しで前の仮の箱が残る・終日から時刻つきへ動かしたときの長さ）。全部この版で直した（§2-2・§2-3・§2-7・§3・§4・§5・§6・§7 の 5）。
