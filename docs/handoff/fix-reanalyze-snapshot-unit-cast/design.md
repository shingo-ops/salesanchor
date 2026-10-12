# design: fix-reanalyze-snapshot-unit-cast

## recon参照
docs/handoff/fix-reanalyze-snapshot-unit-cast/recon.md

## ADR参照
- ADR-072: write endpoint の db.commit() 直後に reset_tenant_context() 必須（本修正は同エリアの services ファイル変更）

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

## 外部・過去事例の参照と我々への応用
PostgreSQL では integer→uuid の暗黙キャストは不可。NULL::uuid は型を明示した NULL リテラルで uuid 列に安全に格納できる標準的な手法。我々への応用: スナップショット保存は補助情報のため NULL を許容しても機能に影響なし。

## 維持の仕組み
analysis_run_snapshots.unit_id / condition_id を将来 integer 型に変更する場合は、NULL::uuid キャストを ar.unit_id / ar.condition_id に戻す。inline コメントを残してあるため変更時に気づける。

守り手: ruff CI（backend/app/services/ 変更時に自動実行）
