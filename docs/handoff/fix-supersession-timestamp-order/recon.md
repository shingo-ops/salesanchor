# recon: fix-supersession-timestamp-order

## 対象ADR
- ADR-158（商品×コンディション単位の差分更新 / supersession）

## バグ所在

`backend/app/services/tcg_analyzer_svc.py:1573-1655`

`_merge_supplier_products()` のステップ3 UPDATE クエリ（同ファイル:1622-1652）が
`source_messages.received_at` を考慮していない。

## バグ発現条件

古いメッセージを再解析（`extraction_job` を再作成）したとき、
同一 `supplier_channel_id` かつ同一 `(product_id, condition_id)` ペアを持つ
**全** `analysis_results`（新しいメッセージ由来のものも含む）が `is_current=FALSE` になる。

## 該当コード（修正前）

`backend/app/services/tcg_analyzer_svc.py:1631-1636`:

```sql
WHERE ar_old.extraction_item_id = ei_old.id
  AND sm_old.supplier_channel_id = :channel_id
  AND ei_old.extraction_job_id != :job_id
  AND ar_old.is_current = TRUE
  AND EXISTS (...)
```

`ei_old.extraction_job_id != :job_id` のみで他ジョブを除外しているが、
そのジョブのメッセージが現在ジョブより新しいか古いかを判定していない。
