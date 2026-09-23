# Recon: extraction_items.resolved_work_id 型修正

## 問題

extraction_items.resolved_work_id が UUID 型（本番のみ・手動変更の痕跡）だが、
master SSOT Phase 2 で work_id が INTEGER に変更されたため型不一致で INSERT 失敗。

## 事実

- マイグレーション定義 (20260912_020000): INTEGER
- 本番DB: UUID
- 影響: 324 件の extraction_jobs が pending のまま停滞
- 旧UUID値: 3,971行（廃止 tcg_series への参照・無効）
- 対象スキーマ: tenant_001, tenant_004
