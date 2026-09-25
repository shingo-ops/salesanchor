# design: fix-supersession-timestamp-order

## 対象ADR
ADR-158

## 修正方針

`_merge_supplier_products()` のステップ3 UPDATE クエリに、
`sm_old.received_at < (現在ジョブの received_at)` 条件を追加する。

これにより UPDATE 対象を「自分より古いメッセージ由来の行」に限定し、
古いメッセージの再解析が新しいメッセージの結果を上書きしないようにする。

## 変更箇所

`backend/app/services/tcg_analyzer_svc.py:1631` の `ei_old.extraction_job_id != :job_id` 行の直後に追加:

```sql
AND sm_old.received_at < (
    SELECT sm2.received_at
    FROM {schema}.extraction_jobs ej2
    JOIN {schema}.source_messages sm2 ON sm2.id = ej2.source_message_id
    WHERE ej2.id = :job_id
)
```

## KGI/KPI（観測可能な判定基準）

| 基準 | 検証方法 |
|------|---------|
| 古いメッセージ再解析後、新しいメッセージ由来の `is_current=TRUE` 行が消えない | 本番DBで `SELECT product_id, condition_id, COUNT(*) FROM tenant_004.analysis_results WHERE is_current=TRUE GROUP BY 1,2 HAVING COUNT(*)>1` が返す行数が変わらないこと |
| 新しいメッセージ解析時は従来どおり古い行が `is_current=FALSE` になる | 新メッセージ解析後に旧行の `is_current` が FALSE になることを確認 |

## 影響範囲

- 変更: `backend/app/services/tcg_analyzer_svc.py` の `_merge_supplier_products()` のみ
- 配信クエリ（`is_current=TRUE` を参照する側）は変更なし
- migration: なし

## 外部・過去事例の参照と我々への応用

PostgreSQL の UPDATE ... FROM ... WHERE サブクエリで「より新しい行を除外する」パターンは
時系列データの supersession 実装で一般的なアプローチ。
`received_at` による時刻比較はインデックスが `source_messages(received_at)` に存在すれば
追加コストは軽微。本案件では1ジョブあたり1回のみ実行されるため性能影響は無視できる。

## 維持の仕組み

- 守り手: ADR-158 の実装レビュー時に `_merge_supplier_products()` の UPDATE 条件に `received_at` 比較が含まれているか確認
- 将来の変更時は「古いメッセージ再解析シナリオ」をテストケースに含めること
