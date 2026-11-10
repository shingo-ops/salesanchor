# 実装カード 便12 直し1: 週表示で仮の箱を動かしても日時が変わらない

- 親: docs/handoff/schedule-gcal-clone/card-bin12.md（G45）・design.md §3（便12）・ADR-1065 What 6
- 範囲: 便12 で PO 承認済みの G45「作成中の箱をドラッグで動かすと日時の行が変わる」を満たすための不具合直し。新しい仕様は足さない
- 状態: 設計作成・設計審査済み（Opus）。実装はクラウド Sonnet

## 1. 観測事実（本番 app.salesanchor.jp/schedule・2026-11-10 JST・読み取りのみ・保存なし）

- 週表示で仮の箱（id "pending"）を月曜 10:00 → 13:15 へ動かすと、見た目は動くが、離したときに FullCalendar は eventDrop を出さず eventLeave と eventReceive を出す。下書きの時刻は元のまま、日時の行も変わらない
- 月表示のドラッグ・週表示の端を引く変更（eventResize）は正しく動く
- 原因（確かめ済み）: `frontend/src/components/CalendarView.tsx:336-351` の eventDidMount が、ドラッグ中に作られる写し（mirror・id も "pending"）にも反応して `setTrackedEl` を呼ぶ。再描画で `@fullcalendar/react` が `resetOptions` を呼び、FullCalendar 6.1.22 の handleDragEnd で `receivingContext !== initialContext` となり、別カレンダーへの移動として扱われる
- 証拠: ページ内でドラッグ中の `resetOptions` を飛ばした（2回）だけで eventDrop が出て、日時の行が「11月9日(月) 午後1:15～午後2:15」に変わった
- FullCalendar の描画の引数に `isMirror` があることは Context7 で確かめ済み

## 2. 触る

### 2-1 `frontend/src/components/CalendarView.tsx`

eventDidMount と eventWillUnmount の追跡の部分を、写し（`arg.isMirror`）のときは何もしないようにする。色を付ける1行（`--comp-calendar-owner-color`）は写しにもそのまま付ける（見た目を変えない）。

変更前（336-351）:

```tsx
        eventDidMount={(arg) => {
          const color = (arg.event.extendedProps.source as CalendarViewEvent).color;
          if (color) arg.el.style.setProperty('--comp-calendar-owner-color', color);
          if (trackRef.current.trackEventId && arg.event.id === trackRef.current.trackEventId) {
```

変更後:

```tsx
        eventDidMount={(arg) => {
          const color = (arg.event.extendedProps.source as CalendarViewEvent).color;
          if (color) arg.el.style.setProperty('--comp-calendar-owner-color', color);
          // ドラッグ中の写しは追わない。追うと再描画で FullCalendar の設定が入れ替わり、
          // 離したときに eventDrop が出なくなる（card-bin12-fix1.md）
          if (arg.isMirror) return;
          if (trackRef.current.trackEventId && arg.event.id === trackRef.current.trackEventId) {
```

eventWillUnmount の先頭にも `if (arg.isMirror) return;` を1行足す（コメントは同じ趣旨を1行）。

### 2-2 `frontend/src/components/CalendarView.test.tsx`

`describe('T10 trackEventId・onEventRect（便12・ADR-1065 What 6）'` の末尾に it を1つ足す:

- 名前: `'ignores the drag mirror: no onEventRect and no re-render'`
- 手順: mountView → 本物の 'p' を eventDidMount → `onEventRect.mockClear()` → `const before = fcProps()` → `eventDidMount({ ...mountArg('p', makeEl(600)), isMirror: true })` → `eventWillUnmount({ ...mountArg('p', makeEl(600)), isMirror: true })`
- 期待: `onEventRect` が呼ばれない。`fcProps()` が `before` と同じもの（`toBe`）＝再描画されていない
- 直す前のコードでこの it が落ちることを確かめてから直す（落ちた出力を報告に貼る）

## 3. 触らない

上の2ファイル以外すべて。特に SchedulePageImpl.tsx・schedule-utils.ts・CalendarView.css・Button・TextField・i18n・backend・migrations・.github・scripts。T1〜T11 の既存の it は変えない。

## 4. 受入条件

| 基準 | 検証方法 |
|---|---|
| 新しい it が直す前に落ち、直した後に通る | 担当が `npx vitest run src/components/CalendarView.test.tsx` を前後で実行し出力を貼る |
| 既存の試験が全部通る | 同じコマンド・CI の frontend 試験 |
| 型・lint が通る | `npx tsc --noEmit -p .`・`npx eslint src/components/CalendarView.tsx src/components/CalendarView.test.tsx` |
| 差分は2ファイル＋このカードだけ | `git diff origin/main --stat` |
| 本番の週表示で箱を月曜→金曜へ動かすと日時の行が金曜に変わり、小窓が箱の横 8px に付く | 本番反映後に Opus が Chrome で読み取りのみ測定（保存しない） |

## 5. 想定分岐

- `arg.isMirror` が型に無いと tsc が言う → 止めて報告（FullCalendar 6.1.22 の EventMountArg には有る。推測で型を足さない）
- 新しい it が直す前でも通る → 止めて報告（試験の作りが原因を捉えていない）

## 6. 戻し方

この PR を revert する。DB・設定の変更は無い。
