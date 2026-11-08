# 実装カード 便7: 上の帯を 1 段・左上のメニューボタン・3日間・1時間の高さ・不具合 2 つ（G20〜G25）（2026-11-08）

- 設計: `docs/handoff/schedule-gcal-clone/design.md` §2.2・§3.12（PO の言葉 2026-11-08・審査は §9 に記録）
- 土台: origin/main 5a531586a。ブランチ `release/schedule-gcal-topbar-bin7`
- 成功条件: G20〜G25（design.md §2.2）
- 対象 ADR: ADR-1065（金型 CalendarView）・ADR-067（トークン）・ADR-144（金型を使う）・ADR-027（文言は t()）
- 行番号はすべて origin/main 5a531586a の値。

## 0. 作業者への決まり

- このカードに書いたこと以外はしない。迷ったら止めて `NEEDS_DECISION:` で返す。
- 作業は必ず `bash scripts/new-worktree.sh release/schedule-gcal-topbar-bin7 --claude` で作った作業場所の中で行う。
- 色・寸法の直書き禁止。css の値は `var()`・`calc()`・`clamp()`・`round()`・`%`・`0` と言葉の値だけ。新しい寸法はトークン（§5）だけ。
- 画面の文字は `t()` だけ。ja.json と en.json は同じキー。
- 1023px 以下の並び方の css は変えない（Android 側の担当が決める・PO 2026-11-08）。
- 試験はクラウドの作業場所で回す（`cd frontend && npx vitest run src/components/CalendarView.test.tsx src/pages/schedule/`・`npx tsc --noEmit`・`npm run lint`・`node scripts/check-css-hardcoded-values.js`・`node scripts/check-css-hardcoded-colors.js`）。

## 1. 触るファイルと触らないファイル

触る:
| ファイル | 中身 |
|---|---|
| `frontend/src/components/PageLayout.tsx` | 口 `headerStart` を足す（§2） |
| `frontend/src/components/calendarView.utils.ts` | `scrollTimeForNow` を変える（§3-2） |
| `frontend/src/components/CalendarView.tsx` | 大きさが変わったら測り直す（§3-1） |
| `frontend/src/components/CalendarView.css` | 末尾に 3 つの規則を足す（§4） |
| `frontend/src/tokens.css` | トークン 3 つを足す（§5） |
| `frontend/src/pages/schedule/schedule-utils.ts` | 種類 `threeDay`・期間（§6-1） |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx` | 説明の文を消す・メニューボタン・3日間（§6-2） |
| `frontend/src/pages/schedule.css` | 規則 1 つを足す（§6-3） |
| `frontend/src/locales/ja.json`・`en.json` | キー 3 つ（§7） |
| `frontend/src/components/CalendarView.test.tsx`・`frontend/src/pages/schedule/schedule-utils.test.ts`・`frontend/src/pages/schedule/SchedulePageImpl.test.tsx` | 試験（§8） |
| `frontend/scripts/check-page-layout.js` | `SUBTITLE_ALLOWLIST`（`:28-33`）の末尾に `'schedule/SchedulePageImpl', // 予定の画面: 上の帯を 1 段（PO 2026-11-08・design §3.12）` を 1 行足すだけ。他は変えない（§6-2 #8 で説明の文を消すと `:94` の検査が落ちるため） |
| `docs/specs/design-system/component-ssot/page-title/design.md` | 口の追加を 1 行記録（§9） |
| .claude-pipeline/active-work.d/release-schedule-gcal-topbar-bin7.md | 台帳（new-worktree.sh が作る形のまま・状態を更新） |

触らない（変えたら差し戻し）:
- `schedule.css` の `@media (max-width: 1023px)`・`(max-width: 767px)` の中
- 文言キー `schedule.subtitle`（ja/en に残す）
- 月の表示（`monthProps`）・既存の css の規則（足すのは末尾だけ）
- 移行（migrations）・`.github/workflows/`・リポジトリ直下の `scripts/`・backend・`frontend/scripts/` の他のファイル

## 2. PageLayout.tsx

`PageLayoutBaseProps` の `headerLeft` の前に足す:
```ts
  /** タイトルより左に置くコンテンツ（メニューボタン等）。見た目は渡さない */
  headerStart?: React.ReactNode;
```
関数の引数に `headerStart,` を `titleText,` の次に足す。`:45` の `<h2 ...>` の前の行に `{headerStart}` を足す:
```tsx
        <div className={`page-layout-title-row${subtitleKey ? " page-layout-title-row--has-subtitle" : ""}`}>
          {headerStart}
          <h2 className="text-page-title">{navKey ? t(navKey) : titleText}</h2>
```

## 3. 金型 CalendarView

