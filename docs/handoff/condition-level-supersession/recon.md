# recon: condition-level supersession (ADR-158 補正)

## 調査対象

`_merge_supplier_products()` が product_id 単位で照合しているため、
同一商品の異なるコンディション（例: Sealed Box と Damaged Box）が
新メッセージに片方しか含まれない場合、含まれない側まで is_current=FALSE に
されてしまう問題。

## 既存ADR

- ADR-158: `docs/adr/ADR-158-product-level-supersession.md`（同一仕入元の旧 analysis_results 更新）

## 変更ファイル

- `backend/app/services/tcg_analyzer_svc.py:1573-1653`
  - `_merge_supplier_products()` 関数
  - 照合を `product_id` 単独 → `(product_id, condition_id)` ペアに変更

## 影響範囲

- 呼び出し元: `analyze_extraction_job()` のみ（同ファイル内）
- migration なし（コード変更のみ）
- DB スキーマ変更なし

## 守り手

- `backend/app/services/tcg_analyzer_svc.py` のテストがあれば影響を確認
