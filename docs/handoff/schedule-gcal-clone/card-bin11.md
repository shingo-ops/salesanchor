# 実装カード 便11: 日・3日間・週の枠線を Google に揃える（G37〜G41）（2026-11-09）

- 設計: `docs/handoff/schedule-gcal-clone/design.md` §2.4（G37〜G41）・§3.16（審査は §9 の 14 回目）
- PO の承認: PO の選択「1」（2026-11-09・「この直し方で作り、本番に出して Google と並べて確かめる」）
- 土台: origin/main（作業の時点の最新）。ブランチ `release/schedule-gcal-borders-impl`
- 対象 ADR: ADR-1065（金型 CalendarView・決まり 7 予定の画面の見た目は金型の css だけ）・ADR-067（トークン）
- 行番号はすべて origin/main 1ca6dbf38 の値。違っていたら中身で場所を探し、見つからなければ止める。

## 0. 作業者への決まり

- このカードに書いたこと以外はしない。迷ったら止めて `NEEDS_DECISION:` で返す。
- 作業は必ず `bash scripts/new-worktree.sh release/schedule-gcal-borders-impl --claude` で作った作業場所の中で行う。
- 足すトークンは §2 の 1 つだけ。文言キー・tsx・試験は変えない。値は var() だけ（px・色の直書き禁止）。
- 確かめはクラウドの作業場所で回す（`cd frontend && npx vitest run src/components/CalendarView.test.tsx src/pages/schedule/`・`npx tsc --noEmit`・`npm run check:all`（eslint・stylelint・css の直書きの見張り・トークンの見張りを含む））。

## 1. 触るファイルと触らないファイル

触る:
| ファイル | 中身 |
|---|---|
| `frontend/src/tokens.css` | トークン 1 行（§2） |
| `frontend/src/components/CalendarView.css` | 規則（§3） |
| `.claude-pipeline/active-work.d/release-schedule-gcal-borders-impl.md` | 台帳（new-worktree.sh が作る形のまま・状態を更新） |

触らない（変えたら差し戻し）:
- `frontend/src/tokens.css` の §2 以外の行（ダークの段を含む。新トークンは色を持たないのでダークに足さない）
- `frontend/src/components/CalendarView.css` の §3 以外の行（月の段 `.comp-calendar--month` `:290-` を含む）
- `frontend/src/components/CalendarView.tsx`・`CalendarView.test.tsx`・`calendarView.utils.ts`・`CalendarView.stories.tsx`
- `frontend/src/pages/schedule/`
- 移行（migrations）・`.github/workflows/`・リポジトリ直下の `scripts/`・backend・`frontend/scripts/`

## 2. tokens.css（`:423` の次の行に足す）
前:
```css
  --schedule-gridline-w:      1px;      /* 時間割の罫線の太さ */
  --schedule-event-border-w:  2px;      /* 予定の枠の太さ（見積もり・重なり） */
```
後:
```css
  --schedule-gridline-w:      1px;      /* 時間割の罫線の太さ */
  --schedule-hour-tick-w:     var(--space-2); /* 毎時の線が時刻の列へ出る長さ（Google 実測 9px・G38） */
  --schedule-event-border-w:  2px;      /* 予定の枠の太さ（見積もり・重なり） */
```

## 3. CalendarView.css（`:288` の `}` の次・`:290` の月の段の見出しの前に足す）
前:
```css
/* 今の時刻の丸を欠けさせない（G24） */
.comp-calendar--schedule.comp-calendar--days .fc-timegrid-now-indicator-container {
  overflow: visible;
}

/* ---- 予定の画面の見た目・月の升目（ADR-1065 What 7・design §3.14 G31〜G33） ---- */
```
後（間に下の塊を入れる。前後の 1 行あきを保つ）:
```css
/* 今の時刻の丸を欠けさせない（G24） */
.comp-calendar--schedule.comp-calendar--days .fc-timegrid-now-indicator-container {
  overflow: visible;
}

/* ---- 便11（design §3.16）: 線は予定を入れる升目だけ（G37〜G40） ---- */
.comp-calendar--schedule.comp-calendar--days .fc-scrollgrid {
  border-top-width: 0;
  border-left-width: 0;
}

.comp-calendar--schedule.comp-calendar--days .fc-scrollgrid-section > * {
  border-right-width: 0;
  border-bottom-width: 0;
}

.comp-calendar--schedule.comp-calendar--days .fc-col-header-cell,
.comp-calendar--schedule.comp-calendar--days .fc-timegrid-axis,
.comp-calendar--schedule.comp-calendar--days .fc-timegrid-slot-label {
  border-width: 0;
}

.comp-calendar--schedule.comp-calendar--days .fc-scrollgrid-section > .fc-timegrid-divider {
  padding: 0;
  border-bottom-width: var(--schedule-gridline-w);
}

.comp-calendar--schedule.comp-calendar--days .fc-timegrid-slot-label {
  position: relative;
}

.comp-calendar--schedule.comp-calendar--days .fc-timegrid-slot-label::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: var(--schedule-hour-tick-w);
  border-top: var(--schedule-gridline-w) solid var(--schedule-gridline);
}

.comp-calendar--schedule.comp-calendar--days .fc-timegrid-slot-label-cushion {
  padding-right: calc(var(--schedule-hour-tick-w) + var(--space-1));
}

/* 上の行と終日の行の空の巻き上げの帯を見せない（幅は残して列をそろえる） */
.comp-calendar--schedule.comp-calendar--days .fc-scrollgrid-section:not(.fc-scrollgrid-section-liquid) .fc-scroller {
  scrollbar-color: transparent transparent;
}

/* ---- 予定の画面の見た目・月の升目（ADR-1065 What 7・design §3.14 G31〜G33） ---- */
```

## 4. 返事

DONE と HEAD の SHA（40 文字）・試験の結果の数（通った／落ちた）・tsc・`check:all` の結果・`git show --stat HEAD`（触るファイル 3 つだけであること）。止めたときは `BLOCKED:` か `NEEDS_DECISION:` と理由。
