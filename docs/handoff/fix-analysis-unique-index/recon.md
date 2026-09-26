# recon: fix-analysis-unique-index

## 問題の実測確認

### 本番DB: public.analysis_results のインデックス（実測）

```sql
SELECT indexname FROM pg_indexes
WHERE schemaname = 'public' AND tablename = 'analysis_results';
```

結果: `analysis_results_pkey` のみ（1件）

### tenant_001.analysis_results のインデックス（参照）

```sql
SELECT indexname FROM pg_indexes
WHERE schemaname = 'tenant_001' AND tablename = 'analysis_results';
```

結果: 9件（`extraction_item_id` の UNIQUE インデックス含む）

### 失敗の根拠

pipeline のコードが `ON CONFLICT (extraction_item_id)` を使用している。
UNIQUE インデックスが存在しないため `InvalidColumnReference` が発生し、全件 `ANALYSIS_FAILED`。

## 関連ファイル

- `migrations/20260923_050000_add_indexes_public_analysis_results.sql` — 修正migration
- 関連する `public` schema 移行: PR #3625 (pipeline_tables_public migration)
  - `migrations/20260921_110000_pipeline_tables_public.sql:1` — テーブル作成時にUNIQUE制約なし

## ADR参照

- ADR-072: write endpoint の db.commit() 直後のリセット
- 共用マスタSSOT方針 (project_shared_master_ssot_policy.md) — public スキーマへの統一
