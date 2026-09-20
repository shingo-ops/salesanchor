# design: extraction-partial-success

## KGI

1アイテムのvalidation失敗（work_id/product_code不一致）が、抽出ジョブ全体のエラーを引き起こさない。

| 基準 | 検証方法 |
|---|---|
| validate_work_id に存在しないIDを渡すと None を返す（例外なし） | `test_validate_work_id_missing_returns_none` PASS |
| validate_product_code に存在しないコードを渡すと None を返す（例外なし） | `test_validate_product_code_missing_returns_none` PASS |
| WORK_ID_CONFLICT 発生時にジョブが `status='error'` にならない | resolved_work_id=None に設定してジョブ継続 |

## 変更内容

### 変更1: tcg_work_reference.py

- `validate_work_id`: `raise ValueError` → `logger.warning` + `return None`
- `validate_work_id`: non-integer入力の `int(value)` が TypeError/ValueError になる場合も `return None`
- `validate_product_code`: `raise ValueError` → `logger.warning` + `return None`
- `import logging` と `logger = logging.getLogger(__name__)` を追加

### 変更2: tcg_extraction.py

- WORK_ID_CONFLICT セクション: `raise RecordError("WORK_ID_CONFLICT")` → `item["resolved_work_id"] = None` + `logger.warning`
- `logger` は既に定義済み（`logger = logging.getLogger(__name__)` at line 39）

## 影響範囲

- `validate_work_id` の呼び出し元: `tcg_extraction.py` の Gemini結果処理（validate後の None は既存ロジックで処理済み）
- `validate_product_code` の呼び出し元: 同上
- `resolve_work_evidence` との組み合わせ: WORK_ID_CONFLICTをNone設定に変更しても、アナライザが search_keywords 経由でマッチングを試みる

## リスク

なし。下流（tcg_analyzer_svc.py）はすでに resolved_work_id=None と resolved_product_code=None を正常処理する実装になっている。

## ロールバック

`backend/app/services/tcg_work_reference.py` と `backend/app/tasks/tcg_extraction.py` の変更を revert するだけ。

## 外部事例

内部ロジック修正のため外部事例調査は不要。

## KPI測定方法

本番デプロイ後、`extraction_jobs` テーブルで `status='error'` かつ `error_message LIKE 'WORK_ID%'` のレコード数がゼロになることを確認。
