# design: fix-reanalyze-snapshot-unit-cast

## recon参照
docs/handoff/fix-reanalyze-snapshot-unit-cast/recon.md

## 変更前後
- 変更前: `ar.unit_id` (integer) → `analysis_run_snapshots.unit_id` (uuid) — 型不一致エラー
- 変更後: `NULL::uuid` → `analysis_run_snapshots.unit_id` (uuid) — 型一致

## 影響範囲
- `backend/app/services/tcg_product_master_svc.py` L614, L617 のみ
- スナップショットテーブルへの unit_id/condition_id は補助情報（NULL許容）

## 基準・検証方法

| 基準 | 検証方法 |
|------|---------|
| 再解析スクリプトがエラーなく完走する | 32ジョブ全件 success=32 / errors=0 |
| pid_resolved=false & resolved_product_code IS NOT NULL の件数が 168 → 0 付近に減少 | 本番DBでCOUNT確認 |

## 外部事例
なし（PostgreSQL型キャストの標準的修正）

## 守り手
ruff PASS済み
