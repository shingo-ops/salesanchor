# design: supersession-global-latest

**対象ADR**: [ADR-158](../../adr/ADR-158-product-level-supersession.md)
**recon**: [docs/handoff/supersession-global-latest/recon.md](./recon.md)

## 現状調査

詳細は [docs/handoff/supersession-global-latest/recon.md](./recon.md) を参照。

## 変更内容

`backend/app/services/tcg_analyzer_svc.py` の `_merge_supplier_products()` 関数のみ変更。

### 変更前後コード概要

**変更前（行1621-1651）**:
```sql
UPDATE analysis_results ar_old
SET is_current = FALSE
WHERE ...
  AND sm_old.received_at < (新ジョブの受信日時)  -- 古いメッセージのみ対象
  AND ar_old.is_current = TRUE
  AND EXISTS (新ジョブの(product_id, condition_id)ペアと一致)
```

**変更後**:
```sql
WITH touched_triples AS (既ジョブの(product_id, condition_id)ペア),
ranked AS (
    ROW_NUMBER() OVER (PARTITION BY product_id, condition_id
                       ORDER BY received_at DESC, computed_at DESC) = 1
    AS should_be_current
    -- 同一 supplier_channel_id の全行を対象
)
UPDATE analysis_results ar_target
SET is_current = ranked.should_be_current
WHERE ar_target.is_current IS DISTINCT FROM ranked.should_be_current
```

### 変更点

1. `new_product_ids` / `new_condition_ids` リストを使った `unnest()` ベースのEXISTSチェックを削除
2. `received_at < (自分の受信日時)` という方向条件を削除
3. `ROW_NUMBER() OVER (PARTITION BY ...)` による全体最新ランキングに変更
4. `IS DISTINCT FROM` で既に正しい状態の行をスキップ（無駄な書き込み防止）
5. docstring・呼び出し元コメントを新ロジックに合わせて更新

## 受入条件

| 基準 | 検証方法 |
|------|----------|
| 同一(product_id, condition_id)について、最新received_atの行のみis_current=TRUEになる | `SELECT product_id, condition_id, COUNT(*) FROM analysis_results WHERE is_current=TRUE GROUP BY 1,2 HAVING COUNT(*)>1` が0件 |
| 古いメッセージを再解析しても二重TRUEにならない | 同上 |
| is_currentが変化しない行は updated_at が更新されない | IS DISTINCT FROM 条件により保証 |
| テスト test_tcg_is_active_filter.py が PASS | pytest実行で確認 |
| test_tcg_distribution_pg.py が PASS または SKIP（DB非接続） | pytest実行で確認 |

## 外部・過去事例の参照と我々への応用

該当なし。PostgreSQL の ROW_NUMBER() CTE UPDATE は標準的なパターンであり、外部事例の参照なしに実装可能。

## 影響範囲

- 呼び出し元: `backend/app/services/tcg_analyzer_svc.py` の `analyze_extraction_job()` 内（行1565付近）のみ
- 関数シグネチャ変更なし（引数・戻り値型は同一）
- 戻り値の意味が「更新した旧行の件数」から「is_currentが変更された件数」に変わる（ログメッセージに反映済み）

## 維持の仕組み

守り手: Hikky-dev (Claude Code) — `backend/app/services/tcg_analyzer_svc.py`

- 既存テスト `backend/tests/test_tcg_is_active_filter.py` が is_current フィルタのロジックをカバー
- ログ出力を `(global-latest)` 付きに変更し、新ロジックが動いていることを確認可能
