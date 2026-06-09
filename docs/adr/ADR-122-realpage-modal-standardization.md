# ADR-122: 実ページ標準部品化（Modal コンポーネントへの移行）

- **Status**: Accepted
- **Date**: 2026-06-09
- **Deciders**: shingo-ops（PO）, Hikky-dev（Dev）

## Context

recon（`docs/handoff/realpage-standardization/recon.md`）で確認した通り、  
38実ページに `<div className="modal-overlay">` の raw div モーダルが **31件**存在し、  
標準 Modal コンポーネント（`frontend/src/components/Modal.tsx`）の実ページ採用数は **0**。

Modal コンポーネントは Task 7C で設計・実装済みだが、実ページへの移行が行われていなかった。  
raw div モーダルには以下の欠如がある:
- Esc キー閉鎖なし
- フォーカストラップなし（Tab がモーダル外に逃げる）
- a11y 属性なし（`role="dialog"` / `aria-modal` / `aria-labelledby`）
- フォーカス復帰なし（閉じた後に元の要素にフォーカスが戻らない）

また調査時に `Modal.css` のバグも発見:  
`background: var(--surface-primary)` → `--surface-primary` は未定義トークン（正しくは `--bg-surface`）。

## Decision

1. **Modal.css のバグ修正**: `var(--surface-primary)` → `var(--bg-surface)`
2. **TeamsPage をパイロット**として `modal-overlay` × 2 を `Modal` コンポーネントに置換
3. **置換テンプレ**を確立し、順次他24ファイルへ展開（各PR個別）
4. `ConfirmModal` は既存の動作に影響しないため今回は対象外（別ADRで検討）

## Consequences

- **Good**: a11y・Esc・フォーカストラップが全モーダルで標準化される
- **Good**: モーダルの見た目ロジックが1コンポーネントに集約
- **Neutral**: Modal のヘッダに X（閉じる）ボタンが追加される → 既存の「キャンセル」ボタンと併存
- **Risk**: `var(--bg-surface)` vs `var(--bg-surface)` の視覚差分。Evaluator で確認必須

## Migration Plan

| ステップ | 内容 |
|---------|------|
| Step 1（本PR）| Modal.css バグ修正 ＋ TeamsPage パイロット（2件） |
| Step 2〜N | 他24ファイルを同テンプレで順次置換（各PR） |
| 最終 | ConfirmModal も Modal コンポーネントベースに移行（別ADR） |
