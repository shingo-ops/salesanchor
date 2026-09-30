---
title: 解析精度管理「状態未解決」列の実数値化
branch: release/condition-fallback-count
status: DESIGN_DONE
blocked_by: PO実装承認待ち（カード: docs/handoff/condition-fallback-count/card.md）
created: 2026-09-27
updated: 2026-09-30
---

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

## 次の一手
1. 設計書確定・実装カード起票（設計担当）
2. PO の実装承認
3. Sonnet 実装（BE集計3本・FE列2本・i18n・pytest）
