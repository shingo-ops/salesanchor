# Recon: 在庫集計テスト用データの仕入元名を仮名に置き換える

実名は書かない。件数のみ記録する（PO 判断 2026-10-01：仕入元データは社外秘）。
実名と仮名の対応表は repo の外にだけ置く。

## 既存 ADR の検索結果

`git grep -i` で `docs/adr/` を「fixture」「匿名」「仮名」「社外秘」で確認。この変更を直接定めた ADR は無い。根拠は PO 判断（2026-10-01、2026-10-13 の y）。

## 事実

- `backend/tests/fixtures/inventory_aggregation/` に CSV が4本ある（repo は PUBLIC）。
  - `ver41_output.csv`：入力。142行（ヘッダー含む）・18列
  - `ver41_aggregation.csv`：期待値。95行（ヘッダー含む）・18列
  - `notetrack_output.csv`：6行・19列
  - `notetrack_aggregation.csv`：4行・19列
- 「提供者」列の仕入元名：ver41 の2本に合計11種類。notetrack の2本は `TEST_A` / `TEST_B` / `TEST_C`（テスト用の仮名と判断できるため対象外）。
- 置き換え対象の行数：`ver41_output.csv` 141行、`ver41_aggregation.csv` 94行。
- 実名は4本の CSV の「提供者」列以外（Note_JA・Note_EN・採用理由・除外理由 等）には出ていない（列ごとに部分一致で数えて 0 件）。
- CSV 以外の repo 内文書にも実名が出ている。場所と件数は PR 本文の報告に記す（本文書には実名の手がかりになる情報は書かない）。今回は置き換えない。
- CSV を読むテスト：`backend/tests/test_inventory_aggregation.py:13`（`FIXTURE_DIR`）、同 `:59` の `test_aggregate_inventory_offers_golden`、`test_aggregate_inventory_offers_note_track_golden`。
- テストでの「提供者」の使われ方：`backend/tests/test_inventory_aggregation.py:24` の `_projection` で `supplier_name` として期待値に含め、実際の集計結果と文字列で完全一致を比較する。
- 集計コードでの使われ方：`backend/app/services/inventory_aggregation.py:272`・`:292`・`:373` で、価格と数量が同じ場合の並び順の最終タイブレーク（`supplier_name`、その次が入力順）にだけ使う。集計キー（`Series`・`Condition`・`Note_JA`）には使わない。

## 変更前の基準

`cd backend && python3 -m pytest tests/test_inventory_aggregation.py -v --no-cov`：3 passed, 1 skipped（skipped は PostgreSQL が必要なテスト）。
