# design — tcg-is-active-filter (IMP-35)

## 目的

再アップロード後に旧 `source_messages`（`is_active = FALSE`）が集計に混入する二重計上バグを修正する。
ADR-154 が定義する TCG LINE インポートパイプラインの supersede 仕組みに対応した読み取り側フィルタを追加する。

## 変更内容

### 変更 1: `backend/app/services/tcg_supplier_quality_svc.py:47` — 品質サマリー集計

```sql
-- 修正前
LEFT JOIN {TCG_SCHEMA}.analysis_results ar ON ar.extraction_item_id = ei.id
GROUP BY sc.id, ts.code, ts.name

-- 修正後
LEFT JOIN {TCG_SCHEMA}.analysis_results ar ON ar.extraction_item_id = ei.id
WHERE sm.is_active = TRUE
GROUP BY sc.id, ts.code, ts.name
```

### 変更 2: `backend/app/services/tcg_supplier_quality_svc.py:82-83` — 仕入元原文取得

```sql
-- 修正前
WHERE ts.code = :supplier_id
ORDER BY sm.id

-- 修正後
WHERE ts.code = :supplier_id
  AND sm.is_active = TRUE
ORDER BY sm.received_at DESC NULLS LAST
```

`ORDER BY sm.received_at DESC NULLS LAST` は最新メッセージを確実に取得するため。
旧: `ORDER BY sm.id` は UUID のため挿入順保証なし。

### 変更 3: `backend/app/services/tcg_distribution_svc.py:228-229` — 配布出力行取得

```sql
-- 修正前
JOIN {TCG_SCHEMA}.source_messages sm
    ON sm.id = ej.source_message_id

-- 修正後
JOIN {TCG_SCHEMA}.source_messages sm
    ON sm.id = ej.source_message_id AND sm.is_active = TRUE
```

### 変更 4: `backend/app/services/tcg_analysis_review_svc.py:35` — 解析レビュー共通 FROM 句

```sql
-- 修正前
JOIN {TCG_SCHEMA}.source_messages sm ON sm.id = ej.source_message_id

-- 修正後
JOIN {TCG_SCHEMA}.source_messages sm ON sm.id = ej.source_message_id AND sm.is_active = TRUE
```

`_BASE_FROM` f-string はこのサービス内の全クエリ（count / providers / items）に共有されるため、
1 箇所の修正で 3 クエリすべてに適用される。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 静的テスト `test_source_messages_sql_always_filters_is_active` が GREEN | `pytest backend/tests/test_tcg_is_active_filter.py -v` |
| 3 サービスの全 source_messages 参照 SQL に `is_active = TRUE` が存在する | 上記テストが担保 |
| CI（backend-lint / pytest-backend）が通過する | PR checks |

## 外部・過去事例の参照と我々への応用

PostgreSQL soft-delete パターンでは `WHERE deleted_at IS NULL` または `WHERE is_active = TRUE` を
JOIN 条件または WHERE 句に含めるのが標準慣習（Django QuerySet の soft-delete、Laravel の SoftDeletes 等）。

本リポジトリでは `source_messages.is_active = FALSE` が supersede 時の soft-delete に相当する。
GAS 実装では `is_active` フィルタが JOIN 条件に組み込まれていたが、
Python 移行時に抜け落ちた（IMP-32 で判明）。

**応用**: `source_messages` を参照する SQL は必ず JOIN 条件か WHERE 句に `is_active = TRUE` を含める。
`backend/tests/test_tcg_is_active_filter.py` がこれを静的に保証する。

## 維持の仕組み

守り手: backend/tests/test_tcg_is_active_filter.py（静的解析テスト・DB 接続不要）

将来 `source_messages` を JOIN する SQL を追加した際、`is_active = TRUE` フィルタを忘れると
`test_source_messages_sql_always_filters_is_active` が RED になる。

## 参照

- IMP-32 recon: docs/handoff/tcg-is-active-filter/recon.md
- ADR-154: docs/adr/ADR-154-tcg-parity02-gas-python-migration.md
- FK 順序修正 recon（supersede 仕組み詳細）: docs/handoff/tcg-import-fk-order-fix/recon.md
