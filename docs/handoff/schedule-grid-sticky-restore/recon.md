# Recon — schedule-grid-sticky-restore

**日付**: 2026-06-23
**担当**: Hikky-dev
**design**: docs/handoff/schedule-grid-sticky-restore/design.md

---

## 問題の特定

### 調査対象ファイル

- `frontend/src/pages/schedule.css` — schedule ページ専用スタイル（復元対象）
- `frontend/src/pages/schedule/SchedulePageImpl.tsx:1205` — `schedule-grid__viewport` JSX 定義（参照のみ）
- `frontend/src/pages/schedule/SchedulePageImpl.tsx:602` — `schedule-grid__header` JSX 定義（参照のみ）
- `frontend/src/pages/schedule/SchedulePageImpl.tsx:623` — `schedule-grid__allday-row` JSX 定義（参照のみ）

### ユーザー報告の課題

P1a（PR #2496）後も「日付行・終日行ごと全部スクロール」が継続。本来は日付ヘッダー・終日行は固定、時間グリッドのみスクロールのはず。

---

## 因果特定（git show / git diff で確定）

### スクロール2段構造

JSX 親子関係（`7c5a5ea2` と現在 `3ee2338e` で**完全一致・変更なし**）:

```
schedule-grid__viewport（スクロール容器 overflow-y:auto）
  └── ScheduleWeekGrid
        └── schedule-grid（flex-col）
              ├── schedule-grid__header  ← sticky 固定対象（欠落）
              ├── schedule-grid__allday-row ← sticky 固定対象（欠落）
              └── schedule-grid__body（通常フロー・スクロールされる）
```

### P1a で復元済みの外側チェーン

- `frontend/src/pages/schedule.css:409` — `.schedule-grid__viewport { flex:1; min-height:0; overflow-y:auto }`（P1a=PR #2496 で復元済み）

### 本件で欠落している内側 sticky

**欠落 (1): CSS 変数3個**（現行 `3ee2338e:schedule.css:19` の `--schedule-control-border` 直後が閉じ括弧）

| 変数 | 正常値（`7c5a5ea2:schedule.css:36-39`） | 現行 |
|------|----------------------------------------|------|
| `--schedule-day-head-h` | `82px` | **未定義** |
| `--schedule-header-z` | `2` | **未定義** |
| `--schedule-allday-z` | `1` | **未定義** |

スコープ: `.schedule-page, .schedule-settings { }` ブロック内（`:root` ではない）

**欠落 (2): `.schedule-grid__header` の sticky 宣言**

現行（`3ee2338e:schedule.css:428-430`）:
```css
.schedule-grid__header {
  border-bottom: 1px solid var(--schedule-cell-border);
}
```

正常値（`7c5a5ea2:schedule.css:450-456`）:
```css
.schedule-grid__header {
  border-bottom: 1px solid var(--schedule-cell-border);
  position: sticky;
  top: 0;
  z-index: var(--schedule-header-z);
  background: var(--bg-surface);
}
```

**欠落 (3): `.schedule-grid__allday-row` の sticky 宣言**

現行（`3ee2338e:schedule.css:495-498`）:
```css
.schedule-grid__allday-row {
  min-height: var(--schedule-allday-row-h);
  border-bottom: 1px solid var(--schedule-cell-border);
}
```

正常値（`7c5a5ea2:schedule.css:523-529`）:
```css
.schedule-grid__allday-row {
  min-height: var(--schedule-allday-row-h);
  border-bottom: 1px solid var(--schedule-cell-border);
  position: sticky;
  top: var(--schedule-day-head-h);
  z-index: var(--schedule-allday-z);
  background: var(--bg-surface);
}
```

---

## 削除経緯（git diff で確定）

- `#2453`（`f5ea8ec7`, 2026-06-22）: P1a で対象にした高さチェーン6プロパティと**同時に**、この sticky 一式も削除。
- `PR #2472`（2026-06-22, revert）: JSX を #2443 状態へ revert したが `schedule.css` は対象外。
- `PR #2496`（P1a, 2026-06-23）: 高さチェーン外側6プロパティのみ復元。内側 sticky は未復元のまま。

---

## P0・P1a との独立性確認

- `schedule.css` は `--topbar-height` を参照しない（P0 = PR #2486 との干渉なし）。
- 本件の復元は `schedule.css` のみ。`pages-layout.css` は **触らない**。
- JSX 構造（`SchedulePageImpl.tsx:602,623,1205`）は変更なし。CSS 追加のみ。

---

## 関連 ADR

- **ADR-067**: デザイントークン強制。追加する値はすべて既存トークン参照（`var(--bg-surface)`, `var(--schedule-header-z)` 等）または #2432 確定値（`82px/2/1`）。hex/直値の独自追加なし。
- **先行 P0**: PR #2486（`pages-layout.css` sticky 除去）— 本件と独立。
- **先行 P1a**: PR #2496（`schedule.css` 高さチェーン復元）— 本件の前提。