### 3-1 CalendarView.tsx
`:73` `const calendarRef = ...` の次に `const wrapperRef = useRef<HTMLDivElement | null>(null);` を足す。`:119` の useEffect の後に足す:
```tsx
  // 包みの大きさが変わったら（左の欄の出し入れ等）FullCalendar に測り直させる（design §3.12・G23）
  useEffect(() => {
    const el = wrapperRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(() => {
      calendarRef.current?.getApi?.().updateSize();
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
```
`:232` の包みに `ref={wrapperRef}` を足す: `<div ref={wrapperRef} className={wrapperClass} role="region" aria-label={ariaLabel}>`。

### 3-2 calendarView.utils.ts（`:236-239`）
変更前:
```ts
/** 今の時刻の 1 時間前（0 時より前にしない）を "HH:00:00" で */
export function scrollTimeForNow(now: Date): string {
  return `${pad2(Math.max(0, now.getHours() - 1))}:00:00`;
}
```
変更後:
```ts
/**
 * 開いた時の上端。今の 1 時間前の 30 分（0 時台は 0 時）。
 * 上端を 1 時間の線からずらし、一番上の時刻の文字が切れないようにする（design §3.12・G25）
 */
export function scrollTimeForNow(now: Date): string {
  const h = now.getHours();
  return h === 0 ? '00:00:00' : `${pad2(h - 1)}:30:00`;
}
```

## 4. CalendarView.css（末尾に足す）

```css
/* ---- 便7（design §3.12）: 1 時間の高さを時間割の見える高さに合わせる（G23） ---- */
.comp-calendar--schedule.comp-calendar--fill.comp-calendar--days .fc-scroller-liquid-absolute {
  container-type: size;
}

.comp-calendar--schedule.comp-calendar--fill.comp-calendar--days .fc-timegrid-slot {
  height: clamp(
    var(--schedule-row-min),
    round(nearest, var(--schedule-row-fit), var(--schedule-row-step)),
    var(--schedule-row-height)
  );
}

/* 今の時刻の丸を欠けさせない（G24） */
.comp-calendar--schedule.comp-calendar--days .fc-timegrid-now-indicator-container {
  overflow: visible;
}
```

## 5. tokens.css（`:426` `--schedule-now-dot-size` の次に足す）

```css
  --schedule-row-min: 48px;          /* 1時間の高さの下限（G23） */
  --schedule-row-step: 16px;         /* 1時間の高さの刻み（G23） */
  --schedule-visible-hours: 13;      /* 時間割に見せたい時間数（G23・Google の実測） */
  --schedule-row-fit: calc(100cqh / var(--schedule-visible-hours)); /* 時間割の見える高さ÷時間数。使う所の容器で決まる */
```
（トークンは 4 行になる。設計の「3 つ」は min・step・hours。`row-fit` は計算式の置き場で、css 本体に `cqh` を直書きしないため。）

PR 本文: tokens.css にトークンを足すので、`frontend/scripts/check-new-tokens.js` が通る形にする。見出しが無いと `:96-97` で rc=1 になり、`[ ]` が残ると `:112-127` で rc=1 になる。`.github/PULL_REQUEST_TEMPLATE.md:51-55` の見出し「### デザイントークン変更時（tokens.css / index.css を変更した場合）」と 4 項目をそのまま残し、4 項目すべてを `- [x]` にする。
- 概要欄に理由を書く: 1 時間の高さを時間割の見える高さに合わせる（design §3.12 G23）。
- 色トークンの項目: 今回足すのは寸法と数のトークンだけで色は無い。`[x]` にして、行末に「（色トークンの追加なし）」と添える。
- `npm run check:dark-parity` の項目: 手元で流して rc=0 を確かめてから `[x]` にする。
- 既存トークンの項目: `--schedule-row-height`（tokens.css:403）は上限として使い続け、下限・刻み・時間数を表すトークンは既存に無いことを確かめて `[x]` にする。

## 6. 予定の画面

### 6-1 schedule-utils.ts
- `:3` → `export type ScheduleView = "day" | "threeDay" | "week" | "month" | "list";`
- `:193` の次に `export const THREE_DAY_VIEW_DAYS = 3;` を足す。
- `toRangeStart`（`:195-200`）: `if (view === "day" || view === "threeDay") return new Date(anchor.getFullYear(), anchor.getMonth(), anchor.getDate());`
- `toRangeEnd`（`:202-207`）の `day` の行の次に: `if (view === "threeDay") return addDays(new Date(anchor.getFullYear(), anchor.getMonth(), anchor.getDate()), THREE_DAY_VIEW_DAYS);`

