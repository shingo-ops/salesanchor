# design: 空の mark・english_title を NULL で保存する

## 方針
- backend/app/services/tcg_product_detail_svc.py の update_product_detail で、UPDATE に渡す mark・english_title を strip 後に空なら None にする（新規作成・tcg_product_master_svc.py:418-419 と同じ表し方）
- ProductDetailUpdate の型・frontend は変えない（frontend は '' を送ってよい）
- 触らない: API の型、新規作成、CSV 取り込み、migration

## 基準と検証方法

|基準|検証方法|
|---|---|
| 空文字・空白だけで保存すると mark・name_en が NULL になり、応答も null | backend/tests/test_tcg_product_detail_pg.py::test_empty_mark_and_english_title_are_saved_as_null_and_values_kept（PG・CI） |
| 値ありはそのまま保存される | 同上 |
| 既存の detail 試験が全て通る | backend/tests/test_tcg_product_detail_pg.py 全体（CI） |

## 外部事例
該当なし（理由: 既存の保存経路の値の正規化のみで、新しい方式を導入しないため）。

## 弊害・トレードオフ
- 旧データの '' は保存時に1回 NULL になり、audit_log にその差が出る

## 維持の仕組み
- 守り手: test_tcg_product_detail_pg.py

## 戻し方
- この PR を revert する

## 継続
- マージ後、PR #4073（除外ワード追加）が mark を '' に戻さないことを確認
