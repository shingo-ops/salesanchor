# 実装カード 便2 直し2（色を変えたら箱の色をすぐ塗り直す）

- 設計: docs/handoff/event-color/design.md §4-11（事実・直し方・選ばなかった案・受け入れ K8）
- 枝: release/event-color-live-repaint（origin/main 0a0b2b141 起点）
- 実装役: クラウドの Sonnet。Opus がカードを書いた。PO の実装承認: 2026-11-20「1」（設計・実装・合流・本番反映まで進める）。

## 1. なぜ

- アプリで色を変えて保存すると、読み直しは動き新しい色も部品に届く（design.md §4-11 の事実）。
- 部品は色を `eventDidMount` の中だけで置く（`frontend/src/components/CalendarView.tsx:336`〜`:338`）。FullCalendar は予定のデータが変わっても `eventDidMount` を再び呼ばない（公式の説明）。だから箱の色が古いまま残る。

## 2. 触るファイル（この 2 つだけ）

1. `frontend/src/components/CalendarView.tsx`
   - `:81`（`const trackRef = ...`）の次の行に足す:
     ```ts
     // 予定の id → いま DOM にある箱の要素。色が変わったときに塗り直すため（eventDidMount は再び呼ばれない・design §4-11）
     const mountedElsRef = useRef(new Map<string, Set<HTMLElement>>());
     ```
   - 部品の関数の外（ファイルの上の方、部品の定義の前）に足す:
     ```ts
     /** 箱の要素に予定の色を置く。色が無ければ外す（色の値は呼ぶ側が渡したトークンのまま） */
     function applyEventColor(el: HTMLElement, color: string | undefined): void {
       if (color) el.style.setProperty('--comp-calendar-owner-color', color);
       else el.style.removeProperty('--comp-calendar-owner-color');
     }
     ```
   - `fcEvents` の `useMemo`（`:132`〜）の後に `useEffect` を 1 つ足す:
     ```ts
     // 色を変えて保存したとき、使い回された箱の色を新しい色に置き直す（design §4-11・K8）
     useEffect(() => {
       for (const ev of events) {
         const els = mountedElsRef.current.get(ev.id);
         if (!els) continue;
         for (const el of els) applyEventColor(el, ev.color);
       }
     }, [events]);
     ```
   - `eventDidMount`（`:336`〜）:
     - 前: `if (color) arg.el.style.setProperty('--comp-calendar-owner-color', color);`
     - 後: `applyEventColor(arg.el, color);`
     - `if (arg.isMirror) return;` の直後（追う処理の前）に足す:
       ```ts
       const set = mountedElsRef.current.get(arg.event.id) ?? new Set<HTMLElement>();
       set.add(arg.el);
       mountedElsRef.current.set(arg.event.id, set);
       ```
   - `eventWillUnmount`（`:348`〜）: `if (arg.isMirror) return;` の直後に足す:
     ```ts
     const set = mountedElsRef.current.get(arg.event.id);
     if (set) {
       set.delete(arg.el);
       if (set.size === 0) mountedElsRef.current.delete(arg.event.id);
     }
     ```
   - ほかの行は変えない。写し（isMirror）は表に入れない。
2. `frontend/src/components/CalendarView.test.tsx`
   - `:497` の試験の後（同じ describe の中）に試験を 3 本足す。どれも `render` の `rerender` を使い、`fcProps().eventDidMount` / `eventWillUnmount` を偽の `arg` で呼ぶ（`event: { id, extendedProps: { source } }, el, isMirror: false`）:
     - `repaints a mounted event when its color changes`: 色 `rgb(1, 2, 3)` の予定で mount → 同じ id で色 `rgb(4, 5, 6)` に変えて rerender → 変数が `rgb(4, 5, 6)`。
     - `clears the color variable when the color is removed`: 色ありで mount → 色なしで rerender → 変数が `''`。
     - `does not repaint unmounted or mirror elements`: 要素 A を mount→unmount、要素 B を `isMirror: true` で mount → 色を変えて rerender → A・B とも前の値のまま。
   - 今ある試験は変えない。

## 3. 触らない

- `frontend/src/components/CalendarView.css`・`calendarView.utils.ts`・`frontend/src/pages/schedule/` の全部・裏側・migrations・ほかの docs。
- 色の値・トークンを新しく書かない（ADR-067・ADR-144）。`backgroundColor`/`borderColor` を FullCalendar に渡さない。

## 4. 確かめ（生の出力をファイルに残し、最後に結果の行を書く）

- `cd frontend && npx vitest run src/components/CalendarView.test.tsx` が全部通る（新しい 3 本を含む）。
- 新しい 3 本のうち 1 本目と 2 本目は、`useEffect` を外すと落ちることを一度確かめ、その出力も残す（確かめた後は戻す）。
- `cd frontend && npx vitest run src/pages/schedule` が通る。
- `cd frontend && npx tsc --noEmit -p .` と `npx eslint src/components/CalendarView.tsx src/components/CalendarView.test.tsx` が通る。
- `git diff origin/main --stat` が上の 2 ファイル＋このカード・design.md だけ。

## 5. 止まる条件

- 確かめが 1 つでも落ちたら、直さずに `NEEDS_DECISION:` で出力を添えて止まる。
- 2 ファイル以外を変えたくなったら止まる。
- commit は 1 つ。文: `fix(calendar): 色を変えたら箱の色をすぐ塗り直す（ADR-1081・K8）`。push は `git push origin release/event-color-live-repaint`（force は使わない）。