### 6-2 SchedulePageImpl.tsx
1. import に `THREE_DAY_VIEW_DAYS` を足す（`:39` `LIST_VIEW_DAYS,` の次）。
2. `formatRangeTitle`（`:142-148`）の `day` の行の次に:
   `if (view === "threeDay") return \`${formatDayLabel(anchorDate)} - ${formatDayLabel(addDays(anchorDate, THREE_DAY_VIEW_DAYS - 1))}\`;`
3. 近道の一覧（`:849` `{ keys: ["D"], labelKey: "day" },` の次）に `{ keys: ["X"], labelKey: "threeDay" },`
4. `:931` の次に `const [panelOpen, setPanelOpen] = useState(true);`（左の欄。保存しない）
5. `navigatePeriod`（`:1164`）: `const step = view === "day" ? 1 : view === "threeDay" ? THREE_DAY_VIEW_DAYS : view === "list" ? LIST_VIEW_DAYS : 7;`
6. `viewDays`（`:1169-1175`）の `day` の枝の次に `: view === "threeDay" ? Array.from({ length: THREE_DAY_VIEW_DAYS }, (_, i) => addDays(new Date(anchorDate.getFullYear(), anchorDate.getMonth(), anchorDate.getDate()), i))` を足す。
7. キー（`:1340` `case "d"` の次）: `case "x": setView("threeDay"); break;`
8. `:1364` `subtitleKey="schedule.subtitle"` の行を消す。その位置に:
```tsx
        headerStart={
          <Button
            variant="ghost"
            size="md"
            iconOnly
            aria-label={t("schedule.togglePanel")}
            aria-expanded={panelOpen}
            onClick={() => setPanelOpen((open) => !open)}
          >
            <NAV_ICONS.menu size={20} aria-hidden="true" />
          </Button>
        }
```
9. 切替（`:1486`）: `(["day", "threeDay", "week", "month", "list"] as const)`
10. `:1495` `<div className="schedule-shell__content">` → `<div className={panelOpen ? "schedule-shell__content" : "schedule-shell__content schedule-shell__content--panel-hidden"}>`。`<ScheduleSidebar ... />`（`:1496-1506`）を `{panelOpen && ( ... )}` で包む。
11. `:1542` → `dayCount={view === "day" ? 1 : view === "threeDay" ? THREE_DAY_VIEW_DAYS : 7}`

`NAV_ICONS.menu` の大きさの書き方（`size={20}`）は同じファイルの `NAV_ICONS.chevronDown size={16}` と同じ形。20 が直書きの検査に当たる場合は止めて `NEEDS_DECISION:`。

### 6-3 schedule.css（`.schedule-shell__content` の規則 `:57-65` の次に足す）
```css
/* 左上のメニューボタンで左の欄をしまった時は 1 列（design §3.12・G21） */
.schedule-shell__content--panel-hidden {
  grid-template-columns: minmax(0, 1fr);
}
```

## 7. 文言（ja.json・en.json の `schedule` の中・`weekView` の次）

| キー | ja | en |
|---|---|---|
| `schedule.threeDayView` | 3日間 | 3 days |
| `schedule.togglePanel` | メニュー | Main menu |
| `schedule.shortcuts.threeDay`（`shortcuts` の `day` の次） | 3日間の表示 | 3-day view |

## 8. 試験

- `CalendarView.test.tsx:290-297` T9: 12:34 → `'11:30:00'`・0:10 → `'00:00:00'`・足す 1:05 → `'00:30:00'`・足す 23:50 → `'22:30:00'`。
- `schedule-utils.test.ts`: `toRangeStart("threeDay", new Date(2026, 10, 4, 15))` が `new Date(2026, 10, 4)`、`toRangeEnd` が `new Date(2026, 10, 7)`。
- `SchedulePageImpl.test.tsx:597` の `toHaveLength(4)` → `5`。足す: (a) キー「x」で `pressed(i18n.t("schedule.threeDayView"))` が true（`:306-310` と同じ形） (b) メニューボタン（名前 `schedule.togglePanel`）を押すと `aria-expanded` が false になり、左の欄の「作成」ボタンが消え、もう一度押すと戻る (c) `.page-subtitle` が 0 個。
- 既存の試験は全部通ること。

## 9. page-title/design.md

§2 D1 の行の次に 1 行足す: `- D1 追記（2026-11-08・予定の画面 便7）: タイトルより左に置く中身の口 headerStart?: ReactNode を足した。見た目の props ではない（headerLeft と同じ種類）。`

## 10. 返事

DONE と HEAD の SHA・試験の結果の数（通った／落ちた）・lint と css 検査の結果。止めたときは `BLOCKED:` か `NEEDS_DECISION:` と理由。
