# PARITY-03 バッジ色付�� — design.md

**対象ADR**: ADR-067
**recon**: docs/handoff/parity03-badge-colors/recon.md
**日付**: 2026-09-03
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- ADR-067（デザイントークン強制）: CSS 直値禁止、`var(--xxx)` 必須。
- GAS `reviewIssues.ts` の tone 定義: `danger`（赤）/ `warning`（黄）が issue severity を示す。
- 既存 `badge-lost`（danger-bg/text）/ `badge-open`（warning-bg/text）が同系トークンを使用済み → 同パターンで追加。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `badge-warning` が warning-bg/text で表示される | SupplierDetailView バッジ目視確認 |
| `badge-danger` が danger-bg/text で表示される | SupplierDetailView バッジ目視確認 |
| ADR-067 トークン使用（直値なし） | `grep -n "badge-warning\|badge-danger\|badge-success" frontend/src/components.css` で var() のみ確認 |
| CSS hex 増加ゼロ | CI「デザイントークン ラチェット」green |

---

## 技術 How・KPI

- KPI: CI 全チェック PASS / デザイントークンラチェット green
- 変更箇所: `frontend/src/components.css` に 4 行追加（コメント1行 + クラス3行）
- トークン対応表:
  - `warning` → `var(--warning-bg)` / `var(--warning-text)`
  - `danger` → `var(--danger-bg)` / `var(--danger-text)`
  - `success` → `var(--success-bg)` / `var(--success-text)`

---

## 弊害・トレードオフ

- `badge-warning` / `badge-danger` 追加後、他のコンポーネントで誤用される可能性がある → StatusBadge.tsx のコメントで用途を限定済み（`status-ssot-exempt: review issue tone`）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `components.css` に 3 クラス追加 | Dev |
| 2 | CI green 確認 | Dev |
| 3 | PO GO → merge | PO |
