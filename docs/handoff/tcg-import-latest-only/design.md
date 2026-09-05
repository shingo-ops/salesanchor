# design — tcg-import-latest-only (SQR-05 移植)

参照: docs/handoff/tcg-import-latest-only/recon.md
ADR 参照: ADR-154

## KGI / 検証基準

| 基準 | 検証方法 |
|------|---------|
| `build_provider_entries` が同一仕入元の複数メッセージのうち最新1件のみを `raw_text` に採用する | `pytest backend/tests/test_tcg_line_import.py::test_build_latest_only_with_three_messages` PASS |
| `skipped_message_count` フィールドが棄却件数を正しく返す | `pytest backend/tests/test_tcg_line_import.py::test_build_skipped_message_count_single` PASS |
| 既存テストが全件 PASS | `pytest backend/tests/test_tcg_line_import.py --no-cov` 31 passed |

## 外部・過去事例の参照と我々への応用

GAS 側の tcg-inventory-parser で 2026-08-30 に SQR-05（PR #279）として
「仕入元ごとに最新メッセージのみ採用」へ変更済み。本PRはその移植であり、
Python 版が SQR-05 以前の全件結合ロジックのまま残っていた乖離を解消する。

## 修正方針

GAS SQR-05（PR #279）の変更を Python 版に移植する。

### 変更箇所

**`backend/app/services/tcg_line_import_svc.py`**

`build_provider_entries`（line 221）:

```python
# 変更前
raw_text = _MSG_SEPARATOR.join(m["body"] for m in sorted_msgs)

# 変更後
latest_msg = sorted_msgs[-1]
raw_text = latest_msg["body"]
skipped_message_count = len(sorted_msgs) - 1
```

戻り値に `"skipped_message_count": skipped_message_count` を追加。

`import_line_export`:
- step4 後に `skipped_message_count = sum(e["skipped_message_count"] for e in provider_entries)` を追加
- `already_imported` / `imported` 両方の戻り値 dict に `"skipped_message_count"` を追加

**`backend/app/routers/tcg_line_import.py`**

`ImportResultResponse` に `skipped_message_count: int` フィールドを追加（GAS の skippedMessageCount に対応）。

### 戻し方

`sorted_msgs[-1]["body"]` → `_MSG_SEPARATOR.join(m["body"] for m in sorted_msgs)` に戻す（1行）。
`ImportResultResponse.skipped_message_count` を削除。
ただし本修正が正しい対応であり revert 不要。

## 維持の仕組み

守り手: `backend/tests/test_tcg_line_import.py` の
test_build_latest_only_with_three_messages / test_build_skipped_message_count_single
（同一仕入元の複数メッセージから最新1件のみが採用されることを検証、CI pytest で毎PR実行）
