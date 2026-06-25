# design — migrate-lead-edit-select

**仕事名**: migrate-lead-edit-select
**日付**: 2026-06-26
**対象ADR**: ADR-073
**recon**: docs/handoff/migrate-lead-edit-select/recon.md

---

## 背景・目的

ADR-073（デザインシステム KGI ルーブリック）の軸1「共通コンポーネント適用率」向上。
`LeadEditPage.tsx` の生 `<select>` 7個を `<Select>` コンポーネントへ置換し、
ページ独自スタイルを排除してデザインシステムの単一管理に収束させる。

recon での調査結果（[recon.md](docs/handoff/migrate-lead-edit-select/recon.md)）に基づく。

---

## 変更方針

- **変更スコープ**: `frontend/src/pages/leads/LeadEditPage.tsx` のみ（1ファイル）
- **移行フェーズ正典**: 1画面・1部品種・1PR を遵守
- **ページ側 CSS 上書きなし**: `Select` の標準スタイル（comp-field）をそのまま使用
- **機能変更なし**: value / onChange / options の内容は変更しない

---

## KGI / KPI

| 基準 | 検証方法 |
|------|---------|
| LeadEditPage の select 7個がすべて `<Select>` に置き換わっている | `grep -c '<select' frontend/src/pages/leads/LeadEditPage.tsx` = 0 |
| `<Select>` に `className` で独自スタイルが付いていない | `grep "lead-select\|className=" LeadEditPage.tsx` に Select 行なし |
| lint 全通過 | CI「Lint & Dark Mode Check (ADR-067)」green |
| UI governance gate 通過（select 数が増えていない） | CI「UI governance gate」green |

---

## 外部事例・過去事例

本作業は自社デザインシステム内の移行（置換）であり、外部サービス・外部APIの変更はない。
過去事例として本プロジェクトの移行フェーズ正典（2026-06-26 PO承認）を基準とする。

---

## 弊害・リスク

| リスク | 対策 |
|-------|------|
| border-radius が 4px→6px に変わる | PO 目視確認済み（GO #2599 2026-06-26）。棚の標準値への統一であり意図的変更 |
| DB 値の日本語文字列で lint エラー | `// eslint-disable-next-line local/no-japanese-literal -- DB value` コメントで除外 |
