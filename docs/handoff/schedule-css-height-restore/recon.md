# Recon — schedule-css-height-restore

**日付**: 2026-06-23
**担当**: Hikky-dev
**design**: docs/handoff/schedule-css-height-restore/design.md

---

## 問題の特定

### 調査対象ファイル

- `frontend/src/pages/schedule.css` — schedule ページ専用スタイル（復元対象）
- `frontend/src/pages-layout.css` — 共通ページレイアウト（P0=PR#2486で確定済み・不触）
- `frontend/src/topbar.css` — `.app-content` 定義（参照のみ）

### ユーザー報告 3 課題

| # | 課題 | CSS 現状（origin/main） |
|---|------|------------------------|
| 1 | カレンダーが「折りたたまれている」 | `frontend/src/pages/schedule.css` に `.schedule-grid__viewport` の定義が存在しない → `overflow-y: auto` なし・高さ未拘束 |
| 2 | 左メニューとページ本体の間に余白がない | `frontend/src/pages/schedule.css:22` の `.schedule-page` に `padding` なし → ヘッダー・本体が左端に密着 |
| 3 | ヘッダーが他ページと不揃い | `frontend/src/pages/schedule.css:29` の `.schedule-shell__header` に `padding-right` なし → アバタークリアランスなし |

---

## 因果特定（git log -p -S で確定）

### `schedule-grid__viewport` が「消えた」経緯

```
PR #2432 (7c5a5ea2, 2026-06-21)
  → schedule.css に height:100% + viewport ブロック + 高さチェーン一式を追加
  → この時点で 3 課題はすべて解消していた（正常状態）

PR #2453 (f5ea8ec7, 2026-06-22 08:41 JST, merge: 27642d33)
  → schedule.css から 6 プロパティ群を削除 ← 再発原因
  → SchedulePage.tsx を 519 行版に大改修（同時変更）

PR #2472 (2026-06-22, revert)
  → SchedulePage.tsx 等を #2443 状態へ revert
  → schedule.css は対象に含めず → 修正漏れで壊れたまま現在に至る
```

### PR #2453 が削除した内容（file:line @ 7c5a5ea2 の正常値）

**`.schedule-page` (`frontend/src/pages/schedule.css:22`、現行）/ schedule.css:42-49 @ 7c5a5ea2（正常値）**
```css
height: 100%; /* fill .app-content so page-level overflow-y never fires */
padding: var(--page-padding-y) var(--page-padding-x); /* 他ページ共通ガター */
```
→ PR #2453 で削除。現在: `min-height: 0` のみ（高さ未拘束・余白ゼロ）。

**`.schedule-shell__header` (`frontend/src/pages/schedule.css:29`、現行）/ schedule.css:53-54 @ 7c5a5ea2（正常値）**
```css
padding-right: var(--page-header-avatar-clearance); /* #7: 固定アバターとのクリアランス 68px */
```
→ PR #2453 で削除。現在: なし。

**`.schedule-shell__content` (`frontend/src/pages/schedule.css:148`、現行）/ schedule.css:180-188 @ 7c5a5ea2（正常値）**
```css
grid-template-rows: 1fr; /* fill all remaining height so .schedule-main can stretch */
flex: 1;                 /* consume remaining height in .schedule-page flex column */
align-items: stretch;    /* .schedule-sidebar keeps align-self:start; .schedule-main fills cell */
```
→ PR #2453 で `grid-template-rows`/`flex` 削除、`align-items` を `start` に格下げ。

**`.schedule-main` (`frontend/src/pages/schedule.css:324`、現行）/ schedule.css:351-353 @ 7c5a5ea2（正常値）**
```css
min-height: 0; /* allow flex children to shrink within the constrained grid cell */
```
→ PR #2453 で削除。

**`.schedule-main__surface` (`frontend/src/pages/schedule.css:331`、現行）/ schedule.css:359-364 @ 7c5a5ea2（正常値）**
```css
flex: 1; /* fill .schedule-main flex column */
```
→ PR #2453 で削除。

**`.schedule-grid__viewport` (`frontend/src/pages/schedule.css`、現行は定義なし）/ schedule.css:431-434 @ 7c5a5ea2（正常値）— ブロックごと消えた**
```css
/* scroll container: only the time body scrolls */
.schedule-grid__viewport {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
```
→ PR #2453 でブロックごと削除。現在: CSS 定義なし（JSX の `className` だけが残る）。

---

## P0（PR #2486）との独立性確認

- `schedule.css` は `--topbar-height` を**一切参照しない**（grep 結果: 0 件）。
- P0 は `pages-layout.css` の `.page-layout-header` から `position:sticky` 等を除去した変更。
- 本件の復元は `schedule.css` のみ。`pages-layout.css` は **触らない**。

---

## 現行 schedule.css 状態確認

### `.schedule-page` (`frontend/src/pages/schedule.css:22`)
```css
.schedule-page {
  display: flex;
  flex-direction: column;
  gap: var(--schedule-shell-gap);
  min-height: 0;
}
```
→ `height: 100%` なし、`padding` なし。

### `.schedule-shell__header` (`frontend/src/pages/schedule.css:29`)
```css
.schedule-shell__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding-bottom: var(--space-1);
}
```
→ `padding-right` なし。

### `.schedule-shell__content` (`frontend/src/pages/schedule.css:148`)
```css
.schedule-shell__content {
  display: grid;
  grid-template-columns: var(--schedule-leftpanel-width) minmax(0, 1fr);
  gap: var(--schedule-shell-gap);
  min-height: 0;
  align-items: start;
}
```
→ `grid-template-rows`/`flex: 1` なし、`align-items: start`（格下げ状態）。

### `.schedule-grid__viewport`（`frontend/src/pages/schedule.css` に定義なし）
→ **CSS 定義なし**（origin/main の schedule.css 全行 grep で 0 件）。
→ JSX の `className` は `frontend/src/pages/schedule/SchedulePageImpl.tsx:1205` に残存。

---

## 関連 ADR

- **ADR-067**: デザイントークン強制。復元する値はすべて既存トークン参照（hex/直値の追加なし）。
- **先行 P0**: PR #2486（`pages-layout.css` sticky 除去）— 本件と独立。
