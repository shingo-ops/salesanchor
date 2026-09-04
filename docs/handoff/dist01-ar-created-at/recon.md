# recon — dist01 ar.created_at バグ修正

## 調査対象

DIST-01（#3250）の `GET /api/v1/tcg/distribution/preview` が 500 エラーを返す。

## 根本原因の特定

`backend/app/services/tcg_distribution_svc.py:349`

```python
# 問題箇所（修正前）:
AND ar.created_at >= NOW() - INTERVAL '30 days'
```

`tenant_004.analysis_results` に `created_at` カラムは存在しない。

### information_schema.columns 実測（2026-09-04）

実行クエリ:
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'tenant_004'
  AND table_name IN ('analysis_results', 'item_corrections')
ORDER BY table_name, ordinal_position;
```

**analysis_results の時刻カラム:**
- `computed_at` (timestamp with time zone)
- `updated_at` (timestamp with time zone)
- `created_at` → **存在しない**

**item_corrections の参照列（全件確認）:**
- `ic.id` (bigint) ✓
- `ic.extraction_item_id` (uuid) ✓
- `ic.corrected_at` (timestamp with time zone) ✓
- `ic.analysis_result_id` → 存在しない（クエリ内で未参照）

## 影響範囲

- 修正箇所: `backend/app/services/tcg_distribution_svc.py:349`（1行のみ）
- 他に `ar.created_at` を参照している箇所: なし（grep 確認済み）
- `tcg_distribution_targets.created_at` は実在する（lines 455/467/486/519 は別テーブル、問題なし）

## 修正内容

`ar.created_at` → `ar.updated_at`（1行変更）
