# Phase 3 設計 — DataTable Step 2（onRowClick + controlled pagination）

**対象ADR**: ADR-122  
**recon**: docs/handoff/datatable-step2/recon.md  
**日付**: 2026-06-09  
**担当**: Generator

---

## 外部・過去事例の参照と我々への応用

- shadcn/ui、Mantine、TanStack Table はすべて `onRowClick` を optional props で提供しており、未指定時は cursor/event handler を追加しない後方互換パターンが標準。
- ページネーションは「内部状態（クライアントサイド）vs 外部制御（サーバーサイド）」の 2 モデルが主流。SuppliersPage はサーバー側でページを制御するため controlled モデル（`page/hasNextPage/onPageChange`）を採用する（MUI DataGrid の controlled pagination と同方針）。
- セル内インタラクティブ要素の二重発火防止（`closest()` ガード）は React テーブルの定番パターン（Radix UI・Headless UI 等でも推奨）。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `onRowClick` 未指定時に既存テーブルの表示・動作が変わらない | 既存 Storybook / Playwright スナップショット差分なし |
| `onRowClick` 指定時に行クリックでコールバックが発火する | DesignPreviewPage デモで動作確認 |
| セル内ボタンクリック時に `onRowClick` が二重発火しない | `isInteractiveTarget()` ガード確認（DesignPreviewPage デモ） |
| Enter/Space キーで `onRowClick` が発火する（アクセシビリティ） | キーボード操作確認 |
| `onPageChange` 指定時のみページネーション UI が表示される | DesignPreviewPage デモ（2件/ページ確認） |
| TypeScript 型エラーなし | `tsc --noEmit` PASS |
| 既存の DataTable props（columns/data/selectable/density等）は変更なし | コードレビュー + CI |

---

## 技術 How・KPI

- KPI: DataTable に `onRowClick` + `page/hasNextPage/onPageChange` を追加。既存 props への破壊的変更ゼロ
- `isInteractiveTarget(e: React.MouseEvent | React.KeyboardEvent)`: `(e.target as HTMLElement).closest('button, a, input, select, textarea, label')` で二重発火防止
- ページネーション UI: `comp-table__pagination` CSS クラス。`var(--primary)` / `var(--border)` / `var(--space-3)` トークン使用

---

## 弊害・トレードオフ

- `onRowClick` + `selectable` 同時使用時: チェックボックス列クリックが `isInteractiveTarget()` ガードで止まる（`label` タグが対象）→ チェックボックス選択は正常動作、行クリックは発火しない。仕様として適切
- ページネーション UI はシンプル（前/次ボタン + ページ情報のみ）。件数表示・ジャンプ機能は要望が来てから追加

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `DataTable.tsx` に `onRowClick` / pagination props 追加 | Generator |
| 2 | `DataTable.css` にクリッカブル行・ページネーション スタイル追加 | Generator |
| 3 | `DesignPreviewPage.tsx` に §9 デモ追加（onRowClick + pagination） | Generator |

---

## 継続

- Step 3（SuppliersPage への DataTable 適用）: #1841 + #1847 マージ後に実施
- 残 25 件のページは Step 3 バッチで順次適用
