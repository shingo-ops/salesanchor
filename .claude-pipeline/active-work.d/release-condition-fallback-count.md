---
title: 解析精度管理「状態未解決」列の実数値化
branch: release/condition-fallback-count
status: IN_PROGRESS
blocked_by: PR #3881 レビュー・CI・GO記録待ち
created: 2026-09-27
updated: 2026-09-30
---

| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | main | 備考 |
|-----------|--------------|---------|------|-----|------|------|
| release/condition-fallback-count | 解析精度管理「状態未解決」列の実数値化 | 2026-09-30 17:12 | DONE | 3881 | | |

## 概要
管理画面 > LINE解析 > 解析精度管理の「状態未解決」列が全仕入先で「集計準備中」と表示される。
バックエンドが `condition_fallback_count: None` を固定返却しているため。
SAアプリ内に `analysis_results.condition_basis` として判定データが全件あるため、集計可能。

## 現状
- 原因特定済み: `backend/app/services/tcg_supplier_quality_svc.py:60` の `None` 固定
- 設計審査（2026-09-30）: 旧案C/Dは不成立（手動レビューで condition_basis が `MANUAL_CONDITION_REVIEW` に上書きされるため C=A）→ 案D' に修正
- PO選択（2026-09-30）: 案D'「3列で確定」（状態未解決／うち完全お手上げ／人が確認済み）
- 設計: `docs/handoff/condition-fallback-count/design.md`
- 調査: `docs/handoff/condition-fallback-count/recon.md`
- worktree: `/Users/tanizawashingo/worktrees/salesanchor/release-condition-fallback-count`

- PO実装承認（2026-09-30）→ 実装済み・PR #3881 起票・Reviewer APPROVE

## 次の一手
1. CI 全緑・Evaluator 確認
2. GO記録（ADR-1003 委任）→ マージ → 本番デプロイ
3. 本番で照合SQLと集計関数の値を比較（design.md 受入条件）
