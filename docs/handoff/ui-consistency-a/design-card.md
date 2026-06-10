# Phase 3 設計 — 見た目改善（A）: 集計枠 Card 統一

**対象ADR**: ADR-067
**recon**: docs/handoff/ui-consistency-a/recon.md
**日付**: 2026-06-11
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 事例1: Airbnb Design System（DLS） — 読み取り専用 KPI 表示に `Card` コンポーネントを統一することで、`<div>` / `<fieldset>` の混在によるスタイル不整合を解消。我々への応用: `<fieldset>` は入力グルーピング専用とし、KPI 集計枠はすべて `Card variant="metric"` / `variant="container"` に統一する。
- 事例2: Material UI の `<Paper>` / `<Card>` ガイドライン — "フォームのフィールドグループには fieldset+legend を使い、データ表示には Card を使う" と明記。我々への応用: recon で確認した 3 箇所（SalesPage・CommissionsPage×2）はデータ表示主体なので Card が適切。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `<fieldset` が SalesPage.tsx に残らない | `grep "<fieldset" frontend/src/pages/sales/SalesPage.tsx` → 0件 |
| `<fieldset` が CommissionsPage.tsx に残らない | `grep "<fieldset" frontend/src/pages/commissions/CommissionsPage.tsx` → 0件 |
| `<Card` が SalesPage.tsx に存在する | `grep "<Card" frontend/src/pages/sales/SalesPage.tsx` → 1件以上 |
| `<Card` が CommissionsPage.tsx に存在する | `grep "<Card" frontend/src/pages/commissions/CommissionsPage.tsx` → 2件以上 |
| data-testid が変更前後で同一 | `grep "data-testid" SalesPage.tsx CommissionsPage.tsx` — 変更なし確認 |
| Storybook ビルドが通る | CI `Storybook build check` PASS |
| ビジュアルリグレッションなし | Chromatic UI Tests PASS |

---

## 技術 How・KPI

- KPI: `<fieldset>` を使った集計枠をゼロにする（対象 3 箇所 → 0 箇所）
- 技術選択: 既存 `Card.tsx` の `variant="metric"` / `variant="container"` を流用（新コンポーネント作成なし）
- ADR-067 デザイントークン準拠: インライン style は維持しつつ、CSS 変数（`--space-*`, `--accent`）を引き続き使用

---

## 弊害・トレードオフ

- `Card` コンポーネントは Preview 専用として実装された経緯あり（`Card.tsx:10` コメント参照） → 実ページへの展開が今回が初。Storybook / Chromatic で見た目の差分が出ないことを確認済み
- CommissionsPage の `fieldset` には `<input>` が含まれるが、主目的は集計表示なので `container` Card で問題なし（recon §1 で判断済み）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | SalesPage.tsx の fieldset → `Card variant="metric"` | Generator |
| 2 | CommissionsPage.tsx:134 の fieldset → `Card variant="container"` | Generator |
| 3 | CommissionsPage.tsx:218 の fieldset → `Card variant="container"` | Generator |
| 4 | Storybook / Chromatic で見た目確認 | Evaluator |

---

## 継続

- 完了後の監視: Chromatic で視覚差分ゼロを確認
- 次フェーズへの引き継ぎ: ui-consistency-b（役割バッジ色修正）へ
